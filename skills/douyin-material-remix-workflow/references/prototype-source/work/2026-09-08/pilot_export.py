"""Export one pilot's reviewed boundaries; all production approvals remain pending."""
import json, hashlib
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
project=root.parent.parent
out=root/'pilot-01'
a=json.loads((out/'analysis.json').read_text(encoding='utf-8'))
annotations=json.loads((out/'annotations.json').read_text(encoding='utf-8'))
source=project/a['source']['path']
source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash==a['source']['sha256']
fps=a['fps']
edges=[0]+a['candidate_cuts']+[a['frame_count']]
assert len(annotations['labels'])==len(edges)-1
(out/'clips').mkdir(exist_ok=True)
(out/'frames').mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
smallfont=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
cap=cv2.VideoCapture(str(source))
clips=[]
cards=[]
for i,((start,end),label) in enumerate(zip(zip(edges,edges[1:]),annotations['labels'])):
    title,category,limitation,slots=label
    cid=f'{a["asset_id"]}_{start:06d}_{end:06d}'
    prefix=f'{i:02d}'
    target=out/'clips'/f'{prefix}.mp4'
    writer=cv2.VideoWriter(str(target),cv2.VideoWriter_fourcc(*'mp4v'),fps,(360,640))
    if not writer.isOpened(): raise RuntimeError('Cannot open writer')
    cap.set(cv2.CAP_PROP_POS_FRAMES,start)
    picks={start:("start"), (start+end)//2:("middle"),end-1:("end")}
    framepaths={}
    fingerprints=[]
    middle=None
    for n in range(start,end):
        ok,frame=cap.read()
        if not ok: raise RuntimeError('Source ended unexpectedly')
        writer.write(cv2.resize(frame,(360,640)))
        if n in picks:
            tag=picks[n]
            p=out/'frames'/f'{prefix}-{tag}.jpg'
            cv2.imwrite(str(p),frame)
            framepaths[tag]=str(p.relative_to(out))
            gray=cv2.resize(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),(32,32)).astype(np.float32)
            low=cv2.dct(gray)[:8,:8].flatten()
            bits=low>np.median(low[1:])
            fingerprints.append({'source_frame':n,'phash_dct64':f'{int("".join("1" if x else "0" for x in bits),2):016x}'})
            if tag=='middle': middle=frame.copy()
    writer.release()
    check=cv2.VideoCapture(str(target)); decoded=0
    while True:
        ok,_=check.read()
        if not ok: break
        decoded+=1
    output_fps=check.get(cv2.CAP_PROP_FPS)
    check.release()
    if decoded!=end-start or abs(output_fps-fps)>.01: raise RuntimeError('Preview validation failed')
    clip={'clip_id':cid,'display_id':prefix,'asset_id':a['asset_id'],'source_id':a['asset_id'],
          'source_path':a['source']['path'],'source_start_frame':start,'source_end_frame_exclusive':end,
          'source_fps':fps,'start_seconds':start/fps,'end_seconds':end/fps,'duration_seconds':(end-start)/fps,
          'title':title,'category':category,'species':'dog','product_model':'unverified',
          'product_color':'yellow' if i>=23 else 'light_color_or_not_visible',
          'burned_in_subtitles':i>0,'limitation':limitation,
          'semantic_reference_candidates':slots,'production_approval':'not_approved',
          'classification_status':'assistant_frame_reviewed_pending_user',
          'availability':'rejected_intro' if i==0 else 'candidate_with_constraints',
          'reference_match_status':'semantic_only_not_production_approved',
          'visual_fingerprints':fingerprints,'fingerprint_method':'dct32_low8_median_ac_v1',
          'duplicate_group_id':None,'visual_dedup_status':'not_run_across_library',
          'preview':str(target.relative_to(out)),'preview_audio':False,'preview_scale':'360x640',
          'preview_fully_decoded':True,'preview_frame_count':decoded,'frames':framepaths}
    clips.append(clip)
    card=Image.new('RGB',(300,625),'#ffffff')
    im=Image.fromarray(cv2.cvtColor(middle,cv2.COLOR_BGR2RGB)); im.thumbnail((300,520))
    card.paste(im,((300-im.width)//2,0))
    d=ImageDraw.Draw(card)
    d.text((8,527),f'{prefix}  {title}',font=smallfont,fill='#18263b')
    d.text((8,553),f'{start/fps:.2f}–{end/fps:.2f}s · {(end-start)/fps:.2f}s',font=smallfont,fill='#4b5669')
    d.text((8,579),category+(' · 排除' if i==0 else ' · 待审核'),font=smallfont,fill='#a04f19')
    cards.append(card)
cap.release()
for page,offset in enumerate(range(0,len(cards),9),1):
    chunk=cards[offset:offset+9]
    board=Image.new('RGB',(900,625*((len(chunk)+2)//3)),'#e8edf3')
    for j,card in enumerate(chunk): board.paste(card,(j%3*300,j//3*625))
    board.save(out/f'classification-{page:02d}.jpg')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
assert sum(c['preview_frame_count'] for c in clips)==a['frame_count']
data={'schema_version':1,'created_at':datetime.now(timezone.utc).isoformat(),'path_base':str(out),
      'source_path_base':str(project),'asset_id':a['asset_id'],'source_sha256':source_hash,
      'reference_template':'reference-2026-09-08-candidate-v1','review_basis':annotations['review_basis'],
      'scope':'one asset only; existing matches untouched','clips':clips}
(out/'segments.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
inv=json.loads((out/'inventory.json').read_text(encoding='utf-8'))
categories=Counter(c['category'] for c in clips if c['display_id']!='00')
rows=[]
for c in clips:
    p=c['preview'].replace('\\','/')
    rows.append(f'| [{c["display_id"]}]({p}) | {c["start_seconds"]:.3f}–{c["end_seconds"]:.3f} | {c["duration_seconds"]:.3f} | {c["title"]} | {c["limitation"]} |')
report=f'''# 单条素材切分分类试处理

状态：切分和画面分类已完成，等待用户确认，尚未批准进入成片；其余 56 条视频未切分分类。

## 已收到的文件

- 57 个 MP4、58 张 JPG、27 个 M4A、29 个 MP3。
- 57 个视频的 SHA-256 各不相同，但其中 1 条与现有参考原片完全相同，已在 inventory.json 标记。
- 这里只完成字节级重复检查，没有对整库做视觉近似去重；音频和图片不计入视频数量。

## 本条来源与结果

源文件：{source.name}

- 素材 ID：{a['asset_id']}；哈希：{source_hash}。
- 原片：{a['width']}×{a['height']}、{fps:g}fps、{a['frame_count']} 帧、{a['duration_seconds']:.3f} 秒；完整解码通过。
- 分为 25 个区间：00 是 0.10 秒的缩小黑边片头，排除生产；其余 24 个是待审核内容片段，分为 {len(categories)} 类。
- 检查了每个检测切点相邻两帧、片段首中尾帧及每秒总览，切点均有可见变化。没有完整实时播放审核，仍需用户看预览确认漏切和动作完整性。
- 预览为 360×640、原速、静音，仅供分类审核，不是 1080×1920/60fps 成片；原音频保留在未修改的原文件中。
- 25 个预览全部重新完整解码校验，帧数合计 1018，与原片一致，源哈希前后相同。

## 分类分布

{chr(10).join('- '+k+'：'+str(v)+' 段' for k,v in categories.items())}

## 分类总览

![分类总览 1](classification-01.jpg)

![分类总览 2](classification-02.jpg)

![分类总览 3](classification-03.jpg)

## 按片段检查

点击编号打开对应静音片段。时间使用原视频的左闭右开区间。

| 预览 | 原片区间/秒 | 时长/秒 | 画面分类 | 复用限制 |
| --- | --- | --- | --- | --- |
{chr(10).join(rows)}

## 与现有参考的关系

- 当前参考主体是猫，本条主体是狗。修脚毛、舔脚、肉垫效果只能作为语义相似候选，不可直接接入猫的连续镜头。
- 13 切毛演示、14 刀头展示、15 皮肤接触演示与参考用途接近，但产品型号未确认，手掌与手臂有差异、背景仍含狗。
- 23–24 为黄色产品，其他主要为浅色产品；单独标记颜色，未确认型号前不混为同一 SKU。
- 几乎全部内容段有原视频烧录字幕；本次未去除字幕，不可把预览当作已清理生产素材。
- 字幕中的健康、锋利、安全和续航说法未验证，本次只按可见动作分类。
- 未发现猫砂盆画面，不能用室内追玩具强行匹配。
- 每段的候选参考镜头 ID 见 segments.json，均未批准；现有 recipe.json 和 matches.json 未更改。

## 本次需要对齐的规则

1. 切分粒度：保留真实画面切换，包括同一产品不同角度的跳切，不按字幕换句机械分割。
2. 分类粒度：画面动作分类与参考用途分开；不同物种、颜色、其他型号、遮挡及烧录字幕均显式标记。
3. 确认这套结果后再处理剩余素材；不同意见可按片段编号指出合并、拆分或改分类。

机器记录：[区间及标签](segments.json) · [文件与哈希清单](inventory.json)。
'''
(out/'试处理报告.md').write_text(report,encoding='utf-8')
print(json.dumps({'clips':len(clips),'excluded':1,'categories':dict(categories),'validated_frames':sum(c['preview_frame_count'] for c in clips),'source_unchanged':True,'report':str(out/'试处理报告.md')},ensure_ascii=True))
