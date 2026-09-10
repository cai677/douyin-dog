import json
from pathlib import Path
import cv2

root = Path(__file__).resolve().parent
report = json.loads((root / 'reference-analysis.json').read_text(encoding='utf-8'))
cap = cv2.VideoCapture(str(root / 'reference-2026-09-08.mp4'))
for segment in report['segments']:
    target = root / 'video_clips' / (segment['id'] + '-preview.mp4')
    writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*'mp4v'), report['fps'], (540, 960))
    if not writer.isOpened():
        raise RuntimeError('Cannot create preview: ' + str(target))
    cap.set(cv2.CAP_PROP_POS_FRAMES, segment['start_frame'])
    written = 0
    for _ in range(segment['start_frame'], segment['end_frame_exclusive']):
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError('Unexpected end of video')
        writer.write(cv2.resize(frame, (540, 960)))
        written += 1
    writer.release()
    check = cv2.VideoCapture(str(target))
    assert int(check.get(cv2.CAP_PROP_FRAME_COUNT)) == written
    check.release()
    segment['preview'] = 'video_clips/' + target.name
    segment['preview_audio'] = False
cap.release()
(root / 'reference-analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
recipe_path = root / 'recipe.json'
recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
recipe['reference'] = {'path': 'reference-2026-09-08.mp4', 'duration_seconds': report['duration_seconds'],
                       'sha256': 'FAFAC499B36392A83EBF9A80522BDEA1882470D5B3EF3B7962E26BF1877FC145'}
recipe['product'] = 'pet-trimmer'
recipe['status'] = 'reference_candidates_extracted_awaiting_assets_and_voice_configuration'
recipe['segments'] = report['segments']
recipe_path.write_text(json.dumps(recipe, ensure_ascii=False, indent=2), encoding='utf-8')
matches = {'schema_version': 1, 'status': 'awaiting_assets', 'reference_analyzed': True,
           'reference_cut_review_status': 'candidate_boundaries_not_fully_verified', 'assets_analyzed': False,
           'segments': [{'id': s['id'], 'status': 'missing_material', 'candidates': [], 'approved': []} for s in report['segments']]}
(root / 'matches.json').write_text(json.dumps(matches, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Validated {len(report["segments"])} silent preview clips.')
