from __future__ import annotations

import os
import time
from typing import List

from backend.modules.kb.domain.chunk_models import ChunkingInfo, DocumentChunk, ElementRefSegment
from backend.modules.kb.domain.element_models import TableElement
from backend.modules.kb.domain.enums import ChunkingStrategy, ElementType


def excel_table_name_from_path(excel_path: str) -> str:
    filename = excel_path.split("/")[-1].split("\\")[-1]
    return os.path.splitext(filename)[0]


def build_empty_excel_table_chunk(*, kb_id: int, document_id: int, table_name: str) -> List[DocumentChunk]:
    now_ms = int(time.time() * 1000)
    return [
        DocumentChunk(
            document_id=int(document_id),
            chunk_index=0,
            segments=[ElementRefSegment(ref_id="table_0", ref_type=ElementType.table)],
            elements=[
                TableElement(
                    id="table_0",
                    title=table_name,
                    markdown="[ExcelEmpty] 未读取到任何非空表格数据",
                    summary="未读取到任何非空表格数据",
                )
            ],
            structure_path=[table_name],
            chunking=ChunkingInfo(
                strategy=ChunkingStrategy.table_based,
                rule="empty_excel_table",
                generator="table_ingestion.build_empty_excel_table_chunk",
            ),
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
    ]
