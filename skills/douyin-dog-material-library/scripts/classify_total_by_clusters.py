import csv
import json
import os
import shutil
import sys


def safe_dir_name(value):
    invalid = '<>:"/\\|?*'
    return "".join("-" if ch in invalid else ch for ch in value).strip().strip(".")


def main():
    if len(sys.argv) != 4:
        print("usage: python classify_total_by_clusters.py <total_dir> <cluster_assignments.csv> <category_mapping.json>")
        return 2

    total_dir = sys.argv[1]
    assignments_path = sys.argv[2]
    mapping_path = sys.argv[3]
    with open(mapping_path, encoding="utf-8") as f:
        mapping = json.load(f)

    out_root = os.path.join(total_dir, "classified_by_content_中文")
    if os.path.exists(out_root):
        shutil.rmtree(out_root)
    os.makedirs(out_root, exist_ok=True)

    rows = []
    with open(assignments_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            cluster = str(int(row["cluster"]))
            content_type = mapping["cluster_categories"].get(cluster, "other")
            label = mapping["categories"][content_type]
            category_dir = os.path.join(out_root, safe_dir_name(label))
            os.makedirs(category_dir, exist_ok=True)

            source_clip = row["clip_path"]
            source_keyframe = row["keyframe_path"]
            clip_name = f"{row['video']}_{os.path.basename(source_clip)}"
            keyframe_name = os.path.splitext(clip_name)[0] + ".jpg"
            dest_clip = os.path.join(category_dir, clip_name)
            dest_keyframe = os.path.join(category_dir, keyframe_name)
            shutil.copy2(source_clip, dest_clip)
            if os.path.exists(source_keyframe):
                shutil.copy2(source_keyframe, dest_keyframe)

            rows.append(
                {
                    "video": row["video"],
                    "segment_id": row["id"],
                    "cluster": cluster,
                    "start": row["start"],
                    "end": row["end"],
                    "duration": row["duration"],
                    "content_type": content_type,
                    "content_label": label,
                    "source_clip": source_clip,
                    "classified_clip": dest_clip,
                    "classified_keyframe": dest_keyframe if os.path.exists(dest_keyframe) else "",
                }
            )

    index_path = os.path.join(out_root, "classified_index.csv")
    with open(index_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary_path = os.path.join(out_root, "category_summary.csv")
    counts = {}
    for row in rows:
        counts[row["content_label"]] = counts.get(row["content_label"], 0) + 1
    with open(summary_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["content_label", "count"])
        writer.writeheader()
        for label, count in sorted(counts.items()):
            writer.writerow({"content_label": label, "count": count})

    print(f"classified={len(rows)}")
    print(f"out_root={out_root}")
    print(f"index={index_path}")
    print(f"summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
