import json
from pathlib import Path
import cv2
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parent
out=root/'pilot-01'
a=json.loads((out/'analysis.json').read_text(encoding='utf-8'))
cap=cv2.VideoCapture(str(root.parent.parent/a['source']['path']))
items=[]
for cut in a['candidate_cuts']:
    for idx in [cut-1,cut]:
        cap.set(cv2.CAP_PROP_POS_FRAMES,idx)
        ok,f=cap.read()
        if not ok: raise RuntimeError(idx)
        items.append((idx,Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB))))
cap.release()
for page,start in enumerate(range(0,len(items),24),1):
    board=Image.new('RGB',(1080,4*345),'white')
    d=ImageDraw.Draw(board)
    for j,(idx,im) in enumerate(items[start:start+24]):
        im.thumbnail((180,315)); x,y=j%6*180,j//6*345
        board.paste(im,(x,y)); d.text((x+3,y+320),f'f{idx} / {idx/a["fps"]:.3f}s',fill='black')
    board.save(out/f'boundaries-{page:02d}.jpg')
