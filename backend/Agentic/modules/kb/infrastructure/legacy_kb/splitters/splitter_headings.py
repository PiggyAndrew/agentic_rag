from typing import Any, Dict, List, Optional
from dataclasses import replace
import re
import time

from pydantic import BaseModel

from .splitter_base import Splitter
from .splitter_utils import normalize_title
from backend.modules.kb.domain.chunk_models import ChunkingInfo, DocumentChunk, TextSegment
from backend.modules.kb.domain.enums import ChunkingStrategy


class HeadingItem(BaseModel):
    number: str
    title: str


class HeadingsSplitter(Splitter):
    name = "headings"

    def __init__(
        self,
        allowed_headings: Optional[List[HeadingItem]] = None,
        *,
        min_subchunk_chars: int = 100,
    ):
        self.allowed_headings = allowed_headings or []
        self.min_subchunk_chars = int(min_subchunk_chars)

    _md_heading_re = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")
    _numbered_title_re = re.compile(r"^\s*(\d+(?:\.\d+)*)(?:\s*[\.)])?\s*(?:[-–—:：]\s*)?(.+?)\s*$")

    @staticmethod
    def _structure_path(meta: Dict[str, Any]) -> list[str]:
        raw_path = meta.get("path") or []
        path: list[str] = []
        if isinstance(raw_path, list):
            for item in raw_path:
                if isinstance(item, dict):
                    number = str(item.get("number") or "").strip()
                    title = str(item.get("title") or "").strip()
                    value = f"{number} {title}".strip() if (number or title) else ""
                    if value:
                        path.append(value)
        if path:
            return path
        number = str(meta.get("number") or "").strip()
        title = str(meta.get("title") or "").strip()
        value = f"{number} {title}".strip() if (number or title) else ""
        return [value] if value else []
    _bullet_line_re = re.compile(r"^\s*[*+-]\s+(.+?)\s*$")
    _appendix_title_re = re.compile(r"^\s*(appendix\s+(?:\d+|[a-z]))\s+(.+?)\s*$", re.IGNORECASE)
    _letter_numbered_title_re = re.compile(r"^\s*([a-z])\.(\d+(?:\.\d+)*)\s+(.+?)\s*$", re.IGNORECASE)

    def _strip_heading_prefix(self, line: str) -> tuple[int, str]:
        s = line or ""
        m = self._md_heading_re.match(s)
        if not m:
            return (0, s)
        level = len(m.group(1))
        return (level, m.group(2).strip())

    def _strip_emphasis(self, s: str) -> str:
        s = (s or "")
        s = re.sub(r"^\s*(?:\*\*|\*|_)\s*", "", s)
        s = re.sub(r"\s*(?:\*\*|\*|_)\s*$", "", s)
        s = re.sub(r"[\*_]+", "", s)
        return s

    def _norm_number(self, n: str) -> str:
        n = (n or "").strip()
        if n.endswith("."):
            n = n[:-1]
        n = re.sub(r"\s+", " ", n)
        return n

    def _order_key_list(self, number: str) -> List[int]:
        n = self._norm_number(number)
        if not n:
            return []
        m_app = re.match(r"^Appendix\s+([A-Za-z0-9]+)(?:\.(\d+(?:\.\d+)*))?$", n)
        if m_app:
            head = m_app.group(1)
            rest = m_app.group(2) or ""
            base: List[int] = [10000]
            if head.isalpha():
                base.append(ord(head.upper()))
            else:
                try:
                    base.append(int(head))
                except Exception:
                    base.append(0)
            for seg in [p for p in rest.split(".") if p]:
                try:
                    base.append(int(seg))
                except Exception:
                    base.append(0)
            return base
        parts = [p for p in n.split(".") if p]
        out: List[int] = []
        for p in parts:
            try:
                out.append(int(p))
            except Exception:
                out.append(0)
        return out

    def _number_pattern(self, number: str) -> re.Pattern[str]:
        n = self._norm_number(number)
        if re.fullmatch(r"\d+(?:\.\d+)*", n):
            esc = re.escape(n)
            return re.compile(rf"{esc}(?:\s*[\.)])?")
        esc = re.escape(n)
        return re.compile(rf"{esc}", re.IGNORECASE)

    def _content_size(self, text: str) -> int:
        return len(re.sub(r"\s+", "", text or ""))

    def _parse_numbered_title(self, text: str) -> Optional[tuple[str, str]]:
        s = self._strip_emphasis(text or "")
        am = self._appendix_title_re.match(s)
        if am:
            raw = re.sub(r"\s+", " ", am.group(1).strip())
            raw = re.sub(r"^appendix\s+", "Appendix ", raw, flags=re.IGNORECASE)
            tail = raw.split(" ", 1)[1].strip() if " " in raw else raw
            tail = tail.upper()
            num = self._norm_number(f"Appendix {tail}")
            title = (am.group(2) or "").strip()
            if num and title:
                return (num, title)

        lm = self._letter_numbered_title_re.match(s)
        if lm:
            num = self._norm_number(f"{lm.group(1).upper()}.{lm.group(2)}")
            title = (lm.group(3) or "").strip()
            if num and title:
                return (num, title)

        m = self._numbered_title_re.match(s)
        if not m:
            return None
        num = self._norm_number(m.group(1))
        title = (m.group(2) or "").strip()
        if not num or not title:
            return None
        return (num, title)

    def _build_number_path(self, number: str, number_to_title: Dict[str, str]) -> List[Dict[str, Any]]:
        n = self._norm_number(number)
        if not n:
            return []
        m_app = re.match(r"^Appendix\s+([A-Za-z0-9]+)(?:\.(\d+(?:\.\d+)*))?$", n)
        if m_app:
            prefix = f"Appendix {m_app.group(1)}"
            rest = m_app.group(2) or ""
            segs = [prefix] + ([p for p in rest.split(".") if p] if rest else [])
            path: List[Dict[str, Any]] = []
            for j in range(1, len(segs) + 1):
                key = segs[0] if j == 1 else (segs[0] + "." + ".".join(segs[1:j]))
                title = number_to_title.get(key)
                if title is not None:
                    path.append({"number": key, "title": title})
            if not path or path[-1]["number"] != n:
                path.append({"number": n, "title": number_to_title.get(n, "")})
            return path
        if "." not in n:
            return [{"number": n, "title": number_to_title.get(n, "")}] if number_to_title.get(n) else [{"number": n, "title": ""}]
        segs = [p for p in n.split(".") if p]
        path: List[Dict[str, Any]] = []
        for j in range(1, len(segs) + 1):
            key = ".".join(segs[:j])
            title = number_to_title.get(key)
            if title is not None:
                path.append({"number": key, "title": title})
        if not path or path[-1]["number"] != n:
            path.append({"number": n, "title": number_to_title.get(n, "")})
        return path

    def _scan_allowed_chapters(self, lines: List[str]) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        allowed: List[Dict[str, Any]] = []
        number_to_title: Dict[str, str] = {}
        for h in self.allowed_headings:
            number = self._norm_number(getattr(h, "number", ""))
            title = (getattr(h, "title", "") or "").strip()
            title_norm = normalize_title(title)
            if not number or not title_norm:
                continue
            allowed.append(
                {
                    "number": number,
                    "title": title,
                    "title_norm": title_norm,
                    "pat": self._number_pattern(number),
                    "order_key": self._order_key_list(number),
                }
            )
            number_to_title[number] = title

        if not allowed:
            return ([], {})

        chapters: List[Dict[str, Any]] = []
        seen_numbers: set[str] = set()
        last_num: str = ""
        for i, raw in enumerate(lines):
            level, body = self._strip_heading_prefix(raw)
            if level <= 0:
                continue
            body = self._strip_emphasis(body)
            body_norm = normalize_title(body)
            if not body_norm:
                continue
            for a in allowed:
                num = a["number"]
                if num in seen_numbers:
                    continue
                if not a["pat"].search(body):
                    continue
                if a["title_norm"] not in body_norm:
                    continue
                if last_num:
                    prev = self._order_key_list(last_num)
                    cur = a.get("order_key") or []
                    if prev and cur:
                        is_child = len(cur) > len(prev) and cur[: len(prev)] == prev
                        is_same_level_next = len(cur) == len(prev) and cur[:-1] == prev[:-1] and cur[-1] == prev[-1] + 1
                        is_upper_level_next = len(cur) < len(prev) and cur[:-1] == prev[: len(cur) - 1] and cur[-1] >= prev[len(cur) - 1] + 1
                        is_next_major = len(cur) == 1 and len(prev) >= 1 and cur[0] == prev[0] + 1
                        is_appendix = cur and cur[0] == 10000
                        if not (is_child or is_same_level_next or is_upper_level_next or is_next_major or is_appendix):
                            continue
                chapters.append({"index": i, "level": level, "number": num, "title": a["title"]})
                seen_numbers.add(num)
                last_num = num
                break

        chapters = sorted(chapters, key=lambda x: x["index"])
        return (chapters, number_to_title)

    def _split_by_markdown_headings(self, lines: List[str]) -> List[Dict[str, Any]]:
        heads: List[Dict[str, Any]] = []
        min_level = 7
        for i, raw in enumerate(lines):
            m = self._md_heading_re.match(raw or "")
            if not m:
                continue
            lvl = len(m.group(1))
            min_level = min(min_level, lvl)
            heads.append({"index": i, "level": lvl, "title": m.group(2).strip()})
        if not heads:
            return [{"content": "\n".join(lines).strip(), "metadata": {"number": "", "title": "", "path": []}}]
        chapters = [h for h in heads if h["level"] == min_level]
        if not chapters:
            return [{"content": "\n".join(lines).strip(), "metadata": {"number": "", "title": "", "path": []}}]
        out: List[Dict[str, Any]] = []
        for idx, ch in enumerate(chapters):
            start = ch["index"]
            end = chapters[idx + 1]["index"] if idx + 1 < len(chapters) else len(lines)
            chapter_lines = lines[start:end]
            parsed = self._parse_numbered_title(ch["title"]) or None
            chapter_number = parsed[0] if parsed else ""
            out.extend(
                self._split_chapter_by_subheadings(
                    chapter_lines,
                    chapter_level=ch["level"],
                    chapter_number=chapter_number,
                    chapter_title=ch["title"],
                    chapter_path=[],
                )
            )
        return out

    def _merge_small_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(chunks) <= 1 or self.min_subchunk_chars <= 0:
            return chunks
        out: List[Dict[str, Any]] = []
        i = 0
        while i < len(chunks):
            cur = chunks[i]
            merged_content = cur.get("content", "")
            j = i
            while j < len(chunks) - 1 and self._content_size(merged_content) < self.min_subchunk_chars:
                nxt = chunks[j + 1]
                if cur.get("metadata", {}).get("number") != nxt.get("metadata", {}).get("number"):
                    break
                merged_content = (merged_content.strip() + "\n" + nxt.get("content", "").strip()).strip()
                j += 1
            cur["content"] = merged_content
            out.append(cur)
            i = j + 1
        if len(out) > 1 and self._content_size(out[-1].get("content", "")) < self.min_subchunk_chars:
            prev = out[-2]
            last = out[-1]
            if prev.get("metadata", {}).get("number") == last.get("metadata", {}).get("number"):
                prev["content"] = (prev.get("content", "").strip() + "\n" + last.get("content", "").strip()).strip()
                out.pop()
        return out

    def _split_chapter_by_subheadings(
        self,
        chapter_lines: List[str],
        *,
        chapter_level: int,
        chapter_number: str,
        chapter_title: str,
        chapter_path: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not chapter_lines:
            return []
        base_level = chapter_level if 1 <= chapter_level <= 6 else 1
        chapter_num_norm = self._norm_number(chapter_number)
        is_appendix_chapter = bool(re.match(r"^Appendix\s+", chapter_num_norm))
        subheads: List[Dict[str, Any]] = []
        seen_sub_numbers: set[str] = set()

        def _accept_number(n: str) -> bool:
            if "." not in n:
                return False
            if chapter_num_norm and not (n == chapter_num_norm or n.startswith(chapter_num_norm + ".")):
                return False
            if n in seen_sub_numbers:
                return False
            return True

        def _add_subhead(i: int, n: str, t: str, lvl: int) -> None:
            nn = self._norm_number(n)
            if not _accept_number(nn):
                return
            seen_sub_numbers.add(nn)
            subheads.append({"index": i, "level": int(lvl), "number": nn, "title": (t or "").strip()})

        for i in range(1, len(chapter_lines)):
            line = chapter_lines[i] or ""
            m = self._md_heading_re.match(line)
            if m:
                lvl = len(m.group(1))
                if lvl <= base_level:
                    continue
                raw_title = m.group(2).strip()
                parsed = self._parse_numbered_title(raw_title)
                if parsed is not None:
                    n, t = parsed
                    _add_subhead(i, n, t, lvl)
                else:
                    subheads.append({"index": i, "level": lvl, "number": "", "title": self._strip_emphasis(raw_title)})
                continue

            bm = self._bullet_line_re.match(line)
            if bm:
                raw = bm.group(1).strip()
                parsed = self._parse_numbered_title(raw)
                if parsed is None:
                    continue
                n, t = parsed
                _add_subhead(i, n, t, base_level + 1)
                continue

            parsed = self._parse_numbered_title(line.strip())
            if parsed is not None:
                n, t = parsed
                _add_subhead(i, n, t, base_level + 1)
                continue
            if is_appendix_chapter:
                s = (line or "").strip()
                bm_bold = re.match(r"^\s*(?:\*\*|__)\s*(.+?)\s*(?:\*\*|__)\s*$", s)
                if bm_bold:
                    raw_title = bm_bold.group(1).strip()
                    subheads.append({"index": i, "level": base_level + 1, "number": "", "title": raw_title})
                    continue
        if not subheads:
            content = "\n".join(chapter_lines).strip()
            return [{"content": content, "metadata": {"number": chapter_number, "title": chapter_title, "path": chapter_path}}] if content else []

        start_to_sub = {h["index"]: (h.get("number", ""), h.get("title", "")) for h in subheads}
        boundaries = [0] + [h["index"] for h in subheads]
        chunks: List[Dict[str, Any]] = []
        for k, start in enumerate(boundaries):
            end = boundaries[k + 1] if k + 1 < len(boundaries) else len(chapter_lines)
            content = "\n".join(chapter_lines[start:end]).strip()
            if not content:
                continue
            if start == 0:
                meta = {"number": chapter_number, "title": chapter_title, "path": chapter_path}
                meta["order_key"] = self._order_key_list(chapter_number)
            else:
                sub_number, sub_title = start_to_sub.get(start, ("", ""))
                sub_number = self._norm_number(sub_number)
                sub_title = (sub_title or "").strip()
                sub_path = list(chapter_path)
                if sub_title:
                    sub_path.append({"number": sub_number, "title": sub_title})
                cur_num = sub_number or chapter_number
                meta = {"number": cur_num, "title": sub_title or chapter_title, "path": sub_path}
                meta["order_key"] = self._order_key_list(cur_num)
            chunks.append({"content": content, "metadata": meta})
        return self._merge_small_chunks(chunks)

    def split(self, text: str, kb_id: int = 0, document_id: int = 0) -> List[DocumentChunk]:
        lines = (text or "").splitlines()
        if not lines:
            now_ms = int(time.time() * 1000)
            return [
                DocumentChunk(
                    document_id=int(document_id),
                    chunk_index=0,
                    segments=[TextSegment(text="")],
                    chunking=ChunkingInfo(
                        strategy=ChunkingStrategy.heading_based,
                        rule="headings_splitter",
                        generator=self.name,
                    ),
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                )
            ]

        if not self.allowed_headings:
            dict_chunks = self._split_by_markdown_headings(lines)
            now_ms = int(time.time() * 1000)
            out: List[DocumentChunk] = []
            for i, d in enumerate(dict_chunks):
                meta = d.get("metadata") if isinstance(d.get("metadata"), dict) else {}
                out.append(
                    DocumentChunk(
                        document_id=int(document_id),
                        chunk_index=i,
                        segments=[TextSegment(text=str(d.get("content", "")))],
                        structure_path=self._structure_path(meta),
                        chunking=ChunkingInfo(
                            strategy=ChunkingStrategy.heading_based,
                            rule="headings_splitter",
                            generator=self.name,
                        ),
                        created_at_ms=now_ms,
                        updated_at_ms=now_ms,
                    )
                )
            return out

        chapters, number_to_title = self._scan_allowed_chapters(lines)
        if not chapters:
            dict_chunks = [{"content": "\n".join(lines).strip(), "metadata": {"number": "", "title": "", "path": []}}]
            now_ms = int(time.time() * 1000)
            meta = dict_chunks[0].get("metadata") if isinstance(dict_chunks[0].get("metadata"), dict) else {}
            return [
                DocumentChunk(
                    document_id=int(document_id),
                    chunk_index=0,
                    segments=[TextSegment(text=str(dict_chunks[0].get("content", "")))],
                    structure_path=self._structure_path(meta),
                    chunking=ChunkingInfo(
                        strategy=ChunkingStrategy.heading_based,
                        rule="headings_splitter",
                        generator=self.name,
                    ),
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                )
            ]

        out_dict: List[Dict[str, Any]] = []
        for idx, ch in enumerate(chapters):
            start = ch["index"]
            end = chapters[idx + 1]["index"] if idx + 1 < len(chapters) else len(lines)
            chapter_lines = lines[start:end]
            chapter_number = ch["number"]
            chapter_title = ch["title"]
            chapter_path = self._build_number_path(chapter_number, number_to_title)
            out_dict.extend(
                self._split_chapter_by_subheadings(
                    chapter_lines,
                    chapter_level=ch.get("level", 0),
                    chapter_number=chapter_number,
                    chapter_title=chapter_title,
                    chapter_path=chapter_path,
                )
            )
        now_ms = int(time.time() * 1000)
        out: List[DocumentChunk] = []
        for i, d in enumerate(out_dict):
            meta = d.get("metadata") if isinstance(d.get("metadata"), dict) else {}
            out.append(
                DocumentChunk(
                    document_id=int(document_id),
                    chunk_index=i,
                    segments=[TextSegment(text=str(d.get("content", "")))],
                    structure_path=self._structure_path(meta),
                    chunking=ChunkingInfo(
                        strategy=ChunkingStrategy.heading_based,
                        rule="headings_splitter",
                        generator=self.name,
                    ),
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                )
            )
        return out
