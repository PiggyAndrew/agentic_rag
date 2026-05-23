from __future__ import annotations

from backend.modules.kb.infrastructure.legacy_kb.ingestion import ingest_excel, ingest_pdf
from backend.modules.kb.infrastructure.legacy_kb.knowledge_base import PersistentKnowledgeBaseController
from backend.modules.kb.infrastructure.legacy_kb.knowledge_repository import (
    KnowledgeConflictError,
    KnowledgeNotFoundError,
    SqlAlchemyKnowledgeRepository,
)
from backend.modules.kb.infrastructure.adapters.vector_store_adapter import VectorStoreAdapter
from backend.modules.kb.infrastructure.adapters.embedding_adapter import EmbeddingAdapter
from backend.modules.kb.infrastructure.adapters.rerank_adapter import RerankAdapter
from backend.modules.kb.infrastructure.adapters.search_adapter import SearchAdapter
from backend.modules.kb.infrastructure.adapters.text_splitter_adapter import TextSplitterAdapter
from backend.modules.kb.infrastructure.adapters.kb_controller_adapter import KnowledgeBaseControllerAdapter
from backend.modules.kb.infrastructure.adapters.chunk_writer_adapter import ChunkWriterAdapter

__all__ = [
    "PersistentKnowledgeBaseController",
    "SqlAlchemyKnowledgeRepository",
    "KnowledgeConflictError",
    "KnowledgeNotFoundError",
    "ingest_pdf",
    "ingest_excel",
    "VectorStoreAdapter",
    "EmbeddingAdapter",
    "RerankAdapter",
    "SearchAdapter",
    "TextSplitterAdapter",
    "KnowledgeBaseControllerAdapter",
    "ChunkWriterAdapter",
]
