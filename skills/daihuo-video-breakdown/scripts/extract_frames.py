# -*- coding: utf-8 -*-
"""
拆片抽帧脚本：从带货视频中提取关键帧 + 检测镜头切换点
用法: python extract_frames.py <视频路径> [输出目录] [抽帧间隔秒数]
输出: 帧图片（带时间戳文件名）+ 镜头切分清单 JSON
"""
import sys, os, json
import cv2
import numpy as np

def main():
    if len(sys.argv) < 2:
        print("用法: python extract_frames.py <视频路径> [输出目录] [间隔秒]")
        sys.exit(1)

    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"错误: 找不到视频文件 {video_path}")
        sys.exit(1)

    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(video_path)),
        "frames_" + os.path.splitext(os.path.basename(video_path))[0])
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5

    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("错误: 无法打开视频")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps
    step = max(1, int(fps * interval))
    print(f"视频: {os.path.basename(video_path)}")
    print(f"时长: {duration:.1f}s | FPS: {fps:.1f} | 总帧: {total}")
    print(f"抽帧间隔: {interval}s (每 {step} 帧取一帧)")

    frames_info = []
    prev_hist = None
    shot_id = 1
    shot_boundaries = []
    idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0:
            t = idx / fps
            # 缩小分辨率做直方图比较（镜头切换检测）
            small = cv2.resize(frame, (160, 160))
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [30, 30], [0, 180, 0, 256])
            cv2.normalize(hist, hist)

            is_cut = False
            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                if diff > 0.55:  # 阈值可调
                    is_cut = True
                    shot_id += 1
                    shot_boundaries.append(round(t, 2))
            prev_hist = hist

            fname = f"t{t:06.2f}s_shot{shot_id:02d}.jpg"
            fpath = os.path.join(out_dir, fname)
            # 限制保存尺寸，控制文件大小
            h, w = frame.shape[:2]
            if w > 720:
                scale = 720 / w
                frame = cv2.resize(frame, (720, int(h * scale)))
            # Windows 中文路径兼容：cv2.imwrite 不支持非 ASCII 路径，用 imencode 写入
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                with open(fpath, "wb") as fp:
                    fp.write(buf.tobytes())
            frames_info.append({
                "file": fname, "time": round(t, 2),
                "shot": shot_id, "is_cut": is_cut})
        idx += 1

    cap.release()

    # 镜头时长统计
    shots = []
    bounds = [0.0] + shot_boundaries + [round(duration, 2)]
    for i in range(len(bounds) - 1):
        shots.append({
            "shot": i + 1,
            "start": bounds[i], "end": bounds[i + 1],
            "duration": round(bounds[i + 1] - bounds[i], 2)})

    result = {
        "video": os.path.basename(video_path),
        "duration": round(duration, 2),
        "fps": round(fps, 1),
        "frame_interval": interval,
        "frames_extracted": len(frames_info),
        "shots": shots}
    with open(os.path.join(out_dir, "shot_list.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n完成: 提取 {len(frames_info)} 帧, 检测到 {len(shots)} 个镜头")
    print(f"输出目录: {out_dir}")
    print("\n镜头切分:")
    for s in shots:
        print(f"  镜头{s['shot']}: {s['start']}s - {s['end']}s (时长 {s['duration']}s)")

if __name__ == "__main__":
    main()
