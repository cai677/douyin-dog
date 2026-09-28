#!/usr/bin/env python3
"""Prepare and check pet eye-drop opening animation folders."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


VERSIONS = [
    ("version-01-bichon", "白色比熊主推可爱版"),
    ("version-02-shiba", "柴犬搞笑传播版"),
    ("version-03-ragdoll-cat", "布偶猫精致猫主人版"),
    ("version-04-puppy-drama", "小奶狗动画短剧版"),
]

SHOTS = [
    ("shot-01", "眼周小世界建立", "1.4"),
    ("shot-02", "棉片来了", "1.6"),
    ("shot-03", "老大嘴硬", "1.7"),
    ("shot-04", "眼药水登场", "1.7"),
    ("shot-05", "警报反转", "1.7"),
    ("shot-06", "老窝被端", "2.7"),
]


def root(path: str | None) -> Path:
    return Path(path or "outputs/eye-drop-opening").resolve()


def init_project(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / "prompts").mkdir(exist_ok=True)
    for version, _label in VERSIONS:
        for sub in ["keyframes", "clips", "audio", "exports"]:
            (base / version / sub).mkdir(parents=True, exist_ok=True)
        review = base / version / "review.md"
        if not review.exists():
            review.write_text(f"# {version} 生成检查\n\n待生成。\n", encoding="utf-8")

    manifest = base / "shot_manifest.csv"
    with manifest.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "version",
            "shot_id",
            "shot_name",
            "target_duration_seconds",
            "keyframe_path",
            "clip_path",
            "status",
            "notes",
        ])
        for version, _label in VERSIONS:
            for shot_id, shot_name, duration in SHOTS:
                writer.writerow([
                    version,
                    shot_id,
                    shot_name,
                    duration,
                    f"{version}/keyframes/{shot_id}-keyframe.png",
                    f"{version}/clips/{shot_id}.mp4",
                    "pending",
                    "",
                ])


def check_version(base: Path, version: str) -> int:
    missing: list[Path] = []
    for shot_id, _shot_name, _duration in SHOTS:
        for rel in [
            Path(version) / "keyframes" / f"{shot_id}-keyframe.png",
            Path(version) / "clips" / f"{shot_id}.mp4",
        ]:
            path = base / rel
            if not path.exists():
                missing.append(rel)
    if missing:
        print(f"Missing files for {version}:")
        for rel in missing:
            print(f"- {rel.as_posix()}")
        return 1
    print(f"{version} is complete for assembly.")
    return 0


def write_concat_list(base: Path, version: str) -> Path:
    concat_path = base / version / "exports" / "concat-list.txt"
    concat_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for shot_id, _shot_name, _duration in SHOTS:
        clip = (base / version / "clips" / f"{shot_id}.mp4").resolve()
        lines.append(f"file '{clip.as_posix()}'")
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return concat_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None, help="Project output root, defaults to outputs/eye-drop-opening")
    parser.add_argument("--init", action="store_true", help="Create folders and manifest")
    parser.add_argument("--check-version", choices=[v for v, _ in VERSIONS], help="Check required keyframes and clips")
    parser.add_argument("--write-concat-list", choices=[v for v, _ in VERSIONS], help="Write ffmpeg concat demuxer list")
    args = parser.parse_args()

    base = root(args.root)
    if args.init:
        init_project(base)
        print(f"Initialized {base}")
    if args.check_version:
        code = check_version(base, args.check_version)
        if code:
            return code
    if args.write_concat_list:
        path = write_concat_list(base, args.write_concat_list)
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

