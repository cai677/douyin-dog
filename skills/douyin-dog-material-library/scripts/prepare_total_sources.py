import csv
import os
import re
import sys


REUSE_BY_ID = {
    "7685292148148686115": r"E:\chatgpt\daihuo-cutfactory\滴眼液\滴眼液-01.mp4",
    "7677137458732446312": r"E:\chatgpt\daihuo-cutfactory\滴眼液\滴眼液-03.mp4",
    "7683436284190264582": r"E:\chatgpt\daihuo-cutfactory\滴眼液\滴眼液-04.mp4",
    "7683435920732753161": r"E:\chatgpt\daihuo-cutfactory\滴眼液\滴眼液-05.mp4",
    "7687893676214832411": r"E:\chatgpt\daihuo-cutfactory\滴眼液\滴眼液-06.mp4",
    "7684283660803840441": r"E:\chatgpt\daihuo-cutfactory\滴眼液\滴眼液-07.mp4",
    "7674159272218346230": r"E:\chatgpt\daihuo-cutfactory\滴眼液\滴眼液-10.mp4",
}


def read_ids(path):
    seen = set()
    ids = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            match = re.search(r"\d{16,20}", line)
            if not match:
                continue
            video_id = match.group(0)
            if video_id not in seen:
                seen.add(video_id)
                ids.append(video_id)
    return ids


def ensure_hardlink_or_copy(src, dst):
    if os.path.exists(dst):
        return "exists"
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        import shutil

        shutil.copy2(src, dst)
        return "copy"


def main():
    if len(sys.argv) != 3:
        print("usage: python prepare_total_sources.py <id_file> <total_dir>")
        return 2

    id_file = sys.argv[1]
    total_dir = sys.argv[2]
    os.makedirs(total_dir, exist_ok=True)

    rows = []
    ids = read_ids(id_file)
    for index, video_id in enumerate(ids, 1):
        name = f"total-{index:03d}"
        url = f"https://www.douyin.com/video/{video_id}"
        target = os.path.join(total_dir, name + ".mp4")
        source = REUSE_BY_ID.get(video_id, "")
        status = "pending_download"
        action = ""
        if source and os.path.exists(source):
            action = ensure_hardlink_or_copy(source, target)
            status = "reused_existing"
        elif os.path.exists(target):
            status = "existing_total"
            action = "exists"
        rows.append(
            {
                "index": index,
                "name": name,
                "video_id": video_id,
                "url": url,
                "status": status,
                "action": action,
                "path": target if os.path.exists(target) else "",
                "reused_from": source,
            }
        )

    manifest = os.path.join(total_dir, "source_manifest.csv")
    with open(manifest, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    pending = [row for row in rows if row["status"] == "pending_download"]
    pending_path = os.path.join(total_dir, "pending_urls.txt")
    with open(pending_path, "w", encoding="utf-8") as f:
        for row in pending:
            f.write(row["url"] + "\n")

    print(f"unique={len(rows)}")
    print(f"reused={sum(1 for row in rows if row['status'] == 'reused_existing')}")
    print(f"existing_total={sum(1 for row in rows if row['status'] == 'existing_total')}")
    print(f"pending_download={len(pending)}")
    print(f"manifest={manifest}")
    print(f"pending_urls={pending_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
