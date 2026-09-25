import csv
import json
import os
import shutil
import sys


def clip_name_for(video_name, row):
    source_name = os.path.basename(row["clip"])
    return f"{video_name}_{source_name}"


def safe_dir_name(value):
    invalid = '<>:"/\\|?*'
    cleaned = "".join("-" if ch in invalid else ch for ch in value)
    return cleaned.strip().strip(".")


def category_dir_name(content_type, categories, use_chinese=False):
    value = categories[content_type] if use_chinese else content_type
    return safe_dir_name(value)


def classify_product(product_dir, mapping_path, output_name="classified_by_content", use_chinese=False):
    with open(mapping_path, encoding="utf-8") as f:
        mapping = json.load(f)

    out_root = os.path.join(product_dir, output_name)
    os.makedirs(out_root, exist_ok=True)

    rows = []
    for video_name, segment_map in mapping["videos"].items():
        material_dir = os.path.join(product_dir, video_name, "material_auto")
        index_path = os.path.join(material_dir, "material_index.csv")
        with open(index_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                segment_id = row["id"]
                content_type = segment_map[segment_id]
                category_dir = os.path.join(
                    out_root,
                    category_dir_name(content_type, mapping["categories"], use_chinese=use_chinese),
                )
                os.makedirs(category_dir, exist_ok=True)

                source_clip = os.path.join(material_dir, row["clip"])
                dest_name = clip_name_for(video_name, row)
                dest_clip = os.path.join(category_dir, dest_name)
                shutil.copy2(source_clip, dest_clip)

                rows.append({
                    "video": video_name,
                    "segment_id": segment_id,
                    "start": row["start"],
                    "end": row["end"],
                    "duration": row["duration"],
                    "content_type": content_type,
                    "content_label": mapping["categories"][content_type],
                    "source_clip": source_clip,
                    "classified_clip": dest_clip,
                })

    summary_path = os.path.join(out_root, "classified_index.csv")
    with open(summary_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return out_root, rows


def main():
    if len(sys.argv) not in (3, 4):
        print("usage: python classify_materials.py <product_dir> <mapping_json> [--chinese]")
        return 2

    use_chinese = len(sys.argv) == 4 and sys.argv[3] == "--chinese"
    output_name = "classified_by_content_中文" if use_chinese else "classified_by_content"
    out_root, rows = classify_product(sys.argv[1], sys.argv[2], output_name=output_name, use_chinese=use_chinese)
    print(f"classified={len(rows)}")
    print(out_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
