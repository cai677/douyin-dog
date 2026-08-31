---
name: daihuo-video-breakdown
description: 带货短视频拆解（抖音爆款视频 → 分镜脚本 → 飞书归档）。当用户提供「编号-产品名 + 抖音视频链接」要求下载并拆片，或提供本地带货视频文件要求拆解分镜脚本时使用此技能。覆盖：哼哼猫 MeowLoad CLI 下载、OpenCV 抽帧+镜头切分、逐帧画面分析（开头3秒钩子/4段式结构/完整分镜脚本）、飞书云文档自动归档（五段式结构，含可复制整段文案和视频源链接）。
agent_created: true
---

# 带货短视频拆解

把一条抖音带货爆款视频自动拆解成「可照着拍摄」的分镜脚本，并归档到飞书。端到端流程：下载 → 抽帧 → 分析 → 生成飞书文档 → 改名归档。

## 触发条件

- 用户提供「编号-产品名 + 抖音视频链接」，如 `24-俘获磨牙圈 https://www.douyin.com/video/xxxx`
- 用户提供本地视频文件，要求拆片/拆解/出分镜脚本

## 固定环境（本机已验证）

| 项 | 值 |
|---|---|
| 下载软件 GUI | `E:\哼哼猫\MeowLoad\MeowLoad.exe` |
| 下载软件 CLI | `E:\哼哼猫\MeowLoad\bin\meowload.exe` |
| Python（含 opencv/Pillow/numpy） | `C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe` |
| 抽帧脚本 | 本技能 `scripts/extract_frames.py` |
| 视频存放目录 | `G:\抖音带货\<编号-产品名>\`（同产品统一放同一文件夹） |
| 飞书归档文件夹 token | `C73SfMg7fliZeAd7lW7cYZI5ndd` |
| 工作目录约定 | 抽帧输出和 XML 草稿放当前项目根目录（CWD 必须是项目根目录，飞书 img 引用用相对路径 `@./frames_x/xxx.jpg`） |

## 流程（按序执行）

### 第 1 步：下载视频

   **注意（2026-08-22 踩坑）**：GUI 窗口会一直卡在「正在启动」猫咪画面，属正常现象（CLI 功能不受影响），用户无法手动关闭。**全部下载完成后必须 taskkill 清理 GUI 进程**：
   ```bash
   tasklist | grep -i "MeowLoad" | awk '{print $2}' | while read pid; do taskkill /PID $pid /F 2>/dev/null; done
   ```
2. 下载：
   ```bash
   cd /e/哼哼猫/MeowLoad/bin && ./meowload.exe download "<抖音链接>" --media_type video --output-dir "G:\抖音带货\<编号-产品名>"
   ```
3. 下载的文件名是视频标题（很长），重命名为 `<编号-产品名>-<当日序号两位>.mp4`（如 `24-俘获磨牙圈-01.mp4`）。序号 = 该产品当日第几条。
   **注意（2026-08-22 踩坑）**：下载刚结束时文件可能仍被下载进程占用，`mv`/直接改名会报 "being used by another process" → 改用 `cp 原文件 新名 && rm -f 原文件`；若 `rm` 仍被占用，不要阻塞流程，规范名文件已可用，向用户说明残留原文件稍后手动删即可。

### 第 2 步：抽帧 + 镜头切分

```bash
"<python路径>" "<本技能scripts路径>/extract_frames.py" "<视频路径>" "<项目根>/frames_<编号>" 0.4
```

- 抽帧间隔 0.4 秒；脚本基于 HSV 直方图 Bhattacharyya 距离 > 0.55 检测切镜
- 输出：帧图片（`t000.00s_shot01.jpg` 命名）+ `shot_list.json`
- 此脚本已处理 Windows 中文路径坑（cv2.imencode + bytes 写入），勿改回 cv2.imwrite

### 第 3 步：逐帧分析

用 Read 工具分批读取全部帧图片（每批 5-8 张），从画面中提取：

1. **开头结构**：判断钩子类型（悬念问句 / 卖点快闪 / 痛点 / 效果展示 / 对比），只输出一句话总结，并选 3-4 张关键帧配画面备注
2. **4 段式结构**：带货视频通常是「钩子展示 → 卖点揭秘 → 功能背书 → 转化收尾」，只输出 4 张关键帧和对应画面备注
3. **完整分镜脚本**：算法检测的镜头数通常少于实际（前几秒快切会合并），要靠看帧细分出子镜头。每镜只记录并输出：镜号(1a/1b…) / 时间 / 时长 / 景别(远景/中景/近景/特写/手持) / 台词字幕（从帧里OCR读） / 画面帧 / 音效建议
4. **整段文案**：按时间顺序汇总全部台词字幕，去重连续重复句

**能力边界（提前告知用户）**：听不到音频（音效/BGM 只能按画面节奏推断）；无内嵌字幕的视频读不到台词（需用户补台词文本）。

### 第 4 步：生成飞书文档（不产 HTML 中间文件）

使用 lark-doc skill 工作流，CWD 必须是项目根目录：

```bash
lark-cli docs +script --command init-draft --presentation-decision '<JSON>' --format json --as user
# 写 draft.xml 到生成的 work_dir（本地图片用 path="@./frames_x/xxx.jpg"，绝不能用 src）
lark-cli docs +script --command parse --content "@./<work_dir>/draft.xml" --format json --as user
lark-cli docs +create --doc-format xml --content "@./<work_dir>/draft.xml" --parent-token C73SfMg7fliZeAd7lW7cYZI5ndd --format json --as user
```

XML 结构模板见 [references/feishu-doc-template.md](references/feishu-doc-template.md)。

**图片上传语法（关键，2026-08-22 踩坑修正）**：
- 本地帧图片必须写 `<img path="@./frames_x/xxx.jpg" />`——**`path` 属性才是上传本地文件**
- `<img src="...">` 的 src 只接受**已上传图片的飞书 token**；误写本地路径时 create 不会报错（ok=true），只返回 `degrade_code=2119 Invalid resource token` 警告，然后**静默丢掉全部图片**（24-俘获磨牙圈首版丢图 47 张就是这个原因）
- **create 后必须回查校验**：`lark-cli docs +fetch --doc "<url>" --format json --as user` 数一下 `<img` 出现次数是否等于预期帧数，等于 0 就是要重建
- XML 不要写 `<?xml?>` 声明和 `<doc>` 根标签（会变成正文纯文本）；开头写 `<title>编号-产品名-序号-日期</title>`，create 直接用作文档名，可省掉第 5 步的改名

**文档固定五段结构**（用户 2026-08-31 调整，勿增删、勿改顺序）：

1. 一、视频源链接 —— 存档用户发的抖音原始链接
2. 二、整段文案（可一键复制）—— 放代码块 `<pre lang="text"><code>…</code></pre>`，用户一键复制进剪映用
3. 三、4 段式结构 —— 只保留 4 个关键帧画面和对应画面备注；不要写每段详细拆解、起止时间解释或额外分析
4. 四、开头结构 —— 只保留钩子类型一句话总结、关键帧画面和对应画面备注；不要写 0-1s/1-2s/2-3s 等详细拆解
5. 五、完整分镜脚本（含画面帧）—— 表格字段且顺序固定为：镜号 / 时间 / 时长 / 景别 / 台词 / 画面帧 / 音效；不要加入画面描述、动作/演示、拍多久/拍摄建议等列；分镜表内图片要小（用户要求，勿放大）

### 第 5 步：改名归档 + 清理

```bash
lark-cli drive +update-title --url "<doc url>" --title "<编号-产品名>-<序号>-<YYYY-MM-DD>" --as user
```

- 命名规范：`编号-产品名称-序号-当日日期`，如 `24-俘获磨牙圈-01-2026-08-22`。**编号 = 用户自定的产品编号（不是日期）**
- 删除临时 work_dir 目录
- 最后把飞书文档链接用 present_files 展示给用户，并在回复里给出：钩子类型、结构摘要、核心镜头提示

## 已知坑（踩过，勿重复）

1. **cv2.imwrite 不支持 Windows 中文路径** → 用 imencode + bytes（脚本已处理）
2. **MeowLoad CLI 报 "Failed to connect to the MeowLoad desktop app"** → 先 nohup 启动 GUI 等 15 秒
3. **飞书 init-draft 必须在项目根目录跑**，否则 img 相对路径解析失败
4. **rm 删临时目录可能被回收站工具拦截** → 换 `rm -f` 前缀路径写法重试即可
5. **suggest_plugin_install 连接卡片可能超时** → 指引用户手动去连接器管理页连接
6. **飞书 XML 本地图片属性是 `path` 不是 `src`**（src 只接受已上传图片 token）→ 写错时 create 静默丢全部图片，只在 warnings 里返回 `degrade_code=2119`；create 后必须 fetch 回查 img 数量
7. **create 的 warnings 必须看**：ok=true 不代表内容完整（丢图、缺标题都只出现在 warnings 里）
8. **删飞书文档**：`lark-cli drive +delete --file-token <token> --type docx --yes --as user`（重建文档后删旧版用）
9. **MeowLoad GUI 卡「正在启动」画面** → 正常现象，CLI 不受影响；用户无法手动关闭，下载全部完成后用 taskkill /F 强杀 GUI 进程（命令见第 1 步）
10. **下载后立即 mv 改名报文件被占用** → 下载进程短暂占用文件，改用 `cp + rm -f`；rm 仍失败则不阻塞，规范名已可用，残留原文件告知用户稍后手动删
