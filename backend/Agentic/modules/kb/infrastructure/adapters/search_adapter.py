from __future__ import annotations

from typing import Any, Dict, List

from backend.database.sqlite import SqliteSessionManager
from backend.modules.kb.domain.chunk_serialization import document_chunk_to_metadata
from backend.modules.kb.domain.ports import SearchPort
from backend.modules.kb.infrastructure.legacy_kb.services.keyword_search import KeywordSearcher


class SearchAdapter(SearchPort):
    def __init__(
        self,
        repo: Any,
        manager: SqliteSessionManager,
        vstore: Any,
        embedder: Any,
        reranker: Any,
    ):
        self._keyword_searcher = KeywordSearcher(manager, repo)
        self._vstore = vstore
        self._embedder = embedder
        self._reranker = reranker
        self._repo = repo

    def search(self, kb_id: int, query: str, top_k: int) -> List[Any]:
        def _document_id_of(item: Dict[str, Any]) -> int:
            return int(item.get("document_id") or item.get("file_id"))

        q = (query or "").strip()
        if not q:
            return []
        semantic = self._vstore.search(kb_id, q, top_k)
        seen_pairs = {(_document_id_of(r), int(r["chunk_index"])) for r in semantic}
        keyword = self._keyword_searcher.search(kb_id, q, top_k=top_k, exclude=seen_pairs)

        combined: List[Dict[str, Any]] = []
        combined.extend(semantic)
        combined.extend(keyword)
        if not combined:
            return []

        pairs_spec = [{"documentId": _document_id_of(r), "chunkIndex": r["chunk_index"]} for r in combined]
        full_chunks = self.read_document_chunks(kb_id, pairs_spec)
        content_map: Dict[tuple[int, int], str] = {}
        meta_map: Dict[tuple[int, int], Any] = {}
        for ch in full_chunks:
            document_id = int(ch.get("document_id"))
            chunk_index = int(ch.get("chunk_index"))
            content_map[(document_id, chunk_index)] = ch.get("content", "")
            meta = ch.get("metadata")
            if meta is not None and hasattr(meta, "data"):
                meta_map[(document_id, chunk_index)] = meta.data
            else:
                meta_map[(document_id, chunk_index)] = meta

        def _load_content(document_id: int, chunk_index: int) -> str:
            return content_map.get((document_id, chunk_index), "")

        ranked = self._reranker._reranker.rerank(q, combined, _load_content, top_k)

        def _order_key_of(item: Dict[str, Any]) -> tuple:
            document_id = _document_id_of(item)
            chunk_index = int(item.get("chunk_index"))
            meta = meta_map.get((document_id, chunk_index))
            ok = None
            if meta is not None:
                if isinstance(meta, dict):
                    ok = meta.get("order_key")
                else:
                    ok = meta.data.get("order_key") if hasattr(meta, "data") else None
            if ok is None:
                ok = []
            if isinstance(ok, list):
                try:
                    return tuple(int(x) for x in ok)
                except Exception:
                    pass
            return (document_id, chunk_index)

        ranked.sort(key=_order_key_of)
        normalized: List[Dict[str, Any]] = []
        for item in ranked[:top_k]:
            row = dict(item)
            row["document_id"] = _document_id_of(row)
            row.pop("file_id", None)
            normalized.append(row)
        return normalized

    def get_documents_meta(self, kb_id: int, document_ids: List[int]) -> List[Any]:
        return self._keyword_searcher.get_documents_meta(kb_id, document_ids)

    def read_document_chunks(self, kb_id: int, chunks: List[Dict[str, int]]) -> List[Any]:
        results: List[Dict] = []
        specs = chunks or []
        by_document: Dict[int, List[int]] = {}

        def _get_int_value(d: Dict[str, Any], keys: List[str]) -> Any:
            for k in keys:
                v = d.get(k)
                if v is None:
                    continue
                try:
                    return int(v)
                except (TypeError, ValueError):
                    continue
            return None

        for s in specs:
            document_id = _get_int_value(s, ["documentId", "document_id"])
            chunk_index = _get_int_value(s, ["chunkIndex", "chunk_index"])
            if document_id is None or chunk_index is None:
                continue
            by_document.setdefault(document_id, []).append(chunk_index)

        rows = self._repo.list_documents(int(kb_id))
        name_map = {int(r.document_id): r.filename for r in rows}
        for document_id, indices in by_document.items():
            chunks_all = self._repo.list_document_chunks(int(kb_id), document_id)
            want = set(indices)
            for ch in chunks_all:
                if int(ch.chunk_index) in want:
                    item = {
                        "document_id": document_id,
                        "chunk_index": int(ch.chunk_index),
                        "content": ch.ai_text(),
                        "filename": name_map.get(document_id, "unknown"),
                        "inline_text": ch.inline_text(),
                        "ai_text": ch.ai_text(),
                        "metadata": document_chunk_to_metadata(ch),
                    }
                    results.append(item)
        return results

    def list_documents_paginated(self, kb_id: int, page: int, page_size: int) -> List[Any]:
        rows = self._repo.list_documents(int(kb_id))
        start = page * page_size
        end = start + page_size
        out: List[Dict[str, Any]] = []
        for r in rows[start:end]:
            out.append(
                {
                    "id": int(r.document_id),
                    "filename": r.filename,
                    "chunk_count": int(r.chunk_count),
                    "status": str(r.status),
                }
            )
        return out
