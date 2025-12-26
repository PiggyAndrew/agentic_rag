import argparse
import json
import os
import sys
from typing import List, Dict, Tuple

# 将项目根目录加入模块搜索路径，确保可导入顶层包 `kb`
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.kb.knowledge_base import PersistentKnowledgeBaseController
from backend.kb.ingestion import ingest_pdf
def run_ingest(pdf_path: str, kb_id: int, chunk_size: int, overlap: int) -> Tuple[Dict, List[Dict]]:
    """执行PDF导入流程并返回文件信息与片段列表

    - `pdf_path`：PDF文件路径
    - `kb_id`：知识库ID
    - `chunk_size`：片段长度
    - `overlap`：片段重叠长度
    - 返回：`(file_info_dict, chunks_dict_list)`
    """
    kb = PersistentKnowledgeBaseController()
    info = ingest_pdf(kb, kb_id, pdf_path, chunk_size=chunk_size, overlap=overlap)
    chunks = kb.readFileChunks(
        kb_id,
        [{"fileId": info.id, "chunkIndex": i} for i in range(info.chunk_count)],
    )
    return (
        {
            "id": info.id,
            "filename": info.filename,
            "chunk_count": info.chunk_count,
            "status": info.status,
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
        default=r"tests\\testfiles\\Attachment E - BIM Guide for Facilities Upkeep_Ver2.0_Jun21-20211007-113450.pdf",
        help="PDF文件路径",
    )
    parser.add_argument("--kb", type=int, default=1, help="知识库ID")
    parser.add_argument("--chunk_size", type=int, default=500, help="片段长度")
    parser.add_argument("--overlap", type=int, default=100, help="片段重叠长度")
    parser.add_argument("--gui", action="store_true", help="是否打开窗口展示")
    args = parser.parse_args()

    info, chunks = run_ingest(args.pdf, args.kb, args.chunk_size, args.overlap)
    print_summary(info, chunks)
    if args.gui:
        show_gui(chunks)


if __name__ == "__main__":
    main()

