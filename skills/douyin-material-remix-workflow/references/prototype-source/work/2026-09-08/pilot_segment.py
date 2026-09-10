"""One-video pilot. Never mutates sources or existing matching approvals."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
OUT = ROOT / 'pilot-01'
OUT.mkdir(exist_ok=True)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def save(name, data):
    path = OUT / name
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)

files = sorted((PROJECT / 'assets/inbox').rglob('*'))
files = [p for p in files if p.is_file()]
ref_hash = digest(ROOT / 'reference-2026-09-08.mp4')
videos = []
for p in files:
    if p.suffix.lower() != '.mp4':
        continue
    before = p.stat()
    sha = digest(p)
    after = p.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError('Source changed while inspecting: ' + p.name)
    videos.append({'path': str(p.relative_to(PROJECT)), 'size': after.st_size,
                   'sha256': sha, 'is_reference_duplicate': sha == ref_hash})
save('inventory.json', {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
     'path_base': str(PROJECT), 'counts': {ext: sum(p.suffix.lower()==ext for p in files)
     for ext in sorted({p.suffix.lower() for p in files})}, 'videos': videos,
     'scope': 'all-file inventory and byte hashes only; one video decoded'})
selection = OUT / 'selection.json'
if selection.exists():
    selected = json.loads(selection.read_text(encoding='utf-8'))
else:
    selected = next(v for v in videos if not v['is_reference_duplicate'])
    save('selection.json', selected)
source = PROJECT / selected['path']
if digest(source) != selected['sha256']:
    raise RuntimeError('Selected source changed')
asset_id = 'asset_' + selected['sha256'][:16]
cap = cv2.VideoCapture(str(source))
if not cap.isOpened():
    raise RuntimeError('Cannot decode source')
fps = cap.get(cv2.CAP_PROP_FPS)
expected = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width, height = int(cap.get(3)), int(cap.get(4))
if fps <= 0 or expected <= 0:
    raise RuntimeError('Invalid media metadata')
small_frames, samples, scores = [], [], []
prev = None
count = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    small = cv2.resize(frame, (90,160))
    small_frames.append(small)
    if prev is not None:
        diff = float(np.abs(small.astype(np.float32)-prev.astype(np.float32)).mean())
        scores.append({'frame': count, 'seconds': count/fps, 'difference': diff})
    prev = small
    if count % max(1,round(fps)) == 0:
        samples.append((count, Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))))
    count += 1
cap.release()
if count != expected:
    raise RuntimeError(f'Decode count mismatch: {count} != {expected}')

def sheet(items, path, columns=6, w=180, h=345):
    board = Image.new('RGB', (columns*w, ((len(items)+columns-1)//columns)*h), '#f3f3f3')
    draw = ImageDraw.Draw(board)
    for i,(label,picture) in enumerate(items):
        picture = picture.copy()
        picture.thumbnail((w, h-26))
        x,y = i%columns*w, i//columns*h
        board.paste(picture, (x+(w-picture.width)//2,y))
        draw.text((x+4,y+h-22), str(label), fill='black')
    board.save(path)

sheet([(f'{i/fps:.2f}s f{i}',im) for i,im in samples], OUT/'overview.jpg')
cuts = []
for s in sorted(scores, key=lambda x:x['difference'], reverse=True):
    if s['difference'] >= 23 and all(abs(s['frame']-c) >= round(fps*.35) for c in cuts):
        cuts.append(s['frame'])
cuts.sort()
save('cut-scores.json', scores)
save('analysis.json', {'schema_version': 1, 'asset_id':asset_id,'source':selected,
 'fps':fps,'width':width,'height':height,'frame_count':count,'duration_seconds':count/fps,
 'full_decode_passed':True,'audio_status':'not_inspected','candidate_cuts':cuts,
 'status':'candidate_cuts_pending_visual_review'})
items=[]
cap=cv2.VideoCapture(str(source))
for n,(a,b) in enumerate(zip([0]+cuts,cuts+[count]),1):
    for tag,idx in [('S',a),('M',(a+b)//2),('E',b-1)]:
        cap.set(cv2.CAP_PROP_POS_FRAMES,idx)
        ok,frame=cap.read()
        if not ok: raise RuntimeError('Cannot extract review frame')
        items.append((f'{n:02d}{tag} {idx/fps:.2f}s',Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))))
cap.release()
for page,start in enumerate(range(0,len(items),24),1):
    sheet(items[start:start+24], OUT/f'candidate-sheet-{page:02d}.jpg',columns=6)
print(json.dumps({'selected':source.name,'asset_id':asset_id,'fps':fps,'duration':count/fps,
 'frames':count,'candidate_cuts':cuts,'reference_duplicates':[v['path'] for v in videos if v['is_reference_duplicate']],
 'unique_video_hashes':len({v['sha256'] for v in videos}), 'out':str(OUT)},ensure_ascii=True))
