"""Generate one VoxCPM utterance per reference shot, preserving the approved text."""
import os,json,hashlib,shutil,re,random,time
from pathlib import Path
from datetime import datetime,timezone

T=Path(__file__).resolve().parent;R=T.parents[1];O=T/'voice'/'voxcpm-01'
O.mkdir(parents=True,exist_ok=True)
for k,v in {'HF_HOME':'assets/models/huggingface','MODELSCOPE_CACHE':'assets/models/modelscope',
            'TORCH_HOME':'assets/models/torch','TEMP':'work/setup-voxcpm/temp','TMP':'work/setup-voxcpm/temp'}.items():
 p=R/v;p.mkdir(parents=True,exist_ok=True);os.environ[k]=str(p)
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
import numpy as np
import torch
import soundfile as sf
import torchaudio
from voxcpm import VoxCPM

source=Path('C:/Users/Admin/Desktop/20260908-1/新建 文本文档.txt')
original=source.read_text(encoding='utf-8-sig').strip()
approved=original.replace('搅搅就滂臭','脚脚就很臭').replace('你看我撞底着剃','你看我贴着剃')
texts=[
'我赌你不知道为什么猫狗的脚底毛要定期清理，',
'绝不是单纯为了美观啊，',
'也不是脚毛过长容易藏污纳垢，',
'而是因为它们身上没有汗腺，',
'主要靠肉垫来排汗。',
'夏天长期潮湿，脚脚就很臭，',
'影响散热不说，',
'还容易打滑扭伤关节。',
'像我每次都是用这个拇指小电推，',
'别看它个头小，',
'剃毛它是一点不含糊，',
'刀头还做了圆角处理，',
'你看我贴着剃也不会刮伤皮肤，',
'噪音小猫咪也不抗拒，',
'自带探照小灯，连脚趾缝都能看清，',
'新手铲屎官也能轻松驾驭。',
'关键好用又不贵，',
'养宠家庭有这一把小电推就够了。']
clean=lambda x:re.sub(r'[^\w]','',x)
assert clean(''.join(texts))==clean(approved),'Segment text must cover the approved source exactly.'
recipe_path=T/'recipe.json';recipe=json.loads(recipe_path.read_text(encoding='utf-8'))
assert len(texts)==len(recipe['segments'])==18
shutil.copy2(source,O/'uploaded-original.txt')
(O/'approved-script.txt').write_text(approved+'\n',encoding='utf-8')
(O/'script-by-shot.txt').write_text('\n'.join(f'{i:02d}\t{s}' for i,s in enumerate(texts,1))+'\n',encoding='utf-8')
prompt=R/'work/setup-voxcpm/voice-test-20260908-165414-015274.wav'
prompt_text='给猫咪修剪脚毛，先轻轻握住爪子，再慢慢修整。'
# Limit this compatibility adapter to our generated WAV; avoid TorchCodec's
# external FFmpeg dependency without altering any installed package files.
original_load=torchaudio.load
def wav_load(path,*args,**kwargs):
 if Path(path).resolve()==prompt.resolve():
  a,s=sf.read(str(path),dtype='float32',always_2d=True)
  return torch.from_numpy(a.T.copy()),s
 return original_load(path,*args,**kwargs)
torchaudio.load=wav_load
model_path=next((R/'assets/models/huggingface/hub/models--openbmb--VoxCPM1.5/snapshots').iterdir())
assert torch.cuda.is_available()
model=VoxCPM.from_pretrained(str(model_path),load_denoiser=False,optimize=False,device='cuda',local_files_only=True)
sr=model.tts_model.sample_rate
report={'schema_version':2,'created_at':datetime.now(timezone.utc).isoformat(),'model':'openbmb/VoxCPM1.5',
        'model_snapshot':model_path.name,'device':'cuda','sample_rate':sr,
        'source_text_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'corrections_approved_by_user':{'搅搅就滂臭':'脚脚就很臭','你看我撞底着剃':'你看我贴着剃'},
        'prompt_source':'previously_generated_synthetic_voice_not_reference_video_speaker',
        'prompt_audio':str(prompt.relative_to(R)),'prompt_text':prompt_text,
        'settings':{'cfg_value':2.0,'inference_timesteps':10,'normalize':False,'denoise':False,'seed':42},
        'speed_change':False,'added_silence_seconds':0,'removed_silence_seconds':0,
        'status':'generating','segments':[]}
arrays=[];cursor=0
for i,(text,ref) in enumerate(zip(texts,recipe['segments']),1):
 target=O/(ref['id']+'.wav');meta=target.with_suffix('.json')
 if target.exists() and meta.exists():
  prior=json.loads(meta.read_text(encoding='utf-8'));assert prior['text']==text
  wav,actual_sr=sf.read(str(target),dtype='float32');assert actual_sr==sr
 else:
  if target.exists():raise RuntimeError('Unverified existing WAV: '+str(target))
  torch.manual_seed(42);random.seed(42);np.random.seed(42)
  wav=np.asarray(model.generate(text=text,prompt_wav_path=str(prompt),prompt_text=prompt_text,
      cfg_value=2.0,inference_timesteps=10,normalize=False,denoise=False,retry_badcase=True,
      retry_badcase_max_times=2,max_len=512),dtype=np.float32).reshape(-1)
  if not wav.size or not np.isfinite(wav).all() or np.max(np.abs(wav))<1e-5:
   raise RuntimeError('Invalid generated audio for '+ref['id'])
  sf.write(str(target),wav,sr,subtype='PCM_16')
  wav,actual_sr=sf.read(str(target),dtype='float32')
 duration=len(wav)/sr;frame=max(1,int(sr*.02));rms=np.array([np.sqrt(np.mean(wav[n:n+frame]**2)) for n in range(0,len(wav),frame)])
 voiced=np.flatnonzero(rms>max(.001,float(rms.max())*.02))
 longest=run=0
 for quiet in rms<.001:
  run=run+1 if quiet else 0;longest=max(longest,run)
 entry={'id':ref['id'],'text':text,'audio_path':str(target.relative_to(T)),
        'sample_count':len(wav),'sample_rate':sr,'actual_duration_seconds':duration,
        'reference_duration_seconds':ref['duration_seconds'],'difference_seconds':duration-ref['duration_seconds'],
        'timeline_start_seconds':cursor/sr,'timeline_end_seconds':(cursor+len(wav))/sr,
        'peak_amplitude':float(np.abs(wav).max()),'clipped_sample_count':int(np.sum(np.abs(wav)>=.999)),
        'leading_quiet_seconds':float(voiced[0]*.02) if len(voiced) else duration,
        'trailing_quiet_seconds':float(max(0,duration-(voiced[-1]+1)*.02)) if len(voiced) else duration,
        'longest_quiet_seconds':longest*.02,'listening_review':'pending_user',
        'asr_verification':'not_run','sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
 meta.write_text(json.dumps(entry,ensure_ascii=False,indent=2),encoding='utf-8')
 report['segments'].append(entry);cursor+=len(wav);arrays.append(wav)
 (O/'voice-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'{ref["id"]}: {duration:.3f}s; reference {ref["duration_seconds"]:.3f}s; delta {entry["difference_seconds"]:+.3f}s',flush=True)
full=np.concatenate(arrays)
sf.write(str(O/'final_voice.wav'),full,sr,subtype='PCM_16')
sf.write(str(O/'final_voice.mp3'),full,sr,format='MP3',subtype='MPEG_LAYER_III')
decoded,decoded_sr=sf.read(str(O/'final_voice.mp3'),dtype='float32');assert decoded_sr==sr and np.isfinite(decoded).all()
report.update(status='generated_pending_listening_review',total_duration_seconds=len(full)/sr,
              reference_duration_seconds=31.7,total_difference_seconds=len(full)/sr-31.7,
              target_range_seconds=[30.7,32.7],within_target=30.7<=len(full)/sr<=32.7,
              mp3_decoded_duration_seconds=len(decoded)/decoded_sr,
              mp3_duration_difference_from_wav_seconds=(len(decoded)-len(full))/sr,
              final_mp3_path=str((O/'final_voice.mp3').relative_to(T)),
              final_wav_path=str((O/'final_voice.wav').relative_to(T)))
(O/'voice-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(recipe_path,O/('recipe.before-voice-'+datetime.now().strftime('%H%M%S')+'.json'))
recipe['voice'].update(configuration_status='batch_generated_pending_listening_review',
   variant_id='voxcpm-01',report_path=str((O/'voice-report.json').relative_to(T)),
   final_audio_path=report['final_mp3_path'],final_wav_path=report['final_wav_path'],
   actual_duration_seconds=report['total_duration_seconds'],reference_difference_seconds=report['total_difference_seconds'],
   within_target=report['within_target'],audio_review_status='pending_user',segments=report['segments'])
for ref,voice in zip(recipe['segments'],report['segments']):
 ref['voice']={k:voice[k] for k in ['text','audio_path','actual_duration_seconds','reference_duration_seconds','difference_seconds','timeline_start_seconds','timeline_end_seconds']}
recipe['status']='voice_generated_pending_user_review'
recipe['timeline_rebuild_required']=True
recipe_path.write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 分镜配音实测报告','',f'已生成18个独立WAV文件。总时长 {len(full)/sr:.3f} 秒，比参考31.7秒相差 {len(full)/sr-31.7:+.3f} 秒。',
       '当前为自然速度试听版，未删词、未变速、未裁剪静音；逐段首尾停顿原样保留。',
       '每段使用同一段此前生成的合成音色作为提示音频；没有使用原参考视频说话人的声音。',
       '仅做文件解码、峰值、静音区间及时间统计，未执行ASR核对；发音、语气和段落衔接等待试听。','',
       '|镜头|参考秒|实际秒|差异秒|','|---|---:|---:|---:|']
for e in report['segments']:lines.append(f"|{e['id']}|{e['reference_duration_seconds']:.3f}|{e['actual_duration_seconds']:.3f}|{e['difference_seconds']:+.3f}|")
lines+=['','总时长是否满足30.7～32.7秒：'+('是' if report['within_target'] else '否，需用户试听后决定语速或文案调整。'),
        'recipe保留原镜头时长，新增每镜头voice及实际语音时间线字段，尚未据此重渲染视频。']
(O/'配音时长报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('COMPLETE: '+json.dumps({k:report[k] for k in ['total_duration_seconds','total_difference_seconds','within_target','mp3_decoded_duration_seconds']},ensure_ascii=True),flush=True)
