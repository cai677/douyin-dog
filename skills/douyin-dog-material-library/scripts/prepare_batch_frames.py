import os
import subprocess
import sys


PYTHON = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
EXTRACT = r"C:\Users\Administrator\.codex\skills\daihuo-video-breakdown\scripts\extract_frames.py"
SHEETS = os.path.join(os.path.dirname(__file__), "make_frame_contact_sheets.py")


def frame_dir_name(interval):
    text = f"{float(interval):g}".replace(".", "_")
    return f"frames_{text}s"


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: python prepare_batch_frames.py <product_dir> [interval_seconds]")
        return 2

    product_dir = sys.argv[1]
    interval = float(sys.argv[2]) if len(sys.argv) == 3 else 0.1
    videos = sorted(
        os.path.join(product_dir, name)
        for name in os.listdir(product_dir)
        if name.lower().endswith(".mp4")
    )

    for video in videos:
        stem = os.path.splitext(os.path.basename(video))[0]
        frames_dir = os.path.join(product_dir, stem, frame_dir_name(interval))
        sheets_dir = os.path.join(product_dir, stem, "frame_sheets")
        os.makedirs(os.path.dirname(frames_dir), exist_ok=True)
        print(f"extracting {stem} interval={interval:g}s", flush=True)
        subprocess.run([PYTHON, EXTRACT, video, frames_dir, f"{interval:g}"], check=True)
        subprocess.run([PYTHON, SHEETS, frames_dir, sheets_dir, "10"], check=True)


if __name__ == "__main__":
    raise SystemExit(main())
