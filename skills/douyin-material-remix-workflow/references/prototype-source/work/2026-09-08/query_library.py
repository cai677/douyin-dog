"""Fast read-only candidate retrieval; does not grant production approval."""
import argparse,json
from pathlib import Path
root=Path(__file__).resolve().parent
project=root.parent.parent
p=argparse.ArgumentParser()
p.add_argument('--product',default='pet-trimmer')
p.add_argument('--species',choices=['c','d','n','u'])
p.add_argument('--action')
p.add_argument('--color',choices=['l','y','m','o','u'])
p.add_argument('--min-seconds',type=float,default=0.4)
p.add_argument('--limit',type=int,default=12)
p.add_argument('--include-hold',action='store_true')
p.add_argument('--output',type=Path)
args=p.parse_args()
clips=[json.loads(line) for line in (project/'assets/catalog/clips.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
candidates=[c for c in clips if c['product_family']==args.product
            and (args.include_hold or c['library_status']=='classified_candidate')
            and (not args.species or c['species']==args.species)
            and (not args.action or c['action']==args.action)
            and (not args.color or c['product_color']==args.color)
            and c['duration_seconds']>=args.min_seconds]
candidates.sort(key=lambda c:(len(c['review_flags']),abs(c['duration_seconds']-args.min_seconds),c['clip_id']))
selected=[]; used_sources=set();similar=set()
# Prefer distinct sources and avoid identified visual-neighbor candidates in the returned shortlist.
for c in candidates:
    if c['clip_id'] in similar or c['asset_id'] in used_sources:continue
    selected.append(c);used_sources.add(c['asset_id']);similar.update(c.get('similarity_candidates',[]))
    similar.add(c['clip_id'])
    if len(selected)>=args.limit:break
result={'total_matching_intervals':len(candidates),'shortlist_count':len(selected),
        'status':'classification_candidates_only_not_production_approved',
        'global_limits':['SKU unverified','subtitles not removed','candidate boundaries need selection-time review'],
        'clips':[{k:c[k] for k in ['display_id','clip_id','source_path','start_seconds','end_seconds','duration_seconds',
                  'action_label','species_label','color_label','browse_preview','review_flags']} for c in selected]}
if args.output:
    dest=args.output.resolve()
    if not dest.is_relative_to(project.resolve()):raise RuntimeError('Output must remain in this project')
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
