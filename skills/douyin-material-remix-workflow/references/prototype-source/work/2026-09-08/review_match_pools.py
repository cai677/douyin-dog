import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
T=Path(__file__).resolve().parent; R=T.parents[1]; O=T/'matching-01'
cs=[json.loads(x) for x in (R/'assets/catalog/clips.jsonl').read_text(encoding='utf-8').splitlines()]
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
groups={
 'product':[c for c in cs if c['action'] in ['product','blade','pet'] and c['species'] in ['c','n'] and c['product_color']=='l'],
 'cat-result':[c for c in cs if c['action']=='result' and c['species']=='c'],
 'cat-trim':[c for c in cs if c['action']=='trim' and c['species']=='c' and c['product_color']=='l'],
 'contact':[c for c in cs if c['action']=='contact' and c['species'] in ['c','n'] and c['product_color']=='l'],
}
for name,items in groups.items():
 items=[c for c in items if c['library_status']!='hold' and c['source_label'] not in ['S15','S42']]
 for page in range(0,len(items),24):
  sheet=Image.new('RGB',(1200,4*330),'white'); d=ImageDraw.Draw(sheet)
  for i,c in enumerate(items[page:page+24]):
   im=Image.open(R/c['frames']['middle']).convert('RGB');im.thumbnail((196,280)); x=(i%6)*200;y=(i//6)*330
   sheet.paste(im,(x+(200-im.width)//2,y+22));d.text((x+3,y+2),c['display_id']+' '+f"{c['duration_seconds']:.2f}s",font=font,fill='black')
   d.text((x+3,y+304),c['action'],font=font,fill='black')
  sheet.save(O/f'pool-{name}-{page//24+1}.jpg')
