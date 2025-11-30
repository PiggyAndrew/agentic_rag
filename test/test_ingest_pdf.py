import argparse
import json
import os
import sys
from typing import List, Dict, Tuple

# 将项目根目录加入模块搜索路径，确保可导入顶层包 `kb`
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from kb.knowledge_base import PersistentKnowledgeBaseController
from kb.ingestion import ingest_pdf


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
    """使用与标准 UI 相同的布局与预览格式展示片段列表与内容"""
    import tkinter as tk
    from tkinter import ttk

    def format_chunk_preview(c: Dict) -> str:
        """与 app/ui.py 同步的预览：包含层级路径（如有）"""
        content = c.get("content", "")
        preview = (content[:80] + "...") if len(content) > 80 else content
        meta = c.get("metadata")
        if meta and meta.get("path"):
            path_str = " > ".join([f"{p['number']} {p['title']}" for p in meta.get("path", [])])
            return f"[{c['chunk_index']}] {path_str} | {preview}"
        return f"[{c['chunk_index']}] {preview}"

    root = tk.Tk()
    root.title("PDF分割结果查看")
    root.geometry("1200x760")

    # 主框架
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 片段列表区域（与标准 UI 一致的标签与宽度）
    chunks_frame = ttk.Frame(main_frame)
    chunks_frame.pack(side=tk.LEFT, fill=tk.Y)
    ttk.Label(chunks_frame, text="片段列表").pack(anchor=tk.W)
    lst = tk.Listbox(chunks_frame, width=60)
    lst.pack(fill=tk.Y, expand=True)

    # 内容展示区域
    content_frame = ttk.Frame(main_frame)
    content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    ttk.Label(content_frame, text="片段内容").pack(anchor=tk.W)
    txt = tk.Text(content_frame, wrap=tk.WORD)
    txt.pack(fill=tk.BOTH, expand=True)

    # 填充列表
    for c in chunks:
        lst.insert(tk.END, format_chunk_preview(c))

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
        default=r"test/testfiles/CPX_NTC_BEP_r5.pdf",
        help="PDF文件路径",
    )
    parser.add_argument("--kb", type=int, default=1, help="知识库ID")
    parser.add_argument("--chunk_size", type=int, default=500, help="片段长度")
    parser.add_argument("--overlap", type=int, default=100, help="片段重叠长度")
    parser.add_argument("--gui", action="store_true", help="是否打开窗口展示")
    args = parser.parse_args()

    info, chunks = run_ingest(args.pdf, args.kb, args.chunk_size, args.overlap)
    #print_summary(info, chunks)
    if args.gui:
        show_gui(chunks)


if __name__ == "__main__":
    main()

