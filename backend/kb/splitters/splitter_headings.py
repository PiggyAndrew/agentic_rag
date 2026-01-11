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
    # 目录/编号标题拆分器
    # - 支持按 Markdown 标题（# 至 ######）作为章节边界
    # - 支持识别编号标题（如 1、1.2、Appendix 1、A.1 等）并构建层级路径
    # - 在章节内部继续按子标题/编号/项目符号进行二次拆分
    # - 提供“allowed_headings”作为白名单，按给定章节顺序扫描并拆分

    name = "headings"

    def __init__(
        self,
        allowed_headings: Optional[List[HeadingItem]] = None,
        *,
        min_subchunk_chars: int = 100,
    ):
        self.allowed_headings = allowed_headings or []
        # 注意：这里将最小子块字符数设为 0，意味着禁用“小块合并”逻辑。
        # 如果希望合并过小的片段，请将其改为传入的参数值（min_subchunk_chars）。
        # 当前实现保留原有行为，仅做说明，避免误解为“生效的阈值”。
        self.min_subchunk_chars = int(min_subchunk_chars)

    # Markdown 标题正则：匹配 1-6 级标题，捕获级别与标题文本
    _md_heading_re = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")
    # 说明：^ 开头，\s* 允许前导空白，(#{1,6}) 捕获 # 的个数作为层级，\s+ 至少一个空格后跟标题体
    # 编号标题正则：匹配“1.2.3”格式，可选后缀“)”或“.”，可选分隔符，捕获编号与标题
    _numbered_title_re = re.compile(r"^\s*(\d+(?:\.\d+)*)(?:\s*[\.)])?\s*(?:[-–—:：]\s*)?(.+?)\s*$")
    # 说明：捕获 1.2.3 等编号；可选 ) 或 . 作为收尾；可选 “- : ：” 作为分隔符；最后捕获标题文本
    # 无序列表项正则：匹配“* / + / -”开头的列表项，捕获内容
    _bullet_line_re = re.compile(r"^\s*[*+-]\s+(.+?)\s*$")
    # 说明：用于识别项目符号行，并尝试在其中二次解析编号标题（如 “- 1.1 子节”）
    # 附录标题正则：匹配“Appendix 1”或“Appendix a”格式，捕获编号与标题（大小写不敏感）
    _appendix_title_re = re.compile(r"^\s*(appendix\s+(?:\d+|[a-z]))\s+(.+?)\s*$", re.IGNORECASE)
    # 说明：将 “Appendix a/1” 与后续标题分离，大小写不敏感；在解析时会统一规范化为大写编号
    # 字母编号标题正则：匹配“a.1.2.3”格式，捕获字母、数字编号与标题（大小写不敏感）
    _letter_numbered_title_re = re.compile(r"^\s*([a-z])\.(\d+(?:\.\d+)*)\s+(.+?)\s*$", re.IGNORECASE)
    # 说明：识别 A.1.2.3 风格，首字母大小写统一在解析时提升为大写

    def _strip_heading_prefix(self, line: str) -> tuple[int, str]:
        # 去掉 Markdown 标题前缀并返回 (层级, 文本)
        s = line or ""
        m = self._md_heading_re.match(s)
        if not m:
            return (0, s)
        
        level = len(m.group(1))
        return (level, m.group(2).strip())

    def _strip_emphasis(self, s: str) -> str:
        # 去除粗体/斜体等强调标记，便于后续编号与标题识别
        s = (s or "")
        s = re.sub(r"^\s*(?:\*\*|\*|_)\s*", "", s)
        s = re.sub(r"\s*(?:\*\*|\*|_)\s*$", "", s)
        s = re.sub(r"[\*_]+", "", s)
        return s

    def _norm_number(self, n: str) -> str:
        # 规范化编号字符串：去结尾点、合并空白
        n = (n or "").strip()
        if n.endswith("."):
            n = n[:-1]
        n = re.sub(r"\s+", " ", n)
        return n

    def _order_key_list(self, number: str) -> List[int]:
        # 将编号转为可排序的整数序列
        # - 普通数字：按分段转换为整数 [1,2,3]
        # - 附录：使用前缀 10000 区分（如 Appendix A → [10000, 65]）
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
        # 内容大小（去空白后的长度），用于判断小块合并
        return len(re.sub(r"\s+", "", text or ""))

    def _parse_numbered_title(self, text: str) -> Optional[tuple[str, str]]:
        # 解析一行文本为 (编号, 标题)
        # 顺序：Appendix → 字母编号（A.1）→ 纯数字编号（1.2.3）
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
        # 构建层级路径：用于在元数据中体现章节层次（如 1 → 1.1 → 1.1.1）
        n = self._norm_number(number)
        if not n:
            return []
        m_app = re.match(r"^Appendix\s+([A-Za-z0-9]+)(?:\.(\d+(?:\.\d+)*))?$", n)
        if m_app:
            # 说明：附录编号的路径构造稍有不同，首段使用 “Appendix X”，其后按点分段扩展
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
        # 在白名单章节中按顺序扫描匹配到的顶级章节
        # - 使用正则与归一化标题进行匹配
        # - 强制推进规则：同层递增/回到上级后的递增/子层推进/进入附录
        allowed: List[Dict[str, Any]] = []
        number_to_title: Dict[str, str] = {}
        for h in self.allowed_headings:
            number = self._norm_number(getattr(h, "number", ""))
            title = (getattr(h, "title", "") or "").strip()
            title_norm = normalize_title(title)
            if not number or not title_norm:
                continue
            allowed.append({
                "number": number,
                "title": title,
                "title_norm": title_norm,
                "pat": self._number_pattern(number),
                "order_key": self._order_key_list(number),
            })
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
            if i==311:
                print(body_norm)
            if not body_norm:
                continue
            for a in allowed:
                num = a["number"]
                if num in seen_numbers:
                    continue
                if not a["pat"].search(body):
                    # 编号未出现：跳过
                    continue
                if a["title_norm"] not in body_norm:
                    # 白名单标题关键字未包含：跳过
                    continue
                if last_num:
                    prev = self._order_key_list(last_num)
                    cur = a.get("order_key") or []
                    if prev and cur:
                        # 允许的推进：子节点、同层后续、跨层回到上级后续、下一个主章节、附录
                        is_child = len(cur) > len(prev) and cur[:len(prev)] == prev
                        is_same_level_next = len(cur) == len(prev) and cur[:-1] == prev[:-1] and cur[-1] == prev[-1] + 1
                        is_upper_level_next = len(cur) < len(prev) and cur[:-1] == prev[:len(cur)-1] and cur[-1] >= prev[len(cur)-1] + 1
                        is_next_major = len(cur) == 1 and len(prev) >= 1 and cur[0] == prev[0] + 1
                        is_appendix = cur and cur[0] == 10000
                        if not (is_child or is_same_level_next or is_upper_level_next or is_next_major or is_appendix):
                            # 若推进不满足层级与序号递增关系则拒绝，确保章节顺序合理
                            continue
                chapters.append({
                    "index": i,
                    "level": level,
                    "number": num,
                    "title": a["title"],
                })
                seen_numbers.add(num)
                last_num = num
                break

        chapters = sorted(chapters, key=lambda x: x["index"])
        return (chapters, number_to_title)

    def _split_by_markdown_headings(self, lines: List[str]) -> List[Dict[str, Any]]:
        # 不使用白名单时：按最低层级的 Markdown 标题作为章节边界拆分
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
        # 说明：选择最浅层级作为外层章节边界，避免被更深层子标题过度切分成碎片
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
        # 合并过小的内容块：保持同一编号下的相邻片段合并，直到达到最小内容阈值
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
                if (cur.get("metadata", {}).get("number") != nxt.get("metadata", {}).get("number")):
                    # 不同编号的片段不合并，保持层级语义
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
                # 尾部小块与前一个同编号片段合并，减少尾碎片
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
        # 章节内部二次拆分：
        # - 识别子标题（更深层级的 Markdown 标题）
        # - 识别项目符号中的编号标题
        # - 识别普通文本行中的编号标题
        # 然后基于这些界标切分内容，并带上层级路径与排序键
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
                    # 不是更深层级的标题，不作为子标题界标
                    continue
                raw_title = m.group(2).strip()
                parsed = self._parse_numbered_title(raw_title)
                if parsed is not None:
                    n, t = parsed
                    _add_subhead(i, n, t, lvl)
                else:
                    # 没有编号标题也视为子标题（仅携带标题文本）
                    subheads.append({"index": i, "level": lvl, "number": "", "title": raw_title})
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
            return [{
                "content": content,
                "metadata": {"number": chapter_number, "title": chapter_title, "path": chapter_path},
            }] if content else []

        start_to_sub = {h["index"]: (h.get("number", ""), h.get("title", "")) for h in subheads}
        # 说明：记录每个子标题起点对应的 (编号, 标题)，用于在切分时填充元数据
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

    def split(self, text: str) -> List[Dict[str, Any]]:
        # 主入口：
        # - 若未提供 allowed_headings，则按 Markdown 标题的最低层级拆分
        # - 若提供了 allowed_headings，则按白名单顺序扫描并拆分
        lines = (text or "").splitlines()
        if not lines:
            return [{"content": "", "metadata": {"number": "", "title": "", "path": []}}]

        if not self.allowed_headings:
            return self._split_by_markdown_headings(lines)

        chapters, number_to_title = self._scan_allowed_chapters(lines)
        if not chapters:
            return [{"content": "\n".join(lines).strip(), "metadata": {"number": "", "title": "", "path": []}}]

        out: List[Dict[str, Any]] = []
        for idx, ch in enumerate(chapters):
            start = ch["index"]
            end = chapters[idx + 1]["index"] if idx + 1 < len(chapters) else len(lines)
            chapter_lines = lines[start:end]
            chapter_number = ch["number"]
            chapter_title = ch["title"]
            chapter_path = self._build_number_path(chapter_number, number_to_title)
            out.extend(
                self._split_chapter_by_subheadings(
                    chapter_lines,
                    chapter_level=ch.get("level", 0),
                    chapter_number=chapter_number,
                    chapter_title=chapter_title,
                    chapter_path=chapter_path,
                )
            )
        return out
