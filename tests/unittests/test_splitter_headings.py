import unittest

from backend.kb.splitters.splitter_headings import HeadingsSplitter, HeadingItem


def _repeat(s: str, n: int) -> str:
    return (s * n).strip()


class TestHeadingsSplitter(unittest.TestCase):
    def test_allowed_chapters_and_markdown_subheadings(self):
        text = "\n".join(
            [
                "## 1 总则",
                _repeat("这是章节一的前置说明。", 80),
                "### 1.1 范围",
                _repeat("范围内容。", 80),
                "### 1.2 定义",
                _repeat("定义内容。", 80),
                "## 2 建筑",
                "短",
                "### 2.1 建筑的空调",
                _repeat("空调内容。", 80),
                "### **2.1.1 建筑空调的调试**",
                _repeat("调试内容。", 80),
                "## Appendix 1 附录A",
                _repeat("附录A内容。", 80),
                "### **Dimensioning Style**",
                _repeat("尺寸样式内容。", 80),
            ]
        )

        allowed = [
            HeadingItem(number="1", title="总则"),
            HeadingItem(number="2", title="建筑"),
            HeadingItem(number="Appendix 1", title="附录A"),
        ]
        splitter = HeadingsSplitter(allowed_headings=allowed, min_subchunk_chars=0)
        chunks = splitter.split(text)

        by_number = {c.get("metadata", {}).get("number"): c.get("metadata", {}).get("title") for c in chunks}
        expected = {
            "1": "总则",
            "1.1": "范围",
            "1.2": "定义",
            "2": "建筑",
            "2.1": "建筑的空调",
            "2.1.1": "建筑空调的调试",
            "Appendix 1": "附录A",
            "Appendix 1": "Dimensioning Style",
        }
        self.assertEqual(by_number, expected)

        for c in chunks:
            self.assertTrue(str(c.get("content", "")).strip())
            m = c.get("metadata", {})
            self.assertTrue(str(m.get("number", "")).strip())
            self.assertTrue(str(m.get("title", "")).strip())
            self.assertTrue(isinstance(m.get("path", None), list))

        c1 = [c for c in chunks if c.get("metadata", {}).get("number") == "1"]
        self.assertEqual(len(c1), 1)

        c11 = next((c for c in chunks if c.get("metadata", {}).get("number") == "1.1"), None)
        self.assertIsNotNone(c11)
        self.assertEqual(c11["metadata"]["title"], "范围")
        self.assertEqual(c11["metadata"]["path"][0], {"number": "1", "title": "总则"})
        self.assertEqual(c11["metadata"]["path"][1], {"number": "1.1", "title": "范围"})

        c12 = next((c for c in chunks if c.get("metadata", {}).get("number") == "1.2"), None)
        self.assertIsNotNone(c12)
        self.assertEqual(c12["metadata"]["title"], "定义")
        self.assertEqual(c12["metadata"]["path"][0], {"number": "1", "title": "总则"})
        self.assertEqual(c12["metadata"]["path"][1], {"number": "1.2", "title": "定义"})

        c2 = next((c for c in chunks if c.get("metadata", {}).get("number") == "2"), None)
        self.assertIsNotNone(c2)
        self.assertEqual(c2["metadata"]["title"], "建筑")
        self.assertEqual(c2["metadata"]["path"], [{"number": "2", "title": "建筑"}])

        c21 = next((c for c in chunks if c.get("metadata", {}).get("number") == "2.1"), None)
        self.assertIsNotNone(c21)
        self.assertEqual(c21["metadata"]["title"], "建筑的空调")
        self.assertEqual(c21["metadata"]["path"][0], {"number": "2", "title": "建筑"})
        self.assertEqual(c21["metadata"]["path"][1], {"number": "2.1", "title": "建筑的空调"})

        c211 = next((c for c in chunks if c.get("metadata", {}).get("number") == "2.1.1"), None)
        self.assertIsNotNone(c211)
        self.assertEqual(c211["metadata"]["title"], "建筑空调的调试")
        self.assertEqual(c211["metadata"]["path"][0], {"number": "2", "title": "建筑"})
        self.assertEqual(c211["metadata"]["path"][1], {"number": "2.1.1", "title": "建筑空调的调试"})

        capp = next((c for c in chunks if c.get("metadata", {}).get("number") == "Appendix 1"), None)
        self.assertIsNotNone(capp)
        self.assertEqual(capp["metadata"]["title"], "附录A")
        self.assertEqual(capp["metadata"]["path"], [{"number": "Appendix 1", "title": "附录A"}])

        cdim = next((c for c in chunks if c.get("metadata", {}).get("number") == "Appendix 1"), None)
        self.assertIsNotNone(cdim)
        self.assertEqual(cdim["metadata"]["title"], "Dimensioning Style")
        self.assertEqual(cdim["metadata"]["path"], [{"number": "Appendix 1", "title": "附录A"}])



    def test_small_intro_keeps_chapter_metadata(self):
        text = "\n".join(
            [
                "## 1 总则",
                _repeat("这是章节一的前置说明。", 80),
                "### 1.1 范围",
                _repeat("范围内容。", 80),
                "## 2 建筑",
                "短",
                "### 2.1 建筑的空调",
                _repeat("空调内容。", 80),
            ]
        )

        allowed = [
            HeadingItem(number="1", title="总则"),
            HeadingItem(number="2", title="建筑"),
        ]
        splitter = HeadingsSplitter(allowed_headings=allowed, min_subchunk_chars=500)
        chunks = splitter.split(text)

        c2 = [c for c in chunks if c.get("metadata", {}).get("number") == "2"]
        self.assertEqual(len(c2), 1)
        self.assertEqual(c2[0]["metadata"]["title"], "建筑")
        self.assertEqual(c2[0]["metadata"]["path"], [{"number": "2", "title": "建筑"}])

    def test_bullet_numbered_subsection_is_detected(self):
        text = "\n".join(
            [
                "## 2 建筑",
                _repeat("章节2的介绍内容。", 80),
                "* 2.1.2 机电系统",
                _repeat("机电系统内容。", 80),
            ]
        )

        allowed = [HeadingItem(number="2", title="建筑")]
        splitter = HeadingsSplitter(allowed_headings=allowed, min_subchunk_chars=0)
        chunks = splitter.split(text)

        c212 = next((c for c in chunks if c.get("metadata", {}).get("number") == "2.1.2"), None)
        self.assertIsNotNone(c212)
        self.assertEqual(c212["metadata"]["title"], "机电系统")
        self.assertEqual(c212["metadata"]["path"][0], {"number": "2", "title": "建筑"})
        self.assertEqual(c212["metadata"]["path"][1], {"number": "2.1.2", "title": "机电系统"})


if __name__ == "__main__":
    unittest.main()
