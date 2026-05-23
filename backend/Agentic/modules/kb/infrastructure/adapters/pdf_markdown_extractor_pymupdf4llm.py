from __future__ import annotations

import logging
import os
from typing import List

from backend.modules.kb.domain.chunk_models import ChunkingInfo, DocumentChunk, ElementRefSegment, TextSegment
from backend.modules.kb.domain.element_models import ImageElement
from backend.modules.kb.domain.enums import ElementType
from backend.modules.kb.domain.enums import PdfDocumentType
from backend.modules.kb.domain.ports import PdfMarkdownExtractorPort
from backend.modules.kb.domain.enums import ChunkingStrategy


logger = logging.getLogger(__name__)


class PyMuPdf4LlmPdfMarkdownExtractor(PdfMarkdownExtractorPort):
    def extract(self, pdf_path: str, image_dir: str, document_type: PdfDocumentType) -> tuple[str, List[DocumentChunk]]:
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

        os.makedirs(image_dir, exist_ok=True)
        doc_type = PdfDocumentType.coerce(document_type)
        markdown_pages = self._extract_markdown_pages_with_pymupdf4llm(pdf_path, image_dir)
        if doc_type is PdfDocumentType.drawing:
            return self._build_drawing_extraction(pdf_path=pdf_path, image_dir=image_dir, text_pages=markdown_pages)
        return self._build_document_extraction(markdown_pages)

    def _build_document_extraction(self, pages: List[str]) -> tuple[str, List[DocumentChunk]]:
        markdown = "\n\n".join((page or "").strip() for page in pages if (page or "").strip()).strip()
        return markdown, []

    def _build_drawing_extraction(
        self,
        *,
        pdf_path: str,
        image_dir: str,
        text_pages: List[str],
    ) -> tuple[str, List[DocumentChunk]]:
        page_images = self._render_page_images(pdf_path, image_dir)
        page_chunks: List[DocumentChunk] = []
        markdown_pages: List[str] = []

        for page_number, image_name in sorted(page_images.items()):
            segments: List[TextSegment | ElementRefSegment] = []
            elements: List[ImageElement] = []
            if page_number <= len(text_pages) and (text_pages[page_number - 1] or "").strip():
                page_text = (text_pages[page_number - 1] or "").strip()
                segments.append(TextSegment(text=page_text))
            image_id = f"page_image_{page_number:04d}"
            segments.append(ElementRefSegment(ref_id=image_id, ref_type=ElementType.image))
            elements.append(
                ImageElement(
                    id=image_id,
                    uri=os.path.join(image_dir, image_name),
                    alt_text=f"第 {page_number} 页整页图像",
                )
            )
            chunk = DocumentChunk(
                document_id=0,
                chunk_index=len(page_chunks),
                segments=segments,
                elements=elements,
                page_start=page_number,
                page_end=page_number,
                chunking=ChunkingInfo(
                    strategy=ChunkingStrategy.page_based,
                    rule="pdf_page_splitter",
                    overlap=0,
                    generator="PyMuPdf4LlmPdfMarkdownExtractor._build_drawing_extraction",
                ),
                created_at_ms=0,
                updated_at_ms=0,
            )
            page_chunks.append(chunk)
            page_markdown = chunk.inline_text()
            if page_markdown:
                markdown_pages.append(page_markdown)

        markdown = "\n\n".join(markdown_pages).strip()
        return markdown, page_chunks

    def _extract_markdown_pages_with_pymupdf4llm(self, pdf_path: str, image_dir: str) -> List[str]:
        try:
            import pymupdf4llm  # type: ignore
        except Exception as e:
            raise RuntimeError("缺少依赖：请安装 pymupdf 与 pymupdf4llm") from e

        md = pymupdf4llm.to_markdown(
            pdf_path,
            write_images=True,
            image_path=image_dir,
            use_ocr=False,
            extract_words=True,
            dpi=200,
        )
        if isinstance(md, list):
            pages: List[str] = []
            for index, page in enumerate(md, start=1):
                del index
                pages.append(str(page.get("text") or "").strip())
            return pages
        return [str(md or "").strip()]

    def _render_page_images(self, pdf_path: str, image_dir: str) -> dict[int, str]:
        try:
            import fitz  # type: ignore
        except Exception as e:
            logger.warning("缺少依赖(PyMuPDF)，跳过整页转图步骤: %s, error=%s", pdf_path, e)
            return {}

        try:
            doc = fitz.open(pdf_path)
        except Exception as exc:
            logger.warning("整页转图失败，跳过额外图片提取: %s, error=%s", pdf_path, exc)
            return {}

        zoom = 200.0 / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        image_names: dict[int, str] = {}
        try:
            for index, page in enumerate(doc, start=1):
                page_name = f"page_{index:04d}.png"
                page_path = os.path.join(image_dir, page_name)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                pix.save(page_path)
                image_names[index] = page_name
        finally:
            doc.close()
        return image_names
