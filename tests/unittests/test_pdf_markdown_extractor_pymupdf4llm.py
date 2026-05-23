import os
import tempfile
import unittest

from backend.modules.kb.domain.chunk_models import DocumentChunk
from backend.modules.kb.domain.enums import PdfDocumentType
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_pymupdf4llm import (
    PyMuPdf4LlmPdfMarkdownExtractor,
)


class _TestableExtractor(PyMuPdf4LlmPdfMarkdownExtractor):
    def _extract_markdown_pages_with_pymupdf4llm(self, pdf_path: str, image_dir: str) -> list[str]:
        return [
            "# 第1页\n\n这里是第一页内容。",
            "# 第2页\n\n这里是第二页内容。",
        ]

    def _render_page_images(self, pdf_path: str, image_dir: str) -> dict[int, str]:
        page_1 = os.path.join(image_dir, "page_0001.png")
        page_2 = os.path.join(image_dir, "page_0002.png")
        for path in [page_1, page_2]:
            with open(path, "wb") as f:
                f.write(b"fake-image")
        return {1: "page_0001.png", 2: "page_0002.png"}


class TestPdfMarkdownExtractorPyMuPdf4Llm(unittest.TestCase):
    def test_extract_document_keeps_plain_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "sample.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4")

            image_dir = os.path.join(tmp, "images")
            extractor = _TestableExtractor()
            markdown, page_chunks = extractor.extract(pdf_path, image_dir, PdfDocumentType.document)

            self.assertIn("# 第1页", markdown)
            self.assertIn("# 第2页", markdown)
            self.assertEqual(page_chunks, [])
            self.assertFalse(os.path.isfile(os.path.join(image_dir, "page_0001.png")))

    def test_extract_drawing_appends_page_images_per_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "sample.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4")

            image_dir = os.path.join(tmp, "images")
            extractor = _TestableExtractor()
            markdown, page_chunks = extractor.extract(pdf_path, image_dir, PdfDocumentType.drawing)

            self.assertEqual(len(page_chunks), 2)
            self.assertIsInstance(page_chunks[0], DocumentChunk)
            self.assertIn("![第 1 页整页图像](page_0001.png)", page_chunks[0].segments[0].text)
            self.assertIn("![第 2 页整页图像](page_0002.png)", page_chunks[1].segments[0].text)
            self.assertIn("![第 1 页整页图像](page_0001.png)", markdown)
            self.assertTrue(os.path.isfile(os.path.join(image_dir, "page_0001.png")))
            self.assertTrue(os.path.isfile(os.path.join(image_dir, "page_0002.png")))


if __name__ == "__main__":
    unittest.main()
