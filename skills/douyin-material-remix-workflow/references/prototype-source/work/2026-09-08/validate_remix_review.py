import json,hashlib,shutil,struct,time
from pathlib import Path
import cv2
T=Path(__file__).resolve().parent;O=T/'remix-review';D=T/'jianying_draft/260908-dy-trimmer-voice01'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
doc=read(D/'draft_content.json');meta=read(D/'draft_meta_info.json');root=read(D.parent/'root_meta_info.json');tl=read(O/'timeline.json')
assert doc['id']==meta['draft_id']==root['all_draft_store'][0]['draft_id']
ids=[];materials={}
for group in doc['materials'].values():
 for m in group:
  ids.append(m['id']);materials[m['id']]=m
  if m.get('path'):assert Path(m['path']).is_absolute() and Path(m['path']).is_file()
for track in doc['tracks']:
 ids.append(track['id']);end=0
 for seg in track['segments']:
  ids.append(seg['id']);m=materials[seg['material_id']];r=seg['target_timerange'];assert r['start']>=end-1;end=r['start']+r['duration']
  assert r['duration']>0 and end<=doc['duration']+1
  for ref in seg['extra_material_refs']:assert ref in materials
  sr=seg['source_timerange']
  if sr:assert sr['start']>=0 and sr['start']+sr['duration']<=m['duration']+1
 assert end==doc['duration']
assert len(ids)==len(set(ids))
p=T/'remix.mp4';c=cv2.VideoCapture(str(p));w,h,fps=c.get(3),c.get(4),c.get(5);count=0;black=[]
while True:
 ok,f=c.read()
 if not ok:break
 if f.mean()<1:black.append(count)
 count+=1
c.release();assert count==2115 and w==1080 and h==1920 and abs(fps-60)<.001 and not black
data=p.read_bytes()
def boxes(buf):
 pos=0
 while pos+8<=len(buf):
  size,typ=struct.unpack('>I4s',buf[pos:pos+8]);header=8
  if size==1:size=struct.unpack('>Q',buf[pos+8:pos+16])[0];header=16
  if size==0:size=len(buf)-pos
  if size<header:break
  yield typ,buf[pos+header:pos+size];pos+=size
handlers=[]
def walk(buf):
 for typ,b in boxes(buf):
  if typ in [b'moov',b'trak',b'mdia']:walk(b)
  if typ==b'hdlr':handlers.append(b[8:12].decode('ascii'))
walk(data);assert handlers.count('vide')==1 and handlers.count('soun')==1
checks={'schema_version':2,'created_at_unix':time.time(),'video_full_decode':'passed','video_frames':count,'width':w,'height':h,'fps':fps,'duration_seconds':count/fps,'mp4_track_handlers':handlers,'black_frames':black,'draft_structure':'passed','draft_id':doc['id'],'unique_object_ids':len(ids),'draft_open_verification':'pending_not_registered_in_native_draft_list','user_review':'pending','missing_ids':[s['id'] for s in tl['segments'] if s['missing_material']],'freeze_total_seconds':sum(s['freeze_seconds'] for s in tl['segments']),'freeze_max_seconds':max(s['freeze_seconds'] for s in tl['segments']),'sha256':hashlib.sha256(data).hexdigest(),'input_sha256':{n:hashlib.sha256((T/n).read_bytes()).hexdigest() for n in ['recipe.json','matches.json','script.txt']},'tools':{'opencv':cv2.__version__,'encoder':'Windows Media Foundation H264 / Windows MediaComposition AAC'},'limitations':['burned_in_source_captions_retained','exact_sku_unverified','voice_listening_review_pending','same_visual_combination_as_previous_silent_preview_not_new_unique_variant','audio_audition_not_run','reference_duration_tolerance_exceeded_by_voice_timeline']}
write(O/'validation.json',checks)
recipe=read(T/'recipe.json');backup=O/('recipe.before-remix-'+str(int(time.time()))+'.json');shutil.copy2(T/'recipe.json',backup)
recipe['status']='remix_review_ready_with_3_material_gaps';recipe['timeline_rebuild_required']=False
recipe['remix']={'video':'remix.mp4','captions':'captions.srt','draft':str(D.relative_to(T)),'timeline':'remix-review/timeline.json','validation':'remix-review/validation.json','duration_seconds':35.25,'duration_basis':'actual_voice_per_latest_user_request','review_status':'pending','draft_open_verification':checks['draft_open_verification']}
write(T/'recipe.json',recipe)
history=T.parents[1]/'assets/history/outputs.jsonl'
with history.open('a',encoding='utf-8') as f:f.write(json.dumps({'schema_version':2,'variant_id':'260908-dy-trimmer-voice01','revision_of':'260908-dy-trimmer-01','status':'review_pending_incomplete','path':str(p.relative_to(T.parents[1])),'duration_seconds':35.25,'sha256':checks['sha256'],'has_audio':True,'has_placeholders':True,'clip_ids':[s['source']['clip_id'] for s in tl['segments'] if s['source']]},ensure_ascii=False)+'\n')
report='''# 带配音审核版检查结果

- 输出：remix.mp4，1080×1920，60fps，35.25秒，H.264视频与AAC配音；2115帧完整解码通过，无全黑帧。
- 18条字幕按每段真实语音时间对齐，18段配音在草稿中独立可编辑；未做逐词识别对齐。
- 15/18镜头有预览批准素材，04（猫砂盆出入，1.99秒）、14（猫靠近/嗅闻电推，1.59秒）、17（单只干净肉垫特写，1.24秒）缺料，保留提示卡。
- 画面1.00x，不延长批准素材源区间；定格累计%.3f秒，最长%.3f秒（18镜头），具体见timeline.json。
- 新版依据用户最新要求采用配音时长，比参考31.7秒多3.55秒；未满足之前±1秒目标，没有通过改语速硬压缩。
- 草稿视频、定格/提示图片、18条配音和字幕分别可编辑。所有媒体已复制进草稿materials目录，使用绝对路径。内容/元数据/根索引ID一致，各对象ID唯一，素材路径和源时间范围检查通过。
- 剪映已启动，但本包尚未注册到原生草稿列表，实际打开与编辑验证待完成，不能仅凭结构校验声称已验证可用。
- 现有素材带有烧录字幕，会与新字幕同时出现；产品型号、声音自然度、节奏和字幕位置待用户审核。保持此版为审核版，未归档final。
- 画面组合沿用上一条静音样片，并非新的去重版本；复用matching-01既有105对源区间/指纹检查，未运行本次成片的跨历史视觉复核。
'''%(checks['freeze_total_seconds'],checks['freeze_max_seconds'])
(O/'审核报告.md').write_text(report,encoding='utf-8')
(D.parent/'使用说明.md').write_text('''# 剪映草稿交付包

草稿子目录：260908-dy-trimmer-voice01。
项目内容、配音、图片及字幕已经写入，媒体均在子目录materials中。请保留当前绝对路径。

结构校验已通过；尚未在剪映中实际打开验证。原有剪映草稿存储在D:/软件/JianyingPro Drafts，本包未修改该目录或原生根索引。
可先在剪映的设置中查看草稿存储入口，再由用户导入此草稿目录；不要用本包root_meta_info.json覆盖原有根索引，否则原有草稿列表会丢失。

审核版仍包含04、14、17缺素材提示卡，并保留原素材烧录字幕。请审核配音、字幕、产品与画面节奏后再补料定稿。
''',encoding='utf-8')
with (T/'任务说明.md').open('a',encoding='utf-8') as f:f.write('\n\n## 配音合成审核版与剪映草稿（最新状态）\n\n'+report.split('\n',1)[1])
print(json.dumps(checks,ensure_ascii=False))
