from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Optional
from urllib.parse import unquote, urlparse

from backend.kb.splitters import AdaptiveSplitter
from backend.modules.kb.domain.models import FileInfo
from backend.modules.kb.domain.ports import (
    AssetPathProviderPort,
    ExcelTextExtractorPort,
    ImageCaptionerPort,
    KnowledgeChunkWriterPort,
    KnowledgeFileResolverPort,
    PdfMarkdownExtractorPort,
    TableChunkerPort,
)
from backend.modules.kb.domain.services.document_ingestion import (
    apply_captions_to_chunks,
    collect_caption_jobs,
    enrich_chunks_with_images_metadata,
    rewrite_markdown_image_urls,
    split_text_normal,
)
from backend.modules.kb.domain.services.table_ingestion import build_empty_excel_table_chunk, excel_table_name_from_path


@dataclass(frozen=True, slots=True)
class PdfIngestionOptions:
    chunk_size: int = 500
    overlap: int = 100
    use_llm_headings: Optional[bool] = None
    enable_caption: Optional[bool] = None
    caption_max_images: Optional[int] = None
    caption_batch_size: Optional[int] = None
    assets_base_url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ExcelIngestionOptions:
    max_rows_per_sheet: int = 5000
    max_cols: int = 50
    use_llm_summary: Optional[bool] = None
    max_rows_per_chunk: int = 80
    max_chars_per_chunk: int = 8000


class FileIngestionService:
    def __init__(
        self,
        *,
        file_resolver: KnowledgeFileResolverPort,
        asset_paths: AssetPathProviderPort,
        chunk_writer: KnowledgeChunkWriterPort,
        pdf_extractor: PdfMarkdownExtractorPort,
        image_captioner: Optional[ImageCaptionerPort] = None,
        excel_text_extractor: Optional[ExcelTextExtractorPort] = None,
        table_chunker: Optional[TableChunkerPort] = None,
    ) -> None:
        self._file_resolver = file_resolver
        self._asset_paths = asset_paths
        self._chunk_writer = chunk_writer
        self._pdf_extractor = pdf_extractor
        self._image_captioner = image_captioner
        self._excel_text_extractor = excel_text_extractor
        self._table_chunker = table_chunker

    def ingest_pdf(self, *, kb_id: int, pdf_path: str, options: Optional[PdfIngestionOptions] = None) -> FileInfo:
        opts = options or PdfIngestionOptions()
        filename = pdf_path.split("/")[-1].split("\\")[-1]
        file_id = self._file_resolver.find_file_id_by_name(int(kb_id), filename)

        assets_dir = self._asset_paths.assets_images_dir(int(kb_id), int(file_id))
        markdown = self._pdf_extractor.extract_markdown(pdf_path, assets_dir)
        base_url = (opts.assets_base_url or self._default_assets_base_url()).rstrip("/")

        def _resolve_src(src: str) -> str:
            s = (src or "").strip()
            if re.match(r"^https?://", s, flags=re.I):
                return s
            normalized = re.sub(r"[\\]+", "/", s)
            if re.match(r"^[a-zA-Z]:/", normalized) or normalized.lower().startswith("file:///"):
                path = re.sub(r"^file:///", "", normalized, flags=re.I)
                m = re.search(r"data/kb/(\\d+)/assets/images/(\\d+)/(.+)$", path, flags=re.I)
                if m:
                    kb = m.group(1)
                    fid = m.group(2)
                    name = m.group(3)
                    return f"{base_url}/assets/{kb}/assets/images/{fid}/{name}"
            if "output_images/" in normalized:
                after_output = normalized.split("output_images/")[1] or normalized.split("/")[-1] or normalized
            else:
                after_output = normalized.split("/")[-1] or normalized
            return f"{base_url}/assets/{int(kb_id)}/assets/images/{int(file_id)}/{after_output}"

        markdown = rewrite_markdown_image_urls(markdown, resolve_src=_resolve_src)
        use_llm = (
            bool(str(os.getenv("INGEST_USE_LLM_HEADING", "")).lower() in {"1", "true", "yes"})
            if opts.use_llm_headings is None
            else bool(opts.use_llm_headings)
        )
        adaptive_chunks = AdaptiveSplitter(use_llm=use_llm).split(markdown, int(kb_id), int(file_id))
        first_meta = (
            adaptive_chunks[0].metadata.data
            if adaptive_chunks
            and getattr(adaptive_chunks[0], "metadata", None) is not None
            and getattr(adaptive_chunks[0].metadata, "data", None) is not None
            else {}
        )
        if (
            adaptive_chunks
            and str(first_meta.get("type", "")).strip() == "toc"
            and str(adaptive_chunks[0].content or "").strip() != ""
        ):
            chunks = adaptive_chunks
        else:
            chunks = split_text_normal(
                text=markdown,
                kb_id=int(kb_id),
                file_id=int(file_id),
                chunk_size=int(opts.chunk_size),
                overlap=int(opts.overlap),
            )
        enrich_chunks_with_images_metadata(chunks)

        enable_caption = (
            bool(str(os.getenv("INGEST_IMAGE_CAPTION", "1")).lower() in {"1", "true", "yes"})
            if opts.enable_caption is None
            else bool(opts.enable_caption)
        )
     

        if enable_caption and self._image_captioner is not None:
            jobs = collect_caption_jobs(
                chunks
            )
            if jobs:
                captions_by_index = self._image_captioner.caption(
                    [{"index": int(j.index), "path": j.path} for j in jobs]
                )
                apply_captions_to_chunks(chunks, captions_by_index=captions_by_index)

        self._chunk_writer.save_chunks(int(kb_id), int(file_id), chunks)
        return FileInfo(id=int(file_id), filename=filename, chunk_count=len(chunks), status="done")

    def ingest_excel(self, *, kb_id: int, excel_path: str, options: Optional[ExcelIngestionOptions] = None) -> FileInfo:
        if self._excel_text_extractor is None or self._table_chunker is None:
            raise RuntimeError("Excel ingestion 未配置")
        opts = options or ExcelIngestionOptions()

        filename = excel_path.split("/")[-1].split("\\")[-1]
        file_id = self._file_resolver.find_file_id_by_name(int(kb_id), filename)
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
        chunks = self._table_chunker.split_table(
            text=text,
            kb_id=int(kb_id),
            file_id=int(file_id),
            table_name=table_name,
            use_llm_summary=use_llm,
            max_rows_per_chunk=int(opts.max_rows_per_chunk),
            max_chars_per_chunk=int(opts.max_chars_per_chunk),
        )
        if not chunks:
            chunks = build_empty_excel_table_chunk(kb_id=int(kb_id), file_id=int(file_id), table_name=table_name)

        self._chunk_writer.save_chunks(int(kb_id), int(file_id), chunks)
        return FileInfo(id=int(file_id), filename=filename, chunk_count=len(chunks), status="done")

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
