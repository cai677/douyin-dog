import json,hashlib,shutil,itertools
from pathlib import Path
from datetime import datetime,timezone
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

T=Path(__file__).resolve().parent;R=T.parents[1];O=T/'matching-01'
plan=json.loads((O/'review-plan.json').read_text(encoding='utf-8'))
segments=plan['segments']; stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
export=T/'exports'/'260908-dy-trimmer-01.mp4';export.parent.mkdir(exist_ok=True)
if export.exists():raise RuntimeError('Preview already exists; do not overwrite reviewed output.')
selected=[s for s in segments if s['selected']]
pair_checks=[]
for a,b in itertools.combinations(selected,2):
 sa,sb=a['selected'],b['selected']
 d=[(int(x,16)^int(y,16)).bit_count() for x,y in zip(sa['visual_fingerprints'],sb['visual_fingerprints'])]
 same_group=sa['duplicate_group_id']==sb['duplicate_group_id']
 overlap=sa['source_sha256']==sb['source_sha256'] and max(sa['source_start_frame'],sb['source_start_frame'])<min(sa['source_end_frame_exclusive'],sb['source_end_frame_exclusive'])
 pair_checks.append({'a':a['id'],'b':b['id'],'phash_distances':d,'same_exact_group':same_group,'source_ranges_overlap':overlap,
                     'near_duplicate_candidate':max(d)<=12 and sum(d)<=24})
 if same_group or overlap:raise RuntimeError('Repeated content selected')
near=[p for p in pair_checks if p['near_duplicate_candidate']]
if near:raise RuntimeError('Near duplicate needs review: '+str(near))
triple=[]
for i in range(len(segments)-2):
 group=[s['selected']['source_group'] if s['selected'] else None for s in segments[i:i+3]]
 if group[0] is not None and len(set(group))==1:triple.append(i+1)
assert not triple
for s in selected:
 s['preview_approval']={'reviewer':'assistant','status':'approved_for_visual_preview_only',
                         'basis':'selected_interval_first_middle_last_frames_viewed',
                         'limitations':['exact_sku_unverified','burned_in_subtitles_retained','user_review_pending']}
for s in segments:
 for c in s['candidates']:
  if c['source_label']=='S15' or c['display_id'] in ['S37-007','S16-005','S37-016']:
   c['eligibility']='held_reference_visual_overlap'
  elif c['score']<.6:c['eligibility']='low_confidence'
  else:c['eligibility']='candidate_not_production_approved'
 if s['id']=='fragment14':
  for c in s['candidates']:
   if c['source_label']!='S15':c['eligibility']='rejected_missing_cat_interaction'
plan['preview_approved_count']=len(selected)
plan['production_approved_count']=0
plan['review_status']='pending_user_visual_review'
plan['adjacent_scene_review']={'status':'reviewed_with_exception',
  'exception':'fragment01→02 keep the same source/pet for trim-to-comparison continuity, composition changes from single action to double paws.',
  'other_transitions':'Different visible backgrounds or composition; repeated physical filming setups recur non-adjacently.',
  'identity_limit':'Different independent demonstration cats appear; only 01→02 retain the same source sequence. Do not imply all shots show one animal.'}
plan['dedup_checks']={'pair_count':len(pair_checks),'near_duplicate_candidates':near,'all_three_same_source_windows':triple,
                       'scope':'selected intervals and cached three-frame fingerprints; not proof of platform originality'}
plan['render_status']='pending'
for name in ['matches.json','fragment_plan.json']:
 p=T/name
 if p.exists():
  b=O/'backups';b.mkdir(exist_ok=True);shutil.copy2(p,b/(name+'.'+stamp))
 (T/name).write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'dedup-checks.json').write_text(json.dumps(pair_checks,ensure_ascii=False,indent=2),encoding='utf-8')

font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',30)
large=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',64)
medium=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',42)
def header(text):
 im=Image.new('RGB',(1080,84),'#172333');d=ImageDraw.Draw(im);d.text((30,22),text,font=font,fill='white')
 return cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR)
def slate(s):
 im=Image.new('RGB',(1080,1920),'#172333');d=ImageDraw.Draw(im)
 d.text((70,560),'缺素材 · '+s['id'][-2:],font=large,fill='#ffd285')
 d.text((70,700),s['requirement'],font=medium,fill='white')
 d.text((70,805),f"需补充至少 {s['duration_seconds']:.2f} 秒",font=medium,fill='white')
 d.text((70,1100),'此处保留原镜头时长',font=font,fill='#b7c6d8')
 d.text((70,1160),'未使用参考原片或无关画面填充',font=font,fill='#b7c6d8')
 return cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR)
def fit(frame):
 h,w=frame.shape[:2];scale=min(1080/w,1920/h);nw,nh=round(w*scale),round(h*scale)
 out=np.zeros((1920,1080,3),dtype=np.uint8);x,y=(1080-nw)//2,(1920-nh)//2
 out[y:y+nh,x:x+nw]=cv2.resize(frame,(nw,nh));return out
temp=export.with_name(export.stem+'.rendering.mp4')
writer=cv2.VideoWriter(str(temp),cv2.CAP_MSMF,cv2.VideoWriter_fourcc(*'H264'),60,(1080,1920))
if not writer.isOpened():raise RuntimeError('H264 writer unavailable')
frame_total=0;poster=[];timeline=[]
for n,s in enumerate(segments,1):
 count=round(s['timeline_end']*60)-round(s['timeline_start']*60)
 label=header(f'素材匹配预览 · {n:02d}/18 · '+(f"相似度 {s['confidence']:.3f}" if s['selected'] else '缺素材'))
 if s['selected']:
  sel=s['selected'];cap=cv2.VideoCapture(str(T/sel['material_path']));assert cap.isOpened()
  next_frame=sel['source_start_frame'];cap.set(cv2.CAP_PROP_POS_FRAMES,next_frame);frame=None
  for k in range(count):
   target=min(sel['source_end_frame_exclusive']-1,sel['source_start_frame']+int(k/60*sel['source_fps']))
   while next_frame<=target:
    ok,frame=cap.read()
    if not ok:raise RuntimeError('Source read failed')
    next_frame+=1
   out=fit(frame);out[:84]=label;writer.write(out)
   if k==count//2:poster.append(out.copy())
  cap.release()
 else:
  out=slate(s);out[:84]=label
  for k in range(count):writer.write(out)
  poster.append(out)
 frame_total+=count
 timeline.append({'id':s['id'],'start_frame':frame_total-count,'end_frame_exclusive':frame_total,
                   'kind':'selected_material' if s['selected'] else 'missing_material_card',
                   'source':s['selected'],'speed':1.0})
 print(f'Rendered {n}/18',flush=True)
writer.release()
check=cv2.VideoCapture(str(temp));decoded=0;wf=int(check.get(3));hf=int(check.get(4));fps=check.get(5)
fourcc=int(check.get(cv2.CAP_PROP_FOURCC));codec=''.join(chr((fourcc>>(8*i))&255) for i in range(4))
while True:
 ok,frame=check.read()
 if not ok:break
 decoded+=1
check.release()
assert decoded==frame_total==1902 and wf==1080 and hf==1920 and abs(fps-60)<.01
temp.replace(export)
summary=Image.new('RGB',(6*180,3*350),'white')
for i,frame in enumerate(poster):
 im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.thumbnail((180,320))
 summary.paste(im,((i%6)*180,(i//6)*350))
 ImageDraw.Draw(summary).text(((i%6)*180+5,(i//6)*350+321),f'{i+1:02d}',fill='black')
summary.save(O/'preview-overview.jpg')
validation={'status':'passed_video_decode','codec':codec,'width':wf,'height':hf,'fps':fps,'decoded_frames':decoded,
            'duration_seconds':decoded/fps,'target_difference_seconds':decoded/fps-31.7,'audio_tracks':0,
            'audio_evidence':'video-only Media Foundation writer; no audio supplied',
            'placeholder_ids':[s['id'] for s in segments if not s['selected']],
            'selected_score_min':min(s['confidence'] for s in selected),'selected_score_max':max(s['confidence'] for s in selected),
            'total_freeze_seconds':sum(s['selected']['freeze_seconds'] for s in selected),
            'source_hashes_after_render':{},'preview_sha256':hashlib.sha256(export.read_bytes()).hexdigest()}
for s in selected:
 sel=s['selected'];original=R/sel['source_original']
 good=hashlib.sha256(original.read_bytes()).hexdigest()==sel['source_sha256']==hashlib.sha256((T/sel['material_path']).read_bytes()).hexdigest()
 assert good;validation['source_hashes_after_render'][sel['display_id']]=good
(O/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'timeline.json').write_text(json.dumps({'schema_version':2,'fps':60,'segments':timeline},ensure_ascii=False,indent=2),encoding='utf-8')
plan['render_status']='visual_preview_generated';plan['preview_path']=str(export.relative_to(T));plan['validation_path']='matching-01/validation.json'
for name in ['matches.json','fragment_plan.json']:(T/name).write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
recipe_path=T/'recipe.json';recipe=json.loads(recipe_path.read_text(encoding='utf-8'))
shutil.copy2(recipe_path,O/'backups'/('recipe.json.'+stamp))
recipe['status']='matching_preview_ready_with_3_material_gaps'
recipe['matching']={'plan':'fragment_plan.json','matches':'matches.json','preview':str(export.relative_to(T)),
                     'selected_for_preview':15,'missing_material':3,'audio':'not_generated_for_this_preview'}
recipe_path.write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
history=R/'assets/history';history.mkdir(exist_ok=True)
with (history/'outputs.jsonl').open('a',encoding='utf-8') as f:
 f.write(json.dumps({'schema_version':2,'variant_id':'260908-dy-trimmer-01','status':'review_pending_incomplete_visual_preview',
                    'path':str(export.relative_to(R)),'sha256':validation['preview_sha256'],'duration_seconds':31.7,
                    'clip_ids':[s['selected']['clip_id'] for s in selected],'has_placeholders':True,'has_audio':False},ensure_ascii=False)+'\n')
print(json.dumps(validation,ensure_ascii=True),flush=True)
