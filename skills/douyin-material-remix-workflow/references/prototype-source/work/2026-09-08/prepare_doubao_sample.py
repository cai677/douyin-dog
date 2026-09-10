"""Prepare the next sample without reusing old voice as Doubao output."""
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone
T=Path(__file__).resolve().parent
O=T/'doubao-sample-01';O.mkdir(exist_ok=True)
recipe=json.loads((T/'recipe.json').read_text(encoding='utf-8'))
matches=json.loads((T/'matches.json').read_text(encoding='utf-8'))
rows=[]
for shot in matches['segments']:
 s=shot['selected']
 row={'id':shot['id'],'requirement':shot['requirement'],'status':'missing_material' if not s else 'awaiting_doubao_duration','actual_new_voice_seconds':None}
 if s:
  length=(s['source_end_frame_exclusive']-s['source_start_frame'])/s['source_fps']
  row.update(clip_id=s['clip_id'],approved_source_seconds=length,maximum_target_seconds_without_freeze=length/.9,full_interval_target_range_seconds=[length/1.1,length/.9],catalog_interval_seconds=(s['catalog_end_frame_exclusive']-s['catalog_start_frame'])/s['source_fps'],catalog_expansion_status='requires_visual_review_not_authorized_by_file_presence')
 rows.append(row)
plan={'schema_version':2,'created_at':datetime.now(timezone.utc).isoformat(),'variant_id':'doubao-sample-01','status':'awaiting_tts_configuration','input_sha256':{n:hashlib.sha256((T/n).read_bytes()).hexdigest() for n in ['recipe.json','matches.json','script.txt']},'voice':{'provider':'doubao_tts','configuration_status':'not_found_in_project_or_process_user_machine_environment','speaker':None,'generated':False,'fallback_to_voxcpm':False},'timing':{'target_seconds':31.7,'tolerance_seconds':1,'video_speed_min':.9,'video_speed_max':1.1,'automatic_freeze':False,'loop_to_fill':False,'shortage_policy':['select_sufficient_candidate','adjust_video_speed_within_range','review_longer_source_interval','use_multiple_semantically_related_shots','report_missing_material'],'final_timeline_basis':'measured_new_doubao_audio_only'},'script':'../script.txt','shots':rows,'video_generated':False}
(O/'sample-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
report='# 豆包新流程样片准备\n\n已记录本次授权：豆包TTS，画面0.90～1.10倍，关闭自动定格和循环补时；文案保持已确认版本。\n\n豆包凭据及音色尚未找到，未调用TTS、未生成新音频或新样片。旧版配音与成片保留。\n\n以下为现有已选源区间在0.90倍播放时最多覆盖的时长，不代表新配音时长。短于该上限的片段可按需裁剪；扩展区间仍需看画面复核。\n\n|镜头|最大覆盖秒数|状态|\n|---|---:|---|\n'
for r in rows:report+=f"|{r['id']}|{r.get('maximum_target_seconds_without_freeze',0):.3f}|{r['status']}|\n"
(O/'准备报告.md').write_text(report,encoding='utf-8')
with (T/'任务说明.md').open('a',encoding='utf-8') as f:f.write('\n\n## 豆包新流程样片准备（最新）\n\n用户要求生成一条新样片，已授权豆包TTS和画面0.90～1.10倍变速，关闭自动定格补时。已检查项目、进程及用户/系统环境配置名称，未找到豆包配置；等待本机配置位置和音色。已生成doubao-sample-01/sample-plan.json及准备报告，记录15个现有素材区间的无定格覆盖上限和04/14/17缺料。未生成豆包音频或新视频；旧recipe保留为旧成片事实，新策略保存在独立样片计划中。\n')
print(json.dumps({'plan':str(O/'sample-plan.json'),'selected':15,'missing':['fragment04','fragment14','fragment17'],'tts_generated':False},ensure_ascii=False))
if __name__=='__main__':pass
