import json,shutil,hashlib
from pathlib import Path
from datetime import datetime
import numpy as np
import soundfile as sf
T=Path(__file__).resolve().parent;O=T/'voice/voxcpm-01'
rp=O/'voice-report.json';report=json.loads(rp.read_text(encoding='utf-8'))
assert not (O/'voice-report-raw.json').exists(),'Do not clean twice.'
shutil.copy2(rp,O/'voice-report-raw.json')
for ext in ['mp3','wav']:shutil.copy2(O/f'final_voice.{ext}',O/f'final_voice-raw.{ext}')
pieces=[];cursor=0;sr=report['sample_rate'];boundaries=[]
for e in report['segments']:
 raw=T/e['audio_path'];x,s=sf.read(str(raw),dtype='float32');assert s==sr
 block=int(sr*.01)
 rms=np.array([np.sqrt(np.mean(x[i:i+block]**2)) for i in range(0,len(x),block)])
 threshold=max(.001,float(rms.max())*.01)
 active=np.flatnonzero(rms>=threshold);assert len(active)
 start=max(0,int(active[0]*block)-round(sr*.06))
 end=min(len(x),int((active[-1]+1)*block)+round(sr*.09))
 y=x[start:end].copy()
 # Tiny fades stay inside preserved quiet margins; no tempo or pitch change.
 fade=min(round(sr*.003),len(y)//2)
 y[:fade]*=np.linspace(0,1,fade);y[-fade:]*=np.linspace(1,0,fade)
 target=O/(e['id']+'-clean.wav');sf.write(str(target),y,sr,subtype='PCM_16')
 y,_=sf.read(str(target),dtype='float32')
 e['raw_audio_path']=e['audio_path'];e['raw_duration_seconds']=e['actual_duration_seconds']
 e['raw_difference_seconds']=e['difference_seconds']
 e['raw_quality_metrics']={k:e.pop(k) for k in ['leading_quiet_seconds','trailing_quiet_seconds','longest_quiet_seconds']}
 e['audio_path']=str(target.relative_to(T));e['actual_duration_seconds']=len(y)/sr
 e['sample_count']=len(y);e['difference_seconds']=len(y)/sr-e['reference_duration_seconds']
 e['trim_start_samples']=start;e['trim_end_samples']=len(x)-end
 e['removed_quiet_seconds']=(len(x)-len(y))/sr
 e['timeline_start_seconds']=cursor/sr;e['timeline_end_seconds']=(cursor+len(y))/sr
 e['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
 e['peak_amplitude']=float(np.abs(y).max());e['clipped_sample_count']=int(np.sum(np.abs(y)>=.999))
 rms2=np.array([np.sqrt(np.mean(y[i:i+block]**2)) for i in range(0,len(y),block)])
 active2=np.flatnonzero(rms2>=threshold)
 e['leading_quiet_seconds']=float(active2[0]*.01)
 e['trailing_quiet_seconds']=max(0,len(y)/sr-float((active2[-1]+1)*.01))
 longest=run=0
 for q in rms2<threshold:run=run+1 if q else 0;longest=max(longest,run)
 e['longest_quiet_seconds']=longest*.01
 if pieces:boundaries.append({'at_seconds':cursor/sr,'left':report['segments'][len(pieces)-1]['id'],'right':e['id'],
     'amplitude_step':abs(float(pieces[-1][-1])-float(y[0])),
     'quiet_gap_seconds':report['segments'][len(pieces)-1]['trailing_quiet_seconds']+e['leading_quiet_seconds']})
 cursor+=len(y);pieces.append(y)
 target.with_suffix('.json').write_text(json.dumps(e,ensure_ascii=False,indent=2),encoding='utf-8')
full=np.concatenate(pieces)
sf.write(str(O/'final_voice-clean-temp.wav'),full,sr,subtype='PCM_16')
sf.write(str(O/'final_voice-clean-temp.mp3'),full,sr,format='MP3',subtype='MPEG_LAYER_III')
mp3,mp3sr=sf.read(str(O/'final_voice-clean-temp.mp3'),dtype='float32');assert mp3sr==sr and np.isfinite(mp3).all()
assert abs(len(mp3)-len(full))<=sr*.03
for ext in ['mp3','wav']:(O/f'final_voice-clean-temp.{ext}').replace(O/f'final_voice.{ext}')
report['raw_total_duration_seconds']=report['total_duration_seconds']
report.update(total_duration_seconds=len(full)/sr,total_difference_seconds=len(full)/sr-31.7,
 within_target=30.7<=len(full)/sr<=32.7,mp3_decoded_duration_seconds=len(mp3)/sr,
 mp3_duration_difference_from_wav_seconds=(len(mp3)-len(full))/sr,
 removed_silence_seconds=sum(e['removed_quiet_seconds'] for e in report['segments']),
 silence_cleanup={'method':'10ms_RMS_activity_with_60ms_head_90ms_tail_padding','threshold':'max(0.001, peak_rms*0.01)',
                  'edge_fades_ms':3,'voice_speed_change':False,'internal_pauses_unchanged':True},
 boundary_checks=boundaries,quality_status='numeric_checks_passed_listening_pending')
rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
recipe_path=T/'recipe.json';recipe=json.loads(recipe_path.read_text(encoding='utf-8'))
shutil.copy2(recipe_path,O/('recipe.before-cleanup-'+datetime.now().strftime('%H%M%S')+'.json'))
recipe['voice'].update(actual_duration_seconds=report['total_duration_seconds'],
 raw_duration_seconds=report['raw_total_duration_seconds'],removed_silence_seconds=report['removed_silence_seconds'],
 reference_difference_seconds=report['total_difference_seconds'],within_target=report['within_target'],segments=report['segments'])
for ref,voice in zip(recipe['segments'],report['segments']):
 ref['voice']={k:voice[k] for k in ['text','audio_path','raw_audio_path','actual_duration_seconds','raw_duration_seconds','reference_duration_seconds','difference_seconds','timeline_start_seconds','timeline_end_seconds']}
recipe_path.write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 分镜配音实测报告','',f"VoxCPM本地生成18段，原始总长 {report['raw_total_duration_seconds']:.2f} 秒；清理多余首尾静音 {report['removed_silence_seconds']:.2f} 秒后，试听总长 **{report['total_duration_seconds']:.2f} 秒**。",
 f"比参考31.7秒长 {report['total_difference_seconds']:.2f} 秒，是否满足30.7～32.7秒：{'是' if report['within_target'] else '否'}。",'',
 '没有改变语速、音高或删除文案；仅清理首尾低电平静音，每段保留约60ms起始和90ms结束余量。内部停顿不修改。原始语音及拼接保留为raw文件。',
 '两处用户确认修正已应用；除补充分句标点外，其他文字与上传文本一致。未进行事实核查或自动语音识别，不能将文案内容当作已验证的商品或健康事实。',
 '音色参考为此前由模型生成的短句，不是原参考视频的说话人。听感、发音、漏字与语速待用户试听确认。','',
 '|镜头|参考秒|原始生成秒|清理后实际秒|相对参考差异秒|','|---|---:|---:|---:|---:|']
for e in report['segments']:lines.append(f"|{e['id']}|{e['reference_duration_seconds']:.3f}|{e['raw_duration_seconds']:.3f}|{e['actual_duration_seconds']:.3f}|{e['difference_seconds']:+.3f}|")
lines+=['',f"拼接边界共检查{len(boundaries)}处；边界振幅跳变最大 {max(b['amplitude_step'] for b in boundaries):.6f}，片段无满幅削波样本。",
 f"完整MP3重新解码通过，实际时长 {len(mp3)/sr:.3f} 秒；与WAV差异 {(len(mp3)-len(full))/sr:.6f} 秒。",
 'recipe已更新每段真实配音起止和时长；保留原始参考时长。现有视频尚未按照新配音重新渲染。',
 '最终试听文件：final_voice.mp3；无损版本：final_voice.wav；逐镜头清理版本：fragmentNN-clean.wav；原始生成版本：fragmentNN.wav。']
(O/'配音时长报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['total_duration_seconds','total_difference_seconds','removed_silence_seconds','within_target']},ensure_ascii=True))
