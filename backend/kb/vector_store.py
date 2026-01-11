import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol, runtime_checkable, Iterable
import numpy as np
import chromadb
import json


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
        self._client = chromadb.PersistentClient(path=self.base_dir)

    def _get_client(self):
        if self._client is not None:
            return self._client
        os.makedirs(self._persist_dir, exist_ok=True)
        self._client = chromadb.Client()
        return self._client

    def _collection_name(self, kb_id: int) -> str:
        return f"kb_{int(kb_id)}"

    def _get_collection(self, kb_id: int):
        client = self._get_client()
        name = self._collection_name(kb_id)
        try:
            col = client.get_or_create_collection(name=name)
        except Exception:
            col = client.create_collection(name=name)
        return col

    def add_items(self, kb_id: int, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        col = self._get_collection(kb_id)
        ids: List[str] = []
        embeddings: List[List[float]] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        for it in items:
            fid = int(it.get("file_id"))
            idx = int(it.get("chunk_index"))
            ids.append(f"{fid}:{idx}")
            embeddings.append(list(it.get("embedding") or []))
            documents.append(str(it.get("preview") or ""))
            md: Dict[str, Any] = {
                "file_id": fid,
                "chunk_index": idx,
                "filename": it.get("filename", ""),
            }
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
        try:
            col.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        except Exception as e:
            print(f"Error upserting items to ChromaDB: {e}")
            raise e

    def query_embeddings(self, kb_id: int, query_vec: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        col = self._get_collection(kb_id)
        q = query_vec.astype(float).tolist()
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
            out.append({
                "file_id": int(md.get("file_id", -1)),
                "chunk_index": int(md.get("chunk_index", -1)),
                "filename": md.get("filename", ""),
                "score": float(-float(dists[0][i]) if isinstance(dists[0][i], (int, float)) else 0.0),
                "preview": md.get("preview"),
                "metadata": meta_val,
            })
        return out

    def delete_items(self, kb_id: int, filter: Dict[str, Any]) -> int:
        col = self._get_collection(kb_id)
        where: Dict[str, Any] = {}
        if filter.get("file_id") is not None:
            where["file_id"] = int(filter.get("file_id"))
        if filter.get("chunk_index") is not None:
            where["chunk_index"] = int(filter.get("chunk_index"))
        if filter.get("filename") is not None:
            where["filename"] = filter.get("filename")
        if not where:
            return 0
        pre = col.get(where=where)
        ids_nested = pre.get("ids") or []
        ids: List[str] = []
        for arr in ids_nested:
            ids.extend(arr)
        if not ids:
            return 0
        col.delete(ids=ids)
        return len(ids)

    def clear(self, kb_id: int) -> None:
        client = self._get_client()
        name = self._collection_name(kb_id)
        try:
            client.delete_collection(name=name)
        except Exception:
            pass
