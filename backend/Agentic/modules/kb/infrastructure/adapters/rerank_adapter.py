from __future__ import annotations

from typing import Any, List

from backend.modules.kb.domain.ports import RerankPort
from backend.modules.kb.infrastructure.legacy_kb.rerank import get_configured_reranker


class RerankAdapter(RerankPort):
    def __init__(self):
        self._reranker = get_configured_reranker()

    def rerank(self, query: str, documents: List[str], top_k: int) -> List[int]:
        if not documents:
            return []
        return self._reranker.rerank(query, documents, top_k)
