import unittest

from backend.modules.kb.domain.models import ChunkMetadata, KnowledgeChunk
from backend.modules.kb.domain.services.document_ingestion import (
    apply_captions_to_chunks,
    collect_caption_jobs,
    enrich_chunks_with_images_metadata,
    extract_image_urls,
    rewrite_markdown_image_urls,
    split_text_normal,
)


class TestDocumentIngestionService(unittest.TestCase):
    def test_extract_image_urls_supports_markdown_and_html(self):
        text = 'a ![x](a.png) b <img src="b.jpg" /> c ![](a.png)'
        urls = extract_image_urls(text)
        self.assertEqual(urls, ["a.png", "b.jpg"])

    def test_rewrite_markdown_image_urls(self):
        md = '![x](a.png) <img src="b.jpg" />'
        out = rewrite_markdown_image_urls(md, resolve_src=lambda s: f"/assets/{s}")
        self.assertIn("(/assets/a.png)", out)
        self.assertIn('src="/assets/b.jpg"', out)

    def test_split_text_normal_produces_overlapping_chunks(self):
        text = "0123456789"
        chunks = split_text_normal(text=text, kb_id=1, file_id=2, chunk_size=6, overlap=2)
        self.assertEqual([c.content for c in chunks], ["012345", "456789"])

    def test_enrich_chunks_with_images_metadata_sets_images_and_count(self):
        now_ms = 1
        ch = KnowledgeChunk(
            kb_id=1,
            file_id=2,
            chunk_index=0,
            content="![a](a.png)",
            metadata=ChunkMetadata.coerce({}),
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        enrich_chunks_with_images_metadata([ch])
        self.assertEqual(ch.metadata.data["image_count"], 1)
        self.assertEqual(ch.metadata.data["images"][0]["url"], "a.png")

    def test_collect_caption_jobs_dedup_and_limits(self):
        now_ms = 1
        ch = KnowledgeChunk(
            kb_id=1,
            file_id=2,
            chunk_index=0,
            content="![a](a.png) ![b](b.png)",
            metadata=ChunkMetadata.coerce({}),
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        enrich_chunks_with_images_metadata([ch])

        jobs = collect_caption_jobs([ch], local_path_from_url=lambda u: f"X/{u}", max_images=1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].index, 0)
        self.assertEqual(jobs[0].path, "X/a.png")

    def test_apply_captions_to_chunks(self):
        now_ms = 1
        ch = KnowledgeChunk(
            kb_id=1,
            file_id=2,
            chunk_index=0,
            content="![a](a.png)",
            metadata=ChunkMetadata.coerce({}),
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        enrich_chunks_with_images_metadata([ch])
        apply_captions_to_chunks([ch], captions_by_index={0: "hello"})
        self.assertEqual(ch.metadata.data["images"][0]["caption"], "hello")


if __name__ == "__main__":
    unittest.main()
