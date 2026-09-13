import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "voice_draft.py"
SPEC = importlib.util.spec_from_file_location("voice_draft", SCRIPT)
voice_draft = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = voice_draft
assert SPEC.loader is not None
SPEC.loader.exec_module(voice_draft)


class ExtractShotLinesTests(unittest.TestCase):
    def test_prefers_sixth_sentence_timeline_over_fifth_shot_script(self):
        content = """
视频时长 | 3.00 秒

## 五、完整分镜脚本（含画面帧）
<table>
<tr><td>镜号</td><td>时间</td><td>时长</td><td>景别</td><td>台词</td><td>画面帧</td><td>音效</td></tr>
<tr><td>1</td><td>0-3s</td><td>3</td><td>近景</td><td>第五段整句，不应该被优先朗读</td><td>frame.jpg</td><td></td></tr>
</table>

## 六、逐句文案时间轴
<table>
<tr><td>序号</td><td>时间</td><td>文案</td></tr>
<tr><td>1</td><td>0-1.2s</td><td>第六段第一句</td></tr>
<tr><td>2</td><td>1.2-3s</td><td>第六段第二句</td></tr>
</table>
"""

        shots, target_duration = voice_draft.extract_shot_lines(content)

        self.assertEqual(target_duration, 3.0)
        self.assertEqual(
            [(shot.start, shot.end, shot.text) for shot in shots],
            [(0.0, 1.2, "第六段第一句"), (1.2, 3.0, "第六段第二句")],
        )

    def test_falls_back_to_fifth_shot_script_when_sixth_timeline_is_missing(self):
        content = """
## 五、完整分镜脚本（含画面帧）
<table>
<tr><td>镜号</td><td>时间</td><td>时长</td><td>景别</td><td>台词</td><td>画面帧</td><td>音效</td></tr>
<tr><td>1</td><td>0-2s</td><td>2</td><td>近景</td><td>第五段台词</td><td>frame.jpg</td><td></td></tr>
</table>
"""

        shots, target_duration = voice_draft.extract_shot_lines(content)

        self.assertEqual(target_duration, 2.0)
        self.assertEqual([(shot.start, shot.end, shot.text) for shot in shots], [(0.0, 2.0, "第五段台词")])


if __name__ == "__main__":
    unittest.main()
