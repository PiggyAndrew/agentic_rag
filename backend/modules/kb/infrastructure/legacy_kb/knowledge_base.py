from __future__ import annotations

from typing import List, Dict, Tuple, Any, Optional
import logging
import numpy as np
from .embeddings import get_configured_embedder
from .rerank import get_configured_reranker, Reranker
from backend.modules.kb.domain.models import ChunkMetadata, FileChunk, FileInfo, FileStatus, KnowledgeBaseCreate, KnowledgeChunk, KnowledgeChunkUpsert, KnowledgeFileCreate, KnowledgeFilePatch
import json
import os
import shutil
import time

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager, init_sqlite_database
from backend.modules.kb.infrastructure.persistence.models import Base
from .knowledge_repository import KnowledgeNotFoundError, SqlAlchemyKnowledgeRepository
from .vector_store import ChromaVectorStore
from .services.embedding_text import compose_embedding_text
from .services.keyword_search import KeywordSearcher, tokenize_query
from .services.paths import KbPaths


logger = logging.getLogger(__name__)


class PersistentKnowledgeBaseController:
    def __init__(
        self,
        base_dir: str = "data/kb",
        embedder: Optional[Any] = None,
        reranker: Optional[Reranker] = None,
        *,
        manager: Optional[SqliteSessionManager] = None,
        repo: Optional[SqlAlchemyKnowledgeRepository] = None,
    ):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self._paths = KbPaths(self.base_dir)
        self._vstore = ChromaVectorStore(base_dir=self.base_dir)
        self._manager = manager or get_default_sqlite_manager()
        init_sqlite_database(manager=self._manager, metadatas=[Base.metadata])
        self._repository = repo or SqlAlchemyKnowledgeRepository(manager=self._manager)
        self._keyword_searcher = KeywordSearcher(manager=self._manager, repo=self._repository)
        self._embedder = embedder
        self._reranker = reranker

    def _kb_dir(self, kb_id: int) -> str:
        return self._paths.kb_dir(kb_id)

    def kb_dir(self, kb_id: int) -> str:
        return self._paths.kb_dir(kb_id)

    def assets_images_dir(self, kb_id: int, file_id: int) -> str:
        return self._paths.assets_images_dir(kb_id, file_id)

    def ensure_kb(self, kb_id: int) -> None:
        self._ensure_kb(kb_id)

    def find_file_id_by_name(self, kb_id: int, filename: str) -> int:
        self._ensure_kb(kb_id)
        name = (filename or "").strip()
        rows = self._repository.list_files(int(kb_id))
        row = next((r for r in rows if str(r.name) == name), None)
        if row is None:
            raise RuntimeError(f"文件未在知识库中登记：{name}")
        return int(row.file_id)

    def _ensure_kb(self, kb_id: int) -> None:
        self._paths.ensure_kb_dir(kb_id)
        self._ensure_kb_row(kb_id)

    def _ensure_kb_row(self, kb_id: int) -> None:
        existing = self._repository.get_kb(int(kb_id))
        if existing is not None:
            return
        created_at = self._paths.kb_created_at_ms(kb_id)
        self._repository.create_kb(
            KnowledgeBaseCreate(
                kb_id=int(kb_id),
                name=f"知识库 {kb_id}",
                description=None,
                created_at_ms=created_at,
                updated_at_ms=created_at,
            )
        )

    def createKnowledgeBase(self, kb_id: int, *, reset_sqlite: bool = True) -> None:
        self._paths.ensure_kb_dir(kb_id)
        if reset_sqlite:
            try:
                self._repository.delete_kb(int(kb_id))
            except KnowledgeNotFoundError:
                pass
            self._ensure_kb_row(kb_id)
        self._vstore.clear(kb_id)

    def deleteKnowledgeBase(self, kb_id: int) -> None:
        try:
            self._repository.delete_kb(int(kb_id))
        except KnowledgeNotFoundError:
            pass
        shutil.rmtree(self._paths.kb_dir(kb_id), ignore_errors=True)

    def add_file(self, kb_id: int, filename: str, chunk_count: int, status: FileStatus | str = FileStatus.done) -> FileInfo:
        self._ensure_kb(kb_id)
        existing_ids = [int(r.file_id) for r in self._repository.list_files(int(kb_id))]
        file_id = (max(existing_ids) + 1) if existing_ids else 1
        info = FileInfo(id=file_id, filename=filename, chunk_count=chunk_count, status=status)
        now_ms = int(time.time() * 1000)
        self._repository.create_file(
            int(kb_id),
            KnowledgeFileCreate(
                file_id=int(info.id),
                name=info.filename,
                mime_type=self._guess_mime_type(info.filename),
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
                chunk_count=int(info.chunk_count),
                status=info.status,
                source_path=None,
            ),
        )
        return info

    def deleteFile(self, kb_id: int, file_id: int) -> bool:
        self._ensure_kb(kb_id)
        existing = self._repository.get_file(int(kb_id), int(file_id))
        if existing is None:
            return False
        self._repository.delete_file(int(kb_id), int(file_id))
        self._vstore.delete_items(kb_id, {"file_id": int(file_id)})
        return True

    def close(self) -> None:
        v = getattr(self, "_vstore", None)
        close = getattr(v, "close", None) if v is not None else None
        if callable(close):
            close()

    def save_chunks(self, kb_id: int, file_id: int, chunks: List[KnowledgeChunk]) -> None:
        self._ensure_kb(kb_id)
        coerced: List[KnowledgeChunk] = []
        now_ms = int(time.time() * 1000)
        for i, c in enumerate(chunks or []):
            if isinstance(c, KnowledgeChunk):
                coerced.append(c)
                continue
            if isinstance(c, dict):
                meta = ChunkMetadata.coerce(c.get("metadata"))
                coerced.append(
                    KnowledgeChunk(
                        kb_id=int(kb_id),
                        file_id=int(file_id),
                        chunk_index=int(c.get("chunk_index", i)),
                        content=str(c.get("content", "") or ""),
                        metadata=meta,
                        created_at_ms=int(c.get("created_at_ms") or now_ms),
                        updated_at_ms=int(c.get("updated_at_ms") or now_ms),
                    )
                )
                continue
        chunks = coerced

        texts: List[str] = []
        vitems: List[Dict[str, Any]] = []
        non_empty_indices: List[int] = []

        for i, c in enumerate(chunks):
            content = str(c.content or "")
            texts.append(compose_embedding_text(content, c.metadata))
            if content.strip():
                non_empty_indices.append(i)
            vitems.append(
                {
                    "file_id": int(file_id),
                    "chunk_index": int(c.chunk_index),
                    "filename": self._filename_of(kb_id, file_id),
                    "metadata": (c.metadata.data if c.metadata is not None else None),
                    "preview": (content[:200] + "...") if len(content) > 200 else content,
                }
            )
        if non_empty_indices:
            to_embed = [texts[i] for i in non_empty_indices]
            try:
                embedder = self._embedder or get_configured_embedder()
                embs = embedder.embed_texts(to_embed)
                for k, i in enumerate(non_empty_indices):
                    vitems[i]["embedding"] = embs[k].tolist()
            except Exception as e:
                logger.warning("skip embedding due to error: %s", e)
        payload: List[KnowledgeChunkUpsert] = []
        for c in chunks:
            payload.append(
                KnowledgeChunkUpsert(
                    chunk_index=int(c.chunk_index),
                    content=str(c.content or ""),
                    metadata=(c.metadata.data if c.metadata is not None else None),
                    created_at_ms=int(c.created_at_ms or now_ms),
                    updated_at_ms=int(c.updated_at_ms or now_ms),
                )
            )
        self._repository.upsert_chunks(int(kb_id), int(file_id), payload)
        vitems_embedded = [vi for vi in vitems if "embedding" in vi]
        if vitems_embedded:
            self._vstore.delete_items(kb_id, {"file_id": int(file_id)})
            self._vstore.add_items(kb_id, vitems_embedded)
            self._repository.update_file(
                int(kb_id),
                int(file_id),
                KnowledgeFilePatch(
                    chunk_count=len(chunks),
                    status=FileStatus.vectorized,
                    updated_at_ms=now_ms,
                ),
            )
        else:
            self._repository.update_file(
                int(kb_id),
                int(file_id),
                KnowledgeFilePatch(
                    chunk_count=len(chunks),
                    status=FileStatus.chunked,
                    updated_at_ms=now_ms,
                ),
            )

    def _filename_of(self, kb_id: int, file_id: int) -> str:
        row = self._repository.get_file(int(kb_id), int(file_id))
        return row.name if row is not None else ""

    def _load_file_chunks(self, kb_id: int, file_id: int) -> List[FileChunk]:
        self._ensure_kb(kb_id)
        rows = self._repository.list_chunks(int(kb_id), int(file_id))
        out: List[FileChunk] = []
        for r in rows:
            out.append(
                FileChunk(
                    file_id=int(r.file_id),
                    chunk_index=int(r.chunk_index),
                    content=str(r.content or ""),
                    metadata=r.metadata,
                    embedding=None,
                )
            )
        return out

    def _tokenize_query_for_keyword_search(self, query: str) -> List[str]:
        return tokenize_query(query)

    def _keyword_search(self, kb_id: int, query: str, top_k: int = 5, exclude: Optional[set[Tuple[int, int]]] = None) -> List[Dict]:
        return self._keyword_searcher.search(kb_id, query, top_k=top_k, exclude=exclude)

    def _guess_mime_type(self, filename: str) -> str:
        lower = (filename or "").lower()
        if lower.endswith(".pdf"):
            return "application/pdf"
        if lower.endswith(".xlsx"):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return "application/octet-stream"

    def search(self, kb_id: int, query: str) -> List[Dict]:
        q = (query or "").strip()
        if not q:
            return []
        embedder = self._embedder or get_configured_embedder()
        q_vec = embedder.embed_text(q)
        semantic = self._vstore.query_embeddings(kb_id, q_vec, top_k=5)
        seen_pairs = {(int(r["file_id"]), int(r["chunk_index"])) for r in semantic}
        keyword = self._keyword_search(kb_id, q, top_k=5, exclude=seen_pairs)

        combined: List[Dict[str, Any]] = []
        combined.extend(semantic)
        combined.extend(keyword)
        if not combined:
            return []

        pairs_spec = [{"fileId": r["file_id"], "chunkIndex": r["chunk_index"]} for r in combined]
        full_chunks = self.readFileChunks(kb_id, pairs_spec)
        content_map: Dict[tuple[int, int], str] = {}
        meta_map: Dict[tuple[int, int], Any] = {}
        for ch in full_chunks:
            fid = int(ch.get("file_id"))
            idx = int(ch.get("chunk_index"))
            content_map[(fid, idx)] = ch.get("content", "")
            meta_map[(fid, idx)] = ch.get("metadata")

        def _load_content(fid: int, idx: int) -> str:
            return content_map.get((fid, idx), "")

        reranker: Reranker = self._reranker or get_configured_reranker()
        ranked = reranker.rerank(q, combined, _load_content, top_k=5)

        def _order_key_of(item: Dict[str, Any]) -> tuple:
            fid = int(item.get("file_id"))
            idx = int(item.get("chunk_index"))
            meta = meta_map.get((fid, idx)) or {}
            ok = meta.get("order_key") or []
            if isinstance(ok, list):
                try:
                    return tuple(int(x) for x in ok)
                except Exception:
                    pass
            return (fid, idx)

        ranked.sort(key=_order_key_of)
        return ranked[:5]

    def getFilesMeta(self, kb_id: int, file_ids: List[int]) -> List[Dict]:
        self._ensure_kb(kb_id)
        idset = {int(i) for i in (file_ids or [])}
        rows = self._repository.list_files(int(kb_id))
        out: List[Dict[str, Any]] = []
        for r in rows:
            if int(r.file_id) in idset:
                out.append({"id": int(r.file_id), "filename": r.name, "chunk_count": int(r.chunk_count), "status": str(r.status)})
        return out

    def readFileChunks(self, kb_id: int, chunks: List[Dict[str, int]]) -> List[Dict]:
        results: List[Dict] = []
        specs = chunks or []
        by_file: Dict[int, List[int]] = {}

        def _get_int_value(d: Dict[str, Any], keys: List[str]) -> Optional[int]:
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
            fid = _get_int_value(s, ["fileId", "file_id"])
            idx = _get_int_value(s, ["chunkIndex", "chunk_index"])
            if fid is None or idx is None:
                continue
            by_file.setdefault(fid, []).append(idx)

        rows = self._repository.list_files(int(kb_id))
        name_map = {int(r.file_id): r.name for r in rows}
        for fid, indices in by_file.items():
            chunks_all = self._load_file_chunks(kb_id, fid)
            want = set(indices)
            for ch in chunks_all:
                if ch.chunk_index in want:
                    item = {
                        "file_id": fid,
                        "chunk_index": ch.chunk_index,
                        "content": ch.content,
                        "filename": name_map.get(fid, "unknown"),
                    }
                    if ch.metadata:
                        item["metadata"] = ch.metadata.data
                    results.append(item)
        return results

    def listFilesPaginated(self, kb_id: int, page: int, page_size: int) -> List[Dict]:
        self._ensure_kb(kb_id)
        rows = self._repository.list_files(int(kb_id))
        start = page * page_size
        end = start + page_size
        out: List[Dict[str, Any]] = []
        for r in rows[start:end]:
            out.append({"id": int(r.file_id), "filename": r.name, "chunk_count": int(r.chunk_count), "status": str(r.status)})
        return out
