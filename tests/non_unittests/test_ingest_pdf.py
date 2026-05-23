import argparse
import json
import os
import sys
from typing import List, Dict, Tuple

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.modules.kb.domain.enums import PdfDocumentType
from backend.modules.kb.domain.services import render_document_chunk_for_ai
from backend.modules.kb.infrastructure.legacy_kb import PersistentKnowledgeBaseController, ingest_pdf


def run_ingest(
    pdf_path: str,
    kb_id: int,
    chunk_size: int,
    overlap: int,
    document_type: PdfDocumentType,
) -> Tuple[Dict, List[Dict]]:
    """执行PDF导入流程并返回文件信息与片段列表

    - `pdf_path`：PDF文件路径
    - `kb_id`：知识库ID
    - `chunk_size`：片段长度
    - `overlap`：片段重叠长度
    - `document_type`：PDF 文档类型，决定导入策略
    - 返回：`(file_info_dict, chunks_dict_list)`
    """
    kb = PersistentKnowledgeBaseController()
    kb.ensure_kb(kb_id)

    filename = os.path.basename(pdf_path)

    try:
        kb.find_document_id_by_name(kb_id, filename)
    except Exception:
        kb.add_document(kb_id, filename, chunk_count=0, status="pending")

    info = ingest_pdf(
        kb,
        kb_id,
        pdf_path,
        chunk_size=chunk_size,
        overlap=overlap,
        document_type=document_type,
    )
    persisted_chunks = kb._repository.list_document_chunks(kb_id, info.document_id)
    chunks = [
        {
            "chunk_index": chunk.chunk_index,
            "content": render_document_chunk_for_ai(chunk),
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
        }
        for chunk in persisted_chunks
    ]
    return (
        {
            "id": info.document_id,
            "filename": info.filename,
            "chunk_count": info.chunk_count,
            "status": str(info.status),
            "document_type": str(document_type.value),
            "page_count": None if info.details is None else info.details.page_count,
        },
        chunks,
    )


def print_summary(info: Dict, chunks: List[Dict]) -> None:
    """在控制台打印分割结果摘要与示例片段"""
    print("文件信息:")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print(f"片段总数: {len(chunks)}")
    preview_count = min(5, len(chunks))
    print(f"示例前{preview_count}个片段预览:")
    for i in range(preview_count):
        c = chunks[i]
        content = c.get("content", "")
        short = (content[:200] + "...") if len(content) > 200 else content
        print(f"- [{c['chunk_index']}] {short}")


def show_gui(chunks: List[Dict]) -> None:
    """使用简单窗口展示片段列表与内容查看"""
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("PDF分割结果查看")
    root.geometry("900x600")

    left = ttk.Frame(root)
    left.pack(side=tk.LEFT, fill=tk.Y)

    right = ttk.Frame(root)
    right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    lst = tk.Listbox(left, width=40)
    lst.pack(fill=tk.Y, expand=True)

    txt = tk.Text(right, wrap=tk.WORD)
    txt.pack(fill=tk.BOTH, expand=True)

    for c in chunks:
        content = c.get("content", "")
        preview = (content[:80] + "...") if len(content) > 80 else content
        lst.insert(tk.END, f"[{c['chunk_index']}] {preview}")

    def on_select(evt):
        idx = lst.curselection()
        if not idx:
            return
        sel = chunks[idx[0]]
        txt.delete("1.0", tk.END)
        txt.insert("1.0", sel.get("content", ""))

    lst.bind("<<ListboxSelect>>", on_select)
    root.mainloop()


def main():
    """命令行入口：执行PDF分割并输出或窗口展示结果"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf",
        default=r"tests\\testfiles\\test drawing reading.pdf",
        help="PDF文件路径",
    )
    parser.add_argument("--kb", type=int, default=1, help="知识库ID")
    parser.add_argument("--chunk_size", type=int, default=500, help="片段长度")
    parser.add_argument("--overlap", type=int, default=100, help="片段重叠长度")
    parser.add_argument(
        "--document_type",
        choices=[item.value for item in PdfDocumentType],
        default=PdfDocumentType.drawing.value,
        help="PDF 文档类型：document 按普通文本切分，drawing 按页切分并生成整页图片",
    )
    parser.add_argument("--gui", action="store_true", help="是否打开窗口展示")
    args = parser.parse_args()

    info, chunks = run_ingest(
        args.pdf,
        args.kb,
        args.chunk_size,
        args.overlap,
        PdfDocumentType.coerce(args.document_type),
    )
    print_summary(info, chunks)
    if args.gui:
        show_gui(chunks)


if __name__ == "__main__":
    main()

