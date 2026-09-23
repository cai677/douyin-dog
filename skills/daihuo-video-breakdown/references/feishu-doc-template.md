# 飞书分镜脚本文档 XML 模板

用户确认的五段式，2026-09-17。新文档按此生成；旧文档仅在用户指定时调整。
交付位置、直接新建方式和本地追溯要求见 [SKILL.md](../SKILL.md) 的“固定交付位置与方式”；不得用 Word 导入代替。
先使用当前CLI的init-draft与parse流程。CWD为项目根目录；本地图片用path="@./..."，src仅用于已有飞书图片token。XML直接从title开始，不加XML声明或doc根标签。

```xml
<title>编号-产品名-序号-YYYY-MM-DD</title>
<h1>「编号-产品名-序号」分镜脚本</h1>
<p>视频时长 | XX.XX 秒 · N 个镜头/动作单元</p>
<h2>一、视频源链接</h2>
<p>视频链接</p>
<h2>二、开头结构</h2>
<p>钩子类型：一句话总结</p>
<grid>
 <column width-ratio="0.333333"><img path="@./frames_x/open1.jpg" caption="简短画面备注"/></column>
 <column width-ratio="0.333333"><img path="@./frames_x/open2.jpg" caption="简短画面备注"/></column>
 <column width-ratio="0.333334"><img path="@./frames_x/open3.jpg" caption="简短画面备注"/></column>
</grid>
<h2>三、完整分镜脚本（含画面帧）</h2>
<table>
 <colgroup><col width="90"/><col width="120"/><col width="68"/><col width="122"/><col width="90"/><col width="120"/><col width="68"/><col width="122"/></colgroup>
 <thead><tr><th><p>镜头信息</p></th><th><p>台词</p></th><th><p>画面帧</p></th><th><p>拍摄动作</p></th><th><p>镜头信息</p></th><th><p>台词</p></th><th><p>画面帧</p></th><th><p>拍摄动作</p></th></tr></thead>
 <tbody><tr>
  <td vertical-align="top"><p>01｜近景·俯拍<br/>0-1.2s<br/>时长 1.2s</p></td><td vertical-align="top"><p>第一镜头台词</p></td><td vertical-align="top"><img path="@./frames_x/shot01.jpg" width="48" height="85"/></td><td vertical-align="top"><p>具体拍摄动作</p></td>
  <td vertical-align="top"><p>02｜近景·俯拍<br/>1.2-3s<br/>时长 1.8s</p></td><td vertical-align="top"><p>第二镜头台词</p></td><td vertical-align="top"><img path="@./frames_x/shot02.jpg" width="48" height="85"/></td><td vertical-align="top"><p>具体拍摄动作</p></td>
 </tr></tbody>
</table>
<h2>四、逐句文案时间轴</h2>
<table><thead><tr><th><p>序号</p></th><th><p>时间</p></th><th><p>文案</p></th></tr></thead><tbody><tr><td><p>1</p></td><td><p>0-1.2s</p></td><td><p>第一句自然短句</p></td></tr></tbody></table>
<h2>五、整段文案（可一键复制）</h2>
<pre lang="text"><code>第一句<br/>第二句</code></pre>
```

开头只保留标题与基本信息，不放转录方式、ASR/BGM、误差及商品事实验证等备注，来源记录保存在本地报告。删除旧4段式结构及配图。完整分镜每行两组、先左后右，奇数镜头最后右组留空；窄列自动换行，保留全部台词和对应画面帧，不加音效列或冗长图注。

parse必须assessment.status=passed；创建/更新后检查warnings并回查5个h2、图片数量、分镜顺序与台词完整性。资源失败修复原文档，不重复创建。下游按“逐句文案时间轴”标题定位，不再硬编码第六段。

创建后按 SKILL.md 的“云端回查与交付”核验五个章节、名称、所在文件夹、全部表格文字及画面帧，保存本地检查记录。
