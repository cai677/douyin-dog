import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def main():
    if len(sys.argv) != 2:
        print("usage: python make_segment_contact_sheet.py <material_sample_dir>")
        return 2

    root = sys.argv[1]
    with open(os.path.join(root, "material_index.json"), encoding="utf-8") as f:
        segments = json.load(f)["segments"]

    width = 200
    height = 356
    font = ImageFont.load_default()
    cards = []

    for segment in segments:
        image = Image.open(os.path.join(root, segment["keyframe"])).convert("RGB")
        image.thumbnail((width, height))
        card = Image.new("RGB", (width, height + 54), "white")
        card.paste(image, ((width - image.width) // 2, 0))
        draw = ImageDraw.Draw(card)
        draw.text((4, height + 4), f"{segment['id']} {segment['start']}-{segment['end']}s", fill=(0, 0, 0), font=font)
        draw.text((4, height + 20), segment["category"][:28], fill=(0, 0, 0), font=font)
        draw.text((4, height + 36), segment["label"][:28], fill=(0, 0, 0), font=font)
        cards.append(card)

    cols = 5
    rows = math.ceil(len(cards) / cols)
    sheet = Image.new("RGB", (cols * width, rows * (height + 54)), (238, 238, 238))
    for index, card in enumerate(cards):
        sheet.paste(card, ((index % cols) * width, (index // cols) * (height + 54)))

    out_path = os.path.join(root, "segment_contact_sheet.jpg")
    sheet.save(out_path, quality=90)
    print(out_path)


if __name__ == "__main__":
    raise SystemExit(main())
