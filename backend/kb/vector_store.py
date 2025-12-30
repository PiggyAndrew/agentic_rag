import os
import json
import shutil
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol, runtime_checkable, Iterable
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


class LocalVectorStore(BaseVectorStore):
    """本地持久化向量存储，基于 numpy 与 json

    - 存储位置：`data/kb/{kb_id}/vector_store/`
      - `embeddings.npy`：形状为 (N, D) 的向量矩阵
      - `meta.json`：长度为 N 的元信息列表，对应每个向量的来源与预览
    """

    def __init__(self, base_dir: str = "data/kb"):
        super().__init__(base_dir=base_dir)

    def _store_dir(self, kb_id: int) -> str:
        return os.path.join(self.base_dir, str(kb_id), "vector_store")

    def _emb_path(self, kb_id: int) -> str:
        return os.path.join(self._store_dir(kb_id), "embeddings.npy")

    def _meta_path(self, kb_id: int) -> str:
        return os.path.join(self._store_dir(kb_id), "meta.json")

    def _ensure_store(self, kb_id: int) -> None:
        os.makedirs(self._store_dir(kb_id), exist_ok=True)
        mp = self._meta_path(kb_id)
        if not os.path.exists(mp):
            with open(mp, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def add_items(self, kb_id: int, items: List[Dict[str, Any]]) -> None:
        """追加写入若干条向量与其元信息

        - 每个 `items` 的元素需包含：`embedding`(List[float])、`file_id`、`chunk_index`、`filename`、`metadata`(可选)、`preview`(可选)
        """
        if not items:
            return
        self._ensure_store(kb_id)
        emb_path = self._emb_path(kb_id)
        meta_path = self._meta_path(kb_id)

        new_embs = np.asarray([it["embedding"] for it in items], dtype=float)
        if os.path.exists(emb_path):
            old = np.load(emb_path)
            if old.ndim == 1:
                old = old.reshape(1, -1)
            if old.shape[1] != new_embs.shape[1]:
                raise ValueError("嵌入维度不一致，无法追加到现有向量存储")
            all_embs = np.vstack([old, new_embs])
        else:
            all_embs = new_embs
        np.save(emb_path, all_embs)

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        for it in items:
            meta.append({
                "file_id": int(it["file_id"]),
                "chunk_index": int(it["chunk_index"]),
                "filename": it.get("filename", ""),
                "metadata": it.get("metadata"),
                "preview": it.get("preview"),
            })
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def query_embeddings(self, kb_id: int, query_vec: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """以查询向量进行相似度检索，返回 Top-K 元信息与分数"""
        self._ensure_store(kb_id)
        emb_path = self._emb_path(kb_id)
        meta_path = self._meta_path(kb_id)
        if not os.path.exists(emb_path):
            return []
        embs = np.load(emb_path)
        if embs.ndim == 1:
            embs = embs.reshape(1, -1)

        q = query_vec.astype(float)
        qn = np.linalg.norm(q)
        if qn == 0:
            return []
        # 余弦相似度
        norms = np.linalg.norm(embs, axis=1)
        nonzero = norms > 0
        sims = np.zeros(embs.shape[0], dtype=float)
        sims[nonzero] = (embs[nonzero] @ q) / (norms[nonzero] * qn)

        idxs = np.argsort(-sims)[:top_k]
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        results: List[Dict[str, Any]] = []
        for i in idxs:
            m = meta[i]
            results.append({
                "file_id": int(m["file_id"]),
                "chunk_index": int(m["chunk_index"]),
                "filename": m.get("filename", ""),
                "score": float(sims[i]),
                "preview": m.get("preview"),
                "metadata": m.get("metadata"),
            })
        return results

    def delete_items(self, kb_id: int, filter: Dict[str, Any]) -> int:
        """根据过滤条件删除若干向量与其元信息，返回删除的数量

        - 支持过滤键：`file_id`、`chunk_index`、`filename`
        """
        self._ensure_store(kb_id)
        emb_path = self._emb_path(kb_id)
        meta_path = self._meta_path(kb_id)
        if not os.path.exists(meta_path):
            return 0
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if not meta:
            return 0
        def match(m: Dict[str, Any]) -> bool:
            if filter.get("file_id") is not None and int(m.get("file_id", -1)) != int(filter.get("file_id")):
                return False
            if filter.get("chunk_index") is not None and int(m.get("chunk_index", -1)) != int(filter.get("chunk_index")):
                return False
            if filter.get("filename") is not None and m.get("filename") != filter.get("filename"):
                return False
            return True
        keep_indices: List[int] = []
        delete_count = 0
        for i, m in enumerate(meta):
            if match(m):
                delete_count += 1
            else:
                keep_indices.append(i)
        if delete_count == 0:
            return 0
        new_meta = [meta[i] for i in keep_indices]
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(new_meta, f, ensure_ascii=False, indent=2)
        if os.path.exists(emb_path):
            embs = np.load(emb_path)
            if embs.ndim == 1:
                embs = embs.reshape(1, -1)
            if keep_indices:
                new_embs = embs[keep_indices, :]
                np.save(emb_path, new_embs)
            else:
                os.remove(emb_path)
        return delete_count

    def clear(self, kb_id: int) -> None:
        """清空指定知识库的向量存储目录"""
        dirp = self._store_dir(kb_id)
        if os.path.exists(dirp):
            shutil.rmtree(dirp, ignore_errors=True)


class MilvusLiteVectorStore(BaseVectorStore):
    def __init__(self, base_dir: str = "data/kb", uri: Optional[str] = None):
        super().__init__(base_dir=base_dir)
        self._client = None
        self._uri = uri or os.path.join(self.base_dir, "milvus_lite.db")

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from pymilvus import MilvusClient
        except Exception:
            raise RuntimeError("pymilvus 未安装，请执行: pip install -U pymilvus[milvus-lite]")
        dirp = os.path.dirname(self._uri)
        if dirp:
            os.makedirs(dirp, exist_ok=True)
        self._client = MilvusClient(self._uri)
        return self._client

    def _collection_name(self, kb_id: int) -> str:
        return f"kb_{int(kb_id)}"

    def _ensure_collection(self, kb_id: int, dim: int) -> None:
        client = self._get_client()
        name = self._collection_name(kb_id)
        if not client.has_collection(collection_name=name):
            client.create_collection(
                collection_name=name,
                dimension=int(dim),
                auto_id=True,
                metric_type="COSINE",
                enable_dynamic_field=True,
            )

    def _iter_hits(self, res: Any) -> Iterable[Any]:
        if res is None:
            return []
        if isinstance(res, list) and res:
            first = res[0]
            if isinstance(first, list):
                return first
        return []

    def _hit_entity(self, hit: Any) -> Dict[str, Any]:
        if isinstance(hit, dict):
            ent = hit.get("entity") or hit.get("fields")
            if isinstance(ent, dict):
                return ent
            return {k: v for k, v in hit.items() if k not in {"id", "distance", "score", "entity", "fields"}}
        ent = getattr(hit, "entity", None)
        if isinstance(ent, dict):
            return ent
        return {}

    def _hit_score(self, hit: Any) -> float:
        if isinstance(hit, dict):
            if hit.get("score") is not None:
                return float(hit.get("score"))
            if hit.get("distance") is not None:
                return float(hit.get("distance"))
            return 0.0
        score = getattr(hit, "score", None)
        if score is not None:
            return float(score)
        dist = getattr(hit, "distance", None)
        if dist is not None:
            return float(dist)
        return 0.0

    def add_items(self, kb_id: int, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        dim = len(items[0].get("embedding") or [])
        if dim <= 0:
            return
        for it in items:
            emb = it.get("embedding") or []
            if len(emb) != dim:
                raise ValueError("同一批次写入的 embedding 维度不一致")
        client = self._get_client()
        name = self._collection_name(kb_id)
        self._ensure_collection(kb_id, dim)
        data = []
        for it in items:
            data.append(
                {
                    "vector": list(it.get("embedding") or []),
                    "file_id": int(it.get("file_id")),
                    "chunk_index": int(it.get("chunk_index")),
                    "filename": it.get("filename", ""),
                    "preview": it.get("preview"),
                    "metadata": it.get("metadata"),
                }
            )
        client.insert(collection_name=name, data=data)

    def query_embeddings(self, kb_id: int, query_vec: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        client = self._get_client()
        name = self._collection_name(kb_id)
        if not client.has_collection(collection_name=name):
            return []
        q = query_vec.astype(float).tolist()
        res = client.search(
            collection_name=name,
            data=[q],
            limit=int(top_k),
            output_fields=["file_id", "chunk_index", "filename", "preview", "metadata"],
        )
        out: List[Dict[str, Any]] = []
        for h in self._iter_hits(res):
            fields = self._hit_entity(h)
            score = self._hit_score(h)
            item = {
                "file_id": int(fields.get("file_id", -1)),
                "chunk_index": int(fields.get("chunk_index", -1)),
                "filename": fields.get("filename", ""),
                "score": float(score),
                "preview": fields.get("preview"),
                "metadata": fields.get("metadata"),
            }
            out.append(item)
        return out

    def delete_items(self, kb_id: int, filter: Dict[str, Any]) -> int:
        client = self._get_client()
        name = self._collection_name(kb_id)
        if not client.has_collection(collection_name=name):
            return 0
        clauses: List[str] = []
        if filter.get("file_id") is not None:
            clauses.append(f"file_id == {int(filter['file_id'])}")
        if filter.get("chunk_index") is not None:
            clauses.append(f"chunk_index == {int(filter['chunk_index'])}")
        if filter.get("filename") is not None:
            v = str(filter["filename"]).replace("\"", "\\\"")
            clauses.append(f"filename == \"{v}\"")
        if not clauses:
            return 0
        flt = " and ".join(clauses)
        res = client.delete(collection_name=name, filter=flt)
        if isinstance(res, dict):
            dc = res.get("delete_count")
            return int(dc or 0)
        return int(getattr(res, "delete_count", 0) or 0)

    def clear(self, kb_id: int) -> None:
        client = self._get_client()
        name = self._collection_name(kb_id)
        if client.has_collection(collection_name=name):
            try:
                client.drop_collection(collection_name=name)
            except Exception:
                pass
