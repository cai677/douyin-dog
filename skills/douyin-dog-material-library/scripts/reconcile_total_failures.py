import csv
import os
import re
import sys


def classify(output):
    lowered = output.lower()
    if "private or restricted" in lowered:
        return "failed_private_or_restricted"
    if "deleted or doesn't exist" in lowered:
        return "failed_deleted_or_missing"
    if "network error" in lowered or "request timed out" in lowered:
        return "failed_network"
    return "failed_other"


def parse_failure_log(path):
    if not os.path.exists(path):
        return {}
    text = open(path, encoding="utf-8").read()
    blocks = re.split(r"\n\s*\n", text.strip())
    failures = {}
    for block in blocks:
        lines = block.splitlines()
        if not lines:
            continue
        fields = lines[0].split("\t")
        if len(fields) < 3:
            continue
        name, video_id, url = fields[:3]
        failures[name] = {
            "video_id": video_id,
            "url": url,
            "status": classify(block),
        }
    return failures


def main():
    if len(sys.argv) != 2:
        print("usage: python reconcile_total_failures.py <source_manifest.csv>")
        return 2

    manifest = sys.argv[1]
    total_dir = os.path.dirname(os.path.abspath(manifest))
    failures = parse_failure_log(os.path.join(total_dir, "download_failures.txt"))
    with open(manifest, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    counts = {}
    for row in rows:
        target = row["path"] or os.path.join(total_dir, row["name"] + ".mp4")
        if os.path.exists(target):
            if row["status"] == "pending_download":
                row["status"] = "downloaded"
                row["action"] = "download"
                row["path"] = target
        elif row["name"] in failures:
            row["status"] = failures[row["name"]]["status"]
            row["path"] = ""
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    with open(manifest, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    retry_path = os.path.join(total_dir, "retry_network_urls.txt")
    with open(retry_path, "w", encoding="utf-8") as f:
        for row in rows:
            if row["status"] == "failed_network":
                f.write(row["url"] + "\n")

    for key in sorted(counts):
        print(f"{key}={counts[key]}")
    print(f"retry_network_urls={retry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
