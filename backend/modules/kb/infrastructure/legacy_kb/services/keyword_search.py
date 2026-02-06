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
    def __init__(self, *, manager: SqliteSessionManager, repo: SqlAlchemyKnowledgeRepository):
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
        file_rows = self._repo.list_files(int(kb_id))
        name_map = {int(r.file_id): str(r.name) for r in file_rows}

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
                fid = int(r.file_id)
                idx = int(r.chunk_index)
                if (fid, idx) in exclude_set:
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
                    "file_id": fid,
                    "chunk_index": idx,
                    "filename": name_map.get(fid, "unknown"),
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

