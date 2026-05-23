import os
import tempfile
import unittest

from backend.modules.kb.application.services.document_ingestion import DocumentIngestionService, PdfIngestionOptions
from backend.modules.kb.domain.chunk_models import ChunkingInfo, DocumentChunk, TextSegment
from backend.modules.kb.domain.element_models import ImageElement
from backend.modules.kb.domain.enums import ChunkingStrategy, PdfDocumentType


class _FakeResolver:
    def find_document_id_by_name(self, kb_id: int, filename: str) -> int:
        return 7


class _FakeAssetPaths:
    def __init__(self, root: str) -> None:
        self._root = root

    def assets_images_dir(self, kb_id: int, document_id: int) -> str:
        path = os.path.join(self._root, "images")
        os.makedirs(path, exist_ok=True)
        return path


class _FakeChunkWriter:
    def __init__(self) -> None:
        self.saved = []

    def save_document_chunks(self, kb_id: int, document_id: int, chunks) -> bool:
        self.saved.append((kb_id, document_id, list(chunks)))
        return True


class _FakePdfExtractor:
    def extract(self, pdf_path: str, image_dir: str, document_type: PdfDocumentType) -> tuple[str, list[DocumentChunk]]:
        del pdf_path, image_dir
        if document_type is PdfDocumentType.drawing:
            return (
                "page-1\n\npage-2",
                [
                    DocumentChunk(
                        document_id=0,
                        chunk_index=0,
                        segments=[TextSegment(text="第一页内容\n\n![page1](page_0001.png)")],
                        elements=[],
                        page_start=1,
                        page_end=1,
                        chunking=ChunkingInfo(strategy=ChunkingStrategy.page_based, rule="test"),
                        created_at_ms=1,
                        updated_at_ms=1,
                    ),
                    DocumentChunk(
                        document_id=0,
                        chunk_index=1,
                        segments=[TextSegment(text="第二页内容\n\n![page2](page_0002.png)")],
                        elements=[],
                        page_start=2,
                        page_end=2,
                        chunking=ChunkingInfo(strategy=ChunkingStrategy.page_based, rule="test"),
                        created_at_ms=1,
                        updated_at_ms=1,
                    ),
                ],
            )
        return "普通文档内容\n\n![inline](inline.png)", []


class _FakeTextSplitter:
    def __init__(self) -> None:
        self.calls = []

    def split(self, text: str, kb_id: int, document_id: int):
        self.calls.append((text, kb_id, document_id))
        return [
            DocumentChunk(
                document_id=document_id,
                chunk_index=0,
                segments=[TextSegment(text=text)],
                elements=[],
                created_at_ms=1,
                updated_at_ms=1,
            )
        ]


class TestDocumentIngestionPdfModes(unittest.TestCase):
    def test_document_type_uses_text_splitter(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = _FakeChunkWriter()
            splitter = _FakeTextSplitter()
            service = DocumentIngestionService(
                document_resolver=_FakeResolver(),
                asset_paths=_FakeAssetPaths(tmp),
                chunk_writer=writer,
                pdf_extractor=_FakePdfExtractor(),
                text_splitter=splitter,
                image_captioner=None,
                excel_text_extractor=None,
                table_chunker=None,
            )

            info = service.ingest_pdf(
                kb_id=1,
                pdf_path=os.path.join(tmp, "sample.pdf"),
                options=PdfIngestionOptions(document_type=PdfDocumentType.document, enable_caption=False),
            )

            self.assertEqual(len(splitter.calls), 1)
            self.assertEqual(info.chunk_count, 1)
            self.assertEqual(info.details.extra["document_type"], "document")
            saved_chunks = writer.saved[0][2]
            self.assertEqual(len(saved_chunks), 1)
            self.assertEqual(len(saved_chunks[0].elements), 1)
            self.assertIsInstance(saved_chunks[0].elements[0], ImageElement)
            self.assertEqual(saved_chunks[0].elements[0].uri, "/assets/1/assets/images/7/inline.png")

    def test_drawing_type_builds_page_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = _FakeChunkWriter()
            splitter = _FakeTextSplitter()
            service = DocumentIngestionService(
                document_resolver=_FakeResolver(),
                asset_paths=_FakeAssetPaths(tmp),
                chunk_writer=writer,
                pdf_extractor=_FakePdfExtractor(),
                text_splitter=splitter,
                image_captioner=None,
                excel_text_extractor=None,
                table_chunker=None,
            )

            info = service.ingest_pdf(
                kb_id=1,
                pdf_path=os.path.join(tmp, "drawing.pdf"),
                options=PdfIngestionOptions(document_type=PdfDocumentType.drawing, enable_caption=False),
            )

            self.assertEqual(splitter.calls, [])
            self.assertEqual(info.chunk_count, 2)
            self.assertEqual(info.details.page_count, 2)
            self.assertEqual(info.details.extra["document_type"], "drawing")
            saved_chunks = writer.saved[0][2]
            self.assertEqual([chunk.page_start for chunk in saved_chunks], [1, 2])
            self.assertEqual([chunk.page_end for chunk in saved_chunks], [1, 2])
            self.assertEqual(len(saved_chunks[0].elements), 1)
            self.assertEqual(saved_chunks[0].elements[0].uri, "/assets/1/assets/images/7/page_0001.png")
            self.assertEqual(saved_chunks[1].elements[0].uri, "/assets/1/assets/images/7/page_0002.png")


if __name__ == "__main__":
    unittest.main()
