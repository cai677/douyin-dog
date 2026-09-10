"""Publish the visually classified library without modifying raw assets or approvals."""
import json, hashlib, os, math
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent.parent
RUN=ROOT/'batch-library'
CAT=PROJECT/'assets/catalog'
LIB=PROJECT/'assets/classified/pet-trimmer'
LIB.mkdir(parents=True,exist_ok=True)
CATEGORIES={'P':'01-产品展示','U':'02-使用动作','S':'03-使用场景','D':'04-对象细节','F':'05-功能演示','E':'06-效果展示','X':'99-待确认'}
ACTIONS={
 'product':('P','产品外观'),'package':('P','包装配件'),'compare':('P','多产品对比'),'blade':('P','刀头特写'),'other':('P','其他电推展示'),
 'trim':('U','脚毛修剪'),'ear':('U','耳部修剪'),'mouth':('U','嘴边修剪'),'rear':('U','尾臀局部修剪'),
 'body':('U','身体局部修剪'),'headtrim':('U','头面局部修剪'),'wipe':('U','擦拭清洁'),'comb':('U','毛发梳理'),'scissors':('U','剪刀修剪'),
 'pet':('S','宠物与产品互动'),'walk':('S','室内活动'),'lick':('S','舔脚动作'),'litter':('S','猫砂盆场景'),'talk':('S','人物讲解'),'scene':('S','生活场景'),
 'detail':('D','对象局部细节'),'result':('E','效果或前后对照'),
 'contact':('F','皮肤接触演示'),'hair':('F','切毛演示'),'charge':('F','充电演示'),'wash':('F','水洗演示'),'noise':('F','仪表声音演示'),'light':('F','照明演示'),
 'intro':('X','片头片尾或黑场'),'mixed':('X','混合动作待圈选')}
SPECIES={'c':'猫','d':'狗','n':'无宠物主体','u':'物种待确认'}
COLORS={'l':'浅色','y':'黄绿色','m':'多色或多产品','o':'其他型号','u':'未见产品或待确认'}
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_suffix(path.suffix+'.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');t.replace(path)
def rel(p):return str(p.relative_to(PROJECT)).replace('\\','/')
def link(p):return str(p.resolve()).replace('\\','/')
def filehash(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

summary=json.loads((RUN/'ingest-summary.json').read_text())
overrides=json.loads((RUN/'review-overrides.json').read_text(encoding='utf-8'))['overrides']
assets=[];clips=[]
for mp in summary['manifests']:
    m=json.loads((PROJECT/mp).read_text(encoding='utf-8'));entry=m['source'];s=entry['source_label']
    labels=json.loads((RUN/'labels'/f'{s}.json').read_text())
    if len(labels['codes'])!=len(m['clips']):raise RuntimeError('Labels mismatch '+s)
    if not m['full_decode_passed'] or not m['source_hash_unchanged']:raise RuntimeError('Input QA failed')
    for c,code in zip(m['clips'],labels['codes']):
        action,species,color=code.split(':');extra=overrides.get(c['display_id'],{})
        action=extra.get('action',action)
        main,title=ACTIONS[action];risks=[]
        if c['source_role']=='reference_duplicate':risks.append('与参考原片相同，默认不作替换素材')
        if c['duration_seconds']<.4:risks.append('短于0.4秒，动作完整性需复核')
        if action=='intro':risks.append('片头片尾或黑场，不进入生产候选')
        if action=='mixed':risks.append('混合动作，需圈选有效区间')
        if color=='o':risks.append('其他型号电推，不与目标型号混用')
        if action=='compare' or color=='m':risks.append('多色或多产品同框，型号与颜色须确认')
        if species=='u':risks.append('物种未确认')
        if c['duration_seconds']>=8:risks.append('长段，使用时按完整动作选择子区间')
        if extra.get('note'):risks.append(extra['note'])
        # Detect border/blank characteristics from already extracted first/middle/last proxies.
        images=[cv2.imread(str(PROJECT/c['frames'][key])) for key in ['start','middle','end']]
        if any(im is None for im in images):raise RuntimeError('Missing review image')
        mid=images[1]; gray=cv2.cvtColor(mid,cv2.COLOR_BGR2GRAY)
        black_ratio=float((gray<12).mean())
        border_ratio=float(((gray[:max(1,gray.shape[0]//10)]<12).mean()+(gray[-max(1,gray.shape[0]//10):]<12).mean())/2)
        if border_ratio>.9:risks.append('上下黑边或暗背景，裁切需复核')
        if black_ratio>.95:risks.append('近黑场')
        hold=action in ['intro','mixed'] or color=='o' or c['duration_seconds']<.4 or c['source_role']=='reference_duplicate' or black_ratio>.95
        folder=CATEGORIES['X' if hold else main]
        c.update({'main_category':CATEGORIES[main],'browse_category':folder,'action':action,'action_label':title,
                  'species':species,'species_label':SPECIES[species],'product_color':color,'color_label':COLORS[color],
                  'sku':'unverified','character_identity':'unverified','classification_status':'assistant_visual_classified',
                  'classification_basis':labels['basis']+('; supplemental temporal samples reviewed' if c['duration_seconds']>=8 else ''),
                  'review_flags':risks,'production_approval':'not_approved',
                  'library_status':'hold' if hold else 'classified_candidate',
                  'burned_in_text_status':'visible_in_review_samples' if action!='intro' else 'not_assessed',
                  'text_removed':False,'black_ratio':round(black_ratio,4),
                  'visual_speed':1.0,'image_color_means':[im.mean(axis=(0,1)).round(2).tolist() for im in images]})
        name=f'{c["display_id"]}_{SPECIES[species]}_{title}_{COLORS[color]}_{c["duration_seconds"]:.2f}s.mp4'
        target=LIB/folder/name;target.parent.mkdir(exist_ok=True)
        original=PROJECT/c['preview']
        if not target.exists():os.link(original,target)
        elif not os.path.samefile(original,target):raise RuntimeError('Browse collision: '+str(target))
        c['browse_preview']=rel(target)
        clips.append(c)
    assets.append({'schema_version':2,**entry,'product_family':'pet-trimmer','sku':'unverified',
                   'duration_seconds':m['duration_seconds'],'fps':m['fps'],'width':m['width'],'height':m['height'],
                   'frame_count':m['frame_count'],'full_decode_passed':True,'source_hash_unchanged':True,
                   'clip_ids':[c['clip_id'] for c in m['clips']],'analysis_manifest':mp})

# Exact proxy hashes and conservative multi-frame similarity candidates; no deletion or claimed human approval.
exact=defaultdict(list)
for c in clips:
    c['preview_sha256']=filehash(PROJECT/c['preview']);exact[c['preview_sha256']].append(c)
    c['duplicate_group_id']='exact_'+c['preview_sha256'][:20]
fp=[[int(h,16) for h in c['visual_fingerprints']] for c in clips]
pairs=[]
for i,c in enumerate(clips):
    if c['action'] in ['intro','mixed'] or c['black_ratio']>.8:continue
    for j in range(i):
        other=clips[j]
        if other['action'] in ['intro','mixed'] or other['black_ratio']>.8:continue
        if c['species']!=other['species'] or c['product_color']!=other['product_color']:continue
        distances=[(x^y).bit_count() for x,y in zip(fp[i],fp[j])]
        if max(distances)>12 or sum(distances)>24:continue
        color_diff=float(np.abs(np.array(c['image_color_means'])-np.array(other['image_color_means'])).mean())
        if color_diff>20:continue
        pairs.append({'left':other['clip_id'],'right':c['clip_id'],'left_display':other['display_id'],'right_display':c['display_id'],
                      'hamming_start_mid_end':distances,'mean_color_difference':round(color_diff,2),
                      'status':'candidate_needs_temporal_review','same_action':c['action']==other['action']})
pair_lookup=defaultdict(list)
for p in pairs:
    pair_lookup[p['left']].append(p['right']);pair_lookup[p['right']].append(p['left'])
for c in clips:
    c['similarity_candidates']=pair_lookup[c['clip_id']]
    c['visual_dedup_status']='three_frame_candidate_scan_complete_not_final_duplicate_verdict'

def save_jsonl(path,rows):
    # Upsert by identity; preserve unrelated product libraries.
    key='asset_id' if path.name=='assets.jsonl' else 'clip_id'
    existing=[]
    if path.exists():existing=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    old_by_id={r[key]:r for r in existing}
    for r in rows:
        old=old_by_id.get(r[key],{})
        # Preserve explicit downstream approvals and identity adjudications on identical media.
        if key=='clip_id' and old.get('preview_sha256')==r.get('preview_sha256'):
            for field in ['production_approval','approved_ranges','reviewer','reviewed_at','approval_history']:
                if field in old:r[field]=old[field]
            for field in ['sku','character_identity']:
                if old.get(field) not in [None,'unverified']:r[field]=old[field]
            changed=any(old.get(f)!=r.get(f) for f in ['action','species','product_color'])
            if changed and old.get('production_approval') not in [None,'not_approved','needs_review']:
                r['previous_production_approval']=old['production_approval']
                r['production_approval']='needs_review'
                r['review_flags'].append('分类变化，保留历史审批并重新检查适用性')
    new_ids={r[key] for r in rows}
    merged=[r for r in existing if r[key] not in new_ids]+rows
    if path.exists():
        backup=RUN/(path.name+'.before-publish')
        if not backup.exists():backup.write_bytes(path.read_bytes())
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in merged),encoding='utf-8');temp.replace(path)

save_jsonl(CAT/'assets.jsonl',assets)
save_jsonl(CAT/'clips.jsonl',clips)
write(CAT/'taxonomy.json',{'schema_version':1,'categories':CATEGORIES,'actions':ACTIONS,'species':SPECIES,'product_colors':COLORS,
      'principle':'Main taxonomy shared across products; queries scoped to product identity, action and constraints'})
write(RUN/'similarity-candidates.json',{'schema_version':1,'method':'three aligned DCT hashes, max distance 12, sum <=24, mean BGR difference <=20',
      'limitations':'Heuristic candidate scan. Does not prove temporal duplication; no crop/time-shift robustness guarantee. No files deleted.',
      'pairs':pairs,'exact_proxy_duplicate_groups':[[c['display_id'] for c in group] for group in exact.values() if len(group)>1]})

font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
groups=defaultdict(list)
for c in clips:groups[c['browse_category']].append(c)
for folder,items in groups.items():
    directory=LIB/folder;rows=[]
    for c in items:
        rows.append(f'| [{c["display_id"]}](<{link(PROJECT/c["browse_preview"])}>) | {c["species_label"]} | {c["action_label"]} | {c["color_label"]} | {c["duration_seconds"]:.2f} | {c["start_seconds"]:.3f}–{c["end_seconds"]:.3f} | '+('；'.join(c['review_flags']) or '型号与字幕需在选用时核对')+' |')
    body=f'# {folder}\n\n共 {len(items)} 段；预览为静音缩略片，生产需回到原片区间。分类完成不代表生产批准。\n\n| 片段预览 | 对象 | 动作 | 颜色 | 秒数 | 原片区间 | 限制 |\n| --- | --- | --- | --- | --- | --- | --- |\n'+'\n'.join(rows)+'\n'
    (directory/'片段目录.md').write_text(body,encoding='utf-8')

counts=Counter(c['browse_category'] for c in clips)
species_counts=Counter(c['species_label'] for c in clips if c['library_status']=='classified_candidate')
total_duration=sum(a['duration_seconds'] for a in assets)
validation={'schema_version':1,'created_at':datetime.now(timezone.utc).isoformat(),'source_count':len(assets),'clip_count':len(clips),
 'category_counts':dict(counts),'candidate_species_counts':dict(species_counts),'source_duration_seconds':total_duration,
 'source_decode_passes':len(assets),'preview_decode_passes':len(clips),'source_hash_checks_passed':len(assets),
 'reference_duplicate_sources':[a['source_label'] for a in assets if a['role']=='reference_duplicate'],
 'similarity_candidate_pairs':len(pairs),'exact_proxy_duplicate_groups':sum(len(g)>1 for g in exact.values()),
 'mixed_clips':[c['display_id'] for c in clips if c['action']=='mixed'],
 'not_performed':['full real-time playback of every clip','ASR/OCR transcription','subtitle removal','SKU confirmation','production approval'],
 'errors':summary['errors']}
# Referential and complete-coverage validation.
for a in assets:
    ac=[c for c in clips if c['asset_id']==a['asset_id']]
    assert ac[0]['source_start_frame']==0 and ac[-1]['source_end_frame_exclusive']==a['frame_count']
    assert all(x['source_end_frame_exclusive']==y['source_start_frame'] for x,y in zip(ac,ac[1:]))
    for c in ac:
        assert (PROJECT/c['source_path']).exists() and (PROJECT/c['browse_preview']).exists()
        assert c['source_end_frame_exclusive']<=a['frame_count']
        assert all((PROJECT/p).exists() for p in c['frames'].values())
assert len({c['clip_id'] for c in clips})==len(clips)
validation['coverage_and_path_validation']='passed'
write(RUN/'validation.json',validation)

report=f'''# 素材库切分与分类交付

本次已完成 57 条原视频的入库、自动候选切分、预览导出、画面主分类和索引。原片未修改；没有执行配音、成片生成或生产素材批准。

## 结果

- 原视频合计 {total_duration/60:.2f} 分钟，生成 {len(clips)} 个区间；原片和所有预览完整解码检查通过。
- 固定为六个主分类加待确认区，不按每条视频增加分类。
- 可检索分类候选 {sum(c['library_status']=='classified_candidate' for c in clips)} 段，待确认/隔离 {sum(c['library_status']=='hold' for c in clips)} 段。候选数不是合格成片数量。
- 57 条视频字节哈希互不相同，其中 S42 与参考原片一致，其 18 段隔离，不当作新的替换素材。
- 附带 58 张图片、56 个音频保留原位，未当作视频重复切分。

## 分类入口

| 文件夹 | 片段数 |
| --- | --- |
{chr(10).join(f'| [{folder}](<{link(LIB/folder/"片段目录.md")}>) | {counts.get(folder,0)} |' for folder in CATEGORIES.values())}

## 怎么快速找素材

打开对应分类文件夹，文件名包含片段编号、猫狗、动作、颜色和秒数；目录文档可以点开预览。主索引保存原片路径和有效区间。以后可直接提出“找猫、浅色电推、脚毛修剪、至少两秒”等条件，从索引筛选即可，不重跑全部原片。

商品库：pet-trimmer。具体 SKU 尚未确认；浅色/黄绿色是视觉颜色标签，不能代替型号识别。不同商品必须使用独立 product_id。

预览最长边不超过 568 像素，保持原始比例、帧率和 1.00x，静音；分类目录通过硬链接引用这些派生预览，不重复保存一份媒体。实际剪辑回到原片区间。不要把这些浏览预览作为高清成片素材。

## 已检查与实际限制

- 所有片段中间帧已由助手按画面归类；试处理 S01 复用首中尾及切点复核结果。31 个至少 8 秒的长段另看了多点时间采样。
- 自动切点仍是候选，未对全部视频逐帧审定，也未完整实时播放全部片段。快速动作可能造成过切，连续长镜头可能包含多个动作；选用前检查首中尾和预览，必要时合并或重选源区间。
- {len(validation['mixed_clips'])} 个用途混合片段已隔离：{', '.join(validation['mixed_clips'])}。这是明确的待圈选项，不会自动当作纯动作使用。
- 小于 0.4 秒、片头片尾/近黑场、明显其他型号、参考副本进入待确认区；未删除任何原素材。
- 原片存在烧录字幕、教程水印、广告外框或遮挡，本次没有去字幕。文案中的性能/健康说法未经验证，只记录可见动作。
- 通过三帧指纹比较发现 {len(pairs)} 对视觉相似候选，需结合时间区间复核；没有把疑似相似直接当成已证实重复，也没有删除素材。
- 每段已保留来源 ID、源帧区间、标签、指纹、分类依据和限制。人物/宠物具体身份及精确 SKU 未确认。

## 数据与检查

- [机器素材索引](<{link(CAT/'assets.jsonl')}>)
- [机器片段索引](<{link(CAT/'clips.jsonl')}>)
- [分类与标签定义](<{link(CAT/'taxonomy.json')}>)
- [检查结果](<{link(RUN/'validation.json')}>)
- [相似候选明细](<{link(RUN/'similarity-candidates.json')}>)

本次不修改当前模板的 matches.json 和 recipe.json；下一步按参考镜头从本库筛候选并审核，而不是直接随机拼接。
'''
(RUN/'批量分类报告.md').write_text(report,encoding='utf-8')
(LIB/'素材库说明.md').write_text(report,encoding='utf-8')
print(json.dumps(validation,ensure_ascii=True))
