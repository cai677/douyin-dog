---
name: douyin-dog-material-library
description: "Build a reusable material library from Douyin pet-commerce videos: download with MeowLoad, split clips with audio, classify by shot/content type, and keep only final useful assets."
---

# Douyin Dog Material Library

Use this skill when the user wants to batch-download Douyin pet commerce videos and turn them into a product-level素材库 for二次创作. It is especially suited to dog/pet product videos where the useful output is organized reusable clips rather than a written拆解文档.

## Local Assumptions

- MeowLoad GUI: `E:\哼哼猫\MeowLoad\MeowLoad.exe`
- MeowLoad CLI: `E:\哼哼猫\MeowLoad\bin\meowload.exe`
- Python with OpenCV/Pillow/numpy: `C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe`
- Product libraries live under the requested workspace, normally `E:\chatgpt\daihuo-cutfactory\<商品名>\`.
- Use `ffmpeg` for final clip cutting so every segment keeps the original audio. In this workspace the proven package is `@ffmpeg-installer/ffmpeg`; if it is missing, install a project-local ffmpeg rather than using OpenCV-only output.

## Operating Rules

1. Download videos into a folder named after the product and normalize names as `<商品名>-01.mp4`, `<商品名>-02.mp4`, etc.
2. Use `0.2s` frame extraction only as boundary-observation precision. Do not treat every subtitle or small overlay change as a cut.
3. Split when the main visual purpose changes: pet eye symptom, eye cleaning/exam, eye-drop demo, product closeup, proof/report, person talking, result scene, price/purchase, or transition.
4. Keep continuous same-composition口播 together unless the subject, action, or visual purpose clearly changes.
5. Final clips must include sound. OpenCV-only clips are acceptable only as temporary diagnostics, not final deliverables.
6. Do not retain raw frame directories or frame contact sheets in the final library unless the user explicitly asks. They are temporary review aids and should be cleaned after classification.
7. Prefer Chinese category folder names for user-facing material libraries.

## Recommended Output Shape

For each video:

```text
<商品名>-01.mp4
<商品名>-01/
  material_auto/
    clips/
    keyframes/
    material_index.csv
    material_index.json
    segment_contact_sheet.jpg   # optional review artifact; remove if user wants lean output
```

For the product-level classified library:

```text
<商品名>/
  classified_by_content_中文/
    人物口播-医生讲解/
    宠物眼部症状-特写/
    眼部检查-擦拭-清洁/
    滴眼-上药使用演示/
    产品包装-瓶身-空镜/
    资质报告-成分-pH-背书/
    宠物状态-效果展示/
    价格-购买-支付画面/
    过渡-其他/
    classified_index.csv
```

## Script Workflow

The `scripts/` directory contains reusable helpers from the verified workflow:

- `download_douyin_batch.py`: download Douyin URLs with MeowLoad and normalize names.
- `prepare_batch_frames.py`: extract 0.2s frames and contact sheets for boundary review.
- `segment_batch_from_shots.py`: create audio-preserving clips from detected boundaries, with long-range splitting.
- `classify_materials.py`: copy clips into content-type folders from a JSON mapping.
- `verify_batch_materials.py`: check segment counts, keyframes, contact sheets, and audio presence.
- `make_segment_contact_sheet.py` and `make_frame_contact_sheets.py`: visual review helpers.

When using these scripts from a different project root, either copy them into that project or run them with paths adjusted to the current workspace. Read [references/content-classification.md](references/content-classification.md) before creating a new product classification map.

## Validation

Before reporting completion:

- Count downloaded source videos.
- Count generated clip files and keyframes against `material_index.csv/json`.
- Verify at least one representative clip per source video has an audio stream.
- Count classified files against `classified_index.csv`.
- If temporary `frames_0_2s` or `frame_sheets` directories were created and the user requested lean output, remove them after classification.
