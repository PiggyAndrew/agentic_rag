from __future__ import annotations

import logging
import os

from backend.modules.kb.domain.ports import PdfMarkdownExtractorPort
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_docling import DoclingPdfMarkdownExtractor
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_pymupdf4llm import (
    PyMuPdf4LlmPdfMarkdownExtractor,
)


logger = logging.getLogger(__name__)

DEFAULT_PDF_EXTRACTOR = "pymupdf"


def build_pdf_markdown_extractor() -> PdfMarkdownExtractorPort:
    extractor_name = str(os.getenv("KB_PDF_MARKDOWN_EXTRACTOR", DEFAULT_PDF_EXTRACTOR)).strip().lower()

    if extractor_name == "docling":
        return DoclingPdfMarkdownExtractor()
    if extractor_name in {"pymupdf4llm", "pymupdf"}:
        return PyMuPdf4LlmPdfMarkdownExtractor()

    return PyMuPdf4LlmPdfMarkdownExtractor()
