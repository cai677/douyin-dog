import csv
import json
import os
import shutil
import sys

import cv2

from materialize_sample import find_ffmpeg, safe_name, save_frame, split_long_ranges, write_clip
from make_segment_contact_sheet import main as _unused_contact_sheet_main


def load_shots(video_dir):
    shot_path = os.path.join(video_dir, "frames_0_2s", "shot_list.json")
    with open(shot_path, encoding="utf-8") as f:
        data = json.load(f)
    ranges = [{"start": item["start"], "end": item["end"]} for item in data["shots"]]
    return data, split_long_ranges(ranges, max_duration=8.0)


def segment_video(video_path, video_dir, ffmpeg_path):
    data, ranges = load_shots(video_dir)
    out_dir = os.path.join(video_dir, "material_auto")
    clips_dir = os.path.join(out_dir, "clips")
    keyframes_dir = os.path.join(out_dir, "keyframes")
    by_category_dir = os.path.join(out_dir, "by_category", "shot_segment")
    for path in (clips_dir, keyframes_dir, by_category_dir):
        os.makedirs(path, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    rows = []
    for index, item in enumerate(ranges, 1):
        segment = {
            "id": f"A{index:02d}",
            "start": item["start"],
            "end": item["end"],
            "category": "shot_segment",
            "label": f"自动镜头段-{index:02d}",
            "note": "0.2秒抽帧检测边界；超过8秒的长段自动拆分，保留原音频。",
        }
        base = f"{segment['id']}_{safe_name(segment['category'])}_{safe_name(segment['label'])}"
        clip_name = base + ".mp4"
        keyframe_name = base + ".jpg"
        clip_path = os.path.join(clips_dir, clip_name)
        keyframe_path = os.path.join(keyframes_dir, keyframe_name)
        write_clip(video_path, segment, clip_path, ffmpeg_path)
        save_frame(cap, fps, (segment["start"] + segment["end"]) / 2, keyframe_path)
        shutil.copy2(clip_path, os.path.join(by_category_dir, clip_name))
        rows.append({
            **segment,
            "duration": round(segment["end"] - segment["start"], 2),
            "clip": os.path.relpath(clip_path, out_dir),
            "keyframe": os.path.relpath(keyframe_path, out_dir),
        })

    cap.release()

    with open(os.path.join(out_dir, "material_index.json"), "w", encoding="utf-8") as f:
        json.dump({
            "video": os.path.basename(video_path),
            "source_shots": len(data["shots"]),
            "segments": rows,
        }, f, ensure_ascii=False, indent=2)

    with open(os.path.join(out_dir, "material_index.csv"), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return out_dir, len(rows)


def main():
    if len(sys.argv) != 2:
        print("usage: python segment_batch_from_shots.py <product_dir>")
        return 2

    product_dir = sys.argv[1]
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg not found")

    videos = sorted(
        os.path.join(product_dir, name)
        for name in os.listdir(product_dir)
        if name.lower().endswith(".mp4")
    )

    for video_path in videos:
        stem = os.path.splitext(os.path.basename(video_path))[0]
        video_dir = os.path.join(product_dir, stem)
        out_dir, count = segment_video(video_path, video_dir, ffmpeg_path)
        print(f"{stem}: {count} segments -> {out_dir}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
