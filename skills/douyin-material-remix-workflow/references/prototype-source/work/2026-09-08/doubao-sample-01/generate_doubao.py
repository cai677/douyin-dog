"""Run locally; credential is held in memory and never written to reports."""
import base64, getpass, hashlib, json, os, re, sys, uuid, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone
import soundfile as sf
import numpy as np

HERE=Path(__file__).resolve().parent
TASK=HERE.parent
SPEECH_RATE=int(os.environ.get('DOUBAO_TTS_SPEECH_RATE','0'))
if not -50<=SPEECH_RATE<=100:raise ValueError('Speech rate out of range')
SPEAKER=os.environ.get('DOUBAO_TTS_SPEAKER','zh_male_beijingxiaoye_emo_v2_mars_bigtts').strip()
if not re.fullmatch(r'[a-zA-Z0-9_]+',SPEAKER):raise ValueError('Invalid speaker ID')
folder=('voice' if SPEECH_RATE==0 else 'voice-rate'+str(SPEECH_RATE))
if SPEAKER!='zh_male_beijingxiaoye_emo_v2_mars_bigtts':folder='voice-'+SPEAKER+'-rate'+str(SPEECH_RATE)
OUT=HERE/folder;OUT.mkdir(exist_ok=True)
URL='https://openspeech.bytedance.com/api/v3/tts/unidirectional'
RESOURCE='volc.service_type.10029'
def save(path,data):
 tmp=path.with_suffix(path.suffix+'.tmp')
 tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
def failure_detail(raw,key,status,request_id,headers=None):
 """Keep only diagnostic fields; never persist requests or credential headers."""
 try:
  obj=json.loads(raw)
  if not isinstance(obj,dict):obj={}
 except (ValueError,TypeError):obj={}
 details={k:obj[k] for k in ('code','message','msg','error_code','error_msg') if k in obj}
 if isinstance(obj.get('error'),dict):
  details['error']={k:obj['error'][k] for k in ('code','message','type') if k in obj['error']}
 elif isinstance(obj.get('error'),str):details['error']=obj['error']
 if not details:
  details={'response_excerpt':raw[:3000] if raw else '(empty response body)'}
 if headers:
  allowed=('content-type','server','via','x-api-status-code','x-api-message','x-api-error-code','x-api-error-message','x-tt-logid')
  details['response_headers']={k:v for k,v in headers.items() if k.lower() in allowed}
 safe=json.dumps(details,ensure_ascii=True).replace(key,'[REDACTED]')
 safe=re.sub(r'(?i)(?:bearer\s+)[A-Za-z0-9._;=-]+','Bearer [REDACTED]',safe)
 safe=re.sub(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}','[REDACTED-ID]',safe)
 report={'http_or_service_status':status,'details':safe[:3000],'request_id':request_id,'speaker':SPEAKER,'resource_id':RESOURCE}
 save(HERE/'last-error.json',report)
 return 'TTS status '+str(status)+': '+safe[:1200]+' (see last-error.json)'
def synthesize(key,text,path):
 payload={'req_params':{'text':text,'speaker':SPEAKER,'additions':json.dumps({'disable_markdown_filter':True,'enable_language_detector':True,'enable_latex_tn':True,'disable_default_bit_rate':True,'max_length_to_filter_parenthesis':0,'cache_config':{'text_type':1,'use_cache':True}}),'audio_params':{'format':'mp3','sample_rate':24000}}}
 payload['user']={'uid':'douyin-dog-video'}
 payload['req_params']['audio_params']['speech_rate']=SPEECH_RATE
 request_id=str(uuid.uuid4())
 request=urllib.request.Request(URL,data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),headers={'x-api-key':key,'X-Api-Resource-Id':RESOURCE,'X-Api-Request-Id':request_id,'Content-Type':'application/json','Connection':'keep-alive'},method='POST')
 chunks=[];finished=False
 try:
  with urllib.request.urlopen(request,timeout=120) as response:
   for line in response:
    line=line.strip()
    if not line:continue
    if line.startswith(b'data:'):line=line[5:].strip()
    event=json.loads(line)
    code=event.get('code')
    if code not in (0,20000000):raise RuntimeError(failure_detail(json.dumps(event),key,code,request_id))
    if event.get('data'):chunks.append(base64.b64decode(event['data'],validate=True))
    if code==20000000:finished=True
 except urllib.error.HTTPError as error:
  raise RuntimeError(failure_detail(error.read(16384).decode('utf-8',errors='replace'),key,error.code,request_id,error.headers)) from None
 except urllib.error.URLError:
  raise RuntimeError('Cannot connect to TTS endpoint. Check local network.') from None
 if not finished or not chunks:raise RuntimeError('Incomplete TTS response; no completed audio saved')
 temp=path.with_suffix('.partial.mp3');temp.write_bytes(b''.join(chunks))
 audio,rate=sf.read(temp,dtype='float32',always_2d=True)
 if len(audio)==0 or rate!=24000:raise RuntimeError('Audio validation failed')
 temp.replace(path)
 return audio,rate
def main():
 key=os.environ.get('DOUBAO_TTS_API_KEY') or getpass.getpass('Doubao API key (hidden): ')
 key=key.strip()
 if not key.strip():raise RuntimeError('Missing API key')
 if any(ord(c)<33 or ord(c)>126 for c in key):
  raise RuntimeError('API key contains whitespace, control or non-ASCII characters. Nothing was sent. Please use the password dialog in the launcher.')
 print('API key input checked (value hidden).',flush=True)
 test=OUT/'connection-test.mp3'
 if not test.exists():synthesize(key,'豆包语音',test)
 print('Connection test passed.',flush=True)
 source=json.loads((TASK/'voice/voxcpm-01/voice-report.json').read_text(encoding='utf-8'))
 segments=[];waves=[];cursor=0
 for item in source['segments']:
  text=item['text'];path=OUT/(item['id']+'.mp3')
  signature=hashlib.sha256(json.dumps({'text':text,'speaker':SPEAKER,'resource':RESOURCE,'rate':24000,'speech_rate':SPEECH_RATE},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
  metadata=path.with_suffix('.json')
  cached=path.exists() and metadata.exists() and json.loads(metadata.read_text(encoding='utf-8')).get('input_signature')==signature
  if cached:audio,rate=sf.read(path,dtype='float32',always_2d=True)
  else:
   if path.exists():raise RuntimeError('Existing different audio: choose a new output directory')
   audio,rate=synthesize(key,text,path)
  duration=len(audio)/rate
  wav=path.with_suffix('.wav');sf.write(wav,audio,rate,subtype='PCM_16')
  row={'id':item['id'],'text':text,'input_signature':signature,'audio_path':str(wav.relative_to(TASK)),'mp3_path':str(path.relative_to(TASK)),'sample_rate':rate,'sample_count':len(audio),'actual_duration_seconds':duration,'reference_duration_seconds':item['reference_duration_seconds'],'difference_seconds':duration-item['reference_duration_seconds'],'timeline_start_seconds':cursor,'timeline_end_seconds':cursor+duration,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  save(metadata,row);segments.append(row);waves.append(audio);cursor+=duration
  print(item['id']+': '+format(duration,'.3f')+' seconds',flush=True)
 sf.write(OUT/'final_voice.wav',np.concatenate(waves),24000,subtype='PCM_16')
 sf.write(OUT/'final_voice.mp3',np.concatenate(waves),24000,format='MP3')
 save(OUT/'voice-report.json',{'schema_version':2,'created_at':datetime.now(timezone.utc).isoformat(),'provider':'doubao_tts','speaker':SPEAKER,'resource_id':RESOURCE,'speech_rate':SPEECH_RATE,'status':'generated_pending_listening_review','actual_duration_seconds':cursor,'reference_difference_seconds':cursor-31.7,'speed_changed':SPEECH_RATE!=0,'postprocess_time_stretch':False,'segments':segments})
 print('DONE. Voice saved to: '+str(OUT),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as error:
  print('FAILED: '+str(error),file=sys.stderr);sys.exit(1)
