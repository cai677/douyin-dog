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


def unique_target(output_dir, product_name, index):
    return os.path.join(output_dir, f"{product_name}-{index:02d}.mp4")


def download_one(url, output_dir, product_name, index):
    before = existing_mp4s(output_dir)
    command = [
        MEOWLOAD,
        "download",
        url,
        "--media_type",
        "video",
        "--output-dir",
        output_dir,
    ]
    result = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    after = existing_mp4s(output_dir)
    created = sorted(after - before, key=os.path.getmtime, reverse=True)
    if result.returncode != 0 or not created:
        return {
            "index": index,
            "url": url,
            "ok": False,
            "output": result.stdout[-2000:],
        }

    src = created[0]
    dst = unique_target(output_dir, product_name, index)
    if os.path.abspath(src) != os.path.abspath(dst):
        try:
            os.replace(src, dst)
        except OSError:
            shutil.copy2(src, dst)
            try:
                os.remove(src)
            except OSError:
                pass

    return {
        "index": index,
        "url": url,
        "ok": True,
        "path": dst,
        "size": os.path.getsize(dst),
    }


def main():
    if len(sys.argv) < 4:
        print("usage: python download_douyin_batch.py <product_name> <output_dir> [--start N] <url> [<url> ...]")
        return 2

    product_name = sys.argv[1]
    output_dir = sys.argv[2]
    args = sys.argv[3:]
    start = 1
    if args[:1] == ["--start"]:
        start = int(args[1])
        args = args[2:]
    urls = args
    os.makedirs(output_dir, exist_ok=True)

    failures = []
    for offset, url in enumerate(urls):
        index = start + offset
        print(f"[{offset + 1:02d}/{len(urls):02d}] downloading {url}", flush=True)
        item = download_one(url, output_dir, product_name, index)
        if item["ok"]:
            print(f"[{index:02d}] ok {item['path']} {item['size']} bytes", flush=True)
        else:
            failures.append(item)
            print(f"[{index:02d}] failed {item['output']}", flush=True)
        time.sleep(0.5)

    if failures:
        print("failures:")
        for item in failures:
            print(f"- {item['index']:02d} {item['url']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
