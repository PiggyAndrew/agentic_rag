from __future__ import annotations

import os
from typing import Optional

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager
from backend.modules.kb.application.services.document_ingestion import DocumentIngestionService
from backend.modules.kb.application.usecase import KnowledgeBaseUseCase
from backend.modules.kb.application.usecase_search import KnowledgeSearchUseCase
from backend.modules.kb.infrastructure.adapters.excel_text_extractor_openpyxl import OpenpyxlExcelTextExtractor
from backend.modules.kb.infrastructure.adapters.image_captioner_legacy import LegacyImageCaptioner
from backend.modules.kb.infrastructure.adapters.kb_document_storage_local import LocalKbDocumentStorage
from backend.modules.kb.infrastructure.adapters.pdf_markdown_extractor_factory import build_pdf_markdown_extractor
from backend.modules.kb.infrastructure.adapters.table_chunker_legacy import LegacyTableChunker
from backend.modules.kb.infrastructure.legacy_kb.knowledge_repository import SqlAlchemyKnowledgeRepository
from backend.modules.kb.infrastructure.adapters.vector_store_adapter import VectorStoreAdapter
from backend.modules.kb.infrastructure.adapters.embedding_adapter import EmbeddingAdapter
from backend.modules.kb.infrastructure.adapters.rerank_adapter import RerankAdapter
from backend.modules.kb.infrastructure.adapters.search_adapter import SearchAdapter
from backend.modules.kb.infrastructure.adapters.text_splitter_adapter import TextSplitterAdapter
from backend.modules.kb.infrastructure.adapters.kb_controller_adapter import KnowledgeBaseControllerAdapter
from backend.modules.kb.infrastructure.adapters.chunk_writer_adapter import ChunkWriterAdapter


def build_kb_usecase(*, manager: Optional[SqliteSessionManager] = None, base_dir: str = "datas/knowledgeRepositories") -> KnowledgeBaseUseCase:
    mgr = manager or get_default_sqlite_manager()
    repo = SqlAlchemyKnowledgeRepository(manager=mgr)
    
    controller = KnowledgeBaseControllerAdapter(base_dir=base_dir, repo=repo)
    storage = LocalKbDocumentStorage(kb_dir_resolver=controller)
    
    vstore = VectorStoreAdapter(base_dir=base_dir)
    embedder = EmbeddingAdapter()
    reranker = RerankAdapter()
    search = SearchAdapter(repo=repo, manager=mgr, vstore=vstore, embedder=embedder, reranker=reranker)
    
    chunk_writer = ChunkWriterAdapter(repo=repo, vstore=vstore, embedder=embedder)
    
    ingestion = DocumentIngestionService(
        document_resolver=controller,
        asset_paths=controller,
        chunk_writer=chunk_writer,
        pdf_extractor=build_pdf_markdown_extractor(),
        image_captioner=LegacyImageCaptioner(),
        excel_text_extractor=OpenpyxlExcelTextExtractor(),
        table_chunker=LegacyTableChunker(),
        text_splitter=TextSplitterAdapter(),
    )
    
    search_usecase = KnowledgeSearchUseCase(controller=controller, repo=repo, search_port=search)
    
    return KnowledgeBaseUseCase(controller=controller, repo=repo, ingestion=ingestion, storage=storage, search_usecase=search_usecase, vstore=vstore)


def default_kb_base_dir() -> str:
    from backend.modules.config.infrastructure.boot_config import get_boot_config
    return get_boot_config().KB_ROOT_DIR
