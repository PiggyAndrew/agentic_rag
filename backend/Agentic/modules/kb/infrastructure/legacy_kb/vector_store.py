import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
import json
import threading

import chromadb
import numpy as np


@runtime_checkable
class VectorStore(Protocol):
    def add_items(self, kb_id: int, items: List[Dict[str, Any]]) -> None: ...

    def query_embeddings(self, kb_id: int, query_vec: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]: ...

    def delete_items(self, kb_id: int, filter: Dict[str, Any]) -> int: ...

    def clear(self, kb_id: int) -> None: ...


class BaseVectorStore(ABC):
    def __init__(self, base_dir: str = "data/kb"):
        self.base_dir = base_dir

    @abstractmethod
    def add_items(self, kb_id: int, items: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def query_embeddings(self, kb_id: int, query_vec: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def delete_items(self, kb_id: int, filter: Dict[str, Any]) -> int:
        raise NotImplementedError

    @abstractmethod
    def clear(self, kb_id: int) -> None:
        raise NotImplementedError


class ChromaVectorStore(BaseVectorStore):
    def __init__(self, base_dir: str = "data/kb", persist_dir: Optional[str] = None):
        super().__init__(base_dir=base_dir)
        self._persist_dir = persist_dir or os.path.join(self.base_dir, "chroma")
        os.makedirs(self._persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._target_cache: Dict[int, int] = {}
        self._cache_lock = threading.Lock()

    def _target_dim_path(self, kb_id: int) -> str:
        return os.path.join(self.base_dir, str(int(kb_id)), "vector_dim.txt")

    def _read_target_dim(self, kb_id: int) -> Optional[int]:
        with self._cache_lock:
            if int(kb_id) in self._target_cache:
                return self._target_cache[int(kb_id)]
        env_val = os.getenv("EMBEDDING_TARGET_DIM", "").strip()
        if env_val.isdigit() and int(env_val) > 0:
            with self._cache_lock:
                self._target_cache[int(kb_id)] = int(env_val)
            return int(env_val)
        p = self._target_dim_path(kb_id)
        try:
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as f:
                    s = f.read().strip()
                    if s.isdigit():
                        d = int(s)
                        if d > 0:
                            with self._cache_lock:
                                self._target_cache[int(kb_id)] = d
                            return d
        except Exception:
            pass
        return None

    def _write_target_dim(self, kb_id: int, dim: int) -> None:
        try:
            os.makedirs(os.path.join(self.base_dir, str(int(kb_id))), exist_ok=True)
            with open(self._target_dim_path(kb_id), "w", encoding="utf-8") as f:
                f.write(str(int(dim)))
            with self._cache_lock:
                self._target_cache[int(kb_id)] = int(dim)
        except Exception:
            pass

    def _ensure_target_dim(self, kb_id: int, incoming_dim: int) -> int:
        if incoming_dim <= 0:
            return incoming_dim
        cur = self._read_target_dim(kb_id)
        if cur and cur > 0:
            return cur
        self._write_target_dim(kb_id, incoming_dim)
        return incoming_dim

    def _coerce_vec_dim(self, vec: List[float], target_dim: int) -> List[float]:
        n = len(vec)
        if target_dim <= 0 or n == target_dim:
            return vec
        if n > target_dim:
            return vec[:target_dim]
        return vec + [0.0] * (target_dim - n)

    def _get_client(self):
        if self._client is not None:
            return self._client
        os.makedirs(self._persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        return self._client

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        c = getattr(self, "_client", None)
        self._client = None
        if c is None:
            return
        try:
            sysobj = getattr(c, "_system", None)
            stop = getattr(sysobj, "stop", None) if sysobj is not None else None
            if callable(stop):
                stop()
        except Exception:
            pass

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _collection_name(self, kb_id: int, dim: Optional[int] = None) -> str:
        if dim and int(dim) > 0:
            return f"kb_{int(kb_id)}_dim_{int(dim)}"
        return f"kb_{int(kb_id)}"

    def _get_collection(self, kb_id: int, dim: Optional[int] = None):
        client = self._get_client()
        name = self._collection_name(kb_id, dim=dim)
        try:
            col = client.get_or_create_collection(name=name)
        except Exception:
            col = client.create_collection(name=name)
        return col

    def add_items(self, kb_id: int, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        ids: List[str] = []
        embeddings: List[List[float]] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        for it in items:
            document_id = int(it.get("document_id") or it.get("file_id"))
            chunk_index = int(it.get("chunk_index"))
            ids.append(f"{document_id}:{chunk_index}")
            embeddings.append(list(it.get("embedding") or []))
            documents.append(str(it.get("preview") or ""))
            md: Dict[str, Any] = {
                "document_id": document_id,
                "chunk_index": chunk_index,
                "filename": it.get("filename", ""),
            }
            # Dual-write legacy key only for old readers; document_id is the new primary key.
            md["file_id"] = document_id
            if it.get("preview") is not None:
                md["preview"] = it.get("preview")
            if it.get("metadata") is not None:
                val = it.get("metadata")
                try:
                    if isinstance(val, (dict, list)):
                        md["metadata"] = json.dumps(val, ensure_ascii=False)
                    elif isinstance(val, np.generic):
                        md["metadata"] = val.item()
                    else:
                        md["metadata"] = val
                except Exception:
                    md["metadata"] = str(val)
            metadatas.append(md)
        incoming_dim = 0
        for e in embeddings:
            if e:
                incoming_dim = len(e)
                break
        target_dim = self._ensure_target_dim(kb_id, incoming_dim)
        if target_dim and target_dim > 0:
            embeddings = [self._coerce_vec_dim(e, target_dim) for e in embeddings]
        col = self._get_collection(kb_id, dim=target_dim if target_dim and target_dim > 0 else None)
        col.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def query_embeddings(self, kb_id: int, query_vec: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        incoming_dim = int(query_vec.shape[-1]) if hasattr(query_vec, "shape") and query_vec.ndim >= 1 else 0
        target_dim = self._ensure_target_dim(kb_id, incoming_dim)
        col = self._get_collection(kb_id, dim=target_dim if target_dim and target_dim > 0 else None)
        q = query_vec.astype(float).tolist()
        if target_dim and target_dim > 0:
            q = self._coerce_vec_dim(q, target_dim)
        res = col.query(query_embeddings=[q], n_results=int(top_k))
        out: List[Dict[str, Any]] = []
        ids = res.get("ids") or [[]]
        dists = res.get("distances") or [[]]
        metas = res.get("metadatas") or [[]]
        for i in range(len(ids[0])):
            md = metas[0][i] or {}
            meta_val = md.get("metadata")
            if isinstance(meta_val, str):
                try:
                    meta_val = json.loads(meta_val)
                except Exception:
                    pass
            out.append(
                {
                    "document_id": int(md.get("document_id", md.get("file_id", -1))),
                    "chunk_index": int(md.get("chunk_index", -1)),
                    "filename": md.get("filename", ""),
                    "score": float(-float(dists[0][i]) if isinstance(dists[0][i], (int, float)) else 0.0),
                    "preview": md.get("preview"),
                    "metadata": meta_val,
                }
            )
        return out

    def delete_items(self, kb_id: int, filter: Dict[str, Any]) -> int:
        target_dim = self._read_target_dim(kb_id)
        col = self._get_collection(kb_id, dim=target_dim if target_dim and target_dim > 0 else None)
        def _build_where(id_key: str) -> Dict[str, Any]:
            where: Dict[str, Any] = {}
            if filter.get(id_key) is not None:
                where[id_key] = int(filter.get(id_key))
            if filter.get("chunk_index") is not None:
                where["chunk_index"] = int(filter.get("chunk_index"))
            if filter.get("filename") is not None:
                where["filename"] = filter.get("filename")
            return where

        candidate_wheres: List[Dict[str, Any]] = []
        if filter.get("document_id") is not None:
            candidate_wheres.append(_build_where("document_id"))
            # Fallback cleanup for historical vectors that only stored file_id.
            candidate_wheres.append(_build_where("file_id"))
        elif filter.get("file_id") is not None:
            candidate_wheres.append(_build_where("file_id"))
        else:
            base_where = _build_where("document_id")
            if base_where:
                candidate_wheres.append(base_where)

        if not candidate_wheres:
            return 0

        deleted_ids: List[str] = []
        seen_where: set[tuple[tuple[str, Any], ...]] = set()
        for where in candidate_wheres:
            if not where:
                continue
            where_key = tuple(sorted(where.items()))
            if where_key in seen_where:
                continue
            seen_where.add(where_key)
            pre = col.get(where=where)
            ids_nested = pre.get("ids") or []
            ids: List[str] = []
            for arr in ids_nested:
                ids.extend(arr)
            if not ids:
                continue
            unique_ids = list(dict.fromkeys(ids))
            col.delete(where=where)
            deleted_ids.extend(unique_ids)
        return len(list(dict.fromkeys(deleted_ids)))

    def clear(self, kb_id: int) -> None:
        client = self._get_client()
        name = self._collection_name(kb_id)
        try:
            client.delete_collection(name=name)
        except Exception:
            pass
