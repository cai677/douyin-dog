import csv
import os
import shutil
import subprocess
import sys
import time


MEOWLOAD = r"E:\哼哼猫\MeowLoad\bin\meowload.exe"


def existing_mp4s(path):
    return {
        os.path.abspath(os.path.join(path, name))
        for name in os.listdir(path)
        if name.lower().endswith(".mp4")
    }


def download_one(url, output_dir, target_path):
    before = existing_mp4s(output_dir)
    result = subprocess.run(
        [
            MEOWLOAD,
            "download",
            url,
            "--media_type",
            "video",
            "--output-dir",
            output_dir,
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    after = existing_mp4s(output_dir)
    created = sorted(after - before, key=os.path.getmtime, reverse=True)
    if result.returncode != 0 or not created:
        return False, result.stdout[-2000:]

    src = created[0]
    if os.path.abspath(src) != os.path.abspath(target_path):
        if os.path.exists(target_path):
            os.remove(target_path)
        try:
            os.replace(src, target_path)
        except OSError:
            shutil.copy2(src, target_path)
            try:
                os.remove(src)
            except OSError:
                pass
    return True, ""


def main():
    if len(sys.argv) != 2:
        print("usage: python download_total_pending.py <source_manifest.csv>")
        return 2

    manifest_path = sys.argv[1]
    output_dir = os.path.dirname(os.path.abspath(manifest_path))
    with open(manifest_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    pending = [
        row
        for row in rows
        if row["status"] in ("pending_download", "failed_network") and not os.path.exists(row["path"] or os.path.join(output_dir, row["name"] + ".mp4"))
    ]
    failures = []
    for offset, row in enumerate(pending, 1):
        target = row["path"] or os.path.join(output_dir, row["name"] + ".mp4")
        print(f"[{offset:03d}/{len(pending):03d}] {row['name']} {row['video_id']}", flush=True)
        ok, output = download_one(row["url"], output_dir, target)
        if ok:
            row["status"] = "downloaded"
            row["action"] = "download"
            row["path"] = target
            print(f"  ok {target}", flush=True)
        else:
            failures.append((row, output))
            print(f"  failed {output}", flush=True)
        time.sleep(0.5)

        with open(manifest_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    if failures:
        fail_path = os.path.join(output_dir, "download_failures.txt")
        with open(fail_path, "w", encoding="utf-8") as f:
            for row, output in failures:
                f.write(f"{row['name']}\t{row['video_id']}\t{row['url']}\n{output}\n\n")
        print(f"failures={len(failures)}")
        print(f"failure_log={fail_path}")
        return 1

    print(f"downloaded={len(pending)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
