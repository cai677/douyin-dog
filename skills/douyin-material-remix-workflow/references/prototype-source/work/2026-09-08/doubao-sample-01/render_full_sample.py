import json,hashlib,shutil,itertools
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent;T=O.parent;R=T.parents[1];V=O/'voice-rate50';E=O/'full-rate50';E.mkdir(exist_ok=True)
report=json.loads((V/'voice-report-clean.json').read_text(encoding='utf-8'));matches=json.loads((T/'matches.json').read_text(encoding='utf-8'));font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',48);big=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',60)
def fit(frame):
 h,w=frame.shape[:2];sc=min(1080/w,1920/h);nw,nh=round(w*sc),round(h*sc);out=np.zeros((1920,1080,3),np.uint8);out[(1920-nh)//2:(1920-nh)//2+nh,(1080-nw)//2:(1080-nw)//2+nw]=cv2.resize(frame,(nw,nh));return out
def stamp(t):
 ms=round(t*1000);return f'00:00:{ms//1000:02d},{ms%1000:03d}'
writer=cv2.VideoWriter(str(E/'silent.mp4'),cv2.CAP_MSMF,cv2.VideoWriter_fourcc(*'H264'),60,(1080,1920));assert writer.isOpened();rows=[];cues=[];posters=[]
for n,(s,v) in enumerate(zip(matches['segments'],report['segments']),1):
 start=v['timeline_start_seconds'];dur=v['actual_duration_seconds'];end=v['timeline_end_seconds'];sel=s['selected'];count=round(end*60)-round(start*60);speed=1.;moving=0;sf=ef=0
 if sel:
  sf=sel['source_start_frame'];ef=sel['source_end_frame_exclusive'];fps=sel['source_fps'];avail=(ef-sf)/fps
  if avail<dur*.9 and n in [5,9,11,16]:sf=sel['catalog_start_frame'];ef=sel['catalog_end_frame_exclusive'];avail=(ef-sf)/fps
  speed=max(.9,min(1.,avail/dur));moving=min(dur,avail/speed)
  cap=cv2.VideoCapture(str(T/sel['material_path']));cap.set(1,sf);nxt=sf;frame=None
 text=v['text'];lines=[text[i:i+16] for i in range(0,len(text),16)]
 for k in range(count):
  if sel and k/60<moving-1e-8:
   target=sf+int(k/60*speed*fps)
   if target>=ef:raise RuntimeError('Source overflow')
   while nxt<=target:
    ok,frame=cap.read();assert ok;nxt+=1
   im=Image.fromarray(cv2.cvtColor(fit(frame),cv2.COLOR_BGR2RGB))
  else:
   im=Image.new('RGB',(1080,1920),'#172333');d=ImageDraw.Draw(im);d.text((70,600),f'缺素材 · {n:02d}',font=big,fill='#ffd285');d.text((70,740),s['requirement'],font=font,fill='white')
  d=ImageDraw.Draw(im)
  for j,line in enumerate(lines):d.text(((1080-d.textlength(line,font=font))/2,1590+j*65),line,font=font,fill='white',stroke_width=3,stroke_fill='black')
  out=cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR);writer.write(out)
  if k==count//2:posters.append(im.copy())
 if sel:cap.release()
 rows.append(dict(id=s['id'],start_seconds=start,end_seconds=end,text=text,source=sel,source_start_frame=sf,source_end_frame_exclusive=ef,speed=speed,moving_seconds=moving,missing_card_seconds=dur-moving,freeze_seconds=0,expanded_range_review='first_middle_last_viewed' if n in [5,9,11,16] else None))
 cues.append(f'{n}\n{stamp(start)} --> {stamp(end)}\n'+'\n'.join(lines)+'\n');print(f'Rendered {n}/18',flush=True)
writer.release();(E/'captions.srt').write_text('\n'.join(cues),encoding='utf-8-sig')
sheet=Image.new('RGB',(1080,1050),'white')
for i,im in enumerate(posters):im.thumbnail((180,320));sheet.paste(im,(i%6*180,i//6*350));ImageDraw.Draw(sheet).text((i%6*180+5,i//6*350+325),str(i+1),fill='black')
sheet.save(E/'overview.jpg')
plan=dict(schema_version=2,provider='doubao_tts',speech_rate=50,duration_seconds=report['actual_duration_seconds'],status='review_pending_material_gaps',video_speed_range=[.9,1.1],freeze_seconds=0,segments=rows)
(E/'timeline.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
