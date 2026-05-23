from __future__ import annotations

import os
from typing import Any, Dict, List

from backend.modules.kb.domain.ports import VectorStorePort
from backend.modules.kb.infrastructure.legacy_kb.vector_store import ChromaVectorStore


class VectorStoreAdapter(VectorStorePort):
    def __init__(self, base_dir: str = "data/kb"):
        self._vstore = ChromaVectorStore(base_dir=base_dir)

    def add(self, kb_id: int, chunks: List[Any]) -> None:
        items = []
        for chunk in chunks:
            document_id = chunk.get("document_id")
            storage_document_id = document_id if document_id is not None else chunk.get("file_id")
            item = {
                "document_id": document_id if document_id is not None else storage_document_id,
                "chunk_index": chunk.get("chunk_index"),
                "content": chunk.get("content"),
                "metadata": chunk.get("metadata"),
                "embedding": chunk.get("embedding"),
            }
            items.append(item)
        if items:
            self._vstore.add_items(kb_id, items)

    def search(self, kb_id: int, query: str, top_k: int) -> List[Any]:
        import numpy as np

        from backend.modules.kb.infrastructure.legacy_kb.embeddings import get_configured_embedder

        embedder = get_configured_embedder()
        query_vec = embedder.embed_texts([query])[0]
        results = self._vstore.query_embeddings(kb_id, np.array(query_vec), top_k=top_k)
        return [
            {
                "document_id": r.get("document_id", r.get("file_id")),
                "chunk_index": r.get("chunk_index"),
                "content": r.get("preview"),
                "score": r.get("score", 0.0),
                "metadata": r.get("metadata"),
            }
            for r in results
        ]

    def delete_by_filter(self, kb_id: int, filters: Dict[str, Any]) -> None:
        self._vstore.delete_items(kb_id, filters)

    def clear(self, kb_id: int) -> None:
        self._vstore.clear(kb_id)
