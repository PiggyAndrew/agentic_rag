import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from backend.modules.kb.domain.chunk_models import ChunkingInfo, DocumentChunk, TextSegment
from backend.modules.kb.domain.enums import ChunkingStrategy
from backend.modules.kb.domain.enums import PdfDocumentType
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_docling import DoclingPdfMarkdownExtractor
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_factory import build_pdf_markdown_extractor
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_pymupdf4llm import (
    PyMuPdf4LlmPdfMarkdownExtractor,
)


class _FakePageImageExtractor:
    def extract(self, pdf_path: str, image_dir: str, document_type: PdfDocumentType) -> tuple[str, list[DocumentChunk]]:
        self.pdf_path = pdf_path
        self.image_dir = image_dir
        self.document_type = document_type
        return "![page](page_0001.png)", [
            DocumentChunk(
                document_id=0,
                chunk_index=0,
                segments=[TextSegment(text="![page](page_0001.png)")],
                elements=[],
                page_start=1,
                page_end=1,
                chunking=ChunkingInfo(strategy=ChunkingStrategy.page_based, rule="test"),
                created_at_ms=1,
                updated_at_ms=1,
            )
        ]


class _FakeDocument:
    def export_to_markdown(self) -> str:
        return "# Docling 正文"


class _FakeConvertResult:
    document = _FakeDocument()


class _FakeDocumentConverter:
    last_source = None

    def convert(self, source: str) -> _FakeConvertResult:
        _FakeDocumentConverter.last_source = source
        return _FakeConvertResult()


TEST_PDF_PATH = Path(__file__).resolve().parents[1] / "testfiles" / "test drawing reading.pdf"


class TestDoclingPdfMarkdownExtractor(unittest.TestCase):
    def test_extract_document_uses_docling(self):
        fake_docling = types.ModuleType("docling")
        fake_document_converter = types.ModuleType("docling.document_converter")
        fake_document_converter.DocumentConverter = _FakeDocumentConverter
        fake_docling.document_converter = fake_document_converter
        pdf_path = str(TEST_PDF_PATH)

        self.assertTrue(TEST_PDF_PATH.is_file())
        with tempfile.TemporaryDirectory() as tmp:
            image_dir = os.path.join(tmp, "images")
            extractor = DoclingPdfMarkdownExtractor(page_image_extractor=_FakePageImageExtractor())

            with patch.dict(
                sys.modules,
                {
                    "docling": fake_docling,
                    "docling.document_converter": fake_document_converter,
                },
            ):
                markdown, page_chunks = extractor.extract(pdf_path, image_dir, PdfDocumentType.document)

        self.assertEqual(_FakeDocumentConverter.last_source, pdf_path)
        self.assertEqual(markdown, "# Docling 正文")
        self.assertEqual(page_chunks, [])

    def test_extract_drawing_delegates_to_page_image_extractor(self):
        pdf_path = str(TEST_PDF_PATH)
        self.assertTrue(TEST_PDF_PATH.is_file())
        with tempfile.TemporaryDirectory() as tmp:
            image_dir = os.path.join(tmp, "images")
            delegate = _FakePageImageExtractor()
            extractor = DoclingPdfMarkdownExtractor(page_image_extractor=delegate)

            markdown, page_chunks = extractor.extract(pdf_path, image_dir, PdfDocumentType.drawing)

        self.assertEqual(delegate.pdf_path, pdf_path)
        self.assertEqual(delegate.image_dir, image_dir)
        self.assertEqual(delegate.document_type, PdfDocumentType.drawing)
        self.assertIn("![page](page_0001.png)", markdown)
        self.assertEqual(len(page_chunks), 1)

    def test_factory_defaults_to_docling_and_supports_legacy_override(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KB_PDF_MARKDOWN_EXTRACTOR", None)
            self.assertIsInstance(build_pdf_markdown_extractor(), PyMuPdf4LlmPdfMarkdownExtractor)

        with patch.dict(os.environ, {"KB_PDF_MARKDOWN_EXTRACTOR": "pymupdf4llm"}, clear=False):
            self.assertIsInstance(build_pdf_markdown_extractor(), PyMuPdf4LlmPdfMarkdownExtractor)


if __name__ == "__main__":
    unittest.main()
