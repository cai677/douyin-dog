import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont


TIME_RE = re.compile(r"t(\d+\.\d+)s")


def frame_time(filename):
    match = TIME_RE.search(filename)
    return float(match.group(1)) if match else 0.0


def main():
    if len(sys.argv) not in (3, 4):
        print("usage: python make_frame_contact_sheets.py <frames_dir> <output_dir> [seconds_per_sheet]")
        return 2

    frames_dir = sys.argv[1]
    output_dir = sys.argv[2]
    seconds_per_sheet = float(sys.argv[3]) if len(sys.argv) == 4 else 10.0
    os.makedirs(output_dir, exist_ok=True)

    files = sorted(
        [name for name in os.listdir(frames_dir) if name.lower().endswith(".jpg")],
        key=frame_time,
    )

    width = 120
    height = 213
    label_height = 18
    cols = 8
    font = ImageFont.load_default()
    sheets = {}

    for name in files:
        t = frame_time(name)
        sheet_index = int(t // seconds_per_sheet)
        sheets.setdefault(sheet_index, []).append((t, name))

    for sheet_index, sheet_files in sheets.items():
        rows = math.ceil(len(sheet_files) / cols)
        sheet = Image.new("RGB", (cols * width, rows * (height + label_height)), (238, 238, 238))
        for index, (t, name) in enumerate(sheet_files):
            image = Image.open(os.path.join(frames_dir, name)).convert("RGB")
            image.thumbnail((width, height))
            card = Image.new("RGB", (width, height + label_height), "white")
            card.paste(image, ((width - image.width) // 2, 0))
            draw = ImageDraw.Draw(card)
            draw.text((3, height + 3), f"{t:05.1f}s", fill=(0, 0, 0), font=font)
            sheet.paste(card, ((index % cols) * width, (index // cols) * (height + label_height)))

        start = sheet_index * seconds_per_sheet
        end = start + seconds_per_sheet
        out_path = os.path.join(output_dir, f"frames_{start:04.1f}_{end:04.1f}.jpg")
        sheet.save(out_path, quality=88)
        print(out_path)


if __name__ == "__main__":
    raise SystemExit(main())
