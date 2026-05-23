from __future__ import annotations

from typing import Any

from backend.modules.kb.domain.chunk_models import DocumentChunk
from backend.modules.kb.domain.chunk_serialization import metadata_to_document_chunk
from backend.modules.kb.domain.document_models import Document
from backend.modules.kb.domain.enums import DocumentStatus
from backend.modules.kb.domain.kb_models import KnowledgeBase


def kb_from_orm(row: Any) -> KnowledgeBase:
    """将 ORM 对象转换为领域模型 KnowledgeBase"""
    return KnowledgeBase(
        kb_id=int(row.kb_id),
        name=str(row.name),
        description=row.description,
        created_at_ms=int(row.created_at_ms),
        updated_at_ms=int(row.updated_at_ms),
    )


def file_from_orm(row: Any) -> Document:
    """将 ORM 对象转换为领域模型 Document"""
    return Document(
        kb_id=int(row.kb_id),
        document_id=int(row.file_id),
        filename=str(row.name),
        mime_type=str(row.mime_type),
        created_at_ms=int(row.created_at_ms),
        updated_at_ms=int(row.updated_at_ms),
        chunk_count=int(row.chunk_count),
        status=DocumentStatus.coerce(row.status),
        source_path=row.source_path,
    )


def chunk_from_orm(row: Any) -> DocumentChunk:
    """将 ORM 对象转换为领域模型 DocumentChunk"""
    import json

    raw_meta: Any = None
    if row.metadata_json:
        try:
            raw_meta = json.loads(row.metadata_json)
        except Exception:
            raw_meta = row.metadata_json
    restored = metadata_to_document_chunk(raw_meta)
    if restored is not None:
        return restored
    return DocumentChunk(
        document_id=int(row.file_id),
        chunk_index=int(row.chunk_index),
        segments=[],
        elements=[],
        created_at_ms=int(row.created_at_ms),
        updated_at_ms=int(row.updated_at_ms),
    )
