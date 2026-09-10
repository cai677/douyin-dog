"""Incremental local video segmentation. Raw sources remain read-only."""
import json, hashlib, traceback, math
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent.parent
RUN=ROOT/'batch-library'
CAT=PROJECT/'assets/catalog'
RUN.mkdir(exist_ok=True)
CAT.mkdir(exist_ok=True)
VERSION='frame_diff23_gap035_v2'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_suffix(path.suffix+'.tmp')
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    t.replace(path)

def phash(frame):
    g=cv2.resize(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),(32,32)).astype(np.float32)
    low=cv2.dct(g)[:8,:8].flatten()
    return f'{int("".join("1" if v>np.median(low[1:]) else "0" for v in low),2):016x}'

files=sorted((PROJECT/'assets/inbox').rglob('*.mp4'))
refsha=sha(ROOT/'reference-2026-09-08.mp4')
inventory=[]
previous_path=RUN/'inventory.json'
previous=json.loads(previous_path.read_text(encoding='utf-8'))['videos'] if previous_path.exists() else []
known={e['sha256']:e for e in previous}
next_number=max([int(e['source_label'][1:]) for e in previous]+[0])+1
seen={}
for p in files:
    stat=p.stat(); h=sha(p)
    if (stat.st_size,stat.st_mtime_ns)!=(p.stat().st_size,p.stat().st_mtime_ns): raise RuntimeError('Input still changing')
    relative_path=str(p.relative_to(PROJECT)).replace('\\','/')
    if h in seen:
        seen[h]['aliases'].append(relative_path)
        continue
    stable_label=known[h]['source_label'] if h in known else f'S{next_number:02d}'
    if h not in known: next_number+=1
    entry={'source_label':stable_label,'asset_id':'asset_'+h[:16], 'sha256':h,
        'path':str(p.relative_to(PROJECT)).replace('\\','/'),'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,
        'aliases':[relative_path],'role':'reference_duplicate' if h==refsha else 'production_candidate'}
    inventory.append(entry);seen[h]=entry
write(RUN/'inventory.json',{'schema_version':1,'created_at':datetime.now(timezone.utc).isoformat(),
                          'path_base':str(PROJECT),'videos':inventory})

def ingest(entry):
    cv2.setNumThreads(1)
    aid=entry['asset_id']; label=entry['source_label']; source=PROJECT/entry['path']
    folder=CAT/'analysis'/aid
    manifest=folder/'segments.json'
    if manifest.exists():
        old=json.loads(manifest.read_text(encoding='utf-8'))
        if old.get('tool_version')==VERSION and old.get('source',{}).get('sha256')==entry['sha256'] and all((PROJECT/c['preview']).exists() for c in old['clips']):
            old['source']=entry
            for c in old['clips']:
                c['source_path']=entry['path']
            write(manifest,old)
            print(label+' cached '+str(len(old['clips'])),flush=True)
            return old
    folder.mkdir(parents=True,exist_ok=True)
    cap=cv2.VideoCapture(str(source))
    fps=cap.get(cv2.CAP_PROP_FPS); expected=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width,height=int(cap.get(3)),int(cap.get(4))
    if not cap.isOpened() or fps<=0 or expected<=0: raise RuntimeError('Invalid source')
    frames=[]; scores=[]; prev=None
    while True:
        ok,f=cap.read()
        if not ok: break
        # Low resolution frames are sufficient for cut detection and silent browsing proxies.
        scale=min(320/width,568/height)
        w=max(2,int(width*scale)//2*2); h=max(2,int(height*scale)//2*2)
        preview=cv2.resize(f,(w,h))
        frames.append(preview)
        small=cv2.resize(f,(90,160))
        if prev is not None: scores.append((len(frames)-1,float(np.abs(small.astype(np.float32)-prev.astype(np.float32)).mean())))
        prev=small
    cap.release()
    if len(frames)!=expected: raise RuntimeError(f'Decode mismatch {len(frames)} != {expected}')
    cuts=[]
    for idx,diff in sorted(scores,key=lambda x:x[1],reverse=True):
        if diff>=23 and all(abs(idx-c)>=max(1,round(fps*.35)) for c in cuts): cuts.append(idx)
    cuts.sort()
    # Reuse the pilot's already reviewed boundaries rather than re-cutting that source.
    pilot=ROOT/'pilot-01/segments.json'
    pilot_data=json.loads(pilot.read_text(encoding='utf-8'))
    reused=pilot_data.get('source_sha256')==entry['sha256']
    if reused: cuts=[c['source_start_frame'] for c in pilot_data['clips'][1:]]
    boundaries=[0]+cuts+[expected]
    clipdir=CAT/'previews'/aid; clipdir.mkdir(parents=True,exist_ok=True)
    framedir=CAT/'frames'/aid; framedir.mkdir(parents=True,exist_ok=True)
    clips=[]; cards=[]
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
    for n,(start,end) in enumerate(zip(boundaries,boundaries[1:]),1):
        cid=f'{aid}_{start:06d}_{end:06d}'
        path=clipdir/(cid+'.mp4')
        writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
        if not writer.isOpened(): raise RuntimeError('Cannot create preview')
        for f in frames[start:end]: writer.write(f)
        writer.release()
        check=cv2.VideoCapture(str(path)); decoded=0
        while True:
            ok,_=check.read()
            if not ok: break
            decoded+=1
        check.release()
        if decoded!=end-start: raise RuntimeError('Output validation failed')
        ids=[start,(start+end)//2,end-1]
        paths=[]
        for tag,idx in zip(['start','middle','end'],ids):
            fp=framedir/(cid+'-'+tag+'.jpg'); cv2.imwrite(str(fp),frames[idx]); paths.append(str(fp.relative_to(PROJECT)).replace('\\','/'))
        c={'clip_id':cid,'display_id':f'{label}-{n:03d}','asset_id':aid,'source_label':label,
            'source_path':entry['path'],'source_start_frame':start,'source_end_frame_exclusive':end,
            'fps':fps,'start_seconds':start/fps,'end_seconds':end/fps,'duration_seconds':(end-start)/fps,
            'preview':str(path.relative_to(PROJECT)).replace('\\','/'),'preview_audio':False,
            'preview_width':w,'preview_height':h,'preview_full_decode_passed':True,
            'frames':dict(zip(['start','middle','end'],paths)),
            'visual_fingerprints':[phash(frames[idx]) for idx in ids],
            'fingerprint_method':'dct32_low8_median_ac_v1',
            'boundary_status':'pilot_frame_reviewed' if reused else 'automatic_candidate',
            'classification_status':'pending_visual_review','production_approval':'not_approved',
            'source_role':entry['role'],'product_family':'pet-trimmer','sku':'unverified'}
        clips.append(c)
        card=Image.new('RGB',(180,350),'white'); image=Image.fromarray(cv2.cvtColor(frames[ids[1]],cv2.COLOR_BGR2RGB)); image.thumbnail((180,310))
        card.paste(image,((180-image.width)//2,0)); d=ImageDraw.Draw(card)
        d.text((3,312),f'{label}-{n:03d} {start/fps:.1f}s',font=font,fill='black')
        d.text((3,331),f'{(end-start)/fps:.2f}s',font=font,fill='#555555')
        cards.append(card)
    sheetdir=RUN/'sheets'; sheetdir.mkdir(exist_ok=True)
    sheetpaths=[]
    for page,offset in enumerate(range(0,len(cards),24),1):
        chunk=cards[offset:offset+24]; board=Image.new('RGB',(1080,350*math.ceil(len(chunk)/6)),'#eeeeee')
        for j,card in enumerate(chunk): board.paste(card,(j%6*180,j//6*350))
        p=sheetdir/f'{label}-{page:02d}.jpg'; board.save(p); sheetpaths.append(str(p.relative_to(PROJECT)).replace('\\','/'))
    if sha(source)!=entry['sha256']: raise RuntimeError('Source changed during processing')
    data={'schema_version':2,'tool_version':VERSION,'created_at':datetime.now(timezone.utc).isoformat(),
        'source':entry,'path_base':str(PROJECT),'fps':fps,'width':width,'height':height,
        'frame_count':expected,'duration_seconds':expected/fps,'full_decode_passed':True,
        'source_hash_unchanged':True,'audio_analysis':'not_run','pilot_boundaries_reused':reused,'sheets':sheetpaths,'clips':clips}
    write(manifest,data)
    print(label+' done '+str(len(clips))+' clips '+str(round(expected/fps,1))+'s',flush=True)
    return data

if __name__=='__main__':
    results=[]; errors=[]
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures={executor.submit(ingest,e):e for e in inventory}
        for fut in as_completed(futures):
            e=futures[fut]
            try: results.append(fut.result())
            except Exception as exc:
                errors.append({'source':e,'error':str(exc),'traceback':traceback.format_exc()});print(e['source_label']+' ERROR '+str(exc),flush=True)
            write(RUN/'progress.json',{'complete':len(results),'total':len(inventory),'errors':errors})
    write(RUN/'ingest-summary.json',{'sources':len(results),'clips':sum(len(r['clips']) for r in results),'errors':errors,
          'manifests':[str((CAT/'analysis'/r['source']['asset_id']/'segments.json').relative_to(PROJECT)).replace('\\','/') for r in sorted(results,key=lambda r:r['source']['source_label'])]})
    print('FINISHED '+str(len(results))+' sources, '+str(sum(len(r['clips']) for r in results))+' clips',flush=True)
