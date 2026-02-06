from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from backend.modules.kb.domain.models import ChunkMetadata, KnowledgeChunk


@dataclass(frozen=True, slots=True)
class CaptionJob:
    index: int
    path: str


def rewrite_markdown_image_urls(md: str, *, resolve_src: Callable[[str], str]) -> str:
    text = md or ""

    def _md_repl(m: re.Match[str]) -> str:
        full = m.group(0)
        src = m.group(1)
        return full.replace(src, resolve_src(src))

    def _html_repl(m: re.Match[str]) -> str:
        tag = m.group(0)
        src = m.group(1)
        return tag.replace(src, resolve_src(src))

    text = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", _md_repl, text)
    text = re.sub(r"<img\s+[^>]*src=[\"']([^\"']+)[\"'][^>]*>", _html_repl, text, flags=re.I)
    return text


def extract_image_urls(text: str) -> List[str]:
    s = text or ""
    urls: List[str] = []
    seen: set[str] = set()

    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", s):
        u = (m.group(1) or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        urls.append(u)

    for m in re.finditer(r"<img\s+[^>]*src=[\"']([^\"']+)[\"'][^>]*>", s, flags=re.I):
        u = (m.group(1) or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        urls.append(u)

    return urls


def split_text_normal(*, text: str, kb_id: int, file_id: int, chunk_size: int, overlap: int) -> List[KnowledgeChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正数")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须为非负且小于 chunk_size")

    cleaned = (text or "").strip()
    chunks: List[KnowledgeChunk] = []
    start = 0
    n = len(cleaned)
    now_ms = int(time.time() * 1000)
    while start < n:
        end = min(start + int(chunk_size), n)
        chunk = cleaned[start:end]
        meta = ChunkMetadata.coerce({"number": "", "title": "", "path": []})
        chunks.append(
            KnowledgeChunk(
                kb_id=int(kb_id),
                file_id=int(file_id),
                chunk_index=len(chunks),
                content=chunk,
                metadata=meta,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            )
        )
        if end == n:
            break
        start = end - int(overlap)
    return chunks


def enrich_chunks_with_images_metadata(chunks: Sequence[KnowledgeChunk]) -> None:
    url_to_index: Dict[str, int] = {}
    next_index = 0
    for ch in chunks:
        meta: Dict[str, Any] = {}
        if getattr(ch, "metadata", None) is not None and getattr(ch.metadata, "data", None) is not None:
            meta = ch.metadata.data

        urls = extract_image_urls(str(getattr(ch, "content", "") or ""))
        if urls:
            images: List[Dict[str, Any]] = []
            for u in urls:
                u = (u or "").strip()
                if not u:
                    continue
                idx = url_to_index.get(u)
                if idx is None:
                    idx = next_index
                    url_to_index[u] = idx
                    next_index += 1
                images.append(
                    {"url": u, "caption": "", "chunk_index": int(getattr(ch, "chunk_index", -1)), "index": int(idx)}
                )
            meta["images"] = images
            meta["image_count"] = len(images)
        else:
            meta.pop("images", None)
            meta.pop("image_count", None)

        if getattr(ch, "metadata", None) is not None:
            ch.metadata.data = meta


def collect_caption_jobs(
    chunks: Sequence[KnowledgeChunk],
) -> List[CaptionJob]:
    jobs: List[CaptionJob] = []
    index_seen: set[int] = set()

    for ch in chunks:
        meta = (
            ch.metadata.data
            if getattr(ch, "metadata", None) is not None and getattr(ch.metadata, "data", None) is not None
            else {}
        )
        imgs = meta.get("images")
        if not isinstance(imgs, list):
            continue
        for it in imgs:
            if not isinstance(it, dict):
                continue
            raw_index = it.get("index")
            index = int(raw_index)
            if index in index_seen:
                continue
            url = (it.get("url") or "").strip()
            if not url:
                continue
            index_seen.add(index)
            jobs.append(CaptionJob(index=index, path=url))
    return jobs


def apply_captions_to_chunks(chunks: Sequence[KnowledgeChunk], *, captions_by_index: Mapping[int, str]) -> None:
    if not captions_by_index:
        return

    for ch in chunks:
        meta = (
            ch.metadata.data
            if getattr(ch, "metadata", None) is not None and getattr(ch.metadata, "data", None) is not None
            else {}
        )
        imgs = meta.get("images")
        if not isinstance(imgs, list):
            continue
        changed = False
        for it in imgs:
            if not isinstance(it, dict):
                continue
            index = it.get("index")
            cap = captions_by_index.get(index)
            if cap:
                it["caption"] = cap
                changed = True
        if changed and getattr(ch, "metadata", None) is not None:
            ch.metadata.data = meta
