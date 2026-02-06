from __future__ import annotations

from typing import Any, Dict, List, Mapping

from backend.modules.kb.domain.ports import ImageCaptionerPort
from backend.modules.kb.infrastructure.legacy_kb.services.image_caption import caption_jobs


class LegacyImageCaptioner(ImageCaptionerPort):
    def caption(self, jobs: List[Dict[str, Any]], *, batch_size: int=1) -> Mapping[int, str]:
        results = caption_jobs(jobs, batch_size=batch_size)
        out: Dict[int, str] = {}
        for r in results or []:
            if not isinstance(r, dict):
                continue
            out[int(r.get("index"))] =  (r.get("description") or "").strip()
        return out
