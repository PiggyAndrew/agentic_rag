from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional
import numpy as np
from .embeddings import get_default_embedder
from .rerank import get_default_reranker, Reranker
from .vector_store import LocalVectorStore
from .types import FileMeta
import json
import os
import re
import heapq
import shutil


@dataclass
class FileChunk:
    """文件片段数据结构"""

    file_id: int
    chunk_index: int
    content: str
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None


@dataclass
class FileInfo:
    """文件元信息数据结构"""

    id: int
    filename: str
    chunk_count: int
    status: str = "done"


class PersistentKnowledgeBaseController:
    """持久化知识库控制器：基于文件系统存储文件与片段

    - 根目录结构：`data/kb/{kb_id}/`
      - `files.json`：文件列表与元信息
      - `chunks/{file_id}.json`：对应文件的片段内容数组
    """

    def __init__(self, base_dir: str = "data/kb", embedder: Optional[Any] = None):
        """初始化控制器并确保基础目录存在"""
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self._embedder = embedder or get_default_embedder()
        self._vstore = LocalVectorStore(base_dir=self.base_dir)

    def _kb_dir(self, kb_id: int) -> str:
        """获取指定知识库的根目录路径"""
        return os.path.join(self.base_dir, str(kb_id))

    def _files_path(self, kb_id: int) -> str:
        """获取文件元信息存储路径"""
        return os.path.join(self._kb_dir(kb_id), "files.json")

    def _chunks_dir(self, kb_id: int) -> str:
        """获取片段存储目录路径"""
        return os.path.join(self._kb_dir(kb_id), "chunks")

    def _ensure_kb(self, kb_id: int) -> None:
        """确保知识库目录与必要文件存在"""
        kb_dir = self._kb_dir(kb_id)
        chunks_dir = self._chunks_dir(kb_id)
        os.makedirs(chunks_dir, exist_ok=True)
        files_path = self._files_path(kb_id)
        if not os.path.exists(files_path):
            with open(files_path, "w", encoding="utf-8") as f:
                json.dump({"files": [], "next_id": 1}, f, ensure_ascii=False, indent=2)

    def createKnowledgeBase(self, kb_id: int) -> None:
        """创建或重置一个知识库的基础目录与索引"""
        os.makedirs(self._kb_dir(kb_id), exist_ok=True)
        self._ensure_kb(kb_id)
        with open(self._files_path(kb_id), "w", encoding="utf-8") as f:
            json.dump({"files": [], "next_id": 1}, f, ensure_ascii=False, indent=2)
        self._vstore.clear(kb_id)

    def deleteKnowledgeBase(self, kb_id: int) -> None:
        """删除整个知识库目录，包括文件索引、片段与向量存储"""
        shutil.rmtree(self._kb_dir(kb_id), ignore_errors=True)

    def _load_files(self, kb_id: int) -> Dict:
        """加载文件列表与下一个可用ID"""
        self._ensure_kb(kb_id)
        with open(self._files_path(kb_id), "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_files(self, kb_id: int, data: Dict) -> None:
        """保存文件列表与下一个可用ID"""
        with open(self._files_path(kb_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_file(self, kb_id: int, filename: str, chunk_count: int, status: str = "done") -> FileInfo:
        """新增文件元信息并返回创建后的 `FileInfo`"""
        meta = self._load_files(kb_id)
        file_id = meta.get("next_id", 1)
        info = FileInfo(id=file_id, filename=filename, chunk_count=chunk_count, status=status)
        meta["files"].append(FileMeta(id=info.id, filename=info.filename, chunk_count=info.chunk_count, status=info.status).to_dict())
        meta["next_id"] = file_id + 1
        self._save_files(kb_id, meta)
        return info

    def deleteFile(self, kb_id: int, file_id: int) -> bool:
        """删除指定文件的元信息、片段与其向量索引"""
        meta = self._load_files(kb_id)
        files = meta.get("files", [])
        new_files = [f for f in files if int(f.get("id")) != int(file_id)]
        if len(new_files) == len(files):
            return False
        meta["files"] = new_files
        self._save_files(kb_id, meta)
        chunk_path = os.path.join(self._chunks_dir(kb_id), f"{int(file_id)}.json")
        if os.path.exists(chunk_path):
            os.remove(chunk_path)
        self._vstore.delete_items(kb_id, {"file_id": int(file_id)})
        return True

    def save_chunks(self, kb_id: int, file_id: int, chunks: List[Any]) -> None:
        """将片段内容持久化到 `chunks/{file_id}.json`

        - 支持字符串片段或包含 `content` 与可选 `metadata` 的字典
        """
        self._ensure_kb(kb_id)
        path = os.path.join(self._chunks_dir(kb_id), f"{file_id}.json")
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
            # 失败时跳过嵌入，不影响片段持久化
            pass
        with open(path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        try:
            # 仅追加有嵌入的条目，避免全部因嵌入失败而不写入向量库
            vitems_embedded = [vi for vi in vitems if "embedding" in vi]
            if vitems_embedded:
                # 先删除旧的向量数据，支持重新解析
                self._vstore.delete_items(kb_id, {"file_id": int(file_id)})
                self._vstore.add_items(kb_id, vitems_embedded)
        except Exception:
            pass

    def _filename_of(self, kb_id: int, file_id: int) -> str:
        """根据文件ID获取文件名"""
        meta = self._load_files(kb_id)
        for f in meta.get("files", []):
            if int(f["id"]) == int(file_id):
                return f["filename"]
        return ""

    def _load_file_chunks(self, kb_id: int, file_id: int) -> List[FileChunk]:
        """加载某个文件的全部片段为 `FileChunk` 列表"""
        path = os.path.join(self._chunks_dir(kb_id), f"{file_id}.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        out: List[FileChunk] = []
        for r in raw:
            out.append(FileChunk(
                file_id=r.get("file_id"),
                chunk_index=r.get("chunk_index"),
                content=r.get("content", ""),
                metadata=r.get("metadata"),
                embedding=r.get("embedding"),
            ))
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

        meta = self._load_files(kb_id)
        name_map = {int(f["id"]): f["filename"] for f in meta.get("files", [])}
        chunks_dir = self._chunks_dir(kb_id)
        if not os.path.exists(chunks_dir):
            return []

        exclude_set: set[Tuple[int, int]] = exclude or set()
        heap: List[Tuple[float, int, int, Dict[str, Any]]] = []
        counter = 0

        q_lower = q.lower()
        token_lowers = [t.lower() for t in tokens]
        is_ascii = [bool(re.fullmatch(r"[A-Za-z0-9_]+", t)) for t in tokens]

        for fname in os.listdir(chunks_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(chunks_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    raw = json.load(f) or []
            except Exception:
                continue
            for r in raw:
                try:
                    fid = int(r.get("file_id"))
                    idx = int(r.get("chunk_index"))
                except Exception:
                    continue
                if (fid, idx) in exclude_set:
                    continue
                content = str(r.get("content", "") or "")
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
                item = {
                    "file_id": fid,
                    "chunk_index": idx,
                    "filename": name_map.get(fid, "unknown"),
                    "score": score,
                    "preview": preview,
                    "metadata": r.get("metadata"),
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
        combined.extend(keyword)
        if not combined:
            return []

        # 构造内容加载器（批量读取避免重复 IO）
        pairs_spec = [{"fileId": r["file_id"], "chunkIndex": r["chunk_index"]} for r in combined]
        full_chunks = self.readFileChunks(kb_id, pairs_spec)
        content_map: Dict[tuple[int, int], str] = {}
        for ch in full_chunks:
            fid = int(ch.get("file_id"))
            idx = int(ch.get("chunk_index"))
            content_map[(fid, idx)] = ch.get("content", "")

        def _load_content(fid: int, idx: int) -> str:
            return content_map.get((fid, idx), "")

        return reranker.rerank(q, combined, _load_content, top_k=8)

    def getFilesMeta(self, kb_id: int, file_ids: List[int]) -> List[Dict]:
        """根据文件ID数组返回对应的元信息"""
        meta = self._load_files(kb_id)
        idset = set(int(i) for i in (file_ids or []))
        res = []
        for f in meta.get("files", []):
            if int(f["id"]) in idset:
                res.append(FileMeta(id=int(f["id"]), filename=f["filename"], chunk_count=int(f["chunk_count"]), status=f.get("status", "done")).to_dict())
        return res

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

        meta = self._load_files(kb_id)
        name_map = {int(f["id"]): f["filename"] for f in meta.get("files", [])}
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
                        item["metadata"] = ch.metadata
                    results.append(item)
        return results

    def listFilesPaginated(self, kb_id: int, page: int, page_size: int) -> List[Dict]:
        """分页列出文件元信息"""
        meta = self._load_files(kb_id)
        files = meta.get("files", [])
        start = page * page_size
        end = start + page_size
        return [FileMeta(id=int(f["id"]), filename=f["filename"], chunk_count=int(f["chunk_count"]), status=f.get("status", "done")).to_dict() for f in files[start:end]]
