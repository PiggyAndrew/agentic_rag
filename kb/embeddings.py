from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer


class SentenceEmbeddingProvider:
    """基于 Sentence-Transformers 的文本嵌入向量生成器"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """批量生成文本嵌入，返回形状为 (n, d) 的 numpy 数组"""
        self._ensure_model()
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=float)

    def embed_text(self, text: str) -> np.ndarray:
        """单条文本嵌入，返回一维向量"""
        self._ensure_model()
        v = self._model.encode([text], normalize_embeddings=True)
        return np.asarray(v[0], dtype=float)

