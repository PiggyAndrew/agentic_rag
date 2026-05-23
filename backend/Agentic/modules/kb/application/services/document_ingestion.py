from __future__ import annotations

from dataclasses import dataclass
import os
import re
import time
from typing import Iterable, Optional, Sequence
from urllib.parse import unquote, urlparse

from backend.modules.kb.domain.chunk_models import DocumentChunk
from backend.modules.kb.domain.document_models import Document, DocumentDetails
from backend.modules.kb.domain.element_models import ImageElement, TableElement
from backend.modules.kb.domain.enums import DocumentStatus, PdfDocumentType
from backend.modules.kb.domain.ports import (
    AssetPathProviderPort,
    ExcelTextExtractorPort,
    ImageCaptionerPort,
    KnowledgeChunkWriterPort,
    KnowledgeDocumentResolverPort,
    PdfMarkdownExtractorPort,
    TableChunkerPort,
    TextSplitterPort,
)
from backend.modules.kb.domain.services.document_ingestion import (
    enrich_chunks_with_images,
    rewrite_markdown_image_urls,
)
from backend.modules.kb.domain.services.table_ingestion import build_empty_excel_table_chunk, excel_table_name_from_path


@dataclass(frozen=True, slots=True)
class PdfIngestionOptions:
    chunk_size: int = 500
    overlap: int = 100
    document_type: PdfDocumentType = PdfDocumentType.document
    use_llm_headings: Optional[bool] = None
    enable_caption: Optional[bool] = None
    caption_max_images: Optional[int] = None
    caption_batch_size: Optional[int] = None
    assets_base_url: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_type", PdfDocumentType.coerce(self.document_type))


@dataclass(frozen=True, slots=True)
class ExcelIngestionOptions:
    max_rows_per_sheet: int = 5000
    max_cols: int = 50
    use_llm_summary: Optional[bool] = None
    max_rows_per_chunk: int = 80
    max_chars_per_chunk: int = 8000


class DocumentIngestionService:
    def __init__(
        self,
        *,
        document_resolver: KnowledgeDocumentResolverPort,
        asset_paths: AssetPathProviderPort,
        chunk_writer: KnowledgeChunkWriterPort,
        pdf_extractor: PdfMarkdownExtractorPort,
        text_splitter: TextSplitterPort,
        image_captioner: Optional[ImageCaptionerPort] = None,
        excel_text_extractor: Optional[ExcelTextExtractorPort] = None,
        table_chunker: Optional[TableChunkerPort] = None,
    ) -> None:
        self._document_resolver = document_resolver
        self._asset_paths = asset_paths
        self._chunk_writer = chunk_writer
        self._pdf_extractor = pdf_extractor
        self._text_splitter = text_splitter
        self._image_captioner = image_captioner
        self._excel_text_extractor = excel_text_extractor
        self._table_chunker = table_chunker

    def ingest_pdf(self, *, kb_id: int, pdf_path: str, options: Optional[PdfIngestionOptions] = None) -> Document:
        opts = options or PdfIngestionOptions()
        filename = self._filename_from_path(pdf_path)
        document_id = self._document_resolver.find_document_id_by_name(int(kb_id), filename)

        markdown, page_chunks, assets_dir = self._extract_pdf_markdown(
            kb_id=int(kb_id),
            document_id=int(document_id),
            pdf_path=pdf_path,
            document_type=opts.document_type,
        )
        document_chunks = self._build_pdf_chunks(
            kb_id=int(kb_id),
            document_id=int(document_id),
            markdown=markdown,
            page_chunks=page_chunks,
            options=opts,
        )
        document_chunks = self._process_pdf_images(document_chunks, options=opts)

        saved = self._chunk_writer.save_document_chunks(int(kb_id), int(document_id), document_chunks)
        if not saved:
            raise RuntimeError("PDF chunk 保存失败")
        return self._build_pdf_document(
            kb_id=int(kb_id),
            document_id=int(document_id),
            filename=filename,
            pdf_path=pdf_path,
            assets_dir=assets_dir,
            document_chunks=document_chunks,
            document_type=opts.document_type,
        )

    def ingest_excel(self, *, kb_id: int, excel_path: str, options: Optional[ExcelIngestionOptions] = None) -> Document:
        if self._excel_text_extractor is None or self._table_chunker is None:
            raise RuntimeError("Excel ingestion 未配置")
        opts = options or ExcelIngestionOptions()

        filename = excel_path.split("/")[-1].split("\\")[-1]
        document_id = self._document_resolver.find_document_id_by_name(int(kb_id), filename)
        text = self._excel_text_extractor.extract_text(
            excel_path,
            max_rows_per_sheet=int(opts.max_rows_per_sheet),
            max_cols=int(opts.max_cols),
        )
        use_llm = (
            bool(str(os.getenv("INGEST_USE_LLM_TABLE_SUMMARY", "")).lower() in {"1", "true", "yes"})
            if opts.use_llm_summary is None
            else bool(opts.use_llm_summary)
        )
        table_name = excel_table_name_from_path(excel_path)
        document_chunks = list(
            self._table_chunker.split_table(
                text=text,
                kb_id=int(kb_id),
                document_id=int(document_id),
                table_name=table_name,
                use_llm_summary=use_llm,
                max_rows_per_chunk=int(opts.max_rows_per_chunk),
                max_chars_per_chunk=int(opts.max_chars_per_chunk),
            )
        )
        if not document_chunks:
            document_chunks = build_empty_excel_table_chunk(
                kb_id=int(kb_id),
                document_id=int(document_id),
                table_name=table_name,
            )

        saved = self._chunk_writer.save_document_chunks(int(kb_id), int(document_id), document_chunks)
        if not saved:
            raise RuntimeError("Excel chunk 保存失败")
        now_ms = int(time.time() * 1000)
        _, table_count = self._count_chunk_elements(document_chunks)
        return Document(
            kb_id=int(kb_id),
            document_id=int(document_id),
            filename=filename,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            chunk_count=len(document_chunks),
            status=DocumentStatus.done,
            source_path=excel_path,
            details=DocumentDetails(
                source_path=excel_path,
                parser_name=type(self._excel_text_extractor).__name__,
                parsed_at_ms=now_ms,
                table_count=table_count,
                extra={
                    "table_name": table_name,
                    "use_llm_summary": use_llm,
                },
            ),
        )

    def _extract_pdf_markdown(
        self,
        *,
        kb_id: int,
        document_id: int,
        pdf_path: str,
        document_type: PdfDocumentType,
    ) -> tuple[str, list[DocumentChunk], str]:
        assets_dir = self._asset_paths.assets_images_dir(int(kb_id), int(document_id))
        markdown, page_chunks = self._pdf_extractor.extract(pdf_path, assets_dir, document_type)

        def _resolve(src: str) -> str:
            return self._resolve_asset_src(src, kb_id=int(kb_id), document_id=int(document_id))

        rewritten_markdown = rewrite_markdown_image_urls(markdown, resolve_src=_resolve)
        return rewritten_markdown, page_chunks, assets_dir

    def _build_pdf_chunks(
        self,
        *,
        kb_id: int,
        document_id: int,
        markdown: str,
        page_chunks: Sequence[DocumentChunk],
        options: PdfIngestionOptions,
    ) -> list[DocumentChunk]:
        if options.document_type is PdfDocumentType.drawing:
            return enrich_chunks_with_images(page_chunks)

        document_chunks = list(self._text_splitter.split(markdown, int(kb_id), int(document_id)))
        return enrich_chunks_with_images(document_chunks)

    def _process_pdf_images(
        self,
        document_chunks: Sequence[DocumentChunk],
        *,
        options: PdfIngestionOptions,
    ) -> list[DocumentChunk]:
        enable_caption = (
            bool(str(os.getenv("INGEST_IMAGE_CAPTION", "1")).lower() in {"1", "true", "yes"})
            if options.enable_caption is None
            else bool(options.enable_caption)
        )
        chunks = list(document_chunks)
        if not enable_caption or self._image_captioner is None:
            return chunks

        max_images = int(options.caption_max_images) if options.caption_max_images else None
        batch_size = int(options.caption_batch_size) if options.caption_batch_size else 1
        return self._image_captioner.caption(
            chunks,
            batch_size=batch_size,
            max_images=max_images,
        )

    def _build_pdf_document(
        self,
        *,
        kb_id: int,
        document_id: int,
        filename: str,
        pdf_path: str,
        assets_dir: str,
        document_chunks: Sequence[DocumentChunk],
        document_type: PdfDocumentType,
    ) -> Document:
        now_ms = int(time.time() * 1000)
        image_count, table_count = self._count_chunk_elements(document_chunks)
        page_count = (
            max(
                [
                    int(chunk.page_end or chunk.page_start or 0)
                    for chunk in document_chunks
                    if chunk.page_start is not None or chunk.page_end is not None
                ],
                default=0,
            )
            or None
        )
        return Document(
            kb_id=int(kb_id),
            document_id=int(document_id),
            filename=filename,
            mime_type="application/pdf",
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            chunk_count=len(document_chunks),
            status=DocumentStatus.done,
            source_path=pdf_path,
            details=DocumentDetails(
                source_path=pdf_path,
                parser_name=type(self._pdf_extractor).__name__,
                parsed_at_ms=now_ms,
                page_count=page_count,
                image_count=image_count,
                table_count=table_count,
                extra={
                    "assets_dir": assets_dir,
                    "document_type": str(document_type.value),
                },
            ),
        )

    def _count_chunk_elements(self, document_chunks: Iterable[DocumentChunk]) -> tuple[int, int]:
        image_ids: set[str] = set()
        table_ids: set[str] = set()
        for chunk in document_chunks:
            for element in chunk.elements:
                if isinstance(element, ImageElement):
                    image_ids.add(element.id)
                    continue
                if isinstance(element, TableElement):
                    table_ids.add(element.id)
        return len(image_ids), len(table_ids)

    def _filename_from_path(self, path: str) -> str:
        return path.split("/")[-1].split("\\")[-1]

    def _resolve_asset_src(self, src: str, *, kb_id: int, document_id: int) -> str:
        s = (src or "").strip()
        if not s:
            return s
        if re.match(r"^https?://", s, flags=re.I):
            try:
                p = urlparse(s)
                if (p.path or "").startswith("/assets/"):
                    return f"{p.path}{'?' + p.query if p.query else ''}{'#' + p.fragment if p.fragment else ''}"
            except Exception:
                return s
            return s
        normalized = re.sub(r"[\\]+", "/", s)
        if re.match(r"^[a-zA-Z]:/", normalized) or normalized.lower().startswith("file:///"):
            path = re.sub(r"^file:///", "", normalized, flags=re.I)
            m = re.search(r"data/kb/(\d+)/assets/images/(\d+)/(.+)$", path, flags=re.I)
            if m:
                kb = m.group(1)
                fid = m.group(2)
                name = m.group(3)
                return f"/assets/{kb}/assets/images/{fid}/{name}"
        if "output_images/" in normalized:
            after_output = normalized.split("output_images/")[1] or normalized.split("/")[-1] or normalized
        else:
            after_output = normalized.split("/")[-1] or normalized
        return f"/assets/{int(kb_id)}/assets/images/{int(document_id)}/{after_output}"

    def _default_assets_base_url(self) -> str:
        port = int(os.getenv("PORT", "8000"))
        return f"http://localhost:{port}"

    def _local_image_path_from_url(self, url: str, assets_dir: str) -> Optional[str]:
        u = (url or "").strip()
        if not u:
            return None

        if re.match(r"^https?://", u, flags=re.I):
            try:
                p = urlparse(u)
                parts = [x for x in (p.path or "").split("/") if x]
                if not parts:
                    return None
                filename = unquote(parts[-1])
                local = os.path.join(assets_dir, filename)
                return local if os.path.isfile(local) else None
            except Exception:
                return None

        normalized = re.sub(r"^[a-zA-Z]+:(//)?", "", u).strip()
        normalized = normalized.replace("\\", "/")
        filename = normalized.split("/")[-1] if normalized else ""
        if not filename:
            return None
        local = os.path.join(assets_dir, filename)
        return local if os.path.isfile(local) else None
