import argparse
import json
import os
import sys
from typing import List, Dict, Optional

# 确保可导入顶层包 `kb`
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from kb.knowledge_base import PersistentKnowledgeBaseController


def list_all_files(kb_id: int) -> List[Dict]:
    """列出持久化知识库中的所有文件元信息"""
    kb = PersistentKnowledgeBaseController()
    return kb.listFilesPaginated(kb_id, page=0, page_size=10000)


def read_chunks(kb_id: int, file_id: int) -> List[Dict]:
    """读取指定文件的全部片段内容"""
    kb = PersistentKnowledgeBaseController()
    files = kb.listFilesPaginated(kb_id, page=0, page_size=1)
    chunks = kb.readFileChunks(
        kb_id,
        [{"fileId": file_id, "chunkIndex": i} for i in range(files[0]["chunk_count"])],
    )
    return chunks


def print_summary(file_info: Dict, chunks: List[Dict]) -> None:
    """打印文件摘要与片段示例信息"""
    print("文件信息:")
    print(json.dumps(file_info, ensure_ascii=False, indent=2))
    print(f"片段总数: {len(chunks)}")
    preview_count = min(5, len(chunks))
    print(f"示例前{preview_count}个片段预览:")
    for i in range(preview_count):
        c = chunks[i]
        content = c.get("content", "")
        short = (content[:200] + "...") if len(content) > 200 else content
        print(f"- [{c['chunk_index']}] {short}")


def show_gui(chunks: List[Dict]) -> None:
    """图形界面展示片段列表与内容"""
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("持久化分割结果查看")
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
    """命令行入口：从持久化中读取文件与片段并展示"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb", type=int, default=1, help="知识库ID")
    parser.add_argument("--file_id", type=int, default=None, help="文件ID，不传则选最新")
    parser.add_argument("--gui", action="store_true", help="是否打开窗口展示")
    args = parser.parse_args()

    files = list_all_files(args.kb)
    if not files:
        print("暂无持久化数据，请先执行导入测试脚本")
        return

    target_id: Optional[int] = args.file_id
    if target_id is None:
        target_id = max(f["id"] for f in files)
    target_file = next((f for f in files if f["id"] == target_id), None)
    if not target_file:
        print(f"未找到文件ID: {target_id}")
        return

    kb = PersistentKnowledgeBaseController()
    chunks = kb.readFileChunks(
        args.kb, [{"fileId": target_id, "chunkIndex": i} for i in range(target_file["chunk_count"])],
    )
    info = {
        "id": target_id,
        "filename": target_file["filename"],
        "chunk_count": target_file["chunk_count"],
        "status": target_file.get("status", "done"),
    }

    print_summary(info, chunks)
    if args.gui:
        show_gui(chunks)


if __name__ == "__main__":
    main()

