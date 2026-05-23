from __future__ import annotations

from typing import List, Optional, Tuple
import re
import time

from backend.shared.prompts.system import get_table_summary_system_prompt, get_table_summary_user_prompt
from .splitter_base import Splitter
from backend.modules.kb.domain.chunk_models import ChunkingInfo, DocumentChunk, ElementRefSegment
from backend.modules.kb.domain.element_models import TableElement
from backend.modules.kb.domain.enums import ChunkingStrategy, ElementType
from ..services.llm_factory import get_deepseek_chat_llm


def _split_sheets(text: str) -> List[Tuple[str, str]]:
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
    table_lines: List[str] = []
    for line in (sheet_text or "").splitlines():
        s = line.rstrip()
        if s.lstrip().startswith("|"):
            table_lines.append(s.strip())
    return table_lines


def _parse_markdown_header(table_lines: List[str]) -> List[str]:
    if not table_lines:
        return []
    header_line = table_lines[0].strip()
    if not header_line.startswith("|"):
        return []
    raw = [c.strip() for c in header_line.strip("|").split("|")]
    return [c for c in raw if c != ""]


def _build_table_chunks(table_lines: List[str], max_rows_per_chunk: int, max_chars_per_chunk: int) -> List[str]:
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


def _llm_summarize_table(llm: object, table_name: str, sheet_name: str, header_cells: List[str]) -> str:
    header_text = " | ".join([c for c in (header_cells or []) if c]).strip()
    if not header_text:
        return ""

    sys_prompt = get_table_summary_system_prompt()
    user_prompt = get_table_summary_user_prompt(
        table_name=table_name,
        sheet_name=sheet_name,
        header_text=header_text,
    )
    try:
        msg = llm.invoke(
            [
                ("system", sys_prompt),
                ("user", user_prompt),
            ]
        )
        summary = (getattr(msg, "content", "") or "").strip()
        summary = re.sub(r"\s+\n", "\n", summary).strip()
        return summary
    except Exception:
        return ""


class TableSplitter(Splitter):
    name = "table"

    def __init__(
        self,
        table_name: str,
        use_llm_summary: bool = True,
        max_rows_per_chunk: int = 200,
        max_chars_per_chunk: int = 8000,
        *,
        llm: Optional[object] = None,
    ):
        self.table_name = (table_name or "").strip()
        self.use_llm_summary = bool(use_llm_summary)
        self.max_rows_per_chunk = int(max_rows_per_chunk)
        self.max_chars_per_chunk = int(max_chars_per_chunk)
        self._llm = llm

    @staticmethod
    def _parse_markdown_rows(markdown: str) -> tuple[list[str], list[list[str]]]:
        table_lines = [line.strip() for line in markdown.splitlines() if line.strip().startswith("|")]
        if not table_lines:
            return [], []

        def _split_row(line: str) -> list[str]:
            return [cell.strip() for cell in line.strip("|").split("|")]

        headers = _split_row(table_lines[0])
        body_lines = table_lines[2:] if len(table_lines) >= 3 else []
        rows = [_split_row(line) for line in body_lines]
        return headers, rows

    def split(self, text: str, kb_id: int, document_id: int) -> List[DocumentChunk]:
        sheets = _split_sheets(text)
        chunks: List[DocumentChunk] = []
        now_ms = int(time.time() * 1000)

        for sheet_name, sheet_text in sheets:
            table_lines = _extract_markdown_table_lines(sheet_text)
            header_cells = _parse_markdown_header(table_lines)

            summary = ""
            if self.use_llm_summary:
                llm = self._llm or get_deepseek_chat_llm()
                if llm:
                    summary = _llm_summarize_table(llm, self.table_name, sheet_name, header_cells)

            parts = _build_table_chunks(
                table_lines=table_lines,
                max_rows_per_chunk=self.max_rows_per_chunk,
                max_chars_per_chunk=self.max_chars_per_chunk,
            )
            if not parts:
                continue

            total_parts = len(parts)
            for idx, md in enumerate(parts, start=1):
                headers, rows = self._parse_markdown_rows(md)
                table_id = f"table_{len(chunks)}"
                chunks.append(
                    DocumentChunk(
                        document_id=int(document_id),
                        chunk_index=len(chunks),
                        segments=[ElementRefSegment(ref_id=table_id, ref_type=ElementType.table)],
                        elements=[
                            TableElement(
                                id=table_id,
                                title=self.table_name,
                                sheet_name=sheet_name,
                                headers=header_cells or headers,
                                rows=rows,
                                markdown=md,
                                summary=summary if idx == 1 and summary else None,
                            )
                        ],
                        structure_path=[self.table_name, sheet_name],
                        chunking=ChunkingInfo(
                            strategy=ChunkingStrategy.table_based,
                            rule=f"table_splitter_part_{idx}_of_{total_parts}",
                            generator=self.name,
                        ),
                        created_at_ms=now_ms,
                        updated_at_ms=now_ms,
                    )
                )

        return chunks
