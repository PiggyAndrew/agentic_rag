from __future__ import annotations

from backend.modules.kb.application.services.file_ingestion import FileIngestionService
from backend.modules.kb.application.usecase import KnowledgeBaseUseCase
from backend.modules.kb.infrastructure.adapters.excel_text_extractor_openpyxl import OpenpyxlExcelTextExtractor
from backend.modules.kb.infrastructure.adapters.image_captioner_legacy import LegacyImageCaptioner
from backend.modules.kb.infrastructure.adapters.kb_file_storage_local import LocalKbFileStorage
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_pymupdf4llm import PyMuPdf4LlmPdfMarkdownExtractor
from backend.modules.kb.infrastructure.adapters.table_chunker_legacy import LegacyTableChunker


class KnowledgeService:
    def __init__(self, *, controller: object, repo: object):
        ingestion = FileIngestionService(
            file_resolver=controller,
            asset_paths=controller,
            chunk_writer=controller,
            pdf_extractor=PyMuPdf4LlmPdfMarkdownExtractor(),
            image_captioner=LegacyImageCaptioner(),
            excel_text_extractor=OpenpyxlExcelTextExtractor(),
            table_chunker=LegacyTableChunker(),
        )
        storage = LocalKbFileStorage(kb_dir_resolver=controller)
        self._uc = KnowledgeBaseUseCase(controller=controller, repo=repo, ingestion=ingestion, storage=storage)

    def __getattr__(self, name: str):
        return getattr(self._uc, name)


__all__ = ["KnowledgeService"]
