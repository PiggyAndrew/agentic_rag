from typing import List, Dict, Any, Optional
import re
from .base import Splitter
from .utils import normalize_title


class HeadingsSplitter(Splitter):
    """编号/附录标题拆分器。"""

    name = "headings"

    def __init__(self, allowed_headings: Optional[List[Dict[str, str]]] = None):
        self.allowed_headings = allowed_headings or []

    def split(self, text: str) -> List[Dict[str, Any]]:
        lines = (text or "").splitlines()
        heading_re = re.compile(r"^\s*(\d+(?:\.\d+)*)(?:\s+|\s*[\-\u2013]\s*)(.+?)\s*$")
        appendix_re = re.compile(r"^\s*(?:Appendix\s+)?([A-Za-z])(?:\.|\-|\s)+(.+?)\s*$")

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
                n = norm_num(str(h.get("number", "")))
                t = normalize_title(h.get("title", ""))
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
                a_letter = norm_num(ma.group(1).strip().upper())
                a_title = ma.group(2).strip()
                if normalize_title(a_title) in {"contents", "table of contents", "目录"}:
                    continue
                if allowed_pairs:
                    pair = (a_letter, normalize_title(a_title))
                    if pair not in allowed_pairs:
                        ref = allowed_map.get(a_letter)
                        if not ref or not (
                            normalize_title(a_title) == ref
                            or normalize_title(a_title).startswith(ref)
                            or ref in normalize_title(a_title)
                        ):
                            continue
                current_appendix = (a_letter, a_title)
                last_appendix_segments = None
                heads.append({"index": i, "number": a_letter, "title": a_title})
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
            if current_appendix is not None:
                segs = _parse_num_segments(num_norm)
                if segs is None:
                    continue
                if not _is_plausible_next(last_appendix_segments, segs):
                    continue
                last_appendix_segments = segs

            final_num = num_norm if current_appendix is None else f"{current_appendix[0]}.{num_norm}"
            heads.append({"index": i, "number": final_num, "title": title})

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