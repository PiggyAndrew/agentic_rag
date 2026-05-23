from __future__ import annotations

from typing import List, Dict, Tuple, Any, Optional
import logging
from .embeddings import get_configured_embedder
from .rerank import get_configured_reranker, Reranker
from backend.modules.kb.domain.chunk_models import DocumentChunk
from backend.modules.kb.domain.document_models import Document
from backend.modules.kb.domain.enums import DocumentStatus
from backend.modules.kb.domain.kb_models import KnowledgeBaseCreate
import os
import shutil
import time
import threading

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager, init_sqlite_database
from backend.modules.kb.infrastructure.adapters.chunk_writer_adapter import ChunkWriterAdapter
from backend.modules.kb.infrastructure.persistence.models import Base
from .knowledge_repository import KnowledgeNotFoundError, SqlAlchemyKnowledgeRepository
from .vector_store import ChromaVectorStore
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
        self._manager = manager or get_default_sqlite_manager()
        init_sqlite_database(manager=self._manager, metadatas=[Base.metadata])
        self._paths = KbPaths(self.base_dir)
        self._vstore = ChromaVectorStore(base_dir=self.base_dir)
        self._repository = repo or SqlAlchemyKnowledgeRepository(manager=self._manager)
        self._keyword_searcher = KeywordSearcher(manager=self._manager, repo=self._repository)
        self._embedder = embedder or get_configured_embedder()
        self._reranker = reranker
        self._chunk_writer = ChunkWriterAdapter(
            repo=self._repository,
            vstore=self._vstore,
            embedder=self._embedder,
        )
        self._file_locks: Dict[int, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def _kb_dir(self, kb_id: int) -> str:
        return self._paths.kb_dir(kb_id)

    def kb_dir(self, kb_id: int) -> str:
        return self._paths.kb_dir(kb_id)

    def assets_images_dir(self, kb_id: int, document_id: int) -> str:
        return self._paths.assets_images_dir(kb_id, document_id)

    def ensure_kb(self, kb_id: int) -> None:
        self._ensure_kb(kb_id)

    def find_document_id_by_name(self, kb_id: int, filename: str) -> int:
        self._ensure_kb(kb_id)
        name = (filename or "").strip()
        rows = self._repository.list_documents(int(kb_id))
        row = next((r for r in rows if str(r.filename) == name), None)
        if row is None:
            raise RuntimeError(f"文件未在知识库中登记：{name}")
        return int(row.document_id)

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

    def add_document(self, kb_id: int, filename: str, chunk_count: int, status: DocumentStatus | str = DocumentStatus.done) -> Document:
        self._ensure_kb(kb_id)
        existing_ids = [int(r.document_id) for r in self._repository.list_documents(int(kb_id))]
        document_id = (max(existing_ids) + 1) if existing_ids else 1
        now_ms = int(time.time() * 1000)
        document = Document(
            kb_id=int(kb_id),
            document_id=int(document_id),
            filename=filename,
            mime_type=self._guess_mime_type(filename),
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            chunk_count=int(chunk_count),
            status=DocumentStatus.coerce(status),
            source_path=None,
        )
        self._repository.create_document(int(kb_id), document)
        return document

    def deleteDocument(self, kb_id: int, document_id: int) -> bool:
        self._ensure_kb(kb_id)
        existing = self._repository.get_document(int(kb_id), int(document_id))
        if existing is None:
            return False
        self._repository.delete_document(int(kb_id), int(document_id))
        self._vstore.delete_items(kb_id, {"document_id": int(document_id)})
        return True

    def close(self) -> None:
        v = getattr(self, "_vstore", None)
        close = getattr(v, "close", None) if v is not None else None
        if callable(close):
            close()

    def save_document_chunks(self, kb_id: int, document_id: int, chunks: List[DocumentChunk]) -> bool:
        lock = self._file_locks.setdefault(int(document_id), threading.Lock())
        with lock:
            self._ensure_kb(kb_id)
            return self._chunk_writer.save_document_chunks(int(kb_id), int(document_id), chunks)

    def _load_document_chunks(self, kb_id: int, document_id: int) -> List[DocumentChunk]:
        self._ensure_kb(kb_id)
        return list(self._repository.list_document_chunks(int(kb_id), int(document_id)))

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

    def search(self, kb_id: int, query: str, top_k: int = 5) -> List[Dict]:
        def _document_id_of(item: Dict[str, Any]) -> int:
            return int(item.get("document_id") or item.get("file_id"))

        q = (query or "").strip()
        if not q:
            return []
        embedder = self._embedder or get_configured_embedder()
        q_vec = embedder.embed_text(q)
        semantic = self._vstore.query_embeddings(kb_id, q_vec, top_k=top_k)
        seen_pairs = {(_document_id_of(r), int(r["chunk_index"])) for r in semantic}
        keyword = self._keyword_search(kb_id, q, top_k=top_k, exclude=seen_pairs)

        combined: List[Dict[str, Any]] = []
        combined.extend(semantic)
        combined.extend(keyword)
        if not combined:
            return []

        pairs_spec = [{"documentId": _document_id_of(r), "chunkIndex": r["chunk_index"]} for r in combined]
        full_chunks = self.readDocumentChunks(kb_id, pairs_spec)
        content_map: Dict[tuple[int, int], str] = {}
        meta_map: Dict[tuple[int, int], Any] = {}
        for ch in full_chunks:
            document_id = int(ch.get("document_id"))
            chunk_index = int(ch.get("chunk_index"))
            content_map[(document_id, chunk_index)] = ch.get("content", "")
            meta_map[(document_id, chunk_index)] = ch.get("metadata")

        def _load_content(document_id: int, chunk_index: int) -> str:
            return content_map.get((document_id, chunk_index), "")

        reranker: Reranker = self._reranker or get_configured_reranker()
        ranked = reranker.rerank(q, combined, _load_content, top_k=top_k)

        def _order_key_of(item: Dict[str, Any]) -> tuple:
            document_id = _document_id_of(item)
            chunk_index = int(item.get("chunk_index"))
            meta = meta_map.get((document_id, chunk_index)) or {}
            ok = meta.get("order_key") or []
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
            row["document_id"] = int(row.get("document_id") or row.get("file_id"))
            row.pop("file_id", None)
            normalized.append(row)
        return normalized

    def getDocumentsMeta(self, kb_id: int, document_ids: List[int]) -> List[Dict]:
        self._ensure_kb(kb_id)
        idset = {int(i) for i in (document_ids or [])}
        rows = self._repository.list_documents(int(kb_id))
        out: List[Dict[str, Any]] = []
        for r in rows:
            if int(r.document_id) in idset:
                out.append({"id": int(r.document_id), "filename": r.filename, "chunk_count": int(r.chunk_count), "status": str(r.status)})
        return out

    def readDocumentChunks(self, kb_id: int, chunks: List[Dict[str, int]]) -> List[Dict]:
        results: List[Dict] = []
        specs = chunks or []
        by_document: Dict[int, List[int]] = {}

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
            document_id = _get_int_value(s, ["documentId", "document_id", "fileId", "file_id"])
            chunk_index = _get_int_value(s, ["chunkIndex", "chunk_index"])
            if document_id is None or chunk_index is None:
                continue
            by_document.setdefault(document_id, []).append(chunk_index)

        rows = self._repository.list_documents(int(kb_id))
        name_map = {int(r.document_id): r.filename for r in rows}
        for document_id, indices in by_document.items():
            chunks_all = self._load_document_chunks(kb_id, document_id)
            want = set(indices)
            for ch in chunks_all:
                if ch.chunk_index in want:
                    item = {
                        "document_id": document_id,
                        "chunk_index": ch.chunk_index,
                        "content": ch.ai_text(),
                        "filename": name_map.get(document_id, "unknown"),
                        "inline_text": ch.inline_text(),
                    }
                    results.append(item)
        return results

    def listDocumentsPaginated(self, kb_id: int, page: int, page_size: int) -> List[Dict]:
        self._ensure_kb(kb_id)
        rows = self._repository.list_documents(int(kb_id))
        start = page * page_size
        end = start + page_size
        out: List[Dict[str, Any]] = []
        for r in rows[start:end]:
            out.append({"id": int(r.document_id), "filename": r.filename, "chunk_count": int(r.chunk_count), "status": str(r.status)})
        return out
