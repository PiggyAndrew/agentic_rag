from __future__ import annotations

import unittest

from backend.modules.kb.infrastructure.legacy_kb.services.embedding_text import compose_embedding_text
from backend.modules.kb.infrastructure.legacy_kb.services.keyword_search import tokenize_query
from backend.modules.kb.domain.services.document_ingestion import extract_image_urls, enrich_chunks_with_images_metadata


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

    def test_extract_image_urls_supports_absolute_urls(self) -> None:
        base = "http://localhost:8000/assets/1/assets/images/2"
        md = "\n".join(
            [
                f'![](output_images/0.png)',
                f'![]({base}/1.png "title")',
                f'<img src="{base}/2.jpg" alt="x">',
                f"plain: {base}/3.webp?x=1",
            ]
        )
        urls = extract_image_urls(md)
        self.assertIn("output_images/0.png", urls)
        self.assertIn(f"{base}/1.png", urls)
        self.assertIn(f"{base}/2.jpg", urls)
        self.assertIn(f"{base}/3.webp?x=1", urls)

    def test_enrich_chunks_with_images_metadata_works_with_dict_chunks(self) -> None:
        chunks = [
            {"chunk_index": 0, "content": "![](http://localhost:8000/assets/1/assets/images/2/0.png)", "metadata": {}},
            {"chunk_index": 1, "content": "no images", "metadata": {}},
        ]
        enrich_chunks_with_images_metadata(chunks)
        self.assertEqual(chunks[0]["metadata"].get("image_count"), 1)
        self.assertIsInstance(chunks[0]["metadata"].get("images"), list)
        self.assertEqual(chunks[0]["metadata"]["images"][0]["chunk_index"], 0)
        self.assertEqual(chunks[1]["metadata"].get("image_count"), None)


if __name__ == "__main__":
    unittest.main()
