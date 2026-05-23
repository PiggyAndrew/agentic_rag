from __future__ import annotations

from dataclasses import replace
import logging
from typing import Any, Dict, List, Sequence

from backend.infrastructure.vll.providers import get_configured_vision_agent
from backend.modules.kb.domain.chunk_models import DocumentChunk
from backend.modules.kb.domain.element_models import ImageElement
from backend.modules.kb.domain.ports import ImageCaptionerPort


logger = logging.getLogger(__name__)


class LegacyImageCaptioner(ImageCaptionerPort):
    def __init__(self, vision_agent: Any | None = None) -> None:
        self._vision_agent = vision_agent or get_configured_vision_agent()

    def _caption_single(self, image: Dict[str, Any]) -> str:
        result = self._vision_agent.analyze_image(image)
        if not isinstance(result, dict):
            logger.warning("Vision agent returned non-dict result: %s", type(result))
            return ""
        return (result.get("description") or "").strip()

    def caption(
        self,
        chunks: Sequence[DocumentChunk],
        *,
        batch_size: int = 1,
        max_images: int | None = None,
    ) -> List[DocumentChunk]:
        seen_image_ids: set[str] = set()
        captions_by_image_id: Dict[str, str] = {}
        processed_count = 0

        for chunk in chunks:
            for element in chunk.elements:
                if max_images is not None and processed_count >= int(max_images):
                    break
                if not isinstance(element, ImageElement):
                    continue
                image_id = str(element.id)
                image_uri = (element.uri or "").strip()
                if not image_uri or image_id in seen_image_ids:
                    continue
                seen_image_ids.add(image_id)
                caption = self._caption_single({"path": image_uri})
                if caption:
                    captions_by_image_id[image_id] = caption
                processed_count += 1
            if max_images is not None and processed_count >= int(max_images):
                break

        if not captions_by_image_id:
            return list(chunks)

        out: List[DocumentChunk] = []
        for chunk in chunks:
            changed = False
            elements = list(chunk.elements)
            for idx, element in enumerate(elements):
                if not isinstance(element, ImageElement):
                    continue
                caption = captions_by_image_id.get(element.id)
                if not caption:
                    continue
                elements[idx] = replace(element, caption=caption)
                changed = True
            out.append(replace(chunk, elements=elements) if changed else chunk)
        return out
