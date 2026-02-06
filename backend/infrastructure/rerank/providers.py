from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import logging
import os

from backend.modules.providers.domain.models import LLMProviderType, ModelCategory
from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository
from backend.infrastructure.embedding.providers import AliyunDashScopeEmbeddingProvider, OllamaEmbeddingProvider


class Reranker:
    pre_k: int = 5

    def rerank(
        self,
        query: str,
        initial: List[Dict[str, Any]],
        load_content: Callable[[int, int], str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        return initial[:top_k]


class NoopReranker(Reranker):
    pre_k = 5

    def rerank(
        self,
        query: str,
        initial: List[Dict[str, Any]],
        load_content: Callable[[int, int], str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        return initial[:top_k]


class OllamaReranker(Reranker):
    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        pre_k: Optional[int] = None,
    ):
        self.model_name = model_name or os.getenv("RERANKER_MODEL", "")
        self.pre_k = int(pre_k or os.getenv("RERANKER_PRE_K", "0") or 0)
        self._embedder = OllamaEmbeddingProvider(
            base_url=base_url or os.getenv("RERANKER_BASE_URL", ""),
            model_name=self.model_name,
        )

    def rerank(
        self,
        query: str,
        initial: List[Dict[str, Any]],
        load_content: Callable[[int, int], str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        logger = logging.getLogger(__name__)
        if not initial:
            return []

        contents: List[str] = []
        keep_idx: List[int] = []
        for i, r in enumerate(initial):
            fid = int(r.get("file_id"))
            idx = int(r.get("chunk_index"))
            content = load_content(fid, idx) or r.get("preview", "")
            if not content:
                continue
            contents.append(content)
            keep_idx.append(i)
        if not contents:
            return initial[:top_k]

        try:
            q_vec = self._embedder.embed_text(query)
            d_mat = self._embedder.embed_texts(contents)
            scores = (d_mat @ q_vec).tolist()
        except Exception:
            logger.exception("Rerank failed")
            return initial[:top_k]

        ranked: List[Dict[str, Any]] = []
        for k, i in enumerate(keep_idx):
            item = dict(initial[i])
            item["rerank_score"] = float(scores[k])
            ranked.append(item)
        ranked.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return ranked[:top_k]


class AliyunDashScopeReranker(Reranker):
    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        pre_k: Optional[int] = None,
    ):
        self.model_name = model_name
        self.pre_k = int(pre_k or 0)
        self._embedder = AliyunDashScopeEmbeddingProvider(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
        )

    def rerank(
        self,
        query: str,
        initial: List[Dict[str, Any]],
        load_content: Callable[[int, int], str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        logger = logging.getLogger(__name__)
        if not initial:
            return []

        contents: List[str] = []
        keep_idx: List[int] = []
        for i, r in enumerate(initial):
            fid = int(r.get("file_id"))
            idx = int(r.get("chunk_index"))
            content = load_content(fid, idx) or r.get("preview", "")
            if not content:
                continue
            contents.append(content)
            keep_idx.append(i)
        if not contents:
            return initial[:top_k]

        try:
            q_vec = self._embedder.embed_text(query)
            d_mat = self._embedder.embed_texts(contents)
            scores = (d_mat @ q_vec).tolist()
        except Exception:
            logger.exception("Rerank failed")
            return initial[:top_k]

        ranked: List[Dict[str, Any]] = []
        for k, i in enumerate(keep_idx):
            item = dict(initial[i])
            item["rerank_score"] = float(scores[k])
            ranked.append(item)
        ranked.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return ranked[:top_k]


def get_configured_reranker() -> Reranker:
    repo = LLMConfigRepository()
    provider = repo.get_default_by_category(ModelCategory.reranker.value)
    if not provider:
        logging.getLogger(__name__).warning("未找到激活的重排模型配置，使用 NoopReranker")
        return NoopReranker()
    logging.getLogger(__name__).info("Initializing configured reranker: %s (type=%s)", provider.name, provider.provider_type)
    if provider.provider_type == LLMProviderType.dashscope:
        return AliyunDashScopeReranker(
            base_url=provider.base_url,
            api_key=provider.api_key,
            model_name=provider.model_name,
        )
    if provider.provider_type == LLMProviderType.ollama:
        return OllamaReranker(
            base_url=provider.base_url,
            model_name=provider.model_name,
        )
    logging.getLogger(__name__).warning("不支持的 Reranker 类型: %s，使用 NoopReranker", provider.provider_type)
    return NoopReranker()
