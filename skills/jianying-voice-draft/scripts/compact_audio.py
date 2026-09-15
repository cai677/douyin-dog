"""Trim isolated leading noise and quiet edges; preserve sentence-internal audio."""
import argparse,array,json,math,wave,hashlib,sys
from pathlib import Path
def trim(source,output,head_ms=20,tail_ms=60,threshold_db=-42):
    with wave.open(str(source),'rb') as w:
        params=w.getparams()
        if params.nchannels!=1 or params.sampwidth!=2:raise ValueError('Requires mono PCM16 WAV')
        pcm=w.readframes(params.nframes)
    x=array.array('h');x.frombytes(pcm)
    if sys.byteorder!='little':x.byteswap()
    step=max(1,round(params.framerate*.01));threshold=32768*10**(threshold_db/20)
    active=[]
    for i in range(0,len(x),step):
        block=x[i:i+step];active.append(math.sqrt(sum(v*v for v in block)/len(block))>=threshold)
    ids=[i for i,v in enumerate(active) if v and sum(active[max(0,i-1):i+2])>=2]
    if not ids:raise ValueError('No sustained activity; requires manual review')
    start=max(0,ids[0]*step-round(params.framerate*head_ms/1000));end=min(len(x),(ids[-1]+1)*step+round(params.framerate*tail_ms/1000))
    if output.exists():raise FileExistsError('Preserve existing output')
    output.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(output),'wb') as w:
        w.setparams(params);w.writeframes(pcm[start*2:end*2])
    return dict(source=str(source),output=str(output),source_sha256=hashlib.sha256(pcm).hexdigest(),start_sample=start,end_sample=end,sample_rate=params.framerate,removed_head_seconds=start/params.framerate,removed_tail_seconds=(len(x)-end)/params.framerate,head_ms=head_ms,tail_ms=tail_ms,threshold_db=threshold_db,internal_audio='unchanged',listening_review='not_run')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--head-ms',type=float,default=20);p.add_argument('--tail-ms',type=float,default=60);p.add_argument('--threshold-db',type=float,default=-42);a=p.parse_args()
    if min(a.head_ms,a.tail_ms)<0:p.error('Padding cannot be negative')
    r=trim(a.source,a.output,a.head_ms,a.tail_ms,a.threshold_db)
    a.output.with_suffix('.trim.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,ensure_ascii=True))
