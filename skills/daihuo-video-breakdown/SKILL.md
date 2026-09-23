---
name: daihuo-video-breakdown
description: 将抖音带货视频下载、抽帧、拆成可复拍分镜，并归档为带图片的飞书五段式文档。用户提供“编号-产品名 + 抖音链接”或本地带货视频并要求拆片、分镜、逐句文案时间轴或飞书归档时使用。
---

# 带货短视频拆解

交付结果是一条视频对应一份可直接复拍的飞书文档。流程为：获取视频 → 抽帧与镜头检测 → 逐帧分析 → 生成固定五段式文档 → 云端回查。

## 本机约定

- MeowLoad 常见位置：`D:\哼哼猫\MeowLoad\bin\meowload.exe`；旧环境可能在 E 盘。执行前用只读检查定位，不假定盘符。
- 抽帧脚本：本技能的 `scripts/extract_frames.py`。
- 联系表脚本：本技能的 `scripts/make_contact_sheets.py`。
- 飞书归档文件夹 token：`C73SfMg7fliZeAd7lW7cYZI5ndd`。
- 抽帧目录与飞书草稿工作区放项目根目录；运行 `lark-cli` 时 CWD 保持项目根目录，使 `@./frames_x/xxx.jpg` 可解析。
- 本机已验证的飞书 CLI 路径：`D:\gpt\douyin_dog_video\work\2026-09-14-breakdown-5\lark-cli\package\bin\lark-cli.exe`。使用前检查文件存在并验证版本；迁移到其他机器时重新定位官方 `@larksuite/cli`，不要假定这个路径存在，也不要依赖旧 WorkBuddy 安装路径。优先使用 `.exe`，避免 `.cmd` 将含 `&user_code=` 的授权 URL 拆参。

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
2. 不再生成“4 段式结构”板块及其配图。
3. 完整分镜：每组为镜头信息 / 台词 / 画面帧 / 拍摄动作；每行左右两组共8列。镜头信息合并镜号、景别、起止时间、时长。
4. 整段文案：按时间顺序合并字幕，去除连续重复句，不改写原意。
5. 逐句文案时间轴：把整段文案拆成自然短句，每句单独一行并标注起止秒数；一句里有两个独立表达时必须拆成两行，例如“给狗狗选尿垫，就选这种带训导因子和防臭的。”拆成“给狗狗选尿垫”和“就选这种带训导因子和防臭的”，分别写对应时间段。

能力边界：无法可靠听取音频时，音效与 BGM 只能按画面节奏推断并标为建议；无内嵌字幕且无法转写音频时，请用户补充台词文本。

## 4. 生成飞书文档

### 固定交付位置与方式（用户确认，2026-09-20）

- 新生成的商品分镜脚本直接在 [分镜脚本文件夹](https://waz4ipzdgdn.feishu.cn/drive/folder/C73SfMg7fliZeAd7lW7cYZI5ndd) 内新建飞书文档，并写入文字、表格与真实画面帧。
- 创建时明确指定 `--parent-token C73SfMg7fliZeAd7lW7cYZI5ndd`；不先生成或上传 Word，也不通过 Word 导入代替直接创建。用户当前另行指定目标时，以当前指令为准。
- 每次执行在项目 `work/YYYY-MM-DD[-任务名]/` 保留来源链接、用户编号、原片路径与 SHA-256、媒体信息、字幕/ASR来源、分镜与参考帧对应关系、XML草稿、创建及回查结果；同步任务说明与检查报告。能力未运行或结果未验证须如实记录，不把飞书创建成功当作本地追溯记录。

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

### 固定五段结构（用户确认，2026-09-17）

开头保留标题和简短视频基本信息（视频时长、镜头/动作单元数）。不展示转录方式、ASR/BGM未运行、采样误差、产品名来源或商品事实未经验证等开头备注；这些来源与能力记录保存在本地任务报告，不伪造已验证状态。

1. 一、视频源链接。
2. 二、开头结构：一句钩子总结，3–4张关键帧及简短备注。
3. 三、完整分镜脚本（含画面帧）：每组“镜头信息 / 台词 / 画面帧 / 拍摄动作”，左右两组共8列，按镜头顺序先左后右。镜头信息合并镜号、景别、起止时间、时长；保留全部台词，动作说明基于画面且具体，如画S型、敲一敲、摸一下、叉腰说话。删除音效列。图片不附冗长图注。台词与动作使用窄列并自动换行，减少无效留白。奇数镜头最后右组留空。
4. 四、逐句文案时间轴：序号 / 时间 / 文案；每个自然短句一行，时间为可解析起止秒数，如0-1.2s。
5. 五、整段文案（可一键复制）：完整文案放最后，使用 `<pre lang="text"><code>…</code></pre>`。

不再生成“4段式结构”板块。推荐表格列宽为90/120/68/122重复两组，竖屏画面展示尺寸48×85；不改变图片原始内容或遗漏镜头。具体XML见模板。

剪映交接按章节标题定位“逐句文案时间轴”，不要依赖旧第六段编号；保留时间和文案列。双组分镜只作回退来源，按每行左组、右组顺序读取镜头信息中的时间及对应台词。旧七列表格仍可按表头识别。保留顶部 `视频时长 | XX.XX 秒` 便于下游读取。

## 5. 云端回查与交付

创建后必须回查：

```powershell
lark-cli docs +fetch --doc '<document_id或URL>' --detail with-ids --doc-format xml --as user
```

完成条件：

- 云端 `<img>` 数量与草稿预期完全相等，而不只是大于 0。
- 云端 `<h2>` 数量为 5，文档名称与用户编号一致，源链接正确。
- 核对文档确在指定文件夹：以可用的文件夹列表、父级元数据或文件夹页面为证据；仅传入 `--parent-token` 不等于已完成所在位置核验。记录所用证据；暂不可读取时明确标记位置核验待完成。
- 逐表核对镜头信息、台词、拍摄动作及逐句时间轴与草稿一致；图片数量完全一致，并抽查画面帧正常显示。
- 本地任务说明、来源与分镜对应关系、检查报告已保存；报告区分创建成功、内容核验及位置核验。
- 创建结果无未处理 warning。
- 一条输入视频只创建一份最终文档。

最终回复提供文档链接、钩子类型、结构摘要和核心镜头提示。只有云端回查全部通过后才可清理桌面下载视频；删除失败时保留文件并报告准确路径。草稿工作区是否保留遵循当前 `lark-doc` 工作流，不擅自删除用户素材。

## 失败停止条件

- 网络或令牌刷新失败时可在确认是瞬时故障后重试；不要在结果未知时重复执行创建命令。
- 先用回查或文件夹列表确认是否已创建，再决定重试，避免产生重复文档。
- 需要系统网络修改、重新授权或删除云端文档时，先向用户说明影响并取得授权。
