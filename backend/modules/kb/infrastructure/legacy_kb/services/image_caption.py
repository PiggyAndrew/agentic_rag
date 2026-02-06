from __future__ import annotations

from typing import Any, Dict, List, Optional


def caption_images(batch_images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        from backend.infrastructure.vll.providers import get_configured_vision_agent
    except Exception:
        return []
    try:
        agent = get_configured_vision_agent()
        res = agent.analyze_image(batch_images)
        return res if isinstance(res, list) else []
    except Exception:
        return []


def caption_jobs(jobs: List[Dict[str, Any]], *, batch_size: int = 1) -> List[Dict[str, Any]]:
    if not jobs:
        return []
    bs = max(1, int(batch_size))
    picked = jobs
    out: List[Dict[str, Any]] = []
    for start in range(0, len(picked), bs):
        batch = picked[start : start + bs]
        if not batch:
            continue
        batch_results = caption_images(batch)
        for i, it in enumerate(batch_results or []):
            if isinstance(it, dict):
                it["index"] = batch[i].get("index")
        out.extend(batch_results)
    return out
