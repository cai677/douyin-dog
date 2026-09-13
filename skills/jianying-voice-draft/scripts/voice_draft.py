from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import shutil
import subprocess
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parents[1]
LARK_CLI = Path(
    r"C:\Users\Administrator\.workbuddy\binaries\node\cli-connector-packages\node_modules\@larksuite\cli\bin\lark-cli.exe"
)
JY_DRAFT_ROOT = Path(r"C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft")
TTS_ENDPOINT = "https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse"
DEFAULT_RESOURCE_ID = "volc.service_type.10029"


@dataclass(frozen=True)
class ShotLine:
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return self.end - self.start


def strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value)
    return html.unescape(text).strip()


def parse_time_range(value: str) -> tuple[float, float]:
    clean = strip_tags(value).replace("\u79d2", "s").replace("\u2013", "-").replace("\u2014", "-")
    match = re.search(r"(\d+(?:\.\d+)?)\s*s?\s*-\s*(\d+(?:\.\d+)?)\s*s?", clean, flags=re.I)
    if not match:
        raise ValueError(f"Cannot parse time range: {value!r}")
    return float(match.group(1)), float(match.group(2))


def extract_section(content: str, title_pattern: str) -> str | None:
    match = re.search(title_pattern, content)
    if not match:
        return None
    next_heading = re.search(r"\n\s*#{1,6}\s*[一二三四五六七八九十]+[、.．]", content[match.end() :])
    if next_heading:
        return content[match.end() : match.end() + next_heading.start()]
    return content[match.end() :]


def extract_tables(content: str) -> list[str]:
    tables = re.findall(r"<table\b.*?</table>", content, flags=re.S)
    return tables if tables else [content]


def extract_lines_from_tables(tables: list[str]) -> list[ShotLine]:
    shots: list[ShotLine] = []
    for table in tables:
        time_idx = 1
        text_idx = 3
        for row in re.findall(r"<tr\b.*?</tr>", table, flags=re.S):
            cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.S)
            clean_cells = [strip_tags(cell) for cell in cells]
            if "\u65f6\u95f4" in clean_cells:
                time_idx = clean_cells.index("\u65f6\u95f4")
                for text_header in ("\u6587\u6848", "\u53f0\u8bcd", "\u53e3\u64ad\u6587\u6848", "\u5b57\u5e55"):
                    if text_header in clean_cells:
                        text_idx = clean_cells.index(text_header)
                        break
                continue
            # Fixed daihuo-video-breakdown shot table:
            # 镜号 / 时间 / 时长 / 景别 / 台词 / 画面帧 / 音效
            row_text_idx = 4 if text_idx == 3 and len(cells) >= 7 else text_idx
            if len(cells) <= max(time_idx, row_text_idx):
                continue
            try:
                start, end = parse_time_range(cells[time_idx])
            except ValueError:
                continue
            text = strip_tags(cells[row_text_idx])
            if text:
                shots.append(ShotLine(start, end, text))
    return shots


def extract_shot_lines(content: str) -> tuple[list[ShotLine], float]:
    duration_match = re.search("\u89c6\u9891\u65f6\u957f\\s*\\|\\s*(\\d+(?:\\.\\d+)?)\\s*\u79d2", content)
    if not duration_match:
        duration_match = re.search("\u89c6\u9891\u65f6\u957f[^\\d]*(\\d+(?:\\.\\d+)?)\\s*\u79d2", content)
    target_duration = float(duration_match.group(1)) if duration_match else None

    sentence_timeline = extract_section(content, r"#{1,6}\s*\u516d[、.．]\s*\u9010\u53e5\u6587\u6848\u65f6\u95f4\u8f74")
    shots = extract_lines_from_tables(extract_tables(sentence_timeline)) if sentence_timeline else []
    if not shots:
        shots = extract_lines_from_tables(extract_tables(content))

    if not shots:
        raise ValueError("Cannot find shot lines in document table")
    if target_duration is None:
        target_duration = max(shot.end for shot in shots)
    return shots, target_duration


def wrap_text_lines(shots: list[ShotLine]) -> list[str]:
    return [shot.text for shot in shots]


def collapse_consecutive_identical_lines(shots: list[ShotLine]) -> list[ShotLine]:
    collapsed: list[ShotLine] = []
    for shot in shots:
        if collapsed and collapsed[-1].text == shot.text:
            previous = collapsed[-1]
            collapsed[-1] = ShotLine(previous.start, shot.end, previous.text)
        else:
            collapsed.append(shot)
    return collapsed


def extend_final_line_to_target(shots: list[ShotLine], target_seconds: float) -> list[ShotLine]:
    if not shots:
        return shots
    if shots[-1].end >= target_seconds:
        return shots
    extended = list(shots)
    last = extended[-1]
    extended[-1] = ShotLine(last.start, target_seconds, last.text)
    return extended


def compute_audio_speed(raw_seconds: float, target_seconds: float) -> float:
    if raw_seconds <= 0:
        raise ValueError("raw_seconds must be positive")
    if target_seconds <= 0:
        raise ValueError("target_seconds must be positive")
    return raw_seconds / target_seconds


def build_audio_segment_plan(
    shots: list[ShotLine],
    raw_durations: list[float],
    *,
    uniform_speed: bool = False,
) -> list[dict[str, float]]:
    if len(shots) != len(raw_durations):
        raise ValueError("shots and raw_durations must have the same length")
    common_speed = None
    if uniform_speed:
        common_speed = compute_audio_speed(sum(raw_durations), sum(shot.duration for shot in shots))
    return [
        {
            "start": shot.start,
            "duration": shot.duration,
            "raw_duration": raw_duration,
            "speed": common_speed if common_speed is not None else compute_audio_speed(raw_duration, shot.duration),
            "audio_duration": raw_duration / common_speed if common_speed is not None else shot.duration,
        }
        for shot, raw_duration in zip(shots, raw_durations)
    ]


def fetch_feishu_doc(doc_url: str) -> str:
    result = subprocess.run(
        [
            str(LARK_CLI),
            "docs",
            "+fetch",
            "--doc",
            doc_url,
            "--doc-format",
            "markdown",
            "--detail",
            "simple",
            "--as",
            "user",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(result.stdout)
    return payload["data"]["document"]["content"]


def synthesize_line(api_key: str, voice_type: str, resource_id: str, text: str, output: Path) -> None:
    reqid = str(uuid.uuid4())
    body = {
        "user": {"uid": "codex-jianying-voice-draft"},
        "req_params": {
            "text": text,
            "speaker": voice_type,
            "audio_params": {
                "format": "wav",
                "sample_rate": 24000,
                "speech_rate": 0,
                "loudness_rate": 0,
                "bit_rate": 64000,
            },
        },
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": reqid,
    }
    req = request.Request(TTS_ENDPOINT, data=data, headers=headers, method="POST")
    with request.urlopen(req, timeout=60) as resp:
        raw = resp.read()

    audio_bytes = extract_audio_bytes(raw)
    output.write_bytes(normalize_wav_bytes(audio_bytes))


def extract_audio_bytes(raw: bytes) -> bytes:
    chunks: list[bytes] = []
    for line in raw.splitlines():
        if not line:
            continue
        if line.startswith(b"data:"):
            line = line[5:].strip()
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        code = event.get("code")
        if code not in (None, 0, 3000, 20000000):
            raise ValueError(f"TTS error code={code}: {event.get('message')}")
        if event.get("data"):
            chunks.append(base64.b64decode(event["data"]))
    if chunks:
        return b"".join(chunks)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return raw
    except json.JSONDecodeError:
        return raw

    for key in ("data", "audio", "audio_data"):
        value = payload.get(key)
        if isinstance(value, str):
            return base64.b64decode(value)
    if isinstance(payload.get("result"), dict):
        for key in ("data", "audio", "audio_data"):
            value = payload["result"].get(key)
            if isinstance(value, str):
                return base64.b64decode(value)
    raise ValueError(f"TTS response did not contain audio data: {payload}")


def normalize_wav_bytes(data: bytes) -> bytes:
    if not (data.startswith(b"RIFF") and data[8:12] == b"WAVE"):
        return data
    fmt_offset = data.find(b"fmt ")
    data_offset = data.find(b"data")
    if fmt_offset < 0 or data_offset < 0:
        return data

    fmt_size = int.from_bytes(data[fmt_offset + 4 : fmt_offset + 8], "little")
    fmt = data[fmt_offset + 8 : fmt_offset + 8 + fmt_size]
    if len(fmt) < 16:
        return data
    audio_format = int.from_bytes(fmt[0:2], "little")
    channels = int.from_bytes(fmt[2:4], "little")
    sample_rate = int.from_bytes(fmt[4:8], "little")
    byte_rate = int.from_bytes(fmt[8:12], "little")
    block_align = int.from_bytes(fmt[12:14], "little")
    bits_per_sample = int.from_bytes(fmt[14:16], "little")
    pcm = data[data_offset + 8 :]

    header = bytearray()
    header.extend(b"RIFF")
    header.extend((36 + len(pcm)).to_bytes(4, "little"))
    header.extend(b"WAVE")
    header.extend(b"fmt ")
    header.extend((16).to_bytes(4, "little"))
    header.extend(audio_format.to_bytes(2, "little"))
    header.extend(channels.to_bytes(2, "little"))
    header.extend(sample_rate.to_bytes(4, "little"))
    header.extend(byte_rate.to_bytes(4, "little"))
    header.extend(block_align.to_bytes(2, "little"))
    header.extend(bits_per_sample.to_bytes(2, "little"))
    header.extend(b"data")
    header.extend(len(pcm).to_bytes(4, "little"))
    return bytes(header) + pcm


def audio_duration_seconds(path: Path) -> float:
    from pymediainfo import MediaInfo

    info = MediaInfo.parse(str(path))
    for track in info.tracks:
        if track.track_type == "Audio" and track.duration:
            return float(track.duration) / 1000.0
    raise ValueError(f"Cannot read audio duration for {path}")


def concat_wavs(inputs: list[Path], output: Path) -> float:
    params = None
    total_frames = 0
    with wave.open(str(output), "wb") as dst:
        for path in inputs:
            with wave.open(str(path), "rb") as src:
                current = src.getparams()
                comparable = (current.nchannels, current.sampwidth, current.framerate)
                if params is None:
                    params = comparable
                    dst.setnchannels(current.nchannels)
                    dst.setsampwidth(current.sampwidth)
                    dst.setframerate(current.framerate)
                elif params != comparable:
                    raise ValueError(f"WAV params differ for {path}")
                frames = src.readframes(src.getnframes())
                dst.writeframes(frames)
                total_frames += current.nframes
    if params is None:
        raise ValueError("No WAV inputs")
    return total_frames / params[2]


def trim_leading_silence_wav(
    source: Path,
    output: Path,
    *,
    threshold: int = 160,
    preroll_seconds: float = 0.06,
) -> float:
    with wave.open(str(source), "rb") as src:
        params = src.getparams()
        if params.nchannels != 1 or params.sampwidth != 2:
            output.write_bytes(source.read_bytes())
            return 0.0
        frames = src.readframes(params.nframes)

    samples = [
        int.from_bytes(frames[i : i + 2], "little", signed=True)
        for i in range(0, len(frames), 2)
    ]
    first_sound = 0
    for index, sample in enumerate(samples):
        if abs(sample) >= threshold:
            first_sound = index
            break
    else:
        output.write_bytes(source.read_bytes())
        return 0.0

    preroll_frames = int(params.framerate * preroll_seconds)
    start = max(0, first_sound - preroll_frames)
    trimmed_frames = frames[start * params.sampwidth :]
    with wave.open(str(output), "wb") as dst:
        dst.setnchannels(params.nchannels)
        dst.setsampwidth(params.sampwidth)
        dst.setframerate(params.framerate)
        dst.writeframes(trimmed_frames)
    return start / params.framerate


def create_jianying_draft(
    draft_name: str,
    audio_paths: list[Path],
    raw_audio_seconds: list[float],
    target_seconds: float,
    shots: list[ShotLine],
) -> Path:
    import pyJianYingDraft as draft

    target = JY_DRAFT_ROOT / draft_name
    if target.exists():
        shutil.rmtree(target)
    folder = draft.DraftFolder(str(JY_DRAFT_ROOT))
    script = folder.create_draft(draft_name, 1080, 1920, fps=30, allow_replace=True)
    audio_track = script.append_track(draft.TrackSpec(draft.TrackType.audio, "朗读音频"))
    text_track = script.append_track(draft.TrackSpec(draft.TrackType.text, "字幕"))

    segment_plan = build_audio_segment_plan(shots, raw_audio_seconds, uniform_speed=True)
    audio_cursor = 0.0
    for audio_path, shot, plan in zip(audio_paths, shots, segment_plan):
        audio_duration = max(0.001, plan["audio_duration"] - 0.002)
        script.add_segment(
            draft.AudioSegment(
                str(audio_path),
                draft.trange(f"{audio_cursor}s", f"{audio_duration}s"),
                speed=plan["speed"],
                volume=1.0,
                change_pitch=False,
            ),
            audio_track,
        )
        audio_cursor += plan["audio_duration"]

    style = draft.TextStyle(size=9.0, bold=True, color=(1, 1, 1), align=1, auto_wrapping=True)
    border = draft.TextBorder(color=(0, 0, 0), width=55)
    font_path = r"C:\Windows\Fonts\msyh.ttc"
    for shot in shots:
        segment = draft.TextSegment(
            shot.text,
            draft.trange(f"{shot.start}s", f"{shot.duration}s"),
            font_path=font_path,
            style=style,
            border=border,
            clip_settings=draft.ClipSettings(transform_y=-0.78),
        )
        # Keep the requested font name even when the local font file is absent.
        segment.font_path = font_path
        script.add_segment(segment, text_track)

    script.save()
    patch_text_font(target / "draft_content.json", "抖音体", 9.0)
    return target


def patch_text_font(draft_content: Path, font_name: str, font_size: float) -> None:
    data = json.loads(draft_content.read_text(encoding="utf-8"))
    for item in data.get("materials", {}).get("texts", []):
        content = json.loads(item.get("content", "{}"))
        content["font_name"] = font_name
        content["font_size"] = font_size
        for style in content.get("styles", []):
            style["size"] = font_size
        item["content"] = json.dumps(content, ensure_ascii=False)
    draft_content.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-url", required=True)
    parser.add_argument("--api-key", default=os.environ.get("DOUBAO_TTS_API_KEY"))
    parser.add_argument("--voice-id", required=True)
    parser.add_argument("--resource-id", default=DEFAULT_RESOURCE_ID)
    parser.add_argument("--draft-name", default="22-乐事宠尿垫-03-朗读字幕轨-20260913")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("Missing --api-key or DOUBAO_TTS_API_KEY")

    out_dir = ROOT / "outputs" / "22-leshi-voice-draft"
    line_dir = out_dir / "lines"
    trimmed_dir = out_dir / "lines_trimmed"
    line_dir.mkdir(parents=True, exist_ok=True)
    trimmed_dir.mkdir(parents=True, exist_ok=True)

    content = fetch_feishu_doc(args.doc_url)
    raw_shots, target_seconds = extract_shot_lines(content)
    shots = extend_final_line_to_target(collapse_consecutive_identical_lines(raw_shots), target_seconds)

    line_paths: list[Path] = []
    line_durations: list[float] = []
    for idx, text in enumerate(wrap_text_lines(shots), start=1):
        output = line_dir / f"{idx:02d}.wav"
        trimmed = trimmed_dir / f"{idx:02d}.wav"
        synthesize_line(args.api_key, args.voice_id, args.resource_id, text, output)
        trim_leading_silence_wav(output, trimmed)
        line_paths.append(trimmed)
        line_durations.append(audio_duration_seconds(trimmed))

    draft_path = create_jianying_draft(args.draft_name, line_paths, line_durations, target_seconds, shots)

    manifest = {
        "draft": str(draft_path),
        "audio_files": [str(path) for path in line_paths],
        "target_seconds": target_seconds,
        "raw_audio_seconds": line_durations,
        "audio_speeds": [item["speed"] for item in build_audio_segment_plan(shots, line_durations, uniform_speed=True)],
        "line_count": len(shots),
        "raw_line_count": len(raw_shots),
    }
    (out_dir / "voice_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
