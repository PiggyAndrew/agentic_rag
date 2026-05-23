import os
import tempfile
import unittest

from backend.modules.kb.application.services.file_ingestion import FileIngestionService, PdfIngestionOptions


class _FakeFileResolver:
    def find_file_id_by_name(self, kb_id: int, filename: str) -> int:
        return 10


class _FakeAssetPaths:
    def __init__(self, root: str):
        self._root = root

    def assets_images_dir(self, kb_id: int, file_id: int) -> str:
        p = os.path.join(self._root, "images")
        os.makedirs(p, exist_ok=True)
        return p


class _FakeChunkWriter:
    def __init__(self):
        self.saved = []

    def save_chunks(self, kb_id: int, file_id: int, chunks):
        self.saved.append((kb_id, file_id, chunks))


class _FakePdfExtractor:
    def extract_markdown(self, pdf_path: str, image_dir: str) -> str:
        return 'hello ![x](x.png) <img src="y.jpg" />'


class _FakeTextSplitter:
    def split(self, text: str, kb_id: int, file_id: int):
        return [
            {
                "kb_id": kb_id,
                "file_id": file_id,
                "chunk_index": 0,
                "content": text,
                "metadata": None,
                "created_at_ms": 0,
                "updated_at_ms": 0,
            }
        ]


class TestFileIngestionServicePdf(unittest.TestCase):
    def test_ingest_pdf_builds_chunks_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = _FakeChunkWriter()
            svc = FileIngestionService(
                file_resolver=_FakeFileResolver(),
                asset_paths=_FakeAssetPaths(tmp),
                chunk_writer=writer,
                pdf_extractor=_FakePdfExtractor(),
                text_splitter=_FakeTextSplitter(),
                image_captioner=None,
                excel_text_extractor=None,
                table_chunker=None,
            )
            info = svc.ingest_pdf(kb_id=1, pdf_path=os.path.join(tmp, "a.pdf"), options=PdfIngestionOptions(enable_caption=False))
            self.assertEqual(info.id, 10)
            self.assertEqual(info.filename, "a.pdf")
            self.assertGreater(info.chunk_count, 0)
            self.assertEqual(len(writer.saved), 1)
            _, _, chunks = writer.saved[0]
            self.assertEqual(len(chunks), 1)
            content = chunks[0]["content"]
            self.assertIn("![x](/assets/1/assets/images/10/x.png)", content)
            self.assertIn('src="/assets/1/assets/images/10/y.jpg"', content)


if __name__ == "__main__":
    unittest.main()
