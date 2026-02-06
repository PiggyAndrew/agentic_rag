from __future__ import annotations

import os
from typing import Optional

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager
from backend.modules.kb.application.services.file_ingestion import FileIngestionService
from backend.modules.kb.application.usecase import KnowledgeBaseUseCase
from backend.modules.kb.infrastructure.adapters.excel_text_extractor_openpyxl import OpenpyxlExcelTextExtractor
from backend.modules.kb.infrastructure.adapters.image_captioner_legacy import LegacyImageCaptioner
from backend.modules.kb.infrastructure.adapters.kb_file_storage_local import LocalKbFileStorage
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_pymupdf4llm import PyMuPdf4LlmPdfMarkdownExtractor
from backend.modules.kb.infrastructure.adapters.table_chunker_legacy import LegacyTableChunker
from backend.modules.kb.infrastructure.legacy import PersistentKnowledgeBaseController, SqlAlchemyKnowledgeRepository


def build_kb_usecase(*, manager: Optional[SqliteSessionManager] = None, base_dir: str = "data/kb") -> KnowledgeBaseUseCase:
    mgr = manager or get_default_sqlite_manager()
    repo = SqlAlchemyKnowledgeRepository(manager=mgr)
    controller = PersistentKnowledgeBaseController(base_dir=base_dir, manager=mgr, repo=repo)
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
    return KnowledgeBaseUseCase(controller=controller, repo=repo, ingestion=ingestion, storage=storage)


def default_kb_base_dir() -> str:
    return os.path.join("data", "kb")

