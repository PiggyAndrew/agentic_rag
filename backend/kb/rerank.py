from typing import List, Dict, Any, Callable, Optional
import os
import logging
import numpy as np
from backend.kb.embeddings import OllamaEmbeddingProvider


def _truthy(s: Optional[str]) -> bool:
    return str(s or "").lower() in {"1", "true", "yes"}


class Reranker:
    """Reranker 接口：对初筛候选做二次排序。

    - `rerank(query, initial, load_content, top_k)` 返回重排后的前 `top_k` 结果。
    - `pre_k` 表示需要的预候选条数（向量检索阶段的 top_k）。
    """

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
    """不做重排的 Reranker，直接返回前 top_k。"""

    pre_k = 5

    def rerank(self, query: str, initial: List[Dict[str, Any]], load_content: Callable[[int, int], str], top_k: int = 5) -> List[Dict[str, Any]]:
        return initial[:top_k]


class OllamaReranker(Reranker):
    """基于 Ollama embeddings 的重排实现（qllama/bge-reranker-v2-m3）"""

    def __init__(self, model_name: Optional[str] = None, base_url: Optional[str] = None, pre_k: Optional[int] = None):
        self.model_name = model_name or os.getenv("KB_RERANK_MODEL", "qllama/bge-reranker-v2-m3")
        self.pre_k = int(pre_k or os.getenv("KB_RERANK_PRE_K", "20"))
        self._embedder = OllamaEmbeddingProvider(
            base_url=base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model_name=self.model_name,
        )

    def rerank(self, query: str, initial: List[Dict[str, Any]], load_content: Callable[[int, int], str], top_k: int = 5) -> List[Dict[str, Any]]:
        """对候选进行重排并返回前 top_k 结果"""
        logger = logging.getLogger(__name__)
        logger.debug("Rerank start (Ollama): model=%s, initial=%d, top_k=%d", self.model_name, len(initial or []), top_k)
        if not initial:
            logger.info("Rerank skipped: empty initial candidates")
            return []

        # 构造文档内容
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
            logger.info("Rerank skipped: no content built")
            return initial[:top_k]
        logger.debug("Rerank contents ready: count=%d, kept=%d, skipped=%d", len(contents), len(keep_idx), len(initial) - len(keep_idx))

        try:
            q_vec = self._embedder.embed_text(query)
            d_mat = self._embedder.embed_texts(contents)
        except Exception:
            logger.exception("Rerank embedding failed: model=%s, count=%d", self.model_name, len(contents))
            return initial[:top_k]

        # 计算余弦相似度（embedder 已标准化，可用点乘）
        try:
            scores = (d_mat @ q_vec).tolist()
        except Exception:
            logger.exception("Rerank score compute failed: shapes=%s", str((d_mat.shape, q_vec.shape)))
            return initial[:top_k]

        ranked: List[Dict[str, Any]] = []
        for k, i in enumerate(keep_idx):
            item = dict(initial[i])
            item["rerank_score"] = float(scores[k])
            ranked.append(item)
        ranked.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        out = ranked[:top_k]
        top_score = out[0]["rerank_score"] if out else None
        logger.info("Rerank success (Ollama): model=%s, outputs=%d, top_score=%s", self.model_name, len(out), f"{top_score:.4f}" if isinstance(top_score, float) else str(top_score))
        return out


def get_default_reranker() -> Reranker:
    """根据环境变量返回默认 Reranker。

    - 当 `KB_RERANK` 为真（1/true/yes）时，使用 `CrossEncoderReranker`。
    - 否则，使用 `NoopReranker`。
    """
    if _truthy(os.getenv("KB_RERANK")):
        logging.getLogger(__name__).info(
            "Reranker selected: OllamaReranker (model=%s, pre_k=%s)",
            os.getenv("KB_RERANK_MODEL", "qllama/bge-reranker-v2-m3"),
            os.getenv("KB_RERANK_PRE_K", "20"),
        )
        return OllamaReranker()
    logging.getLogger(__name__).info(
        "Reranker selected: NoopReranker (KB_RERANK=%s)", os.getenv("KB_RERANK")
    )
    return NoopReranker()
