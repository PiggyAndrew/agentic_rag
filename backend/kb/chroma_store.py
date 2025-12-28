import os
import shutil
from typing import List, Dict, Any, Optional
import numpy as np
import chromadb


class ChromaVectorStore:
    def __init__(self, base_dir: str = "data/kb"):
        self.base_dir = base_dir
        self._clients: Dict[int, chromadb.Client] = {}
        self._collections: Dict[int, Any] = {}

    def _client_path(self, kb_id: int) -> str:
        return os.path.join(self.base_dir, str(kb_id), "chroma")

    def _get_client(self, kb_id: int):
        if kb_id not in self._clients:
            os.makedirs(self._client_path(kb_id), exist_ok=True)
            self._clients[kb_id] = chromadb.PersistentClient(path=self._client_path(kb_id))
        return self._clients[kb_id]

    def _get_collection(self, kb_id: int):
        if kb_id not in self._collections:
            client = self._get_client(kb_id)
            self._collections[kb_id] = client.get_or_create_collection(
                name=f"kb_{kb_id}",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[kb_id]

    def add_items(self, kb_id: int, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        coll = self._get_collection(kb_id)
        ids: List[str] = []
        docs: List[str] = []
        metas: List[Dict[str, Any]] = []
        embs: List[List[float]] = []
        for it in items:
            fid = int(it["file_id"])
            idx = int(it["chunk_index"])
            ids.append(f"{fid}:{idx}")
            docs.append(str(it.get("content") or it.get("preview") or ""))
            meta = {
                "file_id": fid,
                "chunk_index": idx,
                "filename": it.get("filename", ""),
                "preview": it.get("preview"),
            }
            if it.get("metadata") is not None:
                meta["metadata"] = it.get("metadata")
            metas.append(meta)
            embs.append(list(it["embedding"]))
        try:
            coll.delete(ids=ids)
        except Exception:
            pass
        coll.add(ids=ids, documents=docs, metadatas=metas, embeddings=embs)

    def query_embeddings(self, kb_id: int, query_vec: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        coll = self._get_collection(kb_id)
        q = query_vec.astype(float).tolist()
        res = coll.query(
            query_embeddings=[q],
            n_results=int(top_k),
            include=["metadatas", "documents", "distances"],
        )
        out: List[Dict[str, Any]] = []
        mets = res.get("metadatas") or [[]]
        docs = res.get("documents") or [[]]
        dists = res.get("distances") or [[]]
        for i in range(len(mets[0])):
            m = mets[0][i] or {}
            doc = docs[0][i] or ""
            dist = float(dists[0][i]) if dists and dists[0] else 0.0
            sim = 1.0 - dist
            out.append({
                "file_id": int(m.get("file_id", -1)),
                "chunk_index": int(m.get("chunk_index", -1)),
                "filename": str(m.get("filename", "")),
                "score": sim,
                "preview": m.get("preview") or (doc[:200] + "...") if len(doc) > 200 else doc,
                "metadata": m.get("metadata"),
            })
        return out

    def delete_items(self, kb_id: int, filter: Dict[str, Any]) -> int:
        coll = self._get_collection(kb_id)
        where: Dict[str, Any] = {}
        if filter.get("file_id") is not None:
            where["file_id"] = int(filter.get("file_id"))
        if filter.get("chunk_index") is not None:
            where["chunk_index"] = int(filter.get("chunk_index"))
        if filter.get("filename") is not None:
            where["filename"] = str(filter.get("filename"))
        try:
            coll.delete(where=where or None)
        except Exception:
            pass
        return 0

    def clear(self, kb_id: int) -> None:
        path = self._client_path(kb_id)
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
        if kb_id in self._clients:
            del self._clients[kb_id]
        if kb_id in self._collections:
            del self._collections[kb_id]

    def get_file_chunks(self, kb_id: int, file_id: int) -> List[Dict[str, Any]]:
        coll = self._get_collection(kb_id)
        res = coll.get(where={"file_id": int(file_id)}, include=["metadatas", "documents"])
        ids = res.get("ids") or []
        mets = res.get("metadatas") or []
        docs = res.get("documents") or []
        out: List[Dict[str, Any]] = []
        for i in range(len(ids)):
            m = mets[i] or {}
            out.append({
                "file_id": int(m.get("file_id", -1)),
                "chunk_index": int(m.get("chunk_index", -1)),
                "content": docs[i] or "",
                "metadata": m.get("metadata"),
            })
        out.sort(key=lambda r: int(r.get("chunk_index", 0)))
        return out

    def get_chunk_contents_by_pairs(self, kb_id: int, pairs: List[Dict[str, int]]) -> List[Dict[str, Any]]:
        if not pairs:
            return []
        coll = self._get_collection(kb_id)
        ids = [f"{int(p['fileId'])}:{int(p['chunkIndex'])}" for p in pairs]
        res = coll.get(ids=ids, include=["metadatas", "documents"])
        id_list = res.get("ids") or []
        mets = res.get("metadatas") or []
        docs = res.get("documents") or []
        out: List[Dict[str, Any]] = []
        for i in range(len(id_list)):
            m = mets[i] or {}
            out.append({
                "file_id": int(m.get("file_id", -1)),
                "chunk_index": int(m.get("chunk_index", -1)),
                "content": docs[i] or "",
                "metadata": m.get("metadata"),
            })
        return out
