from __future__ import annotations

import heapq
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from backend.database.sqlite import SqliteSessionManager
from backend.modules.kb.infrastructure.persistence.models import KnowledgeChunkORM
from backend.modules.kb.infrastructure.legacy_kb.knowledge_repository import SqlAlchemyKnowledgeRepository


def tokenize_query(query: str) -> List[str]:
    q = (query or "").strip()
    if not q:
        return []
    out: List[str] = []
    seen = set()
    for m in re.finditer(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", q):
        t = (m.group(0) or "").strip()
        if not t:
            continue
        if re.fullmatch(r"[A-Za-z0-9_]+", t) and len(t) < 2:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


class KeywordSearcher:
    def __init__(self, manager: SqliteSessionManager, repo: SqlAlchemyKnowledgeRepository):
        self._manager = manager
        self._repo = repo

    def search(
        self,
        kb_id: int,
        query: str,
        *,
        top_k: int = 5,
        exclude: Optional[set[Tuple[int, int]]] = None,
    ) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []
        tokens = tokenize_query(q)
        if not tokens:
            return []
        document_rows = self._repo.list_documents(int(kb_id))
        name_map = {int(r.document_id): str(r.filename) for r in document_rows}

        exclude_set: set[Tuple[int, int]] = exclude or set()
        heap: List[Tuple[float, int, int, Dict[str, Any]]] = []
        counter = 0

        q_lower = q.lower()
        token_lowers = [t.lower() for t in tokens]
        is_ascii = [bool(re.fullmatch(r"[A-Za-z0-9_]+", t)) for t in tokens]

        stmt = (
            select(
                KnowledgeChunkORM.file_id,
                KnowledgeChunkORM.chunk_index,
                KnowledgeChunkORM.content,
                KnowledgeChunkORM.metadata_json,
            )
            .where(KnowledgeChunkORM.kb_id == int(kb_id))
        )

        with self._manager.session_scope() as session:
            for r in session.execute(stmt):
                document_id = int(r.file_id)
                chunk_index = int(r.chunk_index)
                if (document_id, chunk_index) in exclude_set:
                    continue
                content = str(r.content or "")
                if not content.strip():
                    continue
                content_lower = content.lower()

                score = 0.0
                for i, t in enumerate(tokens):
                    if is_ascii[i]:
                        c = content_lower.count(token_lowers[i])
                    else:
                        c = content.count(t)
                    score += float(min(c, 3))
                if q_lower and q_lower in content_lower:
                    score += 5.0
                if score <= 0:
                    continue

                preview = (content[:200] + "...") if len(content) > 200 else content
                metadata: Any = None
                raw_meta = r.metadata_json
                if raw_meta:
                    try:
                        metadata = json.loads(raw_meta)
                    except Exception:
                        metadata = raw_meta

                item = {
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "filename": name_map.get(document_id, "unknown"),
                    "score": score,
                    "preview": preview,
                    "metadata": metadata,
                }

                counter += 1
                key = (score, -len(content), counter, item)
                if len(heap) < int(top_k):
                    heapq.heappush(heap, key)
                else:
                    if key > heap[0]:
                        heapq.heapreplace(heap, key)

        heap.sort(reverse=True)
        return [it for _, __, ___, it in heap]

    def get_documents_meta(self, kb_id: int, document_ids: List[int]) -> List[Dict[str, Any]]:
        document_rows = self._repo.list_documents(int(kb_id))
        document_map = {int(r.document_id): r for r in document_rows}
        
        result = []
        for document_id in document_ids:
            if document_id in document_map:
                f = document_map[document_id]
                result.append({
                    "document_id": int(f.document_id),
                    "document_name": str(f.filename),
                    "mime_type": str(f.mime_type),
                    "created_at": int(f.created_at_ms),
                    "updated_at": int(f.updated_at_ms),
                })
        return result

    def read_document_chunks(self, kb_id: int, chunks: List[Dict[str, int]]) -> List[Dict[str, Any]]:
        result = []
        
        stmt = (
            select(
                KnowledgeChunkORM.file_id,
                KnowledgeChunkORM.chunk_index,
                KnowledgeChunkORM.content,
                KnowledgeChunkORM.metadata_json,
            )
            .where(KnowledgeChunkORM.kb_id == int(kb_id))
        )
        
        chunk_map = {}
        with self._manager.session_scope() as session:
            for r in session.execute(stmt):
                document_id = int(r.file_id)
                chunk_index = int(r.chunk_index)
                chunk_map[(document_id, chunk_index)] = {
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "content": str(r.content or ""),
                    "metadata": json.loads(r.metadata_json) if r.metadata_json else None,
                }
        
        for chunk_req in chunks:
            document_id = chunk_req.get("documentId")
            chunk_index = chunk_req.get("chunkIndex")
            if (document_id, chunk_index) in chunk_map:
                result.append(chunk_map[(document_id, chunk_index)])
        
        return result

    def list_documents_paginated(self, kb_id: int, page: int, page_size: int) -> List[Dict[str, Any]]:
        document_rows = self._repo.list_documents(int(kb_id))
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_rows = document_rows[start_idx:end_idx]
        
        result = []
        for f in paginated_rows:
            result.append({
                "document_id": int(f.document_id),
                "document_name": str(f.filename),
                "mime_type": str(f.mime_type),
                "created_at": int(f.created_at_ms),
                "updated_at": int(f.updated_at_ms),
            })
        
        return result
