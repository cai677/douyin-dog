import csv
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def load_rows(root):
    rows = []
    for video_dir in sorted(
        [p for p in os.listdir(root) if p.startswith("total-") and os.path.isdir(os.path.join(root, p))]
    ):
        material_dir = os.path.join(root, video_dir, "material_auto_0_1s")
        index_path = os.path.join(material_dir, "material_index.csv")
        if not os.path.exists(index_path):
            continue
        with open(index_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                row = dict(row)
                row["video"] = video_dir
                row["material_dir"] = material_dir
                row["keyframe_path"] = os.path.join(material_dir, row["keyframe"])
                row["clip_path"] = os.path.join(material_dir, row["clip"])
                rows.append(row)
    return rows


def feature(path):
    try:
        image = np.array(Image.open(path).convert("RGB"))
    except Exception as exc:
        raise RuntimeError(f"Cannot read {path}") from exc
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    image = cv2.resize(image, (32, 32), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256]).flatten()
    hist = hist / (np.linalg.norm(hist) + 1e-6)
    small = cv2.resize(image, (12, 12), interpolation=cv2.INTER_AREA).flatten() / 255.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 160)
    edge_density = np.array([edges.mean() / 255.0], dtype=np.float32)
    return np.concatenate([small, hist, edge_density]).astype(np.float32)


def make_sheets(rows, out_dir, per_cluster=6, clusters_per_sheet=12):
    os.makedirs(out_dir, exist_ok=True)
    font = ImageFont.load_default()
    cell_w, cell_h = 180, 250
    cols = 3
    cluster_ids = sorted({int(row["cluster"]) for row in rows})
    sheets = []
    for sheet_index, start in enumerate(range(0, len(cluster_ids), clusters_per_sheet), 1):
        ids = cluster_ids[start:start + clusters_per_sheet]
        sheet_rows = int(np.ceil(len(ids) / cols))
        sheet = Image.new("RGB", (cols * cell_w, sheet_rows * cell_h), "white")
        draw = ImageDraw.Draw(sheet)
        for idx, cluster_id in enumerate(ids):
            x = (idx % cols) * cell_w
            y = (idx // cols) * cell_h
            cluster_rows = [row for row in rows if int(row["cluster"]) == cluster_id][:per_cluster]
            draw.text((x + 4, y + 4), f"C{cluster_id:02d} n={sum(1 for row in rows if int(row['cluster']) == cluster_id)}", fill=(0, 0, 0), font=font)
            thumb_w, thumb_h = 84, 64
            for item_index, row in enumerate(cluster_rows):
                try:
                    img = Image.open(row["keyframe_path"]).convert("RGB")
                except Exception:
                    continue
                img.thumbnail((thumb_w, thumb_h))
                tx = x + 4 + (item_index % 2) * 88
                ty = y + 24 + (item_index // 2) * 72
                sheet.paste(img, (tx, ty))
                draw.text((tx, ty + img.height + 1), f"{row['video']} {row['id']}", fill=(0, 0, 0), font=font)
        path = os.path.join(out_dir, f"cluster_sheet_{sheet_index:02d}.jpg")
        sheet.save(path, quality=92)
        sheets.append(path)
    return sheets


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: python cluster_total_keyframes.py <total_dir> [cluster_count]")
        return 2
    root = sys.argv[1]
    cluster_count = int(sys.argv[2]) if len(sys.argv) == 3 else 48
    rows = load_rows(root)
    vectors = np.vstack([feature(row["keyframe_path"]) for row in rows])
    compactness, labels, centers = cv2.kmeans(
        vectors,
        cluster_count,
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 60, 0.01),
        4,
        cv2.KMEANS_PP_CENTERS,
    )
    for row, label in zip(rows, labels.flatten()):
        row["cluster"] = int(label)

    out_dir = os.path.join(root, "_cluster_preview")
    sheets = make_sheets(rows, out_dir)
    manifest = os.path.join(out_dir, "cluster_assignments.csv")
    keep_fields = ["video", "id", "cluster", "start", "end", "duration", "clip_path", "keyframe_path"]
    with open(manifest, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keep_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in keep_fields})
    summary = {
        "rows": len(rows),
        "clusters": cluster_count,
        "compactness": float(compactness),
        "manifest": manifest,
        "sheets": sheets,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
