import json
import os
import subprocess
import sys

from materialize_sample import find_ffmpeg


def has_audio(ffmpeg_path, clip_path):
    result = subprocess.run(
        [
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            clip_path,
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.returncode == 0


def main():
    if len(sys.argv) != 2:
        print("usage: python verify_batch_materials.py <product_dir>")
        return 2

    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg not found")

    product_dir = sys.argv[1]
    failures = []
    for name in sorted(os.listdir(product_dir)):
        material_dir = os.path.join(product_dir, name, "material_auto")
        if not os.path.isdir(material_dir):
            continue
        with open(os.path.join(material_dir, "material_index.json"), encoding="utf-8") as f:
            data = json.load(f)
        clips_dir = os.path.join(material_dir, "clips")
        keyframes_dir = os.path.join(material_dir, "keyframes")
        clips = sorted([item for item in os.listdir(clips_dir) if item.lower().endswith(".mp4")])
        keyframes = sorted([item for item in os.listdir(keyframes_dir) if item.lower().endswith(".jpg")])
        sheet = os.path.exists(os.path.join(material_dir, "segment_contact_sheet.jpg"))
        audio = bool(clips) and has_audio(ffmpeg_path, os.path.join(clips_dir, clips[0]))
        expected = len(data["segments"])
        ok = len(clips) == expected and len(keyframes) == expected and sheet and audio
        print(f"{name}: segments={expected} clips={len(clips)} keyframes={len(keyframes)} sheet={sheet} audio_sample={audio}")
        if not ok:
            failures.append(name)

    if failures:
        print("failures: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
