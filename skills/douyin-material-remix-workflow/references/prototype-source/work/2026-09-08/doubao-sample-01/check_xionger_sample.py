import json,hashlib,shutil,struct,time,itertools
from pathlib import Path
import cv2
O=Path(__file__).resolve().parent;T=O.parent;R=T.parents[1];E=O/'full-xionger-rate50';V=O/'voice-zh_male_xionger_mars_bigtts-rate50';p=E/'preview.mp4'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
tl=read(E/'timeline.json');vr=read(V/'voice-report.json');vr.update(speech_rate=50,voice_speed_changed=True,postprocess_time_stretch=False);save(V/'voice-report.json',vr)
c=cv2.VideoCapture(str(p));fps=c.get(5);w,h=c.get(3),c.get(4);count=0;black=[]
while True:
 ok,f=c.read()
 if not ok:break
 if f.mean()<1:black.append(count)
 count+=1
c.release();assert count==1852 and abs(fps-60)<.01 and (w,h)==(1080,1920) and not black
handlers=[]
def walk(buf):
 off=0
 while off+8<=len(buf):
  size,typ=struct.unpack('>I4s',buf[off:off+8]);head=8
  if size==1:size=struct.unpack('>Q',buf[off+8:off+16])[0];head=16
  if size==0:size=len(buf)-off
  assert size>=head
  b=buf[off+head:off+size]
  if typ in [b'moov',b'trak',b'mdia']:walk(b)
  if typ==b'hdlr':handlers.append(b[8:12].decode())
  off+=size
data=p.read_bytes();walk(data);assert handlers.count('vide')==handlers.count('soun')==1
used=[r for r in tl['segments'] if r['source']];hashes={}
for r in used:
 assert .9<=r['speed']<=1.1 and r['freeze_seconds']==0
 s=r['source'];assert r['source_start_frame']+r['moving_seconds']*r['speed']*s['source_fps']<=r['source_end_frame_exclusive']+1e-5
 source=R/s['source_original']
 if str(source) not in hashes:hashes[str(source)]=hashlib.sha256(source.read_bytes()).hexdigest();assert hashes[str(source)]==s['source_sha256']
for a,b in itertools.combinations(used,2):
 if a['source']['source_sha256']==b['source']['source_sha256']:assert max(a['source_start_frame'],b['source_start_frame'])>=min(a['source_start_frame']+a['moving_seconds']*a['speed']*a['source']['source_fps'],b['source_start_frame']+b['moving_seconds']*b['speed']*b['source']['source_fps'])
gaps=[{'id':r['id'],'seconds':r['missing_card_seconds']} for r in tl['segments'] if r['missing_card_seconds']>.001]
result=dict(schema_version=2,generated_at_unix=time.time(),video_full_decode='passed',frames=count,fps=fps,width=w,height=h,duration_seconds=count/fps,audio_duration_seconds=vr['actual_duration_seconds'],reference_difference_seconds=count/fps-31.7,within_target=True,mp4_track_handlers=handlers,freeze_seconds=0,actual_speed_min=min(r['speed'] for r in used),actual_speed_max=max(r['speed'] for r in used),gaps=gaps,source_hash_checks='passed',selected_source_overlap_check='passed',postrender_visual_history_check='not_run',listening_review='pending_user',draft='previous_draft_not_updated_for_this_sample',sha256=hashlib.sha256(data).hexdigest(),input_sha256={str(x.relative_to(T)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [V/'voice-report.json',T/'matches.json',T/'script.txt']})
save(E/'validation.json',result)
recipe=read(T/'recipe.json');shutil.copy2(T/'recipe.json',E/'recipe.before-doubao.json');recipe['status']='doubao_sample_review_pending_material_gaps';recipe['timing'].update(visual_speed=None,visual_speed_range=[.9,1.1],short_material_policy='no_freeze_explicit_gap_if_insufficient');recipe['latest_sample']={'video':str(p.relative_to(T)),'timeline':str((E/'timeline.json').relative_to(T)),'captions':str((E/'captions.srt').relative_to(T)),'validation':str((E/'validation.json').relative_to(T)),'duration_seconds':vr['actual_duration_seconds'],'previous_draft_current':False};recipe['voice']={'provider':'doubao_tts','speaker':vr['speaker'],'speech_rate':50,'actual_duration_seconds':vr['actual_duration_seconds'],'final_audio_path':str((V/'final_voice.mp3').relative_to(T)),'final_wav_path':str((V/'final_voice.wav').relative_to(T)),'segments':vr['segments'],'audio_review_status':'pending_user'}
for s,v in zip(recipe['segments'],vr['segments']):s['voice']=v
save(T/'recipe.json',recipe)
history=dict(schema_version=2,variant_id='doubao-xionger-rate50-full',revision_of='260908-dy-trimmer-voice01',status='review_pending_incomplete',path=str(p.relative_to(R)),sha256=result['sha256'],duration_seconds=count/fps,has_audio=True,has_placeholders=True,clip_ids=[r['source']['clip_id'] for r in used])
with (R/'assets/history/outputs.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(history,ensure_ascii=False)+'\n')
note='熊二音色zh_male_xionger_mars_bigtts，speech_rate=50，18段配音总长30.864秒，保留原始首尾停顿，无后处理语速变化。1080×1920、60fps样片生成，零定格补时。缺素材提示和原片烧录字幕保留。实际检查结果和逐镜头缺口见validation.json及timeline.json。用户听感待审，未更新剪映草稿。旧样片保留。'
(E/'审核报告.md').write_text(note,encoding='utf-8')
with (T/'任务说明.md').open('a',encoding='utf-8') as f:f.write(note)
print(json.dumps(result,ensure_ascii=False))

