from __future__ import annotations

from typing import Any, List

from backend.modules.kb.domain.ports import EmbeddingPort
from backend.modules.kb.infrastructure.legacy_kb.embeddings import get_configured_embedder


class EmbeddingAdapter(EmbeddingPort):
    def __init__(self):
        self._embedder = get_configured_embedder()

    def embed_texts(self, texts: List[str]) -> List[Any]:
        if not texts:
            return []
        return self._embedder.embed_texts(texts)
