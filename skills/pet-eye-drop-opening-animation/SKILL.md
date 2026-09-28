---
name: pet-eye-drop-opening-animation
description: Create and assemble pet eye-drop product opening animations from a fixed 6-shot storyboard, including keyframe prompts, external clip handoff rules, file naming, validation, and final concatenation.
---

# Pet Eye Drop Opening Animation

Use this skill when the user wants to produce an 8 to 12 second pet eye-drop product opening animation from a scripted micro-story, especially when external tools generate keyframes or image-to-video clips and Codex later checks, organizes, and assembles the result.

The workflow is intentionally split into controlled short shots. Do not try to generate the whole 10 second video from one prompt unless the user explicitly asks for a rough experiment.

## Core Story

The default story is a comedic micro-world around a pet's eye:

1. Germ characters live around the tear-stain area.
2. A cotton pad approaches.
3. The germ boss says wiping the surface is useless.
4. Eye drops appear.
5. The germ boss panics.
6. The droplet washes away the germ base.

Use the 6-shot structure in [references/shot-workflow.md](references/shot-workflow.md) for prompts, timing, dialogue, and pass or redo criteria.

## Version Strategy

Create variants by keeping the same 6-shot structure and changing only the pet identity, germ design, acting style, and color mood:

- `version-01-bichon`: white bichon, cute clean main version.
- `version-02-shiba`: shiba inu, meme-like comedic version.
- `version-03-ragdoll-cat`: ragdoll cat, softer premium cat-owner version.
- `version-04-puppy-drama`: small puppy, animated short-drama version.

Do not change the shot count, shot IDs, or final file names when creating variants. This keeps comparison and assembly reliable.

## Required File Layout

Before asking the user to generate clips in external tools, create or confirm this structure under the project workspace:

```text
outputs/eye-drop-opening/
  version-01-bichon/
    keyframes/
    clips/
    audio/
    exports/
    review.md
  version-02-shiba/
  version-03-ragdoll-cat/
  version-04-puppy-drama/
  prompts/
  shot_manifest.csv
```

Read [references/file-layout.md](references/file-layout.md) before organizing files, checking clip completeness, or concatenating output.

## External Generation Handoff

When the user will use another tool for image-to-video generation:

1. Give them the exact shot prompt from the workflow.
2. Tell them to save the final selected keyframe as `keyframes/shot-XX-keyframe.png`.
3. Tell them to save the final selected video clip as `clips/shot-XX.mp4`.
4. Let them keep drafts as `shot-XX-v1.mp4` or `shot-XX-candidate-a.png`, but final assembly must use the standard file names.
5. Ask them to return only after all 6 standard clips exist for the chosen version, or after one clip if they want a single-shot quality check.

Never rely on generated Chinese text inside the video model output. Add dialogue, captions, voiceover, and subtitles in post-production.

## Checking and Assembly

For a chosen version:

1. Check that `clips/shot-01.mp4` through `clips/shot-06.mp4` exist.
2. Check basic media properties with `ffprobe` or the provided helper script.
3. If clips are missing, report the exact missing paths and stop.
4. If clips are present, normalize or concatenate with ffmpeg.
5. Save rough assembly to `exports/opening-rough.mp4`.
6. If subtitles or audio are provided, save the finished result as `exports/opening-final.mp4`.

Use `scripts/prepare_opening_project.py` to create folders, write a manifest, and check expected files. Use project-local ffmpeg when available; otherwise use an installed ffmpeg only if it is already usable in the environment.

## Compliance Guardrail

Avoid absolute medical claims in subtitles or voiceover. Prefer:

```text
眼屎多、泪痕重，别只擦表面
```

Avoid wording such as:

```text
专治
根治
保证效果
药到病除
```

