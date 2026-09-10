import json,uuid,copy,shutil,time,hashlib
from pathlib import Path
import cv2
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent;T=O.parent;E=O/'full-xionger-rate50';V=O/'voice-zh_male_xionger_mars_bigtts-rate50';P=T/'jianying_draft';D=P/'260909-dy-trimmer-xionger-01';M=D/'materials'
if D.exists():raise RuntimeError('Draft already exists; preserve existing output')
M.mkdir(parents=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def uid():return str(uuid.uuid4()).upper()
def us(x):return round(x*1000000)
tl=read(E/'timeline.json');voice=read(V/'voice-report.json');old=read(P/'260908-dy-trimmer-voice01/draft_content.json');doc=copy.deepcopy(old);draftid=uid();doc.update(id=draftid,name=D.name,duration=us(tl['duration_seconds']))
protos={tr['type']:copy.deepcopy(tr['segments'][0]) for tr in old['tracks']}
doc['materials']={k:[] for k in old['materials']};doc['tracks']=[]
for typ,name in [('video','画面与缺素材提示'),('audio','熊二配音'),('text','字幕')]:doc['tracks'].append(dict(attribute=0,flag=0,id=uid(),is_default_name=False,name=name,type=typ,segments=[]))
materials=doc['materials'];cache={};checks=[]
def copied(p):
 dest=M/p.name
 if not dest.exists():shutil.copy2(p,dest)
 assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(dest.read_bytes()).digest()
 return dest
def video_material(p,photo=False):
 if str(p) in cache:return cache[str(p)]
 m=copy.deepcopy(old['materials']['videos'][0]);mid=uid()
 if photo:w,h=Image.open(p).size;duration=10800000000
 else:
  c=cv2.VideoCapture(str(p));assert c.isOpened();w,h=int(c.get(3)),int(c.get(4));duration=us(c.get(7)/c.get(5));c.release()
 m.update(id=mid,material_id=mid,path=str(p),material_name=p.name,type='photo' if photo else 'video',duration=duration,width=w,height=h);materials['videos'].append(m);cache[str(p)]=mid;return mid
def segment(typ,mid,start,dur,source_start=0,speed=1):
 s=copy.deepcopy(protos[typ]);s.update(id=uid(),material_id=mid,target_timerange={'start':us(start),'duration':us(dur)},source_timerange=None if typ=='text' else {'start':us(source_start),'duration':us(dur*speed)},speed=speed,volume=1 if typ=='audio' else 0,extra_material_refs=[])
 if typ!='text':
  sp=uid();materials['speeds'].append(dict(id=sp,type='speed',mode=0,speed=speed,curve_speed=None));s['extra_material_refs']=[sp]
 return s
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',48);big=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',60)
for i,(r,v) in enumerate(zip(tl['segments'],voice['segments']),1):
 assert r['id']==v['id'];start=r['start_seconds'];dur=r['end_seconds']-start
 if r['source']:
  p=copied(T/r['source']['material_path']);mid=video_material(p);s=segment('video',mid,start,r['moving_seconds'],r['source_start_frame']/r['source']['source_fps'],r['speed']);doc['tracks'][0]['segments'].append(s)
 if r['missing_card_seconds']>.000001:
  im=Image.new('RGB',(1080,1920),'#172333');draw=ImageDraw.Draw(im);draw.text((70,600),f'缺素材 · {i:02d}',font=big,fill='#ffd285')
  req=read(T/'matches.json')['segments'][i-1]['requirement'];draw.text((70,740),req,font=font,fill='white');p=M/(r['id']+'-missing.png');im.save(p)
  doc['tracks'][0]['segments'].append(segment('video',video_material(p,True),start+r['moving_seconds'],r['missing_card_seconds']))
 p=copied(V/(r['id']+'.wav'));aid=uid();am=copy.deepcopy(old['materials']['audios'][0]);am.update(id=aid,local_material_id=aid,music_id=aid,path=str(p),name=p.name,duration=us(v['actual_duration_seconds']));materials['audios'].append(am);doc['tracks'][1]['segments'].append(segment('audio',aid,start,dur))
 text='\n'.join(r['text'][j:j+16] for j in range(0,len(r['text']),16));tm=copy.deepcopy(old['materials']['texts'][0]);tid=uid();content=json.loads(tm['content']);content['text']=text;content['styles'][0]['range']=[0,len(text)];tm.update(id=tid,content=json.dumps(content,ensure_ascii=False));materials['texts'].append(tm);doc['tracks'][2]['segments'].append(segment('text',tid,start,dur))
for name in ['captions.srt','timeline.json']:shutil.copy2(E/name,D/name)
cap=cv2.VideoCapture(str(E/'preview.mp4'));ok,frame=cap.read();cap.release();assert ok;Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).save(D/'draft_cover.jpg');doc['static_cover_image_path']=str(D/'draft_cover.jpg')
meta=read(P/'260908-dy-trimmer-voice01/draft_meta_info.json');now=int(time.time()*1e6);meta.update(draft_id=draftid,draft_name=D.name,draft_fold_path=str(D),draft_root_path=str(P),draft_json_file=str(D/'draft_content.json'),draft_cover=str(D/'draft_cover.jpg'),tm_duration=doc['duration'],tm_draft_create=now,tm_draft_modified=now)
ids=[];byid={}
for group in materials.values():
 for m in group:
  ids.append(m['id']);byid[m['id']]=m
  if m.get('path'):assert Path(m['path']).is_absolute() and Path(m['path']).is_file()
for track in doc['tracks']:
 ids.append(track['id']);end=0
 for s in track['segments']:
  ids.append(s['id']);m=byid[s['material_id']];a=s['target_timerange'];assert abs(a['start']-end)<=1;end=a['start']+a['duration'];assert a['duration']>0
  if s['source_timerange']:
   q=s['source_timerange'];assert q['start']>=0 and q['start']+q['duration']<=m['duration']+1
  for ref in s['extra_material_refs']:assert ref in byid
 assert abs(end-doc['duration'])<=1
assert len(ids)==len(set(ids));assert doc['id']==meta['draft_id']
save(D/'draft_content.json',doc);save(D/'draft_meta_info.json',meta)
root=read(P/'root_meta_info.json');shutil.copy2(P/'root_meta_info.json',E/'root_meta_info.before-xionger.json');assert all(x['draft_id']!=draftid for x in root['all_draft_store']);root['all_draft_store'].append(meta);root['draft_ids']=len(root['all_draft_store']);save(P/'root_meta_info.json',root)
validation=dict(schema_version=2,created_at_unix=time.time(),draft_id=draftid,id_consistency='passed',object_id_uniqueness='passed',absolute_media_paths='passed',media_copy_hashes='passed',source_ranges='passed',track_coverage='passed',duration_seconds=tl['duration_seconds'],track_segments={t['type']:len(t['segments']) for t in doc['tracks']},freeze_seconds=0,open_in_jianying='not_verified',native_registration='not_performed',video_sample=str(E/'preview.mp4'))
save(D/'validation.json',validation)
(D/'使用说明.md').write_text('熊二音色剪映草稿，30.864秒。独立视频、18段配音和18条字幕；轻微变速与缺素材卡保持样片设置，没有定格补时。所有媒体已复制到本草稿materials中，引用当前绝对路径。结构及源范围检查通过；尚未实际在剪映中打开验证。\n\n导入：退出剪映，复制本文件夹260909-dy-trimmer-xionger-01到D:/软件/JianyingPro Drafts，重启剪映查看本地草稿。不要覆盖原生root_meta_info.json，也请保留项目中的原草稿目录以维持媒体路径。若不出现，需要另行登记原生草稿索引。\n',encoding='utf-8')
recipe=read(T/'recipe.json');shutil.copy2(T/'recipe.json',E/'recipe.before-xionger-draft.json');recipe['latest_sample']['draft']=str(D.relative_to(T));recipe['latest_sample']['draft_open_verification']='not_verified';save(T/'recipe.json',recipe)
with (T/'任务说明.md').open('a',encoding='utf-8') as f:f.write('\n\n熊二样片经用户确认后已生成独立剪映草稿：'+str(D.relative_to(T))+'。媒体复制哈希、绝对路径、ID一致唯一、时间线覆盖、源区间检查通过；原草稿及根索引原条目保留，新增独立ID。实际剪映打开验证及原生列表登记未完成。缺素材卡和烧录字幕保留，未归档final。\n')
print(json.dumps(validation,ensure_ascii=False))
