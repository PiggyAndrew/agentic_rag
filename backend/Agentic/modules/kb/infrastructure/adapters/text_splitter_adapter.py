from __future__ import annotations

from typing import Any, List

from backend.modules.kb.domain.ports import TextSplitterPort
from backend.modules.kb.infrastructure.legacy_kb.splitters.splitter_adaptive import AdaptiveSplitter


class TextSplitterAdapter(TextSplitterPort):
    def __init__(self, use_llm: bool = True):
        self._splitter = AdaptiveSplitter(use_llm=use_llm)

    def split(self, text: str, kb_id: int, document_id: int) -> List[Any]:
        return self._splitter.split(text, kb_id, document_id)
