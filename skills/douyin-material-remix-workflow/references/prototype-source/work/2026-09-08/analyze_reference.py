import cv2
import numpy as np
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'reference-2026-09-08.mp4'
OUT = ROOT / 'video_clips'
OUT.mkdir(exist_ok=True)
cap = cv2.VideoCapture(str(SOURCE))
fps = cap.get(cv2.CAP_PROP_FPS)
count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width, height = int(cap.get(3)), int(cap.get(4))
previous = None
scores = []
samples = []
index = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    small = cv2.resize(frame, (90, 160))
    if previous is not None:
        difference = float(np.abs(small.astype(float) - previous.astype(float)).mean())
        scores.append({'frame': index, 'time': round(index / fps, 3), 'difference': round(difference, 3)})
    previous = small
    if index % round(fps) == 0:
        samples.append((index / fps, Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))))
    index += 1
cap.release()
# Candidate cuts need visual review: fast hand movement may also trigger a cut.
candidates = []
for score in sorted(scores, key=lambda s: s['difference'], reverse=True):
    if score['difference'] >= 23 and all(abs(score['frame'] - other['frame']) >= round(fps * .4) for other in candidates):
        candidates.append(score)
candidates.sort(key=lambda s: s['frame'])
boundaries = [0] + [s['frame'] for s in candidates] + [count]
segments = []
cap = cv2.VideoCapture(str(SOURCE))
for number, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1):
    midpoint = (start + end) // 2
    cap.set(cv2.CAP_PROP_POS_FRAMES, midpoint)
    ok, frame = cap.read()
    filename = f'fragment{number:02d}-reference.jpg'
    if ok:
        cv2.imwrite(str(OUT / filename), frame)
    segments.append({'id': f'fragment{number:02d}', 'start_frame': start, 'end_frame_exclusive': end,
                     'start_seconds': start / fps, 'end_seconds': end / fps,
                     'duration_seconds': (end - start) / fps, 'reference_frame': 'video_clips/' + filename,
                     'status': 'candidate_needs_visual_review'})
cap.release()
sheet = Image.new('RGB', (6 * 180, ((len(samples) + 5) // 6) * 350), 'white')
draw = ImageDraw.Draw(sheet)
for i, (time, picture) in enumerate(samples):
    picture.thumbnail((180, 320))
    x, y = (i % 6) * 180, (i // 6) * 350
    sheet.paste(picture, (x, y))
    draw.text((x + 5, y + 323), f'{time:.1f}s', fill='black')
sheet.save(OUT / 'overview.jpg')
report = {'duration_seconds': count / fps, 'fps': fps, 'frame_count': count,
          'width': width, 'height': height, 'audio_status': 'not_inspected',
          'method': 'adjacent_frame_mean_absolute_difference_threshold_23_min_gap_0.4s',
          'segments': segments}
(ROOT / 'reference-analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(ROOT / 'cut-scores.json').write_text(json.dumps(scores), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
