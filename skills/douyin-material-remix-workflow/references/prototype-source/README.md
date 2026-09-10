# 单次项目原型源码存档

这些脚本保留原任务相对布局。复制 work/2026-09-08 到用户自己的项目根下，并按任务数据改造后使用；不要从本 skill 目录直接运行。需自行准备 assets/catalog、原视频、recipe、matches、配音及草稿模板，Git未包含媒体或完整任务数据。它不是可独立复现成片的备份包。

流程入口：analyze_reference.py → batch_ingest.py / batch_publish.py → match_reference.py / prepare_match_preview.py → doubao-sample-01/generate_doubao.py → render_xionger_sample.py → check_xionger_sample.py → make_xionger_draft.py。顺序仅表示阶段关系，不能作为无人值守批处理命令。

旧 pilot、VoxCPM、rate50 和 action sample 文件作为历史实现保留，不是当前默认。render 和 check 文件包含硬编码路径、帧数及审计措辞，跨商品必须改造。make_xionger_draft.py依赖旧草稿模板，未附带模板媒体，需提供合法可用模板或替换生成器。

Windows渲染使用OpenCV CAP_MSMF与Windows MediaComposition；mux_review.ps1须使用Windows PowerShell 5.1，不能假定PowerShell 7支持WinRT。另需Python、opencv-python、numpy、pillow；豆包音频脚本需soundfile。VoxCPM脚本仅作历史存档，额外依赖不属于当前豆包路径。

运行熊二配音.ps1提供本机密码弹窗；环境目录名.venv-voxcpm是历史名字，用户应改为自己的Python路径。API密钥不落盘。离线或沙箱禁网时明确报告不可调用，不能将联网未执行标为TTS成功。
