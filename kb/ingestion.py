from typing import List, Dict, Any, Optional
import os
import re
import html
from pypdf import PdfReader
from .splitters import (
    NormalSplitter,
    AdaptiveSplitter,
)


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

    
def read_chm_text(chm_path: str) -> str:
    """读取 CHM 文件为纯文本（使用 pychm + beautifulsoup4；无系统命令回退）。

    - 依赖：`pychm`（解析 CHM），`beautifulsoup4`（解析 HTML）
    - 若未安装依赖，会抛出明确的错误提示以指导安装
    - 文本解析：去除脚本/样式/注释，提取可读文本，适合后续拆分与索引
    """
    if not os.path.isfile(chm_path):
        raise FileNotFoundError(f"CHM 文件不存在：{chm_path}")

    try:
        from pychm import ChmFile  # type: ignore
    except Exception:
        raise RuntimeError(
            "缺少依赖：请安装 pychm 和 beautifulsoup4。\n"
            "pip install pychm beautifulsoup4"
        )

    chm = ChmFile(chm_path)
    try:
        content = chm.get_content()
    except Exception as e:
        raise RuntimeError(f"读取 CHM 内容失败: {e}")

    if not content:
        return ""

    if isinstance(content, (bytes, bytearray)):
        try:
            html_str = content.decode("utf-8")
        except Exception:
            html_str = content.decode("latin-1", errors="replace")
    else:
        html_str = str(content)

    try:
        from bs4 import BeautifulSoup  # type: ignore
        soup = BeautifulSoup(html_str, "html.parser")
        text = soup.get_text(" ", strip=True)
        return text
    except Exception:
        # bs4 不可用时，回退为简单的正则去标签（仍不使用系统命令）
        text = re.sub(r"(?is)<script.*?>.*?</script>", "", html_str)
        text = re.sub(r"(?is)<style.*?>.*?</style>", "", text)
        text = re.sub(r"(?is)<!--.*?-->", "", text)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


## 兼容保留：拆分函数已迁移至 kb.splitters 模块


def ingest_pdf(kb_controller, kb_id: int, pdf_path: str, chunk_size: int = 500, overlap: int = 100, use_llm_headings: Optional[bool] = None):
    """读取指定PDF文件，优先识别目录并保持完整；否则按编号标题分割，最后回退为定长分割

    - `kb_controller`：持久化知识库控制器实例
    - `kb_id`：知识库ID
    - `pdf_path`：PDF文件路径
    - `chunk_size` 与 `overlap`：回退分割参数
    - 返回：创建的文件元信息对象
    """
    text = read_pdf_text(pdf_path)
    use_llm = (
        bool(str(os.getenv("INGEST_USE_LLM_HEADING", "")).lower() in {"1", "true", "yes"})
        if use_llm_headings is None else bool(use_llm_headings)
    )
    adaptive_chunks = AdaptiveSplitter(use_llm=use_llm).split(text)
    if adaptive_chunks and adaptive_chunks[0].get("metadata", {}).get("number") == "" and adaptive_chunks[0].get("metadata", {}).get("type") == "toc":
        chunks = adaptive_chunks
    else:
        if adaptive_chunks and adaptive_chunks[0].get("metadata", {}).get("number"):
            chunks = adaptive_chunks
        else:
            chunks = NormalSplitter(chunk_size=chunk_size, overlap=overlap).split(text)
    filename = pdf_path.split("/")[-1].split("\\")[-1]
    info = kb_controller.add_file(kb_id, filename=filename, chunk_count=len(chunks), status="done")
    kb_controller.save_chunks(kb_id, file_id=info.id, chunks=chunks)
    return info


