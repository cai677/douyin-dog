import json,sys,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;T=O.parent;R=T.parents[1]
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
if sys.argv[1]=='audio':
 import soundfile as sf,numpy as np
 raw=json.loads((O/'voice-rate50/voice-report.json').read_text(encoding='utf-8'));parts=[];cursor=0;rows=[];short=[]
 for e in raw['segments']:
  x,sr=sf.read(T/e['audio_path'],dtype='float32');b=round(sr*.01)
  rms=np.array([np.sqrt(np.mean(x[i:i+b]**2)) for i in range(0,len(x),b)]);a=np.flatnonzero(rms>=max(.001,rms.max()*.01));assert len(a)
  start=max(0,a[0]*b-round(sr*.06));end=min(len(x),(a[-1]+1)*b+round(sr*.09));y=x[start:end].copy()
  fade=round(sr*.003);y[:fade]*=np.linspace(0,1,fade);y[-fade:]*=np.linspace(1,0,fade)
  p=O/'voice-rate50'/(e['id']+'-clean.wav');sf.write(p,y,sr,subtype='PCM_16');d=len(y)/sr
  row=dict(e,raw_audio_path=e['audio_path'],audio_path=str(p.relative_to(T)),actual_duration_seconds=d,timeline_start_seconds=cursor,timeline_end_seconds=cursor+d,trim_start_samples=int(start),trim_end_samples=int(len(x)-end),sample_count=len(y),difference_seconds=d-e['reference_duration_seconds'])
  row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();rows.append(row);parts.append(y);cursor+=d
  if e['id'] in ['fragment15','fragment16']:short.append(y)
 sf.write(O/'voice-rate50/final_voice-clean.wav',np.concatenate(parts),sr,subtype='PCM_16');sf.write(O/'voice-rate50/final_voice-clean.mp3',np.concatenate(parts),sr,format='MP3')
 sf.write(O/'action-sample-voice.wav',np.concatenate(short),sr,subtype='PCM_16')
 save(O/'voice-rate50/voice-report-clean.json',dict(schema_version=2,provider='doubao_tts',speaker=raw['speaker'],raw_duration_seconds=raw['actual_duration_seconds'],actual_duration_seconds=cursor,voice_speed_changed=False,cleanup='10ms RMS; 60ms head 90ms tail retained; internal pauses unchanged',segments=rows))
 print('Clean voice:',cursor)
else:
 import cv2,numpy as np
 from PIL import Image,ImageDraw,ImageFont
 report=json.loads((O/'voice-rate50/voice-report-clean.json').read_text(encoding='utf-8'));cat=[json.loads(x) for x in (R/'assets/catalog/clips.jsonl').read_text(encoding='utf-8').splitlines()]
 writer=cv2.VideoWriter(str(O/'action-sample-silent.mp4'),cv2.CAP_MSMF,cv2.VideoWriter_fourcc(*'H264'),60,(1080,1920));assert writer.isOpened()
 font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',48);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',30)
 cursor=0;timeline=[];srt=[]
 def stamp(t):
  ms=round(t*1000);return f'00:00:{ms//1000:02d},{ms%1000:03d}'
 for idx,(sid,cid,speed) in enumerate([('fragment15','S13-008',.95),('fragment16','S06-006',.98)],1):
  e=next(x for x in report['segments'] if x['id']==sid);c=next(x for x in cat if x['display_id']==cid);dur=e['actual_duration_seconds'];sf=c['source_start_frame'];ef=c['source_end_frame_exclusive'];assert sf+dur*speed*c['fps']<=ef
  cap=cv2.VideoCapture(str(R/c['source_path']));cap.set(1,sf);nxt=sf;frame=None
  for k in range(round((cursor+dur)*60)-round(cursor*60)):
   target=sf+int(k/60*speed*c['fps']);assert target<ef
   while nxt<=target:
    ok,frame=cap.read();assert ok;nxt+=1
   h,w=frame.shape[:2];scale=min(1080/w,1920/h);nw,nh=round(w*scale),round(h*scale);out=np.zeros((1920,1080,3),np.uint8);out[(1920-nh)//2:(1920-nh)//2+nh,(1080-nw)//2:(1080-nw)//2+nw]=cv2.resize(frame,(nw,nh))
   im=Image.fromarray(cv2.cvtColor(out,cv2.COLOR_BGR2RGB));d=ImageDraw.Draw(im)
   d.text((30,50),'动作段试看 · 豆包配音 · 无定格',font=small,fill='white',stroke_width=2,stroke_fill='black')
   text=e['text'];lines=[text[i:i+16] for i in range(0,len(text),16)]
   for j,line in enumerate(lines):d.text(((1080-d.textlength(line,font=font))/2,1610+j*65),line,font=font,fill='white',stroke_width=3,stroke_fill='black')
   writer.write(cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR))
  cap.release();timeline.append(dict(id=sid,clip_id=c['clip_id'],source_path=c['source_path'],source_start_seconds=sf/c['fps'],source_duration_seconds=dur*speed,target_start_seconds=cursor,target_duration_seconds=dur,speed=speed,freeze_seconds=0,review='assistant_first_middle_last_viewed_for_action_sample',confidence=.7768 if idx==1 else .7805));srt.append(f'{idx}\n{stamp(cursor)} --> {stamp(cursor+dur)}\n'+ '\n'.join(lines)+'\n');cursor+=dur
 writer.release();(O/'action-sample.srt').write_text('\n'.join(srt),encoding='utf-8-sig');save(O/'action-sample-timeline.json',dict(schema_version=2,purpose='two_shot_action_excerpt_not_full_remix',duration_seconds=cursor,segments=timeline,limitations=['source_burned_in_subtitles_retained','different_demonstration_cats','full_length_target_unresolved']))
 print('Action sample duration:',cursor)

