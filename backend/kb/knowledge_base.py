from typing import List, Dict, Tuple, Any, Optional
import numpy as np
from .embeddings import get_default_embedder
from .rerank import get_default_reranker, Reranker
from .types import (
    FileInfo,
    FileChunk,
    FileStatus,
    KnowledgeBaseCreate,
    KnowledgeChunkUpsert,
    KnowledgeFileCreate,
    KnowledgeFilePatch,
)
import json
import os
import re
import heapq
import shutil
import time

from sqlalchemy import select

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager, init_sqlite_database
from backend.kb.knowledge_models import KnowledgeChunkORM
from backend.kb.knowledge_repository import KnowledgeNotFoundError, SqlAlchemyKnowledgeRepository
from backend.kb.vector_store import ChromaVectorStore



class PersistentKnowledgeBaseController:
    """持久化知识库控制器：元数据与片段持久化到 SQLite，向量索引保留原实现。"""

    def __init__(
        self,
        base_dir: str = "data/kb",
        embedder: Optional[Any] = None,
        *,
        manager: Optional[SqliteSessionManager] = None,
        repo: Optional[SqlAlchemyKnowledgeRepository] = None,
    ):
        """初始化控制器并确保基础目录存在"""
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self._embedder = embedder or get_default_embedder()
       
        self._vstore = ChromaVectorStore(base_dir=self.base_dir)
       
        self._manager = manager or get_default_sqlite_manager()
        init_sqlite_database(manager=self._manager)
        self._repository = repo or SqlAlchemyKnowledgeRepository(manager=self._manager)

    def _kb_dir(self, kb_id: int) -> str:
        """获取指定知识库的根目录路径"""
        return os.path.join(self.base_dir, str(kb_id))

    def _ensure_kb(self, kb_id: int) -> None:
        """确保知识库目录与必要资源存在"""
        os.makedirs(self._kb_dir(kb_id), exist_ok=True)
        self._ensure_kb_row(kb_id)

    def _ensure_kb_row(self, kb_id: int) -> None:
        existing = self._repository.get_kb(int(kb_id))
        if existing is not None:
            return
        created_at = int(os.path.getmtime(self._kb_dir(kb_id)) * 1000) if os.path.exists(self._kb_dir(kb_id)) else int(time.time() * 1000)
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
        """创建或重置一个知识库的基础目录与索引"""
        os.makedirs(self._kb_dir(kb_id), exist_ok=True)
        if reset_sqlite:
            try:
                self._repository.delete_kb(int(kb_id))
            except KnowledgeNotFoundError:
                pass
            self._ensure_kb_row(kb_id)
        self._vstore.clear(kb_id)

    def deleteKnowledgeBase(self, kb_id: int) -> None:
        """删除整个知识库目录，包括文件索引、片段与向量存储"""
        try:
            self._repository.delete_kb(int(kb_id))
        except KnowledgeNotFoundError:
            pass
        shutil.rmtree(self._kb_dir(kb_id), ignore_errors=True)

    def add_file(self, kb_id: int, filename: str, chunk_count: int, status: FileStatus | str = FileStatus.done) -> FileInfo:
        """新增文件元信息并返回创建后的 `FileInfo`"""
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
        """删除指定文件的元信息、片段与其向量索引"""
        self._ensure_kb(kb_id)
        existing = self._repository.get_file(int(kb_id), int(file_id))
        if existing is None:
            return False
        self._repository.delete_file(int(kb_id), int(file_id))
        self._vstore.delete_items(kb_id, {"file_id": int(file_id)})
        return True

    def save_chunks(self, kb_id: int, file_id: int, chunks: List[Any]) -> None:
        """将片段内容持久化到 SQLite，并同步向量索引。"""
        self._ensure_kb(kb_id)
        texts: List[str] = []
        normalized: List[Dict[str, Any]] = []
        vitems: List[Dict[str, Any]] = []
        non_empty_indices: List[int] = []
        for i, c in enumerate(chunks):
            if isinstance(c, str):
                normalized.append({"file_id": file_id, "chunk_index": i, "content": c})
                texts.append(c)
                if c.strip():
                    non_empty_indices.append(i)
                vitems.append({
                    "file_id": file_id,
                    "chunk_index": i,
                    "filename": self._filename_of(kb_id, file_id),
                    "metadata": None,
                    "preview": (c[:200] + "...") if len(c) > 200 else c,
                })
            elif isinstance(c, dict):
                content = c.get("content", "")
                normalized.append({
                    "file_id": file_id,
                    "chunk_index": i,
                    "content": content,
                    "metadata": c.get("metadata"),
                })
                texts.append(content)
                if content.strip():
                    non_empty_indices.append(i)
                vitems.append({
                    "file_id": file_id,
                    "chunk_index": i,
                    "filename": self._filename_of(kb_id, file_id),
                    "metadata": c.get("metadata"),
                    "preview": (content[:200] + "...") if len(content) > 200 else content,
                })
            else:
                s = str(c)
                normalized.append({"file_id": file_id, "chunk_index": i, "content": s})
                texts.append(s)
                if s.strip():
                    non_empty_indices.append(i)
                vitems.append({
                    "file_id": file_id,
                    "chunk_index": i,
                    "filename": self._filename_of(kb_id, file_id),
                    "metadata": None,
                    "preview": (s[:200] + "...") if len(s) > 200 else s,
                })
        try:
            if non_empty_indices:
                # 仅对非空文本进行嵌入，避免服务端拒绝空字符串导致失败
                to_embed = [normalized[i]["content"] for i in non_empty_indices]
                embs = self._embedder.embed_texts(to_embed)
                for k, i in enumerate(non_empty_indices):
                    normalized[i]["embedding"] = embs[k].tolist()
                    vitems[i]["embedding"] = embs[k].tolist()
        except Exception:
            raise
        now_ms = int(time.time() * 1000)
        payload: List[KnowledgeChunkUpsert] = []
        for r in normalized:
            payload.append(
                KnowledgeChunkUpsert(
                    chunk_index=int(r.get("chunk_index")),
                    content=str(r.get("content", "")),
                    metadata=r.get("metadata"),
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                )
            )
        self._repository.upsert_chunks(int(kb_id), int(file_id), payload)
        try:
            # 仅追加有嵌入的条目，避免全部因嵌入失败而不写入向量库
            vitems_embedded = [vi for vi in vitems if "embedding" in vi]
            if vitems_embedded:
                # 先删除旧的向量数据，支持重新解析
                self._vstore.delete_items(kb_id, {"file_id": int(file_id)})
                self._vstore.add_items(kb_id, vitems_embedded)
                self._repository.update_file(
                    int(kb_id),
                    int(file_id),
                    KnowledgeFilePatch(
                        chunk_count=len(normalized),
                        status=FileStatus.vectorized,
                        updated_at_ms=now_ms,
                    ),
                )
            else:
                self._repository.update_file(
                    int(kb_id),
                    int(file_id),
                    KnowledgeFilePatch(
                        chunk_count=len(normalized),
                        status=FileStatus.chunked,
                        updated_at_ms=now_ms,
                    ),
                )
        except Exception:
            raise

    def _filename_of(self, kb_id: int, file_id: int) -> str:
        """根据文件ID获取文件名"""
        row = self._repository.get_file(int(kb_id), int(file_id))
        return row.name if row is not None else ""

    def _load_file_chunks(self, kb_id: int, file_id: int) -> List[FileChunk]:
        """加载某个文件的全部片段为 `FileChunk` 列表"""
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
        """将查询拆解为用于机械关键词检索的 token 列表。"""
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

    def _keyword_search(self, kb_id: int, query: str, top_k: int = 5, exclude: Optional[set[Tuple[int, int]]] = None) -> List[Dict]:
        """基于片段内容做机械关键词检索，返回与向量检索同结构的候选列表。"""
        q = (query or "").strip()
        if not q:
            return []
        tokens = self._tokenize_query_for_keyword_search(q)
        if not tokens:
            return []
        self._ensure_kb(kb_id)
        file_rows = self._repository.list_files(int(kb_id))
        name_map = {int(r.file_id): str(r.name) for r in file_rows}

        exclude_set: set[Tuple[int, int]] = exclude or set()
        heap: List[Tuple[float, int, int, Dict[str, Any]]] = []
        counter = 0

        q_lower = q.lower()
        token_lowers = [t.lower() for t in tokens]
        is_ascii = [bool(re.fullmatch(r"[A-Za-z0-9_]+", t)) for t in tokens]

        with self._manager.session_scope() as session:
            rows = session.execute(select(KnowledgeChunkORM).where(KnowledgeChunkORM.kb_id == int(kb_id))).scalars().all()
        for r in rows:
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
            metadata = None
            if r.metadata_json:
                try:
                    metadata = json.loads(r.metadata_json)
                except Exception:
                    metadata = r.metadata_json

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

    def _guess_mime_type(self, filename: str) -> str:
        lower = (filename or "").lower()
        if lower.endswith(".pdf"):
            return "application/pdf"
        if lower.endswith(".xlsx"):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return "application/octet-stream"

    def search(self, kb_id: int, query: str) -> List[Dict]:
        """混合召回：语义检索 5 条 + 关键词检索 5 条，合并后 rerank 输出 8 条。

        - Reranker 通过 `get_default_reranker()` 选择：Noop 或 CrossEncoder。
        - 使用 provider 模式统一封装，便于扩展与替换实现。
        """
        q = (query or "").strip()
        if not q:
            return []
        q_vec = self._embedder.embed_text(q)

        reranker: Reranker = get_default_reranker()
        semantic = self._vstore.query_embeddings(kb_id, q_vec, top_k=5)
        seen_pairs = {(int(r["file_id"]), int(r["chunk_index"])) for r in semantic}
        keyword = self._keyword_search(kb_id, q, top_k=5, exclude=seen_pairs)

        combined: List[Dict[str, Any]] = []
        combined.extend(semantic)
        if not combined:
            return []

        # 构造内容加载器（批量读取避免重复 IO）
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
        """根据文件ID数组返回对应的元信息"""
        self._ensure_kb(kb_id)
        idset = {int(i) for i in (file_ids or [])}
        rows = self._repository.list_files(int(kb_id))
        out: List[Dict[str, Any]] = []
        for r in rows:
            if int(r.file_id) in idset:
                out.append(
                    {
                        "id": int(r.file_id),
                        "filename": r.name,
                        "chunk_count": int(r.chunk_count),
                        "status": str(r.status),
                    }
                )
        return out

    def readFileChunks(self, kb_id: int, chunks: List[Dict[str, int]]) -> List[Dict]:
        """读取指定的 `fileId`/`file_id` 与 `chunkIndex`/`chunk_index` 片段内容"""
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
        """分页列出文件元信息"""
        self._ensure_kb(kb_id)
        rows = self._repository.list_files(int(kb_id))
        start = page * page_size
        end = start + page_size
        out: List[Dict[str, Any]] = []
        for r in rows[start:end]:
            out.append(
                {
                    "id": int(r.file_id),
                    "filename": r.name,
                    "chunk_count": int(r.chunk_count),
                    "status": str(r.status),
                }
            )
        return out
