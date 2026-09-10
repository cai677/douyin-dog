import json,uuid,shutil,hashlib,time,math
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
T=Path(__file__).resolve().parent
O=T/'remix-review';O.mkdir(exist_ok=True)
D=T/'jianying_draft'/'260908-dy-trimmer-voice01';D.mkdir(parents=True,exist_ok=True)
M=D/'materials';M.mkdir(exist_ok=True)
def uid():return str(uuid.uuid4()).upper()
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def us(x):return round(x*1000000)
def tr(s,d):return {'start':us(s),'duration':us(d)}
plan=json.loads((T/'matches.json').read_text(encoding='utf-8'))
voices=json.loads((T/'voice/voxcpm-01/voice-report.json').read_text(encoding='utf-8'))['segments']
total=voices[-1]['timeline_end_seconds'];draftid=uid()
keys='ai_translates audio_balances audio_effects audio_fades audio_track_indexes audios beats canvases chromas color_curves digital_humans drafts effects flowers green_screens handwrites hsl images log_color_wheels loudnesses manual_deformations masks material_animations material_colors multi_language_refs placeholders plugin_effects primary_color_wheels realtime_denoises shapes smart_crops smart_relights sound_channel_mappings speeds stickers tail_leaders text_templates texts time_marks transitions video_effects video_trackings videos vocal_beautifys vocal_separations'.split()
mats={k:[] for k in keys};tracks=[]
for typ,name in [('video','画面与缺素材提示'),('audio','VoxCPM独立配音'),('text','可编辑字幕')]:
 tracks.append(dict(attribute=0,flag=0,id=uid(),is_default_name=False,name=name,segments=[],type=typ))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',48)
large=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',60)
def fit(f):
 h,w=f.shape[:2];scale=min(1080/w,1920/h);nw,nh=round(w*scale),round(h*scale)
 out=np.zeros((1920,1080,3),np.uint8);x,y=(1080-nw)//2,(1920-nh)//2;out[y:y+nh,x:x+nw]=cv2.resize(f,(nw,nh));return out
def image_save(p,frame):Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).save(p)
def copy(p):
 dest=M/p.name
 if not dest.exists():shutil.copy2(p,dest)
 assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(dest.read_bytes()).digest()
 return dest
cache={}
def material(p,photo=False):
 if str(p) in cache:return cache[str(p)]
 mid=uid()
 if photo:w,h=Image.open(p).size;dur=10800000000
 else:
  c=cv2.VideoCapture(str(p));w,h=int(c.get(3)),int(c.get(4));dur=us(c.get(7)/c.get(5));c.release()
 mats['videos'].append(dict(id=mid,material_id=mid,local_material_id='',path=str(p),media_path='',material_name=p.name,type='photo' if photo else 'video',duration=dur,width=w,height=h,audio_fade=None,category_id='',category_name='local',check_flag=63487,crop={'upper_left_x':0,'upper_left_y':0,'upper_right_x':1,'upper_right_y':0,'lower_left_x':0,'lower_left_y':1,'lower_right_x':1,'lower_right_y':1},crop_ratio='free',crop_scale=1))
 cache[str(p)]=mid;return mid
def seg(mid,start,dur,source=None,volume=0,visual=True):
 sid=uid();mats['speeds'].append(dict(id=sid,type='speed',mode=0,speed=1,curve_speed=None))
 s=dict(id=uid(),material_id=mid,target_timerange=tr(start,dur),source_timerange=source,speed=1,volume=volume,last_nonzero_volume=1,reverse=False,visible=True,track_attribute=0,track_render_index=0,common_keyframes=[],keyframe_refs=[],extra_material_refs=[sid],is_tone_modify=False,enable_adjust=True,enable_color_correct_adjust=False,enable_color_curves=True,enable_color_match_adjust=False,enable_color_wheels=True,enable_lut=True,enable_smart_color_adjust=False)
 if visual:s.update(clip=dict(alpha=1,flip=dict(horizontal=False,vertical=False),rotation=0,scale=dict(x=1,y=1),transform=dict(x=0,y=0)),uniform_scale=dict(on=True,value=1),hdr_settings=dict(intensity=1,mode=1,nits=1000))
 return s
def tc(t):
 ms=round(t*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
silent=O/'silent-captioned.mp4'
if silent.exists():raise RuntimeError('Existing render: preserve it, use separate validation/resume')
writer=cv2.VideoWriter(str(silent),cv2.CAP_MSMF,cv2.VideoWriter_fourcc(*'H264'),60,(1080,1920));assert writer.isOpened()
timeline=[];cues=[];posters=[]
for n,(s,v) in enumerate(zip(plan['segments'],voices),1):
 assert s['id']==v['id']
 start=v['timeline_start_seconds'];dur=v['actual_duration_seconds'];end=v['timeline_end_seconds']
 count=round(end*60)-round(start*60);sel=s['selected'];freeze=0
 text=v['text'];lines='\n'.join(text[i:i+16] for i in range(0,len(text),16))
 cues.append(f'{n}\n{tc(start)} --> {tc(end)}\n{lines}\n')
 if sel:
  p=copy(T/sel['material_path']);mid=material(p);fps=sel['source_fps'];sf=sel['source_start_frame'];ef=sel['source_end_frame_exclusive'];avail=(ef-sf)/fps;moving=min(dur,avail);freeze=max(0,dur-avail)
  tracks[0]['segments'].append(seg(mid,start,moving,tr(sf/fps,moving)))
  cap=cv2.VideoCapture(str(p));cap.set(cv2.CAP_PROP_POS_FRAMES,sf);nextf=sf;frame=None
 else:
  im=Image.new('RGB',(1080,1920),'#172333');draw=ImageDraw.Draw(im)
  draw.text((70,570),'缺素材 · '+s['id'][-2:],font=large,fill='#ffd285');draw.text((70,720),s['requirement'],font=font,fill='white')
  draw.text((70,820),f'需补充 {dur:.2f} 秒画面',font=font,fill='white')
  frame=cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR);p=M/(s['id']+'-missing.png');image_save(p,frame)
  tracks[0]['segments'].append(seg(material(p,True),start,dur,tr(0,dur)))
 for k in range(count):
  if sel:
   target=min(ef-1,sf+int(k/60*fps))
   while nextf<=target:
    ok,frame=cap.read();assert ok;nextf+=1
  out=fit(frame)
  im=Image.fromarray(cv2.cvtColor(out,cv2.COLOR_BGR2RGB));draw=ImageDraw.Draw(im)
  for j,line in enumerate(lines.splitlines()):
   box=draw.textbbox((0,0),line,font=font);x=(1080-(box[2]-box[0]))/2
   draw.text((x,1590+j*65),line,font=font,fill='white',stroke_width=4,stroke_fill='black')
  out=cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR);writer.write(out)
  if k==count//2:posters.append(out.copy())
 if sel:
  cap.release()
  if freeze>0:
   p=M/(s['id']+'-hold.png');image_save(p,fit(frame));tracks[0]['segments'].append(seg(material(p,True),start+moving,freeze,tr(0,freeze)))
 ap=copy(T/v['audio_path']);aid=uid()
 mats['audios'].append(dict(id=aid,local_material_id=aid,music_id=aid,path=str(ap),name=ap.name,type='extract_music',duration=us(dur),app_id=0,category_id='',category_name='local',check_flag=3,copyright_limit_type='none',effect_id='',formula_id='',source_platform=0,wave_points=[]))
 tracks[1]['segments'].append(seg(aid,start,dur,tr(0,dur),1,False))
 tid=uid();style=dict(fill={'alpha':1,'content':{'render_type':'solid','solid':{'alpha':1,'color':[1,1,1]}}},range=[0,len(lines)],size=8,bold=False,italic=False,underline=False,strokes=[{'content':{'solid':{'alpha':1,'color':[0,0,0]}},'width':.04}])
 mats['texts'].append(dict(id=tid,content=json.dumps({'text':lines,'styles':[style]},ensure_ascii=False),typesetting=0,alignment=1,letter_spacing=0,line_spacing=.02,line_feed=1,line_max_width=.82,force_apply_line_max_width=False,check_flag=15,type='subtitle',global_alpha=1))
 ts=seg(tid,start,dur);ts['clip']['transform']['y']=-.73;ts['track_render_index']=1;tracks[2]['segments'].append(ts)
 timeline.append(dict(id=s['id'],start_seconds=start,end_seconds=end,duration_seconds=dur,source=sel,speed=1,freeze_seconds=freeze,missing_material=sel is None,audio_path=str(ap),text=text))
 print(f'Rendered {n}/18; freeze={freeze:.3f}',flush=True)
writer.release()
(T/'captions.srt').write_text('\n'.join(cues),encoding='utf-8-sig')
image_save(D/'draft_cover.jpg',posters[0]);sheet=Image.new('RGB',(1080,1050),'white')
for i,f in enumerate(posters):
 im=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB));im.thumbnail((180,320));sheet.paste(im,(i%6*180,i//6*350));ImageDraw.Draw(sheet).text((i%6*180+5,i//6*350+323),str(i+1),fill='black')
sheet.save(O/'overview.jpg')
platform=dict(app_id=3704,app_source='lv',app_version='5.9.0',os='windows')
doc=dict(id=draftid,name=D.name,version=360000,new_version='110.0.0',duration=us(total),fps=60,canvas_config=dict(width=1080,height=1920,ratio='original'),materials=mats,tracks=tracks,platform=platform,last_modified_platform=platform,color_space=0,config=dict(maintrack_adsorb=True,video_mute=False,material_save_mode=0),keyframes={k:[] for k in ['adjusts','audios','effects','filters','handwrites','stickers','texts','videos']},keyframe_graph_list=[],relationships=[],source='default',static_cover_image_path=str(D/'draft_cover.jpg'),create_time=0,update_time=0,cover=None,extra_info=None,free_render_index_mode_on=False,group_container=None,mutable_config=None,render_index_track_mode_on=False,retouch_cover=None,time_marks=None)
now=int(time.time()*1e6)
meta=dict(draft_id=draftid,draft_name=D.name,draft_fold_path=str(D),draft_root_path=str(D.parent),draft_json_file=str(D/'draft_content.json'),draft_cover=str(D/'draft_cover.jpg'),tm_duration=us(total),tm_draft_create=now,tm_draft_modified=now,tm_draft_removed=0,draft_type='',draft_new_version='',draft_materials=[dict(type=k,value=[]) for k in [0,1,2,3,6,7,8]],draft_materials_copied_info=[],draft_segment_extra_info=[],draft_is_invisible=False,draft_cloud_materials=[])
write(D/'draft_content.json',doc);write(D/'draft_meta_info.json',meta);write(D.parent/'root_meta_info.json',dict(all_draft_store=[meta],draft_ids=1,root_path=str(D.parent)))
write(O/'timeline.json',dict(schema_version=2,draft_id=draftid,duration_seconds=total,fps=60,segments=timeline,status='review_pending_with_material_gaps'))
print('BUILD_DONE',flush=True)
