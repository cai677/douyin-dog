import os
import subprocess
import sys


PYTHON = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
EXTRACT = r"C:\Users\Administrator\.codex\skills\daihuo-video-breakdown\scripts\extract_frames.py"
SHEETS = os.path.join(os.path.dirname(__file__), "make_frame_contact_sheets.py")


def main():
    if len(sys.argv) != 2:
        print("usage: python prepare_batch_frames.py <product_dir>")
        return 2

    product_dir = sys.argv[1]
    videos = sorted(
        os.path.join(product_dir, name)
        for name in os.listdir(product_dir)
        if name.lower().endswith(".mp4")
    )

    for video in videos:
        stem = os.path.splitext(os.path.basename(video))[0]
        frames_dir = os.path.join(product_dir, stem, "frames_0_2s")
        sheets_dir = os.path.join(product_dir, stem, "frame_sheets")
        os.makedirs(os.path.dirname(frames_dir), exist_ok=True)
        print(f"extracting {stem}", flush=True)
        subprocess.run([PYTHON, EXTRACT, video, frames_dir, "0.2"], check=True)
        subprocess.run([PYTHON, SHEETS, frames_dir, sheets_dir, "10"], check=True)


if __name__ == "__main__":
    raise SystemExit(main())
