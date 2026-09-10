import json, math
from pathlib import Path
import cv2
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parent
project=root.parent.parent
run=root/'batch-library'
summary=json.loads((run/'ingest-summary.json').read_text())
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
cards=[]; ids=[]
for manifest in summary['manifests']:
    data=json.loads((project/manifest).read_text(encoding='utf-8'))
    labels=json.loads((run/'labels'/f'{data["source"]["source_label"]}.json').read_text())
    assert len(labels['codes'])==len(data['clips']),(data['source']['source_label'],len(labels['codes']),len(data['clips']))
    for c in data['clips']:
        if c['duration_seconds']<8: continue
        ids.append(c['display_id'])
        cap=cv2.VideoCapture(str(project/c['preview']))
        count=c['source_end_frame_exclusive']-c['source_start_frame']
        fractions=[.05,.28,.72,.95] if c['duration_seconds']<35 else [.02,.15,.28,.42,.57,.72,.85,.98]
        for fraction in fractions:
            idx=min(count-1,round(count*fraction));cap.set(cv2.CAP_PROP_POS_FRAMES,idx)
            ok,f=cap.read()
            if not ok: raise RuntimeError(c['display_id'])
            im=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB));im.thumbnail((180,300))
            card=Image.new('RGB',(180,340),'white');card.paste(im,((180-im.width)//2,0))
            d=ImageDraw.Draw(card);d.text((3,303),c['display_id'],font=font,fill='black')
            d.text((3,323),f'{c["start_seconds"]+idx/c["fps"]:.1f}s',font=font,fill='black');cards.append(card)
        cap.release()
out=run/'long-review';out.mkdir(exist_ok=True)
for page,offset in enumerate(range(0,len(cards),24),1):
    chunk=cards[offset:offset+24]; board=Image.new('RGB',(1080,math.ceil(len(chunk)/6)*340),'#eee')
    for j,im in enumerate(chunk):board.paste(im,(j%6*180,j//6*340))
    board.save(out/f'{page:02d}.jpg')
print(json.dumps({'long_clips':ids,'pages':math.ceil(len(cards)/24)}))
