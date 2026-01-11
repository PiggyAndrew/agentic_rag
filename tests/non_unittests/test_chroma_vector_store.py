import os
import sys
import json
import numpy as np
import chromadb  # noqa: F401

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.kb.vector_store import ChromaVectorStore


class FakeEmbedder:
    def _vec(self, text: str) -> np.ndarray:
        s = text or ""
        a = float(len(s))
        b = float(sum(ord(c) for c in s))
        c = float(s.count(" "))
        v = np.asarray([a, b, c], dtype=float)
        n = np.linalg.norm(v)
        return v / n if n != 0 else v

    def embed_texts(self, texts):
        arr = np.vstack([self._vec(t) for t in texts]) if texts else np.zeros((0, 0), dtype=float)
        return arr

    def embed_text(self, text):
        return self._vec(text)


def run_debug():
    store = ChromaVectorStore(base_dir="data/kb")
    kb_id = 1
    try:
        store.clear(kb_id)
    except Exception:
        pass
    emb = FakeEmbedder()
    texts = [
        "Chroma vector store test for windows environment.",
        "Another piece of text to retrieve.",
    ]
    vecs = emb.embed_texts(texts)
    items = []
    for i, t in enumerate(texts):
        items.append({
            "file_id": 1,
            "chunk_index": i,
            "filename": "chroma_debug.txt",
            "embedding": vecs[i].tolist(),
            "preview": t,
            "metadata": None,
        })
    store.add_items(kb_id, items)
    q = emb.embed_text("Chroma test")
    results = store.query_embeddings(kb_id, q, top_k=2)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_debug()
