from typing import List
import numpy as np
import os
import json
import urllib.request
import logging
from langchain_community.embeddings import DashScopeEmbeddings
from backend.config.settings import resolve_embedding_backend, get_settings, EmbeddingBackend

logger = logging.getLogger(__name__)

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
    backend = resolve_embedding_backend()
    if backend == EmbeddingBackend.dashscope:
        logger.info("Embedding backend selected: dashscope (env=%s)", getattr(get_settings().APP_ENV, "value", get_settings().APP_ENV))
        return AliyunDashScopeEmbeddingProvider()
    logger.info("Embedding backend selected: ollama (env=%s)", getattr(get_settings().APP_ENV, "value", get_settings().APP_ENV))
    return OllamaEmbeddingProvider()


class AliyunDashScopeEmbeddingProvider:
    """基于阿里云百炼（DashScope 兼容模式）的嵌入向量生成器

    - 使用 OpenAI 兼容客户端调用 embeddings 接口
    - 通过环境变量配置：
      - DASHSCOPE_API_KEY：API Key（不要硬编码在代码中）
      - DASHSCOPE_BASE_URL：Base URL（默认北京：https://dashscope.aliyuncs.com/compatible-mode/v1）
      - DASHSCOPE_EMBED_MODEL：模型名称（默认 text-embedding-v4）
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout: int = 30,
    ):
        self._base_url = base_url or os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self._api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self._model_name = model_name or os.getenv("DASHSCOPE_EMBED_MODEL", "text-embedding-v4")
        self._timeout = timeout
        # LangChain DashScopeEmbeddings 使用环境变量或显式传入 API Key
        self._emb = DashScopeEmbeddings(model=self._model_name, dashscope_api_key=self._api_key)

    def _post_embed(self, inputs: List[str]) -> List[List[float]]:
        """请求 embeddings 接口并返回二维向量数组

        - inputs：文本数组（支持批量）
        - 返回：List[List[float]] 嵌入结果
        """
        try:
            logger.debug("DashScope embed start: model=%s, count=%d", self._model_name, len(inputs))
            max_len = int(os.getenv("DASHSCOPE_MAX_INPUT_LEN", "8192"))
            clipped = []
            clipped_count = 0
            for s in inputs:
                t = s or ""
                if len(t) > max_len:
                    clipped.append(t[:max_len])
                    clipped_count += 1
                else:
                    clipped.append(t)
            if clipped_count:
                logger.info("DashScope embed clipping: clipped=%d, max_len=%d", clipped_count, max_len)
            vectors = self._emb.embed_documents(clipped)
            out = [list(map(float, v)) for v in vectors]
            dim = (len(out[0]) if out and out[0] is not None else 0)
            logger.info("DashScope embed success: model=%s, count=%d, dim=%d", self._model_name, len(out), dim)
            return out
        except Exception as e:
            logger.exception("DashScope embed failed: model=%s, count=%d", self._model_name, len(inputs))
            raise RuntimeError(f"DashScope embeddings 请求失败: {e}")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """批量生成文本嵌入，返回形状为 (n, d) 的 numpy 数组"""
        if not texts:
            return np.zeros((0, 0), dtype=float)
        embs = self._post_embed(texts)
        arr = np.asarray(embs, dtype=float)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    def embed_text(self, text: str) -> np.ndarray:
        """单条文本嵌入，返回一维向量"""
        try:
            max_len = int(os.getenv("DASHSCOPE_MAX_INPUT_LEN", "8192"))
            t = text or ""
            if len(t) > max_len:
                logger.info("DashScope query clipping: from=%d to=%d", len(t), max_len)
                t = t[:max_len]
            vec = self._emb.embed_query(t)
        except Exception as e:
            raise RuntimeError(f"DashScope embedding 请求失败: {e}")
        v = np.asarray(vec, dtype=float)
        n = np.linalg.norm(v)
        return v / n if n != 0 else v
