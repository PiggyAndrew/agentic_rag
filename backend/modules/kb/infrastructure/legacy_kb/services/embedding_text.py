from __future__ import annotations

from typing import Any


def compose_embedding_text(content: str, metadata: Any) -> str:
    base = str(content or "")
    if not base.strip():
        return base
    md = metadata.data if hasattr(metadata, "data") else (metadata or {})
    if not isinstance(md, dict):
        return base
    imgs = md.get("images")
    if not isinstance(imgs, list):
        return base
    caps: list[str] = []
    seen: set[str] = set()
    for it in imgs:
        if not isinstance(it, dict):
            continue
        cap = (it.get("caption") or "").strip()
        if not cap or cap in seen:
            continue
        seen.add(cap)
        caps.append(cap)
    if not caps:
        return base
    return (base + "\n\n[ImageCaptions]\n" + "\n".join(f"- {c}" for c in caps)).strip()

