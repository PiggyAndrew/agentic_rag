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
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            body = resp.read()
        parsed = json.loads(body.decode("utf-8"))
        # Ollama 返回 { "embeddings": [[...], [...]] }
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
    """根据环境变量选择默认嵌入提供器

    - 当 `EMBEDDING_BACKEND=ollama` 时，使用 `OllamaEmbeddingProvider`
    - 否则使用 `SentenceEmbeddingProvider`
    """
    backend = os.getenv("EMBEDDING_BACKEND", "sentence_transformers").lower()
    if backend == "ollama":
        return OllamaEmbeddingProvider()
    return OllamaEmbeddingProvider()
