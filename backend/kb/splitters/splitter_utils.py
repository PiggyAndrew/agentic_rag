from typing import List, Dict, Any, Optional, Tuple
import json
import re


def parse_json_array(s: str) -> List[Dict[str, Any]]:
    # 解析字符串中的 JSON 数组，容错支持：
    # 1) 直接是合法 JSON（优先尝试）
    # 2) ```json fenced code block 中的数组
    # 3) 文本里出现的最小匹配的 [ { ... } ] 结构
    # 若解析失败，返回空数组，避免抛异常影响上层逻辑
    try:
        data = json.loads(s)
        return data if isinstance(data, list) else []
    except Exception:
        pass
    # 兼容 Markdown 的 ```json 代码块
    m = re.search(r"```json\s*(\[.*?\])\s*```", s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return []
    # 退路：抓取最短的 [ { ... } ] 数组片段
    m2 = re.search(r"(\[\s*\{.*?\}\s*\])", s, re.DOTALL)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            return []
    return []


def normalize_title(s: str) -> str:
    # 标题归一化：
    # - 去首尾空白并统一为小写，提升匹配稳定性
    # - 合并内部空白为单个空格
    # - 去掉结尾的符号（.:;、，），避免“标题末尾标点差异”导致匹配失败
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[\.:;、，]+$", "", s)
    return s


def is_toc_line(line: str) -> bool:
    # 判断某行文本是否像“目录条目”：
    # 规则要点：
    # - 末尾必须跟页码（1-5 位数字），以避免把普通标题误判为目录
    # - 去掉末尾页码后，主体需具备：编号标题 / 附录标题 / leader（省略号/点位符）等结构
    # - 支持中英文（A-Za-z 与 CJK 范围）
    s = (line or "").strip()
    if not s:
        return False
    # 页码检测：目录常见模式“标题 ....... 12”
    has_page_num = re.search(r"\b\d{1,5}\s*$", s) is not None
    if not has_page_num:
        return False
    # 去掉末尾页码后再分析主体
    body = re.sub(r"\s*\b\d{1,5}\s*$", "", s).strip()
    if not body:
        return False
    # leader：至少连续出现 3 次的点/中点/破折/省略等符号，常见于目录行的点位符
    leader = re.search(r"(?:[\.·•⋅\u2026\-]\s*){3,}", body) is not None
    # 编号标题：如 “1.2.3 标题” 或 “1.2 标题.”（末尾点号可选）
    numbered = re.match(r"^\s*\d+(?:\.\d+)*\s*\.?\s+.+", body) is not None
    # 附录标题：Appendix a/1 - Title（大小写不敏感）
    appendix = (
        re.match(r"^\s*appendix\s+(\d+|[a-z])\s*[\-–—\.]?\s+.+", body, re.IGNORECASE)
        is not None
    )
    # 满足编号/附录则判定为目录行；否则若有 leader 且含字母或中文，则也视为目录行
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
    # 探测范围限制：最多扫描前 5000 行，避免超长文档带来性能问题
    n = len(lines)
    probe_n = min(n, 5000)
    title_idx = None
    title = ""
    # 显式目录标题探测：Table of Contents / Contents / 目录
    title_re = re.compile(r"^\s*(table\s+of\s+contents|contents|目录)\b", re.IGNORECASE)
    for i, line in enumerate(lines[:probe_n]):
        if title_re.match(line or ""):
            title_idx = i
            title = (line or "").strip()
            break
    # 若未命中标题，则从第一条符合 is_toc_line 的行开始作为目录起点，标题记为 Table of Contents
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
        # 页码范围，如 “3 - 7”
        if re.match(r"^\s*\d+\s*\-\s*\d+\s*$", s):
            return True
        # 页码提示，如 “Page 12”
        if re.match(r"^\s*page\s+\d+\b", s, re.IGNORECASE):
            return True
        # 常见页眉字段（作者、版本、日期）
        if re.match(r"^\s*(author|version|current issue date|first issue date)\b", s, re.IGNORECASE):
            return True
        # 部门名等固定页眉标识
        if re.search(r"\b(archsd|property services branch)\b", s, re.IGNORECASE):
            return True
        return False

    # 目录主体扫描：
    # - 记录目录条目数量（toc_count）与最近一条目录行位置（last_toc_idx）
    # - 对噪声行给予较大容忍度（跨页容忍 80 行噪声），确保目录完整性
    # - 若目录条目太少（<3），则认为不是有效目录段
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
                # 目录已足够长，且噪声持续过多，认为目录段结束
                break
            j += 1
            continue
        if toc_count < 3:
            # 目录条目不足且遇到非噪声行，提前终止
            break
        non_toc_streak += 1
        if non_toc_streak > 20:
            # 目录后连续非目录行超过阈值，结束
            break
        j += 1

    # 目录结束位置：以最后一条目录行后一行作为结尾
    end = (last_toc_idx + 1) if last_toc_idx is not None else (start + 1)
    if end - start < 3:
        # 有效目录至少包含 3 行（标题行 + 两条目录条目）
        return None
    return (start, end, title or "Table of Contents")
