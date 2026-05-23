from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import List

import numpy as np
from langchain_community.embeddings import DashScopeEmbeddings

from backend.modules.providers.domain.models import LLMProviderType, ModelCategory
from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider:
    def __init__(self, base_url: str | None = None, model_name: str | None = None, timeout: int = 30):
        self._base_url = (
            base_url
            or os.getenv("EMBEDDING_BASE_URL", "")
            or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        self._model_name = (
            model_name
            or os.getenv("EMBEDDING_MODEL", "")
            or os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding")
        )
        self._timeout = timeout

    def _post_embed(self, inputs: List[str]) -> List[List[float]]:
        url = f"{self._base_url.rstrip('/')}/api/embed"
        payload = {"model": self._model_name, "input": inputs}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            body = resp.read()
        parsed = json.loads(body.decode("utf-8"))
        embs = parsed.get("embeddings") or parsed.get("embedding")
        if not embs:
            raise RuntimeError("Ollama embed API 未返回 embeddings 字段")
        return embs

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=float)
        embs = self._post_embed(texts)
        arr = np.asarray(embs, dtype=float)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    def embed_text(self, text: str) -> np.ndarray:
        embs = self._post_embed([text])
        v = np.asarray(embs[0], dtype=float)
        n = np.linalg.norm(v)
        return v / n if n != 0 else v


class AliyunDashScopeEmbeddingProvider:
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
        self._emb: DashScopeEmbeddings | None = None

    def _post_embed(self, inputs: List[str]) -> List[List[float]]:
        if self._emb is None:
            if not self._api_key:
                raise RuntimeError("DashScope API Key 未配置，请在设置中配置 Embedding Provider")
            self._emb = DashScopeEmbeddings(model=self._model_name, dashscope_api_key=self._api_key)
        max_len = int(os.getenv("DASHSCOPE_MAX_INPUT_LEN", "8192"))
        clipped: List[str] = []
        for s in inputs:
            t = s or ""
            clipped.append(t[:max_len] if len(t) > max_len else t)
        vectors = self._emb.embed_documents(clipped)
        return [list(map(float, v)) for v in vectors]

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=float)
        embs = self._post_embed(texts)
        arr = np.asarray(embs, dtype=float)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    def embed_text(self, text: str) -> np.ndarray:
        if self._emb is None:
            if not self._api_key:
                raise RuntimeError("DashScope API Key 未配置，请在设置中配置 Embedding Provider")
            self._emb = DashScopeEmbeddings(model=self._model_name, dashscope_api_key=self._api_key)
        max_len = int(os.getenv("DASHSCOPE_MAX_INPUT_LEN", "8192"))
        t = text or ""
        if len(t) > max_len:
            t = t[:max_len]
        vec = self._emb.embed_query(t)
        v = np.asarray(vec, dtype=float)
        n = np.linalg.norm(v)
        return v / n if n != 0 else v


def get_configured_embedder():
    repo = LLMConfigRepository()
    provider = repo.get_default_by_category(ModelCategory.embedding.value)
    if not provider:
        logger.warning("未找到激活的嵌入模型配置，使用默认的 Ollama Embedding")
        return OllamaEmbeddingProvider(
            base_url="http://localhost:11434",
            model_name="qwen3-embedding",
        )
    logger.info("Initializing configured embedder: %s (type=%s)", provider.name, provider.provider_type)
    if provider.provider_type == LLMProviderType.dashscope:
        return AliyunDashScopeEmbeddingProvider(
            base_url=provider.base_url,
            api_key=provider.api_key,
            model_name=provider.model_name,
        )
    if provider.provider_type == LLMProviderType.ollama:
        return OllamaEmbeddingProvider(
            base_url=provider.base_url,
            model_name=provider.model_name,
        )
    raise RuntimeError(f"不支持的嵌入模型类型: {provider.provider_type}")
