---
name: daihuo-video-breakdown
description: 将抖音带货视频下载、抽帧、拆成可复拍分镜，并归档为带图片的飞书五段式文档。用户提供“编号-产品名 + 抖音链接”或本地带货视频并要求拆片、分镜或飞书归档时使用。
---

# 带货短视频拆解

交付结果是一条视频对应一份可直接复拍的飞书文档。流程为：获取视频 → 抽帧与镜头检测 → 逐帧分析 → 生成固定五段式文档 → 云端回查。

## 本机约定

- MeowLoad 常见位置：`D:\哼哼猫\MeowLoad\bin\meowload.exe`；旧环境可能在 E 盘。执行前用只读检查定位，不假定盘符。
- 抽帧脚本：本技能的 `scripts/extract_frames.py`。
- 联系表脚本：本技能的 `scripts/make_contact_sheets.py`。
- 飞书归档文件夹 token：`C73SfMg7fliZeAd7lW7cYZI5ndd`。
- 抽帧目录与飞书草稿工作区放项目根目录；运行 `lark-cli` 时 CWD 保持项目根目录，使 `@./frames_x/xxx.jpg` 可解析。
- 已验证的飞书 CLI 固定路径：`C:\Users\Administrator\.workbuddy\binaries\node\cli-connector-packages\node_modules\@larksuite\cli\bin\lark-cli.exe`。优先用这个 exe；不要只依赖 PATH。`C:\Users\Administrator\.workbuddy\binaries\node\cli-connector-packages\lark-cli.cmd` 只是备用包装器，传入含 `&user_code=` 的授权 URL 时会被 Windows shell 拆参，避免用于设备码二维码等 URL 场景。

不要依赖已移除的 WorkBuddy Python。先定位可用 Python 并验证 `import cv2, numpy`。若仅缺 Python，可在项目内使用便携环境；若缺包，安装与 Python ABI 匹配的 OpenCV/Numpy。

## 1. 获取视频

用 MeowLoad CLI 下载抖音视频到用户桌面临时目录：

```powershell
& '<meowload.exe>' version
& '<meowload.exe>' info '<抖音链接>'
& '<meowload.exe>' download '<抖音链接>' --media_type video --output-dir '<桌面路径>'
```

下载后复制为规范名 `<编号-产品名>-<序号两位>.mp4` 到项目目录。序号按用户输入中的 01、02 等编号；不得把产品编号或日期误当序号。

- 下载前必须先用 `version` 或 `info` 验证 CLI 已连上 MeowLoad 桌面端。如果报 `Failed to connect to the MeowLoad desktop app`，根因是 GUI 未就绪/未连接，不是链接失效；先启动或重启 MeowLoad GUI，等待 15-20 秒后重试。
- 文件仍被占用时使用复制，不因删除原文件失败而阻塞后续步骤。
- GUI 卡在“正在启动”不代表 CLI 失败；所有下载结束后关闭 MeowLoad 进程。
- 用户提供本地视频时跳过下载，不修改原件。

## 2. 抽帧与联系表

```powershell
& '<python.exe>' '<skill>/scripts/extract_frames.py' '<video.mp4>' '<project>/frames_<唯一标识>' 0.4
& '<python.exe>' '<skill>/scripts/make_contact_sheets.py' '<project>/frames_<唯一标识>' '<project>/sheets_<唯一标识>' 8
```

- 抽帧间隔固定为 0.4 秒；镜头检测使用 HSV 直方图 Bhattacharyya 距离阈值 0.55。
- 输出帧名包含时间和算法镜号；`shot_list.json` 记录时长、FPS 与镜头边界。
- Windows 中文路径必须使用 `cv2.imencode(...).tofile(...)` 或二进制写入，不改回 `cv2.imwrite`。
- 先分批查看联系表，再按需打开原始帧读取小字幕或动作细节。算法镜头数只是参考；视觉动作变化可继续细分为 1a、1b。

## 3. 逐帧分析

从全部画面提取：

1. 开头结构：只写一句钩子类型总结，并选 3–4 张关键帧配简短画面备注。
2. 4 段式结构：通常为“钩子展示 → 卖点揭秘 → 功能背书 → 转化收尾”，每段只放 1 张关键帧和画面备注。
3. 完整分镜：字段固定为镜号 / 时间 / 时长 / 景别 / 台词 / 画面帧 / 音效。
4. 整段文案：按时间顺序合并字幕，去除连续重复句，不改写原意。

能力边界：无法可靠听取音频时，音效与 BGM 只能按画面节奏推断并标为建议；无内嵌字幕且无法转写音频时，请用户补充台词文本。

## 4. 生成飞书文档

### 安装与认证

优先使用飞书官方 `@larksuite/cli`：

```powershell
npx @larksuite/cli@latest install
lark-cli config init --new
lark-cli auth login --recommend
lark-cli auth status
```

如果系统没有 npm，可从 npm 官方注册表获取 `@larksuite/cli` 包，并运行包内官方安装脚本；必须校验包内 SHA-256。不得安装名称相似、来源不明的 `lark-cli` 包。登录需要用户浏览器授权时，提供 CLI 返回的验证链接并等待用户完成。

若 `open.feishu.cn` DNS 解析失败，先用公共 DNS 对比确认。优先让用户修复网络、DNS 或 VPN；不得擅自永久修改 hosts。采用临时代理或临时 hosts 时必须说明范围、获得授权，并在归档完成后撤销。

每次创建飞书文档前先检查身份状态，不要默认要求用户重新扫码：

```powershell
& '<lark-cli.exe>' doctor
& '<lark-cli.exe>' whoami
```

- 优先用 `--as user` 创建到 `C73SfMg7fliZeAd7lW7cYZI5ndd` 文件夹；该文件夹下 Bot 身份可能报 `3380004 Permission denied`，遇到这个错误直接切 User，不要要求用户改文件夹权限。
- 只有 `doctor` 明确显示 `User identity: missing` 或 `refresh token expired`，且 `--as user` 创建失败时，才发起 `auth login --domain docs,drive --no-wait --json` 让用户授权。
- 设备码登录成功后，本机 token 应复用；不要每条视频都让用户扫码。用户确认授权后，继续执行同一次返回的 `auth login --device-code <device_code>`，不要重新发起新设备码。
- 生成二维码或处理带 `&user_code=` 的验证链接时使用 `lark-cli.exe`，不要用 `.cmd` 包装器，避免 URL 被 shell 拆开。

### 草稿与上传

执行前读取当前 CLI 自带的 `lark-doc` 创建工作流和 XML 参考；以当前版本规则为准。模板见 [references/feishu-doc-template.md](references/feishu-doc-template.md)。

```powershell
& '<lark-cli.exe>' docs +script --command init-draft --presentation-decision '<JSON>' --format json --as user
# 把完整 XML 写入返回的 draft_path
& '<lark-cli.exe>' docs +script --command parse --content '@./<draft_path>' --format json --as user
& '<lark-cli.exe>' docs +create --doc-format xml --content '@./<draft_path>' --parent-token C73SfMg7fliZeAd7lW7cYZI5ndd --format json --as user
```

必须满足：

- `parse` 顶层 `ok=true` 不够；还要确认 `data.assessment.status=passed`。
- 本地图片只用 `<img path="@./frames_x/xxx.jpg"/>`。`src` 仅用于已上传的飞书资源 token。
- XML 开头直接写唯一 `<title>`；不要 XML 声明和 `<doc>` 根标签。
- 创建后检查 `warnings`。若存在局部资源失败，按当前 `lark-doc` 更新流程修复已创建文档，不重复新建。

### 固定五段结构

顺序和字段不可改变：

1. 一、视频源链接
2. 二、整段文案（可一键复制）：使用 `<pre lang="text"><code>…</code></pre>`
3. 三、4 段式结构：仅 4 张关键帧及备注
4. 四、开头结构：仅一句钩子总结、3–4 张关键帧及备注
5. 五、完整分镜脚本（含画面帧）：表格列固定为镜号 / 时间 / 时长 / 景别 / 台词 / 画面帧 / 音效

不要增加画面描述、动作、拍多久、拍摄建议等表格列。表格内每个镜头通常只放一张代表帧，并保持图片小尺寸。

## 5. 云端回查与交付

创建后必须回查：

```powershell
lark-cli docs +fetch --doc '<document_id或URL>' --detail with-ids --doc-format xml --as user
```

完成条件：

- 云端 `<img>` 数量与草稿预期完全相等，而不只是大于 0。
- 云端 `<h2>` 数量为 5，标题和源链接正确。
- 创建结果无未处理 warning。
- 一条输入视频只创建一份最终文档。

最终回复提供文档链接、钩子类型、结构摘要和核心镜头提示。只有云端回查全部通过后才可清理桌面下载视频；删除失败时保留文件并报告准确路径。草稿工作区是否保留遵循当前 `lark-doc` 工作流，不擅自删除用户素材。

## 失败停止条件

- 网络或令牌刷新失败时可在确认是瞬时故障后重试；不要在结果未知时重复执行创建命令。
- 先用回查或文件夹列表确认是否已创建，再决定重试，避免产生重复文档。
- 需要系统网络修改、重新授权或删除云端文档时，先向用户说明影响并取得授权。


## 2026-09-13 剪映下游固定交接补充

后续与 `jianying-voice-draft` 对接时，飞书文档格式固定为当前五段式结构，尤其是第五段“完整分镜脚本（含画面帧）”。该表格列顺序固定为：镜号 / 时间 / 时长 / 景别 / 台词 / 画面帧 / 音效。

下游会优先读取第五段完整分镜脚本里的 `时间` 和 `台词`，并在没有单独 `视频时长 | XX.XX 秒` 字段时，用最后一条时间段结束点作为总时长。
