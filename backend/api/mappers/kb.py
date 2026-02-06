from __future__ import annotations

from typing import Any

from backend.api.models import KBFile, KnowledgeBase
from backend.shared.ids import format_file_id, format_kb_id


def kb_meta_to_api(meta: Any) -> KnowledgeBase:
    return KnowledgeBase(
        id=format_kb_id(int(meta.kb_id)),
        name=meta.name,
        description=meta.description,
        createdAt=int(meta.created_at_ms),
    )


def kb_file_to_api(meta: Any) -> KBFile:
    return KBFile(
        id=format_file_id(int(meta.file_id)),
        kbId=format_kb_id(int(meta.kb_id)),
        name=meta.name,
        type=meta.mime_type,
        createdAt=int(meta.created_at_ms),
        chunkCount=int(meta.chunk_count),
        status=str(meta.status),
    )
