from typing import List
import numpy as np
import os
import json
import urllib.request

class OllamaEmbeddingProvider:
    """基于 Ollama 的嵌入向量生成器（例如 qwen3-embedding）"""

    def __init__(self, base_url: str | None = None, model_name: str | None = None, timeout: int = 30):
        self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._model_name = model_name or os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding")
        self._timeout = timeout

    def _post_embed(self, inputs: List[str]) -> List[List[float]]:
        url = f"{self._base_url.rstrip('/')}/api/embed"
        payload = {
            "model": self._model_name,
            "input": inputs,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read()
            parsed = json.loads(body.decode("utf-8"))
        except Exception:
            if self._model_name == "qwen3-embedding":
                fb_payload = {
                    "model": "bge-m3",
                    "input": inputs,
                }
                fb_data = json.dumps(fb_payload).encode("utf-8")
                fb_req = urllib.request.Request(url, data=fb_data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(fb_req, timeout=self._timeout) as resp:
                    body = resp.read()
                parsed = json.loads(body.decode("utf-8"))
            else:
                raise
        embs = parsed.get("embeddings") or parsed.get("embedding")
        if not embs:
            raise RuntimeError("Ollama embed API 未返回 embeddings 字段")
        return embs

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """批量生成文本嵌入，返回形状为 (n, d) 的 numpy 数组"""
        if not texts:
            return np.zeros((0, 0), dtype=float)
        embs = self._post_embed(texts)
        arr = np.asarray(embs, dtype=float)
        # 可选：标准化，保证余弦相似度稳定
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    def embed_text(self, text: str) -> np.ndarray:
        """单条文本嵌入，返回一维向量"""
        embs = self._post_embed([text])
        v = np.asarray(embs[0], dtype=float)
        n = np.linalg.norm(v)
        return v / n if n != 0 else v


def get_default_embedder():
    backend = os.getenv("EMBEDDING_BACKEND", "ollama").lower()
    return OllamaEmbeddingProvider()
