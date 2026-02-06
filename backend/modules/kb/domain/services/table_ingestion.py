from __future__ import annotations

import os
import time
from typing import List

from backend.modules.kb.domain.models import ChunkMetadata, KnowledgeChunk


def excel_table_name_from_path(excel_path: str) -> str:
    filename = excel_path.split("/")[-1].split("\\")[-1]
    return os.path.splitext(filename)[0]


def build_empty_excel_table_chunk(*, kb_id: int, file_id: int, table_name: str) -> List[KnowledgeChunk]:
    now_ms = int(time.time() * 1000)
    meta = ChunkMetadata.coerce(
        {"type": "table", "table_name": table_name, "sheet_name": "", "part_index": 1, "part_count": 1, "header": []}
    )
    return [
        KnowledgeChunk(
            kb_id=int(kb_id),
            file_id=int(file_id),
            chunk_index=0,
            content=f"[Table] {table_name}\n[ExcelEmpty] 未读取到任何非空表格数据",
            metadata=meta,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
    ]

