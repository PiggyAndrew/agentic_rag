from __future__ import annotations

import os

from backend.modules.kb.domain.chunk_models import DocumentChunk
from backend.modules.kb.domain.enums import PdfDocumentType
from backend.modules.kb.domain.ports import PdfMarkdownExtractorPort
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_pymupdf4llm import (
    PyMuPdf4LlmPdfMarkdownExtractor,
)


class DoclingPdfMarkdownExtractor(PdfMarkdownExtractorPort):
    def __init__(self, *, page_image_extractor: PyMuPdf4LlmPdfMarkdownExtractor | None = None) -> None:
        self._page_image_extractor = page_image_extractor or PyMuPdf4LlmPdfMarkdownExtractor()

    def extract(self, pdf_path: str, image_dir: str, document_type: PdfDocumentType) -> tuple[str, list[DocumentChunk]]:
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

        os.makedirs(image_dir, exist_ok=True)
        doc_type = PdfDocumentType.coerce(document_type)
        if doc_type is PdfDocumentType.drawing:
            return self._page_image_extractor.extract(pdf_path, image_dir, doc_type)

        markdown = self._extract_markdown_with_docling(pdf_path)
        return markdown, []

    def _extract_markdown_with_docling(self, pdf_path: str) -> str:
        try:
            from docling.document_converter import DocumentConverter  # type: ignore
        except Exception as e:
            raise RuntimeError("缺少依赖：请安装 docling") from e

        result = DocumentConverter().convert(pdf_path)
        return str(result.document.export_to_markdown() or "").strip()
