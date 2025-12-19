from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import os
import re

from langchain_openai import ChatOpenAI

from .base import Splitter
from app.prompts import (
    get_table_summary_system_prompt,
    get_table_summary_user_prompt,
)


def _split_sheets(text: str) -> List[Tuple[str, str]]:
    """将 `read_excel_text` 生成的文本按 `[Sheet]` 分块为 (sheet_name, sheet_text) 列表。"""
    lines = (text or "").splitlines()
    blocks: List[Tuple[str, List[str]]] = []
    current_name: Optional[str] = None
    current_lines: List[str] = []

    for line in lines:
        m = re.match(r"^\[Sheet\]\s*(.+?)\s*$", line)
        if m:
            if current_name is not None:
                blocks.append((current_name, current_lines))
            current_name = m.group(1).strip()
            current_lines = []
            continue
        if current_name is None:
            continue
        current_lines.append(line)

    if current_name is not None:
        blocks.append((current_name, current_lines))

    out: List[Tuple[str, str]] = []
    for name, ls in blocks:
        sheet_text = "\n".join(ls).strip()
        if sheet_text:
            out.append((name, sheet_text))
    return out


def _extract_markdown_table_lines(sheet_text: str) -> List[str]:
    """从工作表块中提取 Markdown 表格行（以 `|` 开头的行）。"""
    table_lines: List[str] = []
    for line in (sheet_text or "").splitlines():
        s = line.rstrip()
        if s.lstrip().startswith("|"):
            table_lines.append(s.strip())
    return table_lines


def _parse_markdown_header(table_lines: List[str]) -> List[str]:
    """从 Markdown 表格行中解析表头单元格文本（第 1 行）。"""
    if not table_lines:
        return []
    header_line = table_lines[0].strip()
    if not header_line.startswith("|"):
        return []
    raw = [c.strip() for c in header_line.strip("|").split("|")]
    return [c for c in raw if c != ""]


def _build_table_chunks(
    table_lines: List[str],
    max_rows_per_chunk: int,
    max_chars_per_chunk: int,
) -> List[str]:
    """将一张 Markdown 表格按行数/字符数切分为多个 Markdown 表格片段。"""
    if not table_lines:
        return []

    header = table_lines[0]
    sep = table_lines[1] if len(table_lines) >= 2 else ""
    body = table_lines[2:] if len(table_lines) >= 3 else []

    if max_rows_per_chunk <= 0:
        max_rows_per_chunk = 50
    if max_chars_per_chunk <= 0:
        max_chars_per_chunk = 6000

    chunks: List[str] = []
    cur_rows: List[str] = []

    def _flush() -> None:
        if not cur_rows:
            return
        md_lines = [header]
        if sep:
            md_lines.append(sep)
        md_lines.extend(cur_rows)
        chunks.append("\n".join(md_lines).strip())
        cur_rows.clear()

    for row in body:
        cur_rows.append(row)
        if len(cur_rows) >= max_rows_per_chunk:
            _flush()
            continue
        md_lines = [header]
        if sep:
            md_lines.append(sep)
        md_lines.extend(cur_rows)
        if len("\n".join(md_lines)) >= max_chars_per_chunk:
            cur_rows.pop()
            _flush()
            cur_rows.append(row)

    _flush()

    if not chunks and (header or sep):
        md_lines = [header]
        if sep:
            md_lines.append(sep)
        chunks = ["\n".join(md_lines).strip()]

    return chunks


def _llm_summarize_table(
    table_name: str,
    sheet_name: str,
    header_cells: List[str],
) -> str:
    """基于表格名称、Sheet 名称与表头文本调用 LLM 生成表格摘要（无 Key 或失败则返回空）。"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return ""

    header_text = " | ".join([c for c in (header_cells or []) if c]).strip()
    if not header_text:
        return ""

    llm = ChatOpenAI(
        temperature=0,
        max_retries=2,
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key=api_key,
    )

    sys_prompt = get_table_summary_system_prompt()
    user_prompt = get_table_summary_user_prompt(
        table_name=table_name,
        sheet_name=sheet_name,
        header_text=header_text,
    )
    try:
        msg = llm.invoke([
            ("system", sys_prompt),
            ("user", user_prompt),
        ])
        summary = (getattr(msg, "content", "") or "").strip()
        summary = re.sub(r"\s+\n", "\n", summary).strip()
        return summary
    except Exception:
        return ""


class TableSplitter(Splitter):
    """表格拆分器：按表格（Excel 工作表）拆分，并可为每张表生成概要信息。"""

    name = "table"

    def __init__(
        self,
        table_name: str,
        use_llm_summary: bool = True,
        max_rows_per_chunk: int = 200,
        max_chars_per_chunk: int = 8000,
    ):
        self.table_name = (table_name or "").strip()
        self.use_llm_summary = bool(use_llm_summary)
        self.max_rows_per_chunk = int(max_rows_per_chunk)
        self.max_chars_per_chunk = int(max_chars_per_chunk)

    def split(self, text: str) -> List[Dict[str, Any]]:
        sheets = _split_sheets(text)
        chunks: List[Dict[str, Any]] = []

        for sheet_name, sheet_text in sheets:
            table_lines = _extract_markdown_table_lines(sheet_text)
            header_cells = _parse_markdown_header(table_lines)

            summary = ""
            if self.use_llm_summary:
                summary = _llm_summarize_table(
                    table_name=self.table_name,
                    sheet_name=sheet_name,
                    header_cells=header_cells,
                )

            parts = _build_table_chunks(
                table_lines=table_lines,
                max_rows_per_chunk=self.max_rows_per_chunk,
                max_chars_per_chunk=self.max_chars_per_chunk,
            )
            if not parts:
                continue

            total_parts = len(parts)
            for idx, md in enumerate(parts, start=1):
                prefix_lines = [
                    f"[Table] {self.table_name}",
                    f"[Sheet] {sheet_name}",
                ]
                if idx == 1 and summary:
                    prefix_lines.append(f"[TableSummary] {summary}")
                content = ("\n".join(prefix_lines) + "\n" + md).strip()
                chunks.append({
                    "content": content,
                    "metadata": {
                        "type": "table",
                        "table_name": self.table_name,
                        "sheet_name": sheet_name,
                        "part_index": idx,
                        "part_count": total_parts,
                        "header": header_cells,
                    },
                })

        return chunks

