from __future__ import annotations

from dataclasses import dataclass, replace
import re
import time
from typing import Callable, Dict, List, Optional, Sequence

from backend.modules.kb.domain.chunk_models import ChunkingInfo, DocumentChunk, ElementRefSegment, TextSegment
from backend.modules.kb.domain.element_models import ImageElement
from backend.modules.kb.domain.enums import ChunkingStrategy, ElementType


@dataclass(frozen=True, slots=True)
class _ImageOccurrence:
    start: int
    end: int
    src: str
    alt_text: Optional[str] = None


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

    def _strip_md_title_and_brackets(raw: str) -> str:
        u = (raw or "").strip()
        if not u:
            return ""
        if u.startswith("<") and u.endswith(">") and len(u) >= 2:
            u = u[1:-1].strip()
        u = re.sub(r"""\s+["'].*$""", "", u).strip()
        return u

    def _is_likely_image_ref(u: str) -> bool:
        val = (u or "").strip().lower()
        if not val:
            return False
        if "/assets/images/" in val:
            return True
        path = val.split("?", 1)[0].split("#", 1)[0]
        return bool(re.search(r"\.(png|jpe?g|gif|webp|bmp|svg|tiff?|ico)$", path))

    def _add(raw: str) -> None:
        u = _strip_md_title_and_brackets(raw)
        if not u or u in seen:
            return
        seen.add(u)
        urls.append(u)

    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", s):
        _add(m.group(1) or "")

    for m in re.finditer(r"<img\s+[^>]*src=[\"']([^\"']+)[\"'][^>]*>", s, flags=re.I):
        _add(m.group(1) or "")

    for m in re.finditer(
        r"(https?://[^\s<>'\")]+|file:///[^\s<>'\")]+|[a-zA-Z]:[\\/][^\s<>'\")]+)",
        s,
        flags=re.I,
    ):
        cand = (m.group(0) or "").strip()
        if not cand or not _is_likely_image_ref(cand):
            continue
        _add(cand)

    return urls


def _strip_markdown_src(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("<") and text.endswith(">") and len(text) >= 2:
        text = text[1:-1].strip()
    text = re.sub(r"""\s+["'].*$""", "", text).strip()
    return text


def _extract_image_occurrences(text: str) -> list[_ImageOccurrence]:
    occurrences: list[_ImageOccurrence] = []
    for match in re.finditer(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)", text or ""):
        occurrences.append(
            _ImageOccurrence(
                start=match.start(),
                end=match.end(),
                src=_strip_markdown_src(match.group("src") or ""),
                alt_text=(match.group("alt") or "").strip() or None,
            )
        )
    for match in re.finditer(r"<img\s+[^>]*src=[\"'](?P<src>[^\"']+)[\"'][^>]*>", text or "", flags=re.I):
        tag = match.group(0)
        alt_match = re.search(r"""alt=["']([^"']+)["']""", tag, flags=re.I)
        occurrences.append(
            _ImageOccurrence(
                start=match.start(),
                end=match.end(),
                src=(match.group("src") or "").strip(),
                alt_text=(alt_match.group(1).strip() if alt_match else None),
            )
        )
    occurrences.sort(key=lambda item: item.start)
    return occurrences


def _chunk_text(chunk: DocumentChunk) -> str:
    pieces: list[str] = []
    for segment in chunk.segments:
        if isinstance(segment, TextSegment):
            pieces.append(segment.text)
    return "".join(pieces)


def split_text_normal(*, text: str, kb_id: int, document_id: int, chunk_size: int, overlap: int) -> List[DocumentChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正数")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须为非负且小于 chunk_size")

    cleaned = (text or "").strip()
    chunks: List[DocumentChunk] = []
    start = 0
    n = len(cleaned)
    now_ms = int(time.time() * 1000)
    while start < n:
        end = min(start + int(chunk_size), n)
        chunk = cleaned[start:end]
        chunks.append(
            DocumentChunk(
                document_id=int(document_id),
                chunk_index=len(chunks),
                segments=[TextSegment(text=chunk)],
                elements=[],
                chunking=ChunkingInfo(
                    strategy=ChunkingStrategy.fixed_size,
                    rule="normal_splitter",
                    overlap=int(overlap),
                    generator="document_ingestion.split_text_normal",
                ),
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            )
        )
        if end == n:
            break
        start = end - int(overlap)
    return chunks


def enrich_chunks_with_images(chunks: Sequence[DocumentChunk]) -> list[DocumentChunk]:
    url_to_index: Dict[str, int] = {}
    out: list[DocumentChunk] = []
    for ch in chunks:
        text = _chunk_text(ch)
        occurrences = _extract_image_occurrences(text)
        if not occurrences:
            out.append(ch)
            continue

        segments: list[TextSegment | ElementRefSegment] = []
        elements = list(ch.elements)
        cursor = 0

        for occurrence in occurrences:
            if occurrence.start > cursor:
                leading = text[cursor:occurrence.start]
                if leading:
                    segments.append(TextSegment(text=leading))

            idx = url_to_index.get(occurrence.src)
            if idx is None:
                idx = len(url_to_index)
                url_to_index[occurrence.src] = idx
            element_id = f"image_{idx}"
            if not any(isinstance(element, ImageElement) and element.id == element_id for element in elements):
                elements.append(
                    ImageElement(
                        id=element_id,
                        uri=occurrence.src,
                        alt_text=occurrence.alt_text,
                    )
                )
            segments.append(ElementRefSegment(ref_id=element_id, ref_type=ElementType.image))
            cursor = occurrence.end

        if cursor < len(text):
            trailing = text[cursor:]
            if trailing:
                segments.append(TextSegment(text=trailing))

        out.append(replace(ch, segments=segments, elements=elements))

    return out

__all__ = [
    "enrich_chunks_with_images",
    "extract_image_urls",
    "rewrite_markdown_image_urls",
    "split_text_normal",
]
