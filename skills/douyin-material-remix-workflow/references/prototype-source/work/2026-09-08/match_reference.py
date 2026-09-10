import json, hashlib
from pathlib import Path
from datetime import datetime, timezone
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[1]
OUT = TASK / 'matching-01'
OUT.mkdir(exist_ok=True)
recipe = json.loads((TASK/'recipe.json').read_text(encoding='utf-8'))
clips = [json.loads(s) for s in (ROOT/'assets/catalog/clips.jsonl').read_text(encoding='utf-8').splitlines()]
assets = [json.loads(s) for s in (ROOT/'assets/catalog/assets.jsonl').read_text(encoding='utf-8').splitlines()]
requirements = [
 ('脚毛修剪开场',['trim'],'c',True), ('脚掌前后效果',['result'],'c',False),
 ('脚毛与肉垫细节',['detail'],'c',False), ('猫砂盆出入',['litter'],'c',False),
 ('猫舔脚',['lick'],'c',False), ('脚毛修剪近景',['trim'],'c',True),
 ('脚掌修剪侧面',['trim'],'c',True), ('猫行走或打滑',['walk'],'c',False),
 ('猫与电推外观',['product'],'cn',True), ('小刀头修脚毛',['trim'],'c',True),
 ('侧面修剪动作',['trim'],'c',True), ('刀头圆角特写',['blade'],'cn',True),
 ('手臂接触演示',['contact'],'cn',True), ('猫靠近电推',['pet','product'],'c',True),
 ('带灯脚毛修剪',['trim'],'c',True), ('脚毛修剪收尾',['trim'],'c',True),
 ('干净肉垫效果',['result','detail'],'c',False), ('两只脚掌效果收尾',['result'],'c',False)]

def read(path):
    data=np.fromfile(str(path),dtype=np.uint8)
    result=cv2.imdecode(data,cv2.IMREAD_COLOR)
    if result is None: raise RuntimeError(str(path))
    return result

def feature(im):
    # Use the central area to reduce influence of burned-in bottom subtitles.
    im=im[int(im.shape[0]*.05):int(im.shape[0]*.82)]
    im=cv2.resize(im,(72,112))
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
    hist=cv2.calcHist([hsv],[0,1],None,[18,8],[0,180,0,256]); hist/=hist.sum()
    gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    layout=cv2.resize(cv2.cvtColor(im,cv2.COLOR_BGR2LAB),(6,8)).astype(float)/255
    edges=cv2.resize(cv2.Canny(gray,60,140),(6,8)).astype(float)/255
    return hist,float(gray.mean())/255,layout,edges

def compare(a,b):
    color=float(np.sqrt(a[0]*b[0]).sum())
    bright=max(0,1-abs(a[1]-b[1])*2)
    layout=max(0,1-float(np.abs(a[2]-b[2]).mean())*3)
    edges=max(0,1-float(np.abs(a[3]-b[3]).mean())*2)
    return {'color':round(color,4),'brightness':round(bright,4),'composition':round(layout,4),
            'edge_layout':round(edges,4),'score':round(.35*color+.15*bright+.35*layout+.15*edges,4)}

changed=[]
for a in assets:
    p=ROOT/a['path']
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=a['sha256']:
        changed.append(a['asset_id'])
if changed: raise RuntimeError('Catalog sources changed: '+str(changed))
valid=[c for c in clips if c['library_status']!='hold' and c['source_role']=='production_candidate' and c['asset_id'] not in changed]
features={}
for c in valid:
    features[c['clip_id']]=[(k,feature(read(ROOT/p))) for k,p in c['frames'].items()]
rankings=[]
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
for segment,req in zip(recipe['segments'],requirements):
    name,actions,species,product=req
    ref=feature(read(TASK/segment['reference_frame']))
    candidates=[]
    for c in valid:
        if c['action'] not in actions or c['species'] not in species: continue
        if product and c['product_color']!='l': continue
        if c['duration_seconds']<min(.8,segment['duration_seconds']*.45): continue
        metrics=[(k,compare(ref,f)) for k,f in features[c['clip_id']]]
        metrics.sort(key=lambda v:v[1]['score'],reverse=True)
        candidates.append({'display_id':c['display_id'],'clip_id':c['clip_id'],
                           'score':metrics[0][1]['score'],'best_frame':metrics[0][0],
                           'components':metrics[0][1], 'duration_seconds':c['duration_seconds'],
                           'source_label':c['source_label'], 'action':c['action'],
                           'requires_freeze':max(0,segment['duration_seconds']-c['duration_seconds'])})
    candidates.sort(key=lambda x:x['score']-.06*min(x['requires_freeze'],2),reverse=True)
    rankings.append({'id':segment['id'],'requirement':name,'reference_frame':segment['reference_frame'],
                     'duration_seconds':segment['duration_seconds'],'candidates':candidates})
mapping={c['clip_id']:c for c in clips}
for page in range(0,len(rankings),3):
    sheet=Image.new('RGB',(6*200,3*410),'#f0f0f0'); d=ImageDraw.Draw(sheet)
    for row,r in enumerate(rankings[page:page+3]):
        entries=[('REF '+r['id'],TASK/r['reference_frame'],r['requirement'])]
        # Show different sources to avoid a top list of near-identical shots.
        seen=set()
        for cand in r['candidates']:
            if cand['source_label'] in seen: continue
            seen.add(cand['source_label']); c=mapping[cand['clip_id']]
            entries.append((f"{cand['display_id']} {cand['score']:.3f}",ROOT/c['frames'][cand['best_frame']],f"{c['duration_seconds']:.2f}s {c['action']}"))
            if len(entries)==6: break
        for col,(title,path,footer) in enumerate(entries):
            image=Image.open(path).convert('RGB'); image.thumbnail((196,348))
            x,y=col*200,row*410
            sheet.paste(image,(x+(200-image.width)//2,y+25))
            d.text((x+4,y+3),title,font=font,fill='black')
            d.text((x+4,y+376),footer,font=font,fill='black')
    sheet.save(OUT/f'candidates-{page//3+1:02d}.jpg')
report={'schema_version':2,'generated_at':datetime.now(timezone.utc).isoformat(),
        'path_base':str(ROOT),'reference_path_base':str(TASK),
        'source_count_verified':len(assets),'indexed_clip_count':len(clips),'eligible_clip_count':len(valid),
        'keyframes_reused':sum(len(c['frames']) for c in valid),'threshold':.6,
        'score_meaning':'heuristic_visual_similarity_not_calibrated_probability',
        'weights':{'color':.35,'brightness':.15,'composition':.35,'edge_layout':.15},
        'segments':rankings}
(OUT/'rankings.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Source hashes verified:',len(assets),'keyframes compared:',report['keyframes_reused'])
for r in rankings: print(r['id'],len(r['candidates']),[(c['display_id'],c['score']) for c in r['candidates'][:3]])
