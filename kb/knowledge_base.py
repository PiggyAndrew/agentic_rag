from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional
import numpy as np
from .embeddings import get_default_embedder
from .vector_store import LocalVectorStore
import json
import os
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
        meta["files"].append({
            "id": info.id,
            "filename": info.filename,
            "chunk_count": info.chunk_count,
            "status": info.status,
        })
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
        for i, c in enumerate(chunks):
            if isinstance(c, str):
                normalized.append({"file_id": file_id, "chunk_index": i, "content": c})
                texts.append(c)
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
                vitems.append({
                    "file_id": file_id,
                    "chunk_index": i,
                    "filename": self._filename_of(kb_id, file_id),
                    "metadata": None,
                    "preview": (s[:200] + "...") if len(s) > 200 else s,
                })
        try:
            if texts:
                embs = self._embedder.embed_texts(texts)
                for i in range(len(normalized)):
                    normalized[i]["embedding"] = embs[i].tolist()
                    vitems[i]["embedding"] = embs[i].tolist()
        except Exception:
            pass
        with open(path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        try:
            if vitems and all("embedding" in vi for vi in vitems):
                self._vstore.add_items(kb_id, vitems)
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

    def search(self, kb_id: int, query: str) -> List[Dict]:
        """基于向量嵌入的语义检索，返回相关性最高的片段"""
        q = (query or "").strip()
        if not q:
            return []
        q_vec = self._embedder.embed_text(q)
        results = self._vstore.query_embeddings(kb_id, q_vec, top_k=5)
        return results

    def getFilesMeta(self, kb_id: int, file_ids: List[int]) -> List[Dict]:
        """根据文件ID数组返回对应的元信息"""
        meta = self._load_files(kb_id)
        idset = set(int(i) for i in (file_ids or []))
        res = []
        for f in meta.get("files", []):
            if int(f["id"]) in idset:
                res.append({
                    "id": int(f["id"]),
                    "filename": f["filename"],
                    "chunk_count": int(f["chunk_count"]),
                    "status": f.get("status", "done"),
                })
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
        return [{
            "id": int(f["id"]),
            "filename": f["filename"],
            "chunk_count": int(f["chunk_count"]),
            "status": f.get("status", "done"),
        } for f in files[start:end]]
