from typing import List, Dict, Any, Optional
import os
import re
from langchain_openai import ChatOpenAI
from .base import Splitter
from .utils import parse_json_array, normalize_title
from .headings import HeadingsSplitter

class AdaptiveSplitter(Splitter):
    """自适应拆分器：识别目录块并按编号标题拆分正文，可选使用LLM解析目录。"""

    name = "adaptive"

    def __init__(self, use_llm: bool = False):
        self.use_llm = bool(use_llm)

    def _is_toc_line(self, line: str) -> bool:
        s = (line or "").strip()
        if not s:
            return False
        dotted = re.search(r"[\.··•⋅\u2026\-]{3,}", s) is not None
        page_num = re.search(r"\b\d{1,5}\s*$", s) is not None
        numbered = re.match(r"^\s*\d+(?:\.\d+)*\s+.+", s) is not None
        return (dotted and page_num) or (numbered and page_num)

    def _detect_toc_bounds(self, lines: List[str]) -> Optional[tuple[int, int, str]]:
        n = len(lines)
        title_idx = None
        title = ""
        title_re = re.compile(r"^\s*(contents|table of contents|目录)\s*$", re.IGNORECASE)
        for i, line in enumerate(lines[: min(n, 400)]):
            if title_re.match(line or ""):
                title_idx = i
                title = (line or "").strip()
                break
        start = None
        if title_idx is not None:
            start = title_idx
        else:
            for i, line in enumerate(lines[: min(n, 400)]):
                if self._is_toc_line(line):
                    start = i
                    title = "Table of Contents"
                    break
        if start is None:
            return None
        j = start + 1
        while j < n:
            s = (lines[j] or "")
            if self._is_toc_line(s) or not s.strip():
                j += 1
                continue
            break
        end = j
        if end - start < 3:
            return None
        return (start, end, title or "Table of Contents")

    def _llm_extract_toc_headings(self, toc_text: str) -> List[Dict[str, str]]:
        sample = (toc_text or "").strip()
        if not sample:
            return []
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return []
        llm = ChatOpenAI(
            temperature=0,
            max_retries=2,
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_key=api_key,
        )
        sys_prompt = (
            "你是目录解析器。仅根据下面的目录文本，提取真正的章节条目并输出 JSON 数组。\n"
            "- 每项结构：{number: '1.2.3', title: '章节标题'}\n"
            "- 保持顺序，不要包含页码或点线，不要返回除 JSON 外的任何文本。"
        )
        user_prompt = (
            "目录：\n" + sample + "\n\n请仅输出 JSON 数组，字段为 number 与 title。"
        )
        try:
            msg = llm.invoke([
                ("system", sys_prompt),
                ("user", user_prompt),
            ])
            arr = parse_json_array(getattr(msg, "content", "") or "")
            out: List[Dict[str, str]] = []
            seen = set()
            for h in arr:
                num = str(h.get("number", "")).strip()
                title = str(h.get("title", "")).strip()
                if not title:
                    continue
                key = (num, normalize_title(title))
                if key in seen:
                    continue
                seen.add(key)
                out.append({"number": num, "title": title})
            return out
        except Exception:
            return []

    def split(self, text: str) -> List[Dict[str, Any]]:
        lines = (text or "").splitlines()
        bounds = self._detect_toc_bounds(lines)
        if not bounds:
            return HeadingsSplitter().split(text)
        s, e, title = bounds
        toc_text = "\n".join(lines[s:e]).strip()
        rest = "\n".join(lines[:s] + lines[e:])
        allowed: Optional[List[Dict[str, str]]] = None
        if self.use_llm:
            allowed = self._llm_extract_toc_headings(toc_text)
        chunks_rest = HeadingsSplitter(allowed_headings=allowed).split(rest)
        out: List[Dict[str, Any]] = []
        out.append({
            "content": toc_text,
            "metadata": {"number": "", "title": title, "path": [], "type": "toc"},
        })
        out.extend(chunks_rest)
        return out