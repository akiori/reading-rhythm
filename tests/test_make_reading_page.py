#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make_reading_page.py"
SPEC = importlib.util.spec_from_file_location("make_reading_page", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ReadingPageTests(unittest.TestCase):
    def test_plain_text_remains_paragraph_units(self):
        output = MODULE.make_html("测试", "第一段。\n\n第二段。", [])
        self.assertEqual(output.count('class="unit" data-index='), 2)
        self.assertNotIn("<table>", output)

    def test_gfm_pipe_table_becomes_semantic_table(self):
        source = """# 结果

| Subject | Accuracy | Rank |
|:---|---:|---:|
| S1 | 0.93 | 1 |
| S2 | 0.73 | 9 |
"""
        output = MODULE.make_html("测试", source, [])
        self.assertIn('<section class="unit table-unit"', output)
        self.assertIn("<table><thead><tr>", output)
        self.assertIn('<th class="align-right">', output)
        self.assertIn("Accuracy", output)
        self.assertIn('<td class="align-right">0.93</td>', output)
        self.assertNotIn("|:---|---:|", output)

    def test_escaped_pipe_stays_inside_cell(self):
        source = """| Item | Meaning |
|---|---|
| A | x \\| y |
"""
        blocks = MODULE.parse_blocks(source)
        self.assertEqual(blocks[0]["rows"][0][1], "x | y")

    def test_common_markdown_blocks_are_not_flattened(self):
        source = """## 标题

- 第一项
- 第二项

> 一段引用

```text
a | b
```
"""
        output = MODULE.make_html("测试", source, [])
        self.assertIn('class="unit heading-unit"', output)
        self.assertIn('class="unit list-unit"', output)
        self.assertIn('class="unit quote-unit"', output)
        self.assertIn('class="unit code-unit"', output)
        self.assertNotIn("## 标题", output)

    def test_english_page_uses_english_interface_and_serif_keyword(self):
        output = MODULE.make_html(
            "Focused reading",
            "Research writing becomes easier when visual rhythm guides attention.",
            [("visual rhythm", "anchor")],
        )
        self.assertIn('<html lang="en">', output)
        self.assertIn('class="anchor en">visual rhythm</span>', output)
        self.assertIn("Focus highlights", output)
        self.assertIn("Read one block at a time.", output)


if __name__ == "__main__":
    unittest.main()
