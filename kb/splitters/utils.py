from typing import List, Dict, Any, Optional, Tuple
import os
import json
import re
from langchain_openai import ChatOpenAI


def parse_json_array(s: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(s)
        return data if isinstance(data, list) else []
    except Exception:
        pass
    m = re.search(r"```json\s*(\[.*?\])\s*```", s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return []
    m2 = re.search(r"(\[\s*\{.*?\}\s*\])", s, re.DOTALL)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            return []
    return []


def normalize_title(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[\.:;、，]+$", "", s)
    return s


def is_toc_line(line: str) -> bool:
    s = (line or "").strip()
    if not s:
        return False
    dotted = re.search(r"[\.··•⋅\u2026\-]{3,}", s) is not None
    page_num = re.search(r"\b\d{1,5}\s*$", s) is not None
    numbered = re.match(r"^\s*\d+(?:\.\d+)*\s+.+", s) is not None
    return (dotted and page_num) or (numbered and page_num)


def detect_toc_bounds(lines: List[str]) -> Optional[Tuple[int, int, str]]:
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
            if is_toc_line(line):
                start = i
                title = "Table of Contents"
                break
    if start is None:
        return None
    j = start + 1
    while j < n:
        s = (lines[j] or "")
        if is_toc_line(s) or not s.strip():
            j += 1
            continue
        break
    end = j
    if end - start < 3:
        return None
    return (start, end, title or "Table of Contents")


def llm_extract_toc_headings(toc_text: str) -> List[Dict[str, str]]:
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