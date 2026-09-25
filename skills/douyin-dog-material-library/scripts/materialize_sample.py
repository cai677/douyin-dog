import csv
import json
import os
import shutil
import subprocess
import sys

import cv2


SEMANTIC_SEGMENTS = [
    {
        "id": "S01",
        "start": 0.0,
        "end": 4.4,
        "category": "pain_hook",
        "label": "症状钩子-眼屎多发黄",
        "note": "开头用医生形象和狗眼屎问题制造痛点。",
    },
    {
        "id": "S02",
        "start": 4.4,
        "end": 7.8,
        "category": "pain_hook",
        "label": "症状钩子-泪痕和眼病",
        "note": "继续放大乱用东西的风险和常见眼部问题。",
    },
    {
        "id": "S03",
        "start": 7.8,
        "end": 10.4,
        "category": "symptom_montage",
        "label": "多狗症状合集",
        "note": "多只狗眼部异常画面，可复用作问题场景。",
    },
    {
        "id": "S04",
        "start": 10.4,
        "end": 14.8,
        "category": "demo_exam",
        "label": "眼部检查和清理",
        "note": "医生给狗做眼部检查、擦拭、观察。",
    },
    {
        "id": "S05",
        "start": 14.8,
        "end": 19.8,
        "category": "expert_talking",
        "label": "专家口播-不要乱用",
        "note": "医生口播解释乱用药水的风险。",
    },
    {
        "id": "S06",
        "start": 19.8,
        "end": 23.2,
        "category": "product_setup",
        "label": "产品出场-兽药字滴眼液",
        "note": "桌面拿出产品，建立产品身份。",
    },
    {
        "id": "S07",
        "start": 23.2,
        "end": 24.8,
        "category": "product_closeup",
        "label": "产品特写-包装瓶身",
        "note": "瓶身和包装近景，适合作为商品素材。",
    },
    {
        "id": "S08",
        "start": 24.8,
        "end": 27.2,
        "category": "usage_demo",
        "label": "使用演示-滴眼",
        "note": "把滴眼液滴到狗眼部的核心使用画面。",
    },
    {
        "id": "S09",
        "start": 27.2,
        "end": 31.6,
        "category": "proof",
        "label": "资质背书-检测报告和pH",
        "note": "检测报告、pH 值、成分/温和背书。",
    },
    {
        "id": "S10",
        "start": 31.6,
        "end": 33.0,
        "category": "result_scene",
        "label": "正常眼泪场景",
        "note": "用狗眼部状态承接放心使用。",
    },
    {
        "id": "S11",
        "start": 33.0,
        "end": 35.4,
        "category": "usage_demo",
        "label": "使用演示-柯基滴眼",
        "note": "另一只狗的使用画面，补充素材多样性。",
    },
    {
        "id": "S12",
        "start": 35.4,
        "end": 36.8,
        "category": "symptom_montage",
        "label": "严重眼部情况",
        "note": "白色小狗眼部异常，适合做问题强调。",
    },
    {
        "id": "S13",
        "start": 36.8,
        "end": 38.57,
        "category": "closing_demo",
        "label": "收尾-活力和品质",
        "note": "结尾继续使用演示，并用活力、品质收束。",
    },
]


EYE_DROP_SHOT_TYPE_SEGMENTS = [
    {
        "id": "T01",
        "start": 0.0,
        "end": 4.4,
        "category": "person_talking_pet",
        "label": "人物讲解-眼屎发黄",
        "note": "人出镜讲解，宠物眼部问题作为画面主体。",
    },
    {
        "id": "T02",
        "start": 4.4,
        "end": 7.8,
        "category": "person_talking_pet",
        "label": "人物讲解-泪痕和眼病",
        "note": "医生/达人继续讲解眼部风险。",
    },
    {
        "id": "T03",
        "start": 7.8,
        "end": 10.4,
        "category": "pet_eye_montage",
        "label": "宠物眼部症状合集",
        "note": "多只宠物眼部异常拼图和合集画面。",
    },
    {
        "id": "T04",
        "start": 10.4,
        "end": 12.8,
        "category": "pet_eye_closeup",
        "label": "宠物眼睛特写-分泌物",
        "note": "近距离展示宠物眼周分泌物和眼部状态。",
    },
    {
        "id": "T05",
        "start": 12.8,
        "end": 14.8,
        "category": "eye_exam_cleaning",
        "label": "眼部检查清理",
        "note": "手部接触眼周，进行擦拭和检查。",
    },
    {
        "id": "T06",
        "start": 14.8,
        "end": 19.8,
        "category": "person_talking_pet",
        "label": "人物讲解-抱宠口播",
        "note": "人和宠物同框口播说明。",
    },
    {
        "id": "T07",
        "start": 19.8,
        "end": 23.2,
        "category": "product_hand_demo",
        "label": "手部展示产品",
        "note": "手拿产品、桌面准备、产品进入使用流程。",
    },
    {
        "id": "T08",
        "start": 23.2,
        "end": 24.8,
        "category": "product_empty_shot",
        "label": "产品空镜-包装瓶身",
        "note": "单独展示包装和瓶身，宠物作为背景或陪衬。",
    },
    {
        "id": "T09",
        "start": 24.8,
        "end": 25.6,
        "category": "product_hand_demo",
        "label": "手部准备滴眼液",
        "note": "产品滴头靠近宠物眼睛前的准备动作。",
    },
    {
        "id": "T10",
        "start": 25.6,
        "end": 27.2,
        "category": "eye_drop_demo",
        "label": "给宠物滴眼液",
        "note": "核心使用镜头，滴头对准眼睛并完成滴眼。",
    },
    {
        "id": "T11",
        "start": 27.2,
        "end": 28.4,
        "category": "eye_drop_demo",
        "label": "给宠物滴眼液-重复演示",
        "note": "同类滴眼动作，角度和狗不同。",
    },
    {
        "id": "T12",
        "start": 28.4,
        "end": 31.6,
        "category": "proof_closeup",
        "label": "检测报告和pH近景",
        "note": "检测报告、pH 试纸和说明类近景。",
    },
    {
        "id": "T13",
        "start": 31.6,
        "end": 36.8,
        "category": "pet_result_scene",
        "label": "宠物眼部状态展示",
        "note": "展示宠物正常眼泪、放心使用和其他眼部状态。",
    },
    {
        "id": "T14",
        "start": 36.8,
        "end": 38.57,
        "category": "product_hand_demo",
        "label": "收尾手部展示产品",
        "note": "结尾桌面产品和宠物同框，手部继续操作。",
    },
]


SEMANTIC_FINE_SEGMENTS = [
    {"id": "F01", "start": 0.0, "end": 7.4, "category": "pain_hook", "label": "痛点开场-连续症状钩子", "note": "同一口播构图下连续列举眼屎、泪痕、眼病等问题，不因字幕变化单独切开。"},
    {"id": "F02", "start": 7.4, "end": 8.4, "category": "symptom_montage", "label": "症状合集-狗狗出现这些情况", "note": "人物口播过渡到症状合集。"},
    {"id": "F03", "start": 8.4, "end": 10.0, "category": "symptom_montage", "label": "症状合集-多狗眼部问题", "note": "多只狗眼部异常拼图。"},
    {"id": "F04", "start": 10.0, "end": 11.2, "category": "demo_exam", "label": "检查演示-抱狗观察眼部", "note": "抱狗检查眼部位置。"},
    {"id": "F05", "start": 11.2, "end": 12.6, "category": "pet_eye_closeup", "label": "眼部特写-体菌在折磨它", "note": "白狗眼部分泌物特写。"},
    {"id": "F06", "start": 12.6, "end": 14.2, "category": "demo_exam", "label": "清理演示-擦拭眼周", "note": "手部擦拭白狗眼周。"},
    {"id": "F07", "start": 14.2, "end": 15.6, "category": "usage_demo", "label": "局部操作-眼部点涂", "note": "近景对眼部进行点涂或上药。"},
    {"id": "F08", "start": 15.6, "end": 19.4, "category": "expert_talking", "label": "专家口播-不要乱用", "note": "人物和宠物同框口播解释风险。"},
    {"id": "F09", "start": 19.4, "end": 23.8, "category": "product_setup", "label": "产品出场-桌面拿起和说明", "note": "产品在桌面出现，手部展示和准备。"},
    {"id": "F10", "start": 23.8, "end": 25.0, "category": "product_closeup", "label": "产品特写-包装瓶身", "note": "包装和瓶身近景，宠物作背景。"},
    {"id": "F11", "start": 25.0, "end": 27.0, "category": "usage_demo", "label": "使用演示-滴眼近景", "note": "滴头对准宠物眼部的核心使用画面。"},
    {"id": "F12", "start": 27.0, "end": 28.8, "category": "product_setup", "label": "产品说明-回到桌面", "note": "从滴眼近景回到桌面产品讲解。"},
    {"id": "F13", "start": 28.8, "end": 30.6, "category": "proof", "label": "资质背书-检测报告", "note": "检测报告与滴眼画面同框。"},
    {"id": "F14", "start": 30.6, "end": 32.2, "category": "proof", "label": "资质背书-pH试纸", "note": "pH 值色卡和滴眼画面。"},
    {"id": "F15", "start": 32.2, "end": 33.4, "category": "result_scene", "label": "结果展示-正常眼泪", "note": "金毛眼部状态展示。"},
    {"id": "F16", "start": 33.4, "end": 35.0, "category": "usage_demo", "label": "使用演示-柯基滴眼", "note": "另一只狗的滴眼使用画面。"},
    {"id": "F17", "start": 35.0, "end": 36.4, "category": "symptom_montage", "label": "症状展示-白狗眼部情况", "note": "白狗眼部状态画面。"},
    {"id": "F18", "start": 36.4, "end": 38.57, "category": "closing_demo", "label": "收尾演示-活力和品质", "note": "桌面产品与宠物同框完成收尾。"},
]


PRESETS = {
    "semantic": SEMANTIC_SEGMENTS,
    "semantic_fine": SEMANTIC_FINE_SEGMENTS,
    "eye_drop_shot_type": EYE_DROP_SHOT_TYPE_SEGMENTS,
}


def safe_name(value):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)


def save_frame(cap, fps, time_sec, path):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(time_sec * fps))
    ok, frame = cap.read()
    if not ok:
        return False
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        return False
    with open(path, "wb") as f:
        f.write(buf.tobytes())
    return True


def find_ffmpeg():
    candidates = [
        os.environ.get("FFMPEG_PATH"),
        os.path.join(
            os.getcwd(),
            "node_modules",
            ".pnpm",
            "@ffmpeg-installer+ffmpeg@1.1.0",
            "node_modules",
            "@ffmpeg-installer",
            "win32-x64",
            "ffmpeg.exe",
        ),
        os.path.join(
            os.getcwd(),
            "node_modules",
            ".pnpm",
            "ffmpeg-static@5.3.0",
            "node_modules",
            "ffmpeg-static",
            "ffmpeg.exe",
        ),
        shutil.which("ffmpeg"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def build_ffmpeg_clip_command(ffmpeg_path, video_path, segment, out_path):
    duration = round(segment["end"] - segment["start"], 3)
    return [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(segment["start"]),
        "-i",
        video_path,
        "-t",
        str(duration),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        out_path,
    ]


def split_long_ranges(ranges, max_duration=8.0):
    result = []
    for item in ranges:
        start = float(item["start"])
        end = float(item["end"])
        cursor = start
        while end - cursor > max_duration:
            next_end = round(cursor + max_duration, 2)
            result.append({"start": round(cursor, 2), "end": next_end})
            cursor = next_end
        if end - cursor > 0.05:
            result.append({"start": round(cursor, 2), "end": round(end, 2)})
    return result


def write_clip_with_opencv(video_path, segment, out_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Cannot write {out_path}")

    start_frame = int(segment["start"] * fps)
    end_frame = int(segment["end"] * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    frame_no = start_frame
    while frame_no < end_frame:
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(frame)
        frame_no += 1

    writer.release()
    cap.release()


def write_clip(video_path, segment, out_path, ffmpeg_path=None):
    if ffmpeg_path:
        command = build_ffmpeg_clip_command(ffmpeg_path, video_path, segment, out_path)
        subprocess.run(command, check=True)
        return
    write_clip_with_opencv(video_path, segment, out_path)


def main():
    if len(sys.argv) not in (3, 4):
        print("usage: python materialize_sample.py <video> <output_dir> [preset]")
        return 2

    video_path = sys.argv[1]
    out_dir = sys.argv[2]
    preset = sys.argv[3] if len(sys.argv) == 4 else "semantic"
    if preset not in PRESETS:
        print(f"unknown preset: {preset}")
        print("available presets: " + ", ".join(sorted(PRESETS)))
        return 2
    segments = PRESETS[preset]
    clips_dir = os.path.join(out_dir, "clips")
    keyframes_dir = os.path.join(out_dir, "keyframes")
    by_category_dir = os.path.join(out_dir, "by_category")

    for path in (clips_dir, keyframes_dir, by_category_dir):
        os.makedirs(path, exist_ok=True)

    ffmpeg_path = find_ffmpeg()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    rows = []
    for seg in segments:
        base = f"{seg['id']}_{safe_name(seg['category'])}_{safe_name(seg['label'])}"
        clip_name = base + ".mp4"
        keyframe_name = base + ".jpg"
        clip_path = os.path.join(clips_dir, clip_name)
        keyframe_path = os.path.join(keyframes_dir, keyframe_name)

        write_clip(video_path, seg, clip_path, ffmpeg_path)
        save_frame(cap, fps, (seg["start"] + seg["end"]) / 2, keyframe_path)

        category_dir = os.path.join(by_category_dir, seg["category"])
        os.makedirs(category_dir, exist_ok=True)
        category_clip_path = os.path.join(category_dir, clip_name)
        if os.path.exists(category_clip_path):
            os.remove(category_clip_path)
        shutil.copy2(clip_path, category_clip_path)

        row = {
            **seg,
            "duration": round(seg["end"] - seg["start"], 2),
            "clip": os.path.relpath(clip_path, out_dir),
            "keyframe": os.path.relpath(keyframe_path, out_dir),
        }
        rows.append(row)

    cap.release()

    json_path = os.path.join(out_dir, "material_index.json")
    csv_path = os.path.join(out_dir, "material_index.csv")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"video": os.path.basename(video_path), "preset": preset, "segments": rows}, f, ensure_ascii=False, indent=2)

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"segments={len(rows)}")
    print(json_path)
    print(csv_path)


if __name__ == "__main__":
    raise SystemExit(main())
