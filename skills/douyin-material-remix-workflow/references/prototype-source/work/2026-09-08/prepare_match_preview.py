import json, hashlib, shutil
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image,ImageDraw,ImageFont
import cv2
import numpy as np

T=Path(__file__).resolve().parent; R=T.parents[1]; O=T/'matching-01'
recipe=json.loads((T/'recipe.json').read_text(encoding='utf-8'))
ranking=json.loads((O/'rankings.json').read_text(encoding='utf-8'))
clips=[json.loads(x) for x in (R/'assets/catalog/clips.jsonl').read_text(encoding='utf-8').splitlines()]
byid={c['display_id']:c for c in clips}
selection=['S21-007','S21-008','S06-004',None,'S24-015','S02-015','S06-012','S13-006',
           'S56-005','S10-016','S06-010','S46-011','S56-008',None,'S10-023','S06-006',None,'S21-021']
missing={4:'唯一猫砂盆候选 S15-006 与参考使用相同场景及动作画面，隔离为疑似参考同源；缺独立猫砂盆出入镜头。',
         14:'S15-011 疑似参考同源；其余高分候选仅产品展示，没有猫靠近或嗅闻电推的动作。',
         17:'缺独立的单只干净肉垫近景；高分候选为参考同源、双爪对比或未修剪细节，动作与构图均不满足本镜头。'}
notes={1:'猫脚毛修剪，爪部近景，浅色黑面板电推带照明。',2:'与上一镜头保留同一来源的猫及双爪前后对照，优先保证对比连续性。',
3:'灰猫脚毛细节，保留手持肉垫动作。',5:'猫舔脚动作成立；与原片椅子场景不同，作为独立场景示意。',
6:'同款外观的小电推修剪脚毛，近景构图。',7:'切换灰猫及不同背景与角度，避免相邻构图重复。',
8:'猫室内行走场景；只证明行走，不能作为打滑或受伤证据。',9:'浅色黑面板电推产品侧面展示；没有猫同框，作为产品外观替代，不宣称完全复刻。',
10:'带灯修剪脚毛近景，侧面接触角度。',11:'灰猫侧面修剪，背景与上一段不同。',12:'刀头特写满足产品细节用途，背景不同；精确 SKU 仍待用户确认。',
13:'同款外观电推接触手部皮肤；手部替代参考前臂，不作安全性能验证。',
15:'带照明修剪脚毛，选用不同于第10段的源区间。',16:'灰猫修剪脚毛，独立动作演示。',18:'双爪干净肉垫效果作为独立收尾示意；不是第16段灰猫的前后对照，正式配音不得暗示同一只猫。'}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
segments=[]; review_images=[]
for i,(ref,rank,label) in enumerate(zip(recipe['segments'],ranking['segments'],selection),1):
 entry={'id':ref['id'],'requirement':rank['requirement'],'timeline_start':ref['start_seconds'],
        'timeline_end':ref['end_seconds'],'duration_seconds':ref['duration_seconds'],
        'reference_frame':ref['reference_frame'],'reference_boundary_status':ref['status'],
        'status':'missing_material' if label is None else 'selected_for_visual_preview',
        'user_approval':'pending','production_approval':'not_approved',
        'confidence':None,'score_type':'heuristic_visual_similarity_not_probability',
        'candidates':rank['candidates'],'selected':None}
 if label is None:
  entry['missing_reason']=missing[i];segments.append(entry);continue
 c=byid[label];score=next(x for x in rank['candidates'] if x['display_id']==label)
 assert score['score']>=.6
 assert c['source_role']=='production_candidate' and c['library_status']!='hold'
 extra=max(0,c['duration_seconds']-ref['duration_seconds'])
 start=c['source_start_frame']+int(extra*c['fps']/2)
 end=min(c['source_end_frame_exclusive'],start+int(np.ceil(ref['duration_seconds']*c['fps'])))
 dest=T/'material'/ref['id']/(c['source_label']+'-source.mp4');dest.parent.mkdir(exist_ok=True,parents=True)
 source=R/c['source_path']; sha=hashlib.sha256(source.read_bytes()).hexdigest()
 if dest.exists():
  assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
 else: shutil.copy2(source,dest)
 assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
 sel={**score,'source_original':c['source_path'],'material_path':str(dest.relative_to(T)),
      'source_sha256':sha,'source_fps':c['fps'],'source_start_frame':start,'source_end_frame_exclusive':end,
      'catalog_start_frame':c['source_start_frame'],'catalog_end_frame_exclusive':c['source_end_frame_exclusive'],
      'source_start_seconds':start/c['fps'],'source_end_seconds':end/c['fps'],
      'visual_speed':1.0,'freeze_seconds':max(0,ref['duration_seconds']-(end-start)/c['fps']),
      'duplicate_group_id':c['duplicate_group_id'],'visual_fingerprints':c['visual_fingerprints'],
      'reason':notes[i],'sku_status':'appearance_consistent_exact_sku_unverified',
      'burned_in_text':'present_not_removed','source_group':c['source_label']}
 entry['confidence']=score['score'];entry['selected']=sel
 cap=cv2.VideoCapture(str(dest));actual=[]
 for tag,fno in [('start',start),('middle',(start+end)//2),('end',end-1)]:
  cap.set(cv2.CAP_PROP_POS_FRAMES,fno);ok,frame=cap.read();assert ok
  p=O/f"{ref['id']}-selected-{tag}.jpg"; cv2.imwrite(str(p),frame);actual.append(p)
 cap.release();entry['selected_frame_evidence']=[str(p.relative_to(T)) for p in actual]
 review_images.append((entry,actual));segments.append(entry)
for page in range(0,len(review_images),4):
 sheet=Image.new('RGB',(1000,4*400),'white');d=ImageDraw.Draw(sheet)
 for row,(e,paths) in enumerate(review_images[page:page+4]):
  for col,path in enumerate([T/e['reference_frame']]+paths):
   im=Image.open(path).convert('RGB');im.thumbnail((246,345));x=col*250;y=row*400
   sheet.paste(im,(x+(250-im.width)//2,y+25))
   d.text((x+4,y+3),('参考 '+e['id']) if col==0 else (e['selected']['display_id']+' '+['','首','中','末'][col]),font=font,fill='black')
   if col==0:d.text((x+4,y+375),f"相似度 {e['confidence']:.3f}",font=font,fill='black')
 sheet.save(O/f'selected-review-{page//4+1}.jpg')
data={'schema_version':2,'created_at':datetime.now(timezone.utc).isoformat(),'task_path_base':str(T),
      'asset_path_base':str(R),'purpose':'visual_matching_review_not_publishable_final',
      'threshold':.6,'target_duration_seconds':31.7,'output':{'width':1080,'height':1920,'fps':60},
      'audio_status':'silent_visual_review_new_voice_not_generated',
      'source_folder_rule':'All original inputs share assets/inbox; source_label used as content-source group. Physical-folder diversity cannot be claimed.',
      'selected_count':sum(x is not None for x in selection),'missing_count':sum(x is None for x in selection),
      'reference_related_exclusions':['S42 exact reference copy','S15 high visual reference overlap','S37-007 reference hallway footage','S16-005 and S37-016 reference-scene result footage held conservatively'],
      'segments':segments}
(O/'review-plan.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared',data['selected_count'],'selections;',data['missing_count'],'gaps. Awaiting first/middle/last visual review.')
