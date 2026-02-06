from __future__ import annotations

from typing import Any, List

from backend.modules.kb.domain.ports import TableChunkerPort
from backend.modules.kb.infrastructure.legacy_kb.splitters.splitter_table import TableSplitter


class LegacyTableChunker(TableChunkerPort):
    def split_table(
        self,
        *,
        text: str,
        kb_id: int,
        file_id: int,
        table_name: str,
        use_llm_summary: bool,
        max_rows_per_chunk: int,
        max_chars_per_chunk: int,
    ) -> List[Any]:
        return TableSplitter(
            table_name=table_name,
            use_llm_summary=bool(use_llm_summary),
            max_rows_per_chunk=int(max_rows_per_chunk),
            max_chars_per_chunk=int(max_chars_per_chunk),
        ).split(text, int(kb_id), int(file_id))

