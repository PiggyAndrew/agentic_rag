from typing import List, Dict, Any
from pypdf import PdfReader
import re


def read_pdf_text(pdf_path: str) -> str:
    """读取PDF文件的全部文本内容并返回字符串

    - 参数 `pdf_path`：PDF文件的绝对或相对路径
    - 返回：合并后的纯文本
    """
    reader = PdfReader(pdf_path)
    texts: List[str] = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts).strip()


def split_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """将长文本按定长切片并设置重叠区，返回片段列表

    - `chunk_size`：每个片段的目标长度（字符数）
    - `overlap`：相邻片段的重叠长度，提升语义连续性
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正数")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须为非负且小于 chunk_size")
    text = (text or "").strip()
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
    return chunks


def split_by_numbered_headings(text: str) -> List[Dict[str, Any]]:
    """按编号标题进行分割，生成包含层级路径的片段字典列表

    - 标题格式示例：`1 Overview`、`1.1 Introduction`、`1.2.1 Industry Standards`
    - 返回的每个片段包含 `content` 与 `metadata`，其中 `metadata` 包括：
      - `number`：编号，如 `1.2.1`
      - `title`：标题文本，如 `Industry Standards`
      - `path`：从大到小的层级路径列表，如 `[{"number": "1", "title": "Overview"}, {"number": "1.2", "title": "References"}, {"number": "1.2.1", "title": "Industry Standards"}]`
    """
    lines = (text or "").splitlines()
    heading_re = re.compile(r"^\s*(\d+(?:\.\d+)*)(?:\s+|\s*[\-\u2013]\s*)(.+?)\s*$")
    heads: List[Dict[str, Any]] = []
    for i, line in enumerate(lines):
        m = heading_re.match(line)
        if m:
            num = m.group(1).strip()
            title = m.group(2).strip()
            if title.lower() == "contents":
                continue
            heads.append({"index": i, "number": num, "title": title})

    if not heads:
        return [{"content": "\n".join(lines).strip(), "metadata": {"number": "", "title": "", "path": []}}]

    number_to_title: Dict[str, str] = {h["number"]: h["title"] for h in heads}
    chunks: List[Dict[str, Any]] = []

    for idx, h in enumerate(heads):
        start = h["index"]
        end = heads[idx + 1]["index"] if idx + 1 < len(heads) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        segs = h["number"].split(".")
        path = []
        for j in range(1, len(segs) + 1):
            key = ".".join(segs[:j])
            if key in number_to_title:
                path.append({"number": key, "title": number_to_title[key]})
        chunks.append({
            "content": content,
            "metadata": {"number": h["number"], "title": h["title"], "path": path},
        })
    return chunks


def ingest_pdf(kb_controller, kb_id: int, pdf_path: str, chunk_size: int = 500, overlap: int = 100):
    """读取指定PDF文件，按编号标题分割并持久化；若未匹配到标题则回退为定长分割

    - `kb_controller`：持久化知识库控制器实例
    - `kb_id`：知识库ID
    - `pdf_path`：PDF文件路径
    - `chunk_size` 与 `overlap`：回退分割参数
    - 返回：创建的文件元信息对象
    """
    text = read_pdf_text(pdf_path)
    heading_chunks = split_by_numbered_headings(text)
    chunks = heading_chunks if heading_chunks and heading_chunks[0].get("metadata", {}).get("number") else [
        {"content": c, "metadata": {"number": "", "title": "", "path": []}} for c in split_text(text, chunk_size=chunk_size, overlap=overlap)
    ]
    filename = pdf_path.split("/")[-1].split("\\")[-1]
    info = kb_controller.add_file(kb_id, filename=filename, chunk_count=len(chunks), status="done")
    kb_controller.save_chunks(kb_id, file_id=info.id, chunks=chunks)
    return info
