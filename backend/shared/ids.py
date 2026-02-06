from __future__ import annotations

import re


def format_kb_id(kb_id: int) -> str:
    return f"kb-{int(kb_id)}"


def parse_kb_id(kb_id: str | int) -> int:
    if isinstance(kb_id, int):
        return kb_id
    m = re.match(r"^kb-(\d+)$", str(kb_id))
    if m:
        return int(m.group(1))
    return int(kb_id)


def format_file_id(file_id: int) -> str:
    return f"f-{int(file_id)}"


def parse_file_id(file_id: str | int) -> int:
    if isinstance(file_id, int):
        return file_id
    m = re.match(r"^f-(\d+)$", str(file_id))
    if m:
        return int(m.group(1))
    raise ValueError("文件ID格式错误")

