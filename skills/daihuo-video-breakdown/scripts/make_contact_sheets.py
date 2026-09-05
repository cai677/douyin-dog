# -*- coding: utf-8 -*-
"""Create labeled contact sheets from extracted JPG frames using OpenCV only."""

from pathlib import Path
import sys

import cv2
import numpy as np


def read_image(path: Path):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def write_image(path: Path, image):
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError(f"无法编码联系表：{path}")
    encoded.tofile(path)


def main():
    if len(sys.argv) < 3:
        print("用法: python make_contact_sheets.py <帧目录> <输出目录> [每页帧数]")
        raise SystemExit(1)

    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    per_sheet = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    if per_sheet < 1:
        raise ValueError("每页帧数必须大于 0")

    files = sorted(source.glob("*.jpg"))
    if not files:
        raise FileNotFoundError(f"未找到 JPG 帧：{source}")
    output.mkdir(parents=True, exist_ok=True)

    columns = 2
    rows = (per_sheet + columns - 1) // columns
    thumb_w, thumb_h, label_h = 480, 270, 30

    for page, start in enumerate(range(0, len(files), per_sheet), 1):
        canvas = np.full(((thumb_h + label_h) * rows, thumb_w * columns, 3), 255, np.uint8)
        for index, path in enumerate(files[start : start + per_sheet]):
            image = read_image(path)
            if image is None:
                raise RuntimeError(f"无法读取帧：{path}")
            scale = min(thumb_w / image.shape[1], thumb_h / image.shape[0])
            image = cv2.resize(image, (int(image.shape[1] * scale), int(image.shape[0] * scale)))
            column, row = index % columns, index // columns
            x = column * thumb_w + (thumb_w - image.shape[1]) // 2
            y = row * (thumb_h + label_h) + (thumb_h - image.shape[0]) // 2
            canvas[y : y + image.shape[0], x : x + image.shape[1]] = image
            cv2.putText(canvas, path.stem, (column * thumb_w + 5, row * (thumb_h + label_h) + thumb_h + 21), cv2.FONT_HERSHEY_SIMPLEX, 0.47, (0, 0, 0), 1, cv2.LINE_AA)
        write_image(output / f"sheet_{page:02d}.jpg", canvas)

    print(f"完成: {len(files)} 帧 -> {(len(files) + per_sheet - 1) // per_sheet} 张联系表")


if __name__ == "__main__":
    main()

