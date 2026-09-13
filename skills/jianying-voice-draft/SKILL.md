---
name: jianying-voice-draft
description: 根据飞书爆款视频拆解文档生成剪映可打开的朗读音频轨和字幕轨草稿；适用于用户要求按拆解文案生成豆包 TTS、逐句独立音频、统一倍速、句首气口裁剪、字幕轨对齐的工作流。
---

# 剪映朗读音频字幕轨

用于把飞书爆款视频拆解文档转换成剪映草稿。草稿只包含朗读音频轨和字幕轨，不处理画面素材。

## 适用场景

使用本 skill 当用户要求：

- 根据飞书拆解文档生成剪映草稿；
- 只生成朗读音频轨和字幕轨；
- 使用豆包/火山语音 TTS；
- 一句文案对应一个独立朗读音频片段；
- 所有句子的朗读倍速一致；
- 去掉每句开头多余气口。

如果用户要求拆解视频、抽帧、生成带图片分镜文档，应使用带货视频拆解 skill，而不是本 skill。

## 已验证约束

- 飞书文档必须包含视频总时长和“文案+画面对照表”。
- 连续重复文案只朗读一次；非连续重复保留。
- 如果表格最后一行早于视频总时长，则最后一句延长到视频总时长。
- 每句文案单独生成 WAV，不合并为一条总音频。
- 每个 WAV 重写标准 WAV 头，避免剪映解析异常。
- 每句只裁剪句首静音，保留约 60ms 缓冲；不裁剪句尾。
- 所有音频片段使用同一个统一倍速。
- 字幕按飞书表格时间轴排列。
- 字幕字体名写入“抖音体”，字号写入 9。

## 本机依赖

优先使用当前项目或本机已验证的 Python：

```powershell
C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe
```

脚本需要：

- `pyJianYingDraft`
- `pymediainfo`
- 飞书 CLI：`C:\Users\Administrator\.workbuddy\binaries\node\cli-connector-packages\node_modules\@larksuite\cli\bin\lark-cli.exe`

豆包 API Key 不写入文件，通过环境变量或命令参数传入。

## 运行脚本

脚本在本 skill 的 `scripts/voice_draft.py`。

```powershell
$env:DOUBAO_TTS_API_KEY='你的 API Key'

& 'C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe' `
  '<skill-folder>\scripts\voice_draft.py' `
  --doc-url '<飞书文档链接>' `
  --voice-id 'zh_male_xionger_mars_bigtts' `
  --draft-name '<剪映草稿名>'
```

当前已验证语音参数：

```text
resource_id: volc.service_type.10029
voice_id: zh_male_xionger_mars_bigtts
```

## 输出

剪映草稿写入：

```text
C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<draft-name>
```

中间音频写入 skill 目录下：

```text
outputs\*\lines
outputs\*\lines_trimmed
```

## 验收标准

生成后检查：

1. 剪映草稿能打开。
2. 音频轨是多段独立 WAV，不是合并 MP3 或合并 WAV。
3. 音频片段数等于字幕片段数。
4. 所有音频片段的 speed 完全一致。
5. 草稿总时长等于飞书文档视频总时长。
6. 连续重复文案没有重复朗读。
7. 每句起声没有明显句首空白。
8. 字幕显示为抖音体、9 号；若本机缺字体，剪映可能回退，需要人工确认。

## 参考文档

完整工作流、踩坑记录和复用说明见 [references/workflow.md](references/workflow.md)。当用户要求复用、维护或解释该剪辑工作流时，先读取该参考文档。
