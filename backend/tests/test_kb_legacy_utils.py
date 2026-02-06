from __future__ import annotations

import unittest

from backend.modules.kb.infrastructure.legacy_kb.services.embedding_text import compose_embedding_text
from backend.modules.kb.infrastructure.legacy_kb.services.keyword_search import tokenize_query


class KBLegacyUtilsTests(unittest.TestCase):
    def test_compose_embedding_text_with_captions(self) -> None:
        meta = {"images": [{"caption": "A"}, {"caption": "A"}, {"caption": "B"}, {"caption": ""}]}
        out = compose_embedding_text("hello", meta)
        self.assertIn("hello", out)
        self.assertIn("[ImageCaptions]", out)
        self.assertIn("- A", out)
        self.assertIn("- B", out)

    def test_tokenize_query(self) -> None:
        toks = tokenize_query("hello hello 世界 1 a")
        self.assertIn("hello", toks)
        self.assertIn("世界", toks)
        self.assertNotIn("a", toks)


if __name__ == "__main__":
    unittest.main()

