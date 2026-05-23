from __future__ import annotations

from typing import Any

from backend.api.models import KBDocument, KnowledgeBase
from backend.shared.ids import format_document_id, format_kb_id


def kb_meta_to_api(meta: Any) -> KnowledgeBase:
    return KnowledgeBase(
        id=format_kb_id(int(meta.kb_id)),
        name=meta.name,
        description=meta.description,
        createdAt=int(meta.created_at_ms),
    )


def kb_document_to_api(meta: Any) -> KBDocument:
    return KBDocument(
        id=format_document_id(int(meta.document_id)),
        kbId=format_kb_id(int(meta.kb_id)),
        name=meta.filename,
        type=meta.mime_type,
        createdAt=int(meta.created_at_ms),
        chunkCount=int(meta.chunk_count),
        status=str(meta.status),
    )
