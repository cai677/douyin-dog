# 飞书分镜脚本文档 XML 模板

draft.xml 的整体结构。使用前先跑 `docs +script --command init-draft`，把本文内容写进生成的 work_dir 里的 draft.xml，图片用相对路径 `@./frames_<编号>/xxx.jpg`（CWD 必须是项目根目录）。

## 骨架

> **⚠️ 图片属性必须是 `path`，不是 `src`**（2026-08-22 实测踩坑：`src` 会被当成飞书资源 token 解析，create 返回 `degrade_code=2119 Invalid resource token` 警告并**静默丢掉全部图片**，文档只有文字）。`path="@./..."` 上传本地图；`href="URL"` 上传网络图；`src="token"` 仅用于复制已上传图片。
> XML 里**不要写** `<?xml ...?>` 声明和 `<doc>` 根标签（会被转义成正文纯文本）。开头直接写 `<title>` 即可，create 时可省掉改名步骤。

```xml
<title>编号-产品名-序号-YYYY-MM-DD</title>
<h1>「编号-产品名」分镜脚本</h1>
<p>视频时长 XX.Xs · 分辨率 · fps · 主镜头 N 个（实测子镜头 M 个） · 品牌与产品信息</p>

<h2>一、视频源链接</h2>
<p>源视频（抖音）：https://www.douyin.com/video/xxxxx （编号 XX-产品名，YYYY-MM-DD 下载归档）</p>

<h2>二、整段文案（可一键复制）</h2>
<pre lang="text" caption="「编号-产品名」整段文案"><code>第一句台词
第二句台词
…（按时间顺序去重汇总）</code></pre>

<h2>三、4 段式结构</h2>
<grid>
  <column width-ratio="0.25"><img path="@./frames_x/xx.jpg" caption="① 画面备注" /></column>
  <column width-ratio="0.25"><img path="@./frames_x/xx.jpg" caption="② 画面备注" /></column>
  <column width-ratio="0.25"><img path="@./frames_x/xx.jpg" caption="③ 画面备注" /></column>
  <column width-ratio="0.25"><img path="@./frames_x/xx.jpg" caption="④ 画面备注" /></column>
</grid>

<h2>四、开头结构</h2>
<p>钩子类型：XXX（一句话总结）</p>
<grid>
  <column width-ratio="0.333"><img path="@./frames_x/t000.00s_shot01.jpg" caption="画面备注" /></column>
  <column width-ratio="0.333"><img path="@./frames_x/t001.60s_shot01.jpg" caption="画面备注" /></column>
  <column width-ratio="0.334"><img path="@./frames_x/t002.40s_shot01.jpg" caption="画面备注" /></column>
</grid>

<h2>五、完整分镜脚本（含画面帧）</h2>
<table>
  <thead>
    <tr><th><p>镜号</p></th><th><p>时间</p></th><th><p>时长</p></th><th><p>景别</p></th><th><p>台词</p></th><th><p>画面帧</p></th><th><p>音效</p></th></tr>
  </thead>
  <tbody>
    <tr>
      <td><p>1a</p></td><td><p>0–1.2s</p></td><td><p>1.2s</p></td><td><p>中景</p></td>
      <td><p>台词</p></td><td><img path="@./frames_x/t000.00s_shot01.jpg" width="120" /></td><td><p>音效建议</p></td>
    </tr>
    <!-- 每个子镜头一行 -->
  </tbody>
</table>
```

## 注意事项

- **图片属性用 `path="@./..."`（本地路径上传）**。`src` 只接受已上传图片的 token，写本地路径会静默丢图（create 仅返回 `degrade_code=2119` 警告，ok 仍为 true）——2026-08-22 24-俘获磨牙圈首版全丢图就是这个原因，务必检查 create 输出的 warnings
- **create 后必须校验**：`docs +fetch --detail with-ids --doc-format xml` 回查 `<img>` 数量是否与草稿预期完全相等，同时确认 `<h2>` 为 5 个
- XML 不要带 `<?xml?>` 声明和 `<doc>` 根标签，开头直接 `<title>`（create 会用它作文档名，可省 rename 步骤）
- 表格单元格内文本必须包 `<p>`，图片直接 `<img path=...>`（实测 td 内放图没问题）
- 代码块必须 `<pre><code>` 嵌套，不能裸放 `<pre>`
- 每镜 1 张代表帧即可；核心镜头可放 2 张（如掰开动作的前后帧）
- 文档顺序固定为：视频源链接、整段文案、4 段式结构、开头结构、完整分镜脚本
- 4 段式结构只放 4 个关键帧和对应画面备注，不写详细拆解
- 开头结构只放钩子类型一句话总结、关键帧和对应画面备注，不写分秒详细拆解
- 完整分镜脚本表格列固定为：镜号、时间、时长、景别、台词、画面帧、音效；不要添加画面描述、动作、拍摄建议或拍多久
- parse 只做语法校验不上传图片；上传发生在 create 阶段
- `parse` 通过标准为 `data.assessment.status=passed`，不是只看顶层 `ok=true`
- create 成功后检查 `warnings`；存在局部资源失败时更新已创建文档，不要直接再建一份
- 草稿 work_dir 是否保留遵循当前 `lark-doc` 工作流

