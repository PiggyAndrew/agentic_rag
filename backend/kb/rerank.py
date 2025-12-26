from typing import List, Dict, Any, Callable, Optional
import os


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


class CrossEncoderReranker(Reranker):
    """基于 sentence-transformers CrossEncoder 的重排实现。"""

    def __init__(self, model_name: Optional[str] = None, pre_k: Optional[int] = None):
        self.model_name = model_name or os.getenv("KB_RERANK_MODEL", "dengcao/Qwen3-Reranker-8B:Q3_K_M")
        self.pre_k = int(pre_k or os.getenv("KB_RERANK_PRE_K", "20"))
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder  # type: ignore
            self._model = CrossEncoder(self.model_name)

    def rerank(self, query: str, initial: List[Dict[str, Any]], load_content: Callable[[int, int], str], top_k: int = 5) -> List[Dict[str, Any]]:
        if not initial:
            return []
        try:
            self._ensure_model()
        except Exception:
            # 模型不可用则直接回退初始结果
            return initial[:top_k]

        pairs = []
        keep_idx: List[int] = []
        for i, r in enumerate(initial):
            fid = int(r.get("file_id"))
            idx = int(r.get("chunk_index"))
            content = load_content(fid, idx) or r.get("preview", "")
            if not content:
                continue
            pairs.append((query, content))
            keep_idx.append(i)
        if not pairs:
            return initial[:top_k]

        try:
            scores = self._model.predict(pairs)
        except Exception:
            return initial[:top_k]

        ranked: List[Dict[str, Any]] = []
        for k, i in enumerate(keep_idx):
            item = dict(initial[i])
            item["rerank_score"] = float(scores[k])
            ranked.append(item)
        ranked.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return ranked[:top_k]


def get_default_reranker() -> Reranker:
    """根据环境变量返回默认 Reranker。

    - 当 `KB_RERANK` 为真（1/true/yes）时，使用 `CrossEncoderReranker`。
    - 否则，使用 `NoopReranker`。
    """
    if _truthy(os.getenv("KB_RERANK")):
        return CrossEncoderReranker()
    return NoopReranker()