# File Layout and Naming Rules

These rules make externally generated clips easy for Codex and other tools to find, inspect, and assemble.

## Root

Use this project-relative root:

```text
outputs/eye-drop-opening/
```

## Version Directories

Use these exact names:

```text
version-01-bichon
version-02-shiba
version-03-ragdoll-cat
version-04-puppy-drama
```

Each version should contain:

```text
keyframes/
clips/
audio/
exports/
review.md
```

## Shot IDs

There are exactly 6 shots:

```text
shot-01  eye micro-world establishing shot
shot-02  cotton pad approaching
shot-03  germ boss dismisses surface wiping
shot-04  eye-drop bottle appears
shot-05  red warning reversal
shot-06  germ base washed away
```

## Keyframe Names

Final selected keyframes must use:

```text
keyframes/shot-01-keyframe.png
keyframes/shot-02-keyframe.png
keyframes/shot-03-keyframe.png
keyframes/shot-04-keyframe.png
keyframes/shot-05-keyframe.png
keyframes/shot-06-keyframe.png
```

Drafts may use:

```text
keyframes/shot-02-candidate-a.png
keyframes/shot-02-candidate-b.png
```

The selected draft must be copied or exported to the standard name before assembly.

## Clip Names

Final selected clips must use:

```text
clips/shot-01.mp4
clips/shot-02.mp4
clips/shot-03.mp4
clips/shot-04.mp4
clips/shot-05.mp4
clips/shot-06.mp4
```

Drafts may use:

```text
clips/shot-04-v1.mp4
clips/shot-04-v2.mp4
```

The selected draft must be copied or exported to the standard name before assembly.

## Optional Audio and Subtitle Files

Use:

```text
audio/voiceover.wav
audio/sfx-warning.wav
audio/sfx-splash.wav
audio/subtitles.srt
```

If the clips already include all needed audio, `audio/` can remain empty.

## Export Names

Use:

```text
exports/opening-rough.mp4
exports/opening-with-subtitles.mp4
exports/opening-final.mp4
```

## Completeness Check

A version is ready for assembly when these 12 files exist:

```text
keyframes/shot-01-keyframe.png
keyframes/shot-02-keyframe.png
keyframes/shot-03-keyframe.png
keyframes/shot-04-keyframe.png
keyframes/shot-05-keyframe.png
keyframes/shot-06-keyframe.png
clips/shot-01.mp4
clips/shot-02.mp4
clips/shot-03.mp4
clips/shot-04.mp4
clips/shot-05.mp4
clips/shot-06.mp4
```

