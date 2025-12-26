from typing import List, Dict, Any, Optional
import re
from pydantic import BaseModel
from .splitter_base import Splitter
from .splitter_utils import normalize_title


class HeadingItem(BaseModel):
    """
    Represents a heading item with a number and a title.
    """
    number: str
    title: str


class HeadingsSplitter(Splitter):
    """编号/附录标题拆分器。"""

    name = "headings"

    def __init__(self, allowed_headings: Optional[List[HeadingItem]] = None):
        self.allowed_headings = allowed_headings or []

    def _scan_with_allowed(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Strictly scan lines for allowed headings."""
        heads: List[Dict[str, Any]] = []
        matchers = []
        for h in self.allowed_headings:
            n = str(h.number).strip()
            t = normalize_title(h.title)
            if not n:
                continue
            # Match number at start of line, followed by separator or end of line
            # Separators: dot, space, colon, dash, closing paren
            # We use re.escape to handle dots in number (e.g. "1.1")
            pat = re.compile(r"^\s*" + re.escape(n) + r"(?=$|[\.\s\:\-\u2013\)])", re.IGNORECASE)
            matchers.append((pat, t, n, h.title))

        for i, line in enumerate(lines):
            line_norm = normalize_title(line)
            for (pat, t_norm, n_raw, t_raw) in matchers:
                if pat.match(line):
                    # Check if normalized title is present
                    if t_norm in line_norm:
                        heads.append({"index": i, "number": n_raw, "title": t_raw})
                        break
        return heads

    def _chunk(self, lines: List[str], heads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not heads:
            return [{"content": "\n".join(lines).strip(), "metadata": {"number": "", "title": "", "path": []}}]

        number_to_title: Dict[str, str] = {h["number"]: h["title"] for h in heads}
        chunks: List[Dict[str, Any]] = []

        ordered = sorted(heads, key=lambda x: x["index"])
        for idx, h in enumerate(ordered):
            start = h["index"]
            end = ordered[idx + 1]["index"] if idx + 1 < len(ordered) else len(lines)
            content = "\n".join(lines[start:end]).strip()
            segs = h["number"].split(".")
            path: List[Dict[str, Any]] = []
            for j in range(1, len(segs) + 1):
                key = ".".join(segs[:j])
                if key in number_to_title:
                    path.append({"number": key, "title": number_to_title[key]})
                else:
                    if j == len(segs):
                        path.append({"number": key, "title": h["title"]})
            chunks.append({
                "content": content,
                "metadata": {"number": h["number"], "title": h["title"], "path": path},
            })
        return chunks

    def split(self, text: str) -> List[Dict[str, Any]]:
        lines = (text or "").splitlines()

        if self.allowed_headings:
            heads = self._scan_with_allowed(lines)
            return self._chunk(lines, heads)

        heading_re = re.compile(r"^\s*(\d+(?:\.\d+)*)(?:\s+|\s*[\-\u2013]\s*)(.+?)\s*$")
        appendix_re = re.compile(r"^\s*(?:Appendix\s+)(\d+|[A-Za-z])(?:\.|\-|\s)+(.+?)\s*$", re.IGNORECASE)
        appendix_letter_re = re.compile(r"^\s*([A-Za-z])(?:\.|\-|\s)+(.+?)\s*$")

        def looks_like_table_row(title: str) -> bool:
            """
            判断一行是否更像表格行而非章节标题。

            在 PDF 文本中，表格行常包含多个数值列（如 RGB、LOD 等），例如：
            "Ramps 175-175-175 300 500"
            这种行如果被当作章节会造成错误拆分。
            """
            t = (title or "").strip()
            if not t:
                return False
            numeric_tokens = re.findall(r"\b\d+(?:[,\-]\d+)*\b", t)
            if len(numeric_tokens) >= 2:
                return True
            if re.search(r"\b\d{1,4}(?:-\d{1,4}){2,}\b", t):
                return True
            return False

        def norm_num(n: str) -> str:
            n = (n or "").strip()
            if n.endswith("."):
                n = n[:-1]
            return n

        heads: List[Dict[str, Any]] = []
        allowed_pairs: set[tuple[str, str]] = set()
        allowed_map: Dict[str, str] = {}
        if self.allowed_headings:
            for h in self.allowed_headings:
                # Use attribute access for Pydantic model
                raw_n = str(h.number).strip()
                m_app = re.match(r"^\s*Appendix\s+(\d+|[A-Za-z])\s*$", raw_n, flags=re.IGNORECASE)
                if m_app:
                    n = f"Appendix {norm_num(m_app.group(1).strip().upper())}"
                else:
                    n = norm_num(raw_n)
                t = normalize_title(h.title)
                if t:
                    allowed_map[n] = t
                    allowed_pairs.add((n, t))

        current_appendix: Optional[tuple[str, str]] = None
        last_appendix_segments: Optional[List[int]] = None

        def _parse_num_segments(s: str) -> Optional[List[int]]:
            s = (s or "").strip()
            if not s:
                return None
            try:
                parts = s.split(".")
                segs = [int(p) for p in parts if p != ""]
                return segs if segs else None
            except Exception:
                return None

        def _is_plausible_next(last: Optional[List[int]], cur: List[int]) -> bool:
            if not last:
                return len(cur) >= 1 and cur[0] == 1
            Ln, Cn = len(last), len(cur)
            if Cn == Ln and cur[:-1] == last[:-1] and cur[-1] == last[-1] + 1:
                return True
            if Cn == Ln + 1 and cur[:Ln] == last and cur[-1] == 1:
                return True
            if Cn < Ln:
                prefix = last[:Cn]
                if cur[:-1] == prefix[:-1] and cur[-1] == prefix[-1] + 1:
                    return True
            return False

        for i, raw in enumerate(lines):
            line = raw or ""

            ma = appendix_re.match(line)
            if ma:
                a_id = f"Appendix {norm_num(ma.group(1).strip().upper())}"
                a_title = ma.group(2).strip()
                if normalize_title(a_title) in {"contents", "table of contents", "目录"}:
                    continue
                if allowed_pairs:
                    pair = (a_id, normalize_title(a_title))
                    if pair not in allowed_pairs:
                        ref = allowed_map.get(a_id)
                        if not ref or not (
                            normalize_title(a_title) == ref
                            or normalize_title(a_title).startswith(ref)
                            or ref in normalize_title(a_title)
                        ):
                            continue
                current_appendix = (a_id, a_title)
                last_appendix_segments = None
                heads.append({"index": i, "number": a_id, "title": a_title})
                continue
            mb = appendix_letter_re.match(line)
            if mb:
                a_id = norm_num(mb.group(1).strip().upper())
                a_title = mb.group(2).strip()
                if normalize_title(a_title) in {"contents", "table of contents", "目录"}:
                    continue
                if allowed_pairs:
                    pair = (a_id, normalize_title(a_title))
                    if pair not in allowed_pairs:
                        ref = allowed_map.get(a_id)
                        if not ref or not (
                            normalize_title(a_title) == ref
                            or normalize_title(a_title).startswith(ref)
                            or ref in normalize_title(a_title)
                        ):
                            continue
                current_appendix = (a_id, a_title)
                last_appendix_segments = None
                heads.append({"index": i, "number": a_id, "title": a_title})
                continue

            m = heading_re.match(line)
            if not m:
                continue
            num_raw = m.group(1).strip()
            title = m.group(2).strip()
            if title.lower() in {"contents", "table of contents", "目录"}:
                continue
            if re.match(r"^\s*\d+\)\s+", line):
                continue
            if re.search(r"\b\d{1,5}\s*$", line) and re.search(r"[\.·\-]{3,}", line):
                continue

            num_norm = norm_num(num_raw)
            cand_pair = (num_norm, normalize_title(title))
            if allowed_pairs and cand_pair not in allowed_pairs and current_appendix is None:
                continue
            if current_appendix is not None and looks_like_table_row(title):
                continue
            if current_appendix is not None:
                segs = _parse_num_segments(num_norm)
                if segs is None:
                    continue
                if not _is_plausible_next(last_appendix_segments, segs):
                    continue
                last_appendix_segments = segs

            final_num = num_norm if current_appendix is None else f"{current_appendix[0]}.{num_norm}"
            heads.append({"index": i, "number": final_num, "title": title})

        return self._chunk(lines, heads)
