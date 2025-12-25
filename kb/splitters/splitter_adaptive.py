from typing import List, Dict, Any, Optional
import os
import re
from dotenv import load_dotenv
from app.prompts import get_toc_parser_system_prompt, get_toc_parser_user_prompt
from .splitter_base import Splitter
from .splitter_utils import parse_json_array, normalize_title, is_toc_line, detect_toc_bounds
from .splitter_headings import HeadingsSplitter, HeadingItem


def get_toc_parsing_llm() -> Optional[object]:
    """获取用于解析目录的专用LLM对象"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    try:
        from langchain_openai import ChatOpenAI
    except Exception:
        return None
    return ChatOpenAI(
        temperature=0,
        max_retries=2,
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key=api_key,
    )
# 加载 .env 环境变量，确保在独立调用拆分器时也能读取到密钥
load_dotenv()


class AdaptiveSplitter(Splitter):
    """自适应拆分器：识别目录块并按编号标题拆分正文，可选使用LLM解析目录。"""

    name = "adaptive"

    def __init__(self, use_llm: bool = False):
        self.use_llm = bool(use_llm)

    def _is_toc_line(self, line: str) -> bool:
        return is_toc_line(line)

    def _detect_toc_bounds(self, lines: List[str]) -> Optional[tuple[int, int, str]]:
        return detect_toc_bounds(lines)

    def _llm_extract_toc_headings(self, toc_text: str) -> List[HeadingItem]:
        sample = (toc_text or "").strip()
        if not sample:
            return []
        
        llm = get_toc_parsing_llm()
        if not llm:
            return []

        sys_prompt = get_toc_parser_system_prompt()
        user_prompt = get_toc_parser_user_prompt(sample)
        
        try:
            msg = llm.invoke([
                ("system", sys_prompt),
                ("user", user_prompt),
            ])
            arr = parse_json_array(getattr(msg, "content", "") or "")
            out: List[HeadingItem] = []
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
                out.append(HeadingItem(number=num, title=title))
            return out
        except Exception:
            return []

    def split(self, text: str) -> List[Dict[str, Any]]:
        lines = (text or "").splitlines()
        bounds = self._detect_toc_bounds(lines)
        if not bounds:
            return HeadingsSplitter().split(text)
        s, e, title = bounds
        toc_text = "\n".join(
            [
                ln
                for ln in lines[s:e]
                if (ln or "").strip()
                and (
                    re.match(r"^\s*(table\s+of\s+contents|contents|目录)\b", (ln or ""), re.IGNORECASE)
                    or is_toc_line(ln)
                )
            ]
        ).replace(".....", "").strip()
        rest = "\n".join(lines[:s] + lines[e:])
        allowed: Optional[List[HeadingItem]] = None
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
