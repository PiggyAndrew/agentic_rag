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
    has_page_num = re.search(r"\b\d{1,5}\s*$", s) is not None
    if not has_page_num:
        return False

    body = re.sub(r"\s*\b\d{1,5}\s*$", "", s).strip()
    if not body:
        return False

    leader = re.search(r"(?:[\.·•⋅\u2026\-]\s*){3,}", body) is not None
    numbered = re.match(r"^\s*\d+(?:\.\d+)*\s*\.?\s+.+", body) is not None
    appendix = (
        re.match(r"^\s*appendix\s+(\d+|[a-z])\s*[\-–—\.]?\s+.+", body, re.IGNORECASE)
        is not None
    )

    if numbered or appendix:
        return True
    if leader and re.search(r"[A-Za-z\u4e00-\u9fff]", body):
        return True
    return False


def detect_toc_bounds(lines: List[str]) -> Optional[Tuple[int, int, str]]:
    """
    识别目录（TOC）在全文中的行区间。

    支持目录跨页：允许在目录条目之间夹杂少量页眉/页脚/空行等噪声，
    并以最后一条目录行作为目录结束位置，避免被跨页噪声提前截断。
    """
    n = len(lines)
    probe_n = min(n, 5000)
    title_idx = None
    title = ""
    title_re = re.compile(r"^\s*(table\s+of\s+contents|contents|目录)\b", re.IGNORECASE)
    for i, line in enumerate(lines[:probe_n]):
        if title_re.match(line or ""):
            title_idx = i
            title = (line or "").strip()
            break
    start = None
    if title_idx is not None:
        start = title_idx
    else:
        for i, line in enumerate(lines[:probe_n]):
            if is_toc_line(line):
                start = i
                title = "Table of Contents"
                break
    if start is None:
        return None
    if start + 1 >= n:
        return None

    def is_toc_noise_line(line: str) -> bool:
        """
        判断目录跨页时可能出现的噪声行（页眉/页脚/页码范围等），用于跨页连续性。
        """
        s = (line or "").strip()
        if not s:
            return True
        if title_re.match(s):
            return True
        if re.match(r"^\s*\d+\s*-\s*\d+\s*$", s):
            return True
        if re.match(r"^\s*page\s+\d+\b", s, re.IGNORECASE):
            return True
        if re.match(r"^\s*(author|version|current issue date|first issue date)\b", s, re.IGNORECASE):
            return True
        if re.search(r"\b(archsd|property services branch)\b", s, re.IGNORECASE):
            return True
        return False

    toc_count = 0
    last_toc_idx: Optional[int] = None
    non_toc_streak = 0
    j = start + 1
    while j < n:
        line = lines[j] or ""
        if is_toc_line(line):
            toc_count += 1
            last_toc_idx = j
            non_toc_streak = 0
            j += 1
            continue
        if is_toc_noise_line(line):
            non_toc_streak += 1
            if toc_count >= 3 and non_toc_streak > 80:
                break
            j += 1
            continue
        if toc_count < 3:
            break
        non_toc_streak += 1
        if non_toc_streak > 20:
            break
        j += 1

    end = (last_toc_idx + 1) if last_toc_idx is not None else (start + 1)
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
