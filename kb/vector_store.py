import os
import json
from typing import List, Dict, Any, Optional
import numpy as np


class LocalVectorStore:
    """本地持久化向量存储，基于 numpy 与 json

    - 存储位置：`data/kb/{kb_id}/vector_store/`
      - `embeddings.npy`：形状为 (N, D) 的向量矩阵
      - `meta.json`：长度为 N 的元信息列表，对应每个向量的来源与预览
    """

    def __init__(self, base_dir: str = "data/kb"):
        self.base_dir = base_dir

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

