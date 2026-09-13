# 剪映朗读音频字幕轨工作流

本文档记录当前已验证可复用的工作流：根据飞书爆款视频拆解文档，生成一个可在剪映打开的草稿。草稿只包含朗读音频轨和字幕轨，不处理画面素材。

## 目标产物

- 剪映可打开草稿
- 一句文案对应一个独立朗读音频片段
- 一句文案对应一个字幕片段
- 字幕按爆款拆解文档时间轴排列
- 所有朗读音频片段使用同一个统一倍速
- 每句朗读音频已裁掉句首多余气口

## 当前已验证版本

最新可用基准草稿：

```text
22-乐事宠尿垫-03-逐句音频统一倍速-句首裁剪版-20260913
```

草稿目录：

```text
C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft
```

当前脚本：

```text
tools\voice_draft.py
```

测试文件：

```text
tests\test_voice_draft.py
```

## 输入要求

### 1. 飞书拆解文档

文档里必须包含：

- 视频总时长，例如 `视频时长 | 24.40 秒`
- `文案+画面对照表`
- 表格字段至少包含：
  - 镜号
  - 时间
  - 口播文案/字幕

脚本会读取表格里的每一行时间和文案。

### 2. 豆包/火山语音参数

当前已验证参数：

```text
resource_id: volc.service_type.10029
voice_id: zh_male_xionger_mars_bigtts
```

API Key 通过环境变量传入，不写进代码：

```powershell
$env:DOUBAO_TTS_API_KEY='你的 API Key'
```

## 核心规则

### 文案处理

1. 从飞书表格逐行提取文案。
2. 连续重复文案只保留一次朗读。
   - 例如 `0-1s` 和 `1-2s` 都是同一句，则合并成一个 `0-2s` 字幕/朗读片段。
   - 非连续重复不合并。
3. 如果文档视频总时长大于最后一行表格结束时间，则最后一句自然延长到视频总时长。
   - 例如表格最后一行是 `23-24s`，视频总时长是 `24.40s`，则最后一句延长到 `23-24.40s`。

### 音频处理

1. 每句文案单独调用豆包 TTS。
2. 每句输出一个独立 WAV。
3. 每个 WAV 先重写成标准 WAV 头，避免剪映解析异常。
4. 每句只裁剪句首静音。
5. 句首裁剪保留约 `60ms` 缓冲，避免削掉第一个字。
6. 不裁剪句尾。
7. 不把多句音频合并成一条总音频。
8. 所有音频片段使用同一个统一倍速。

### 字幕处理

1. 字幕片段与处理后的文案行一一对应。
2. 字幕按文档时间轴排列。
3. 字幕字体名写入 `抖音体`。
4. 字号写入 `9`。
5. 如果本机没有抖音体字体，剪映可能回退到默认字体，需要在剪映里手动确认。

## 为什么不用整段合并音频

之前试过两种方案，均不作为复用方案：

### 方案 A：多段 MP3 直接拼接成一条 MP3

问题：

- 剪映会对多段 MP3 头信息解析不稳定。
- 表现为音频提前结束，后面出现空波形或空片段。

结论：不要使用。

### 方案 B：逐句 WAV 拼接成一条总 WAV

问题：

- 虽然 WAV 更稳定，但整条音频不方便逐句微调。
- 用户明确要求一句文案对应一句单独朗读音频。

结论：不作为最终方案。

## 当前最终方案

```text
飞书表格文案
  -> 连续重复文案合并
  -> 最后一句延长到视频总时长
  -> 每句单独 TTS 生成 WAV
  -> 标准化 WAV 头
  -> 裁剪句首气口
  -> 计算所有句子的统一倍速
  -> 在剪映草稿里生成：
       音频轨：每句一个 WAV 片段，统一 speed
       字幕轨：每句一个字幕片段，按文档时间轴
```

## 运行命令

在项目根目录执行：

```powershell
$env:DOUBAO_TTS_API_KEY='你的 API Key'

& 'C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe' `
  tools\voice_draft.py `
  --doc-url '飞书文档链接' `
  --voice-id 'zh_male_xionger_mars_bigtts' `
  --draft-name '剪映草稿名'
```

示例：

```powershell
$env:DOUBAO_TTS_API_KEY='你的 API Key'

& 'C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe' `
  tools\voice_draft.py `
  --doc-url 'https://waz4ipzdgdn.feishu.cn/docx/YjqYdjIS1oW2eExCMFpct0HYnzc' `
  --voice-id 'zh_male_xionger_mars_bigtts' `
  --draft-name '22-乐事宠尿垫-03-逐句音频统一倍速-句首裁剪版-20260913'
```

## 输出位置

### 剪映草稿

```text
C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\<draft-name>
```

### 逐句原始 WAV

```text
outputs\22-leshi-voice-draft\lines
```

### 裁剪后 WAV

```text
outputs\22-leshi-voice-draft\lines_trimmed
```

### manifest

```text
outputs\22-leshi-voice-draft\voice_manifest.json
```

manifest 会记录：

- 草稿路径
- 每句音频文件路径
- 目标总时长
- 每句原始音频时长
- 每句音频倍速
- 合并前文案行数
- 合并后文案行数

## 验收标准

生成后需要检查：

1. 剪映草稿能打开。
2. 音频轨不是一条合并音频，而是多段独立 WAV。
3. 字幕轨数量等于音频片段数量。
4. 所有音频片段倍速一致。
5. 总时长等于飞书文档里的视频总时长。
6. 连续重复文案没有重复朗读。
7. 每句起声没有明显句首空白。
8. 字幕字体和字号符合要求：抖音体、9号。

## 当前脚本核验命令

运行单元测试：

```powershell
& 'C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe' `
  -m unittest tests.test_voice_draft
```

当前覆盖的关键规则：

- 从飞书内容提取文案表格
- 连续重复文案合并
- 最后一行延长到视频总时长
- 一句文案一个音频段
- 统一倍速
- 句首静音裁剪

## 常见问题

### 1. 为什么剪映里音频比字幕提前结束？

通常是因为使用了旧版合并 MP3 草稿。检查音频轨文件名：

- 错误旧版：`doubao_voice_lines_combined.mp3`
- 正确新版：多个独立 `01.wav`、`02.wav`、`03.wav`

### 2. 为什么某句没有完全贴合字幕格子？

当前规则要求所有句子统一倍速，因此音频是按统一语速顺序排布的。字幕仍按爆款文档时间轴。这样整体听感更流畅，但个别句子的起止点可能和字幕格子不是完全逐帧贴合。

### 3. 为什么要合并连续重复文案？

拆解表格常常按每秒截图记录，同一句字幕可能跨多个画面帧。如果不合并，就会出现同一句朗读两次。

### 4. 为什么不插静音？

用户明确要求不使用静音间隙凑时长。当前方案只做句首静音裁剪，不插入静音。

## 后续新脚本复用步骤

1. 确认飞书文档包含视频总时长和文案表格。
2. 准备豆包 API Key 和音色 ID。
3. 用唯一草稿名运行 `tools\voice_draft.py`。
4. 打开剪映检查草稿。
5. 如果确认可用，把该草稿名记录为新项目基准版本。
