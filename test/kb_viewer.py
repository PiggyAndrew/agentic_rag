import os
import sys
from typing import List, Dict

# 确保可导入顶层包 `kb`
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from kb.knowledge_base import PersistentKnowledgeBaseController


def list_kb_ids(base_dir: str) -> List[int]:
    """列出所有存在的知识库ID（基于目录名解析）"""
    ids: List[int] = []
    if not os.path.exists(base_dir):
        return ids
    for name in os.listdir(base_dir):
        p = os.path.join(base_dir, name)
        if os.path.isdir(p):
            try:
                ids.append(int(name))
            except Exception:
                pass
    return sorted(ids)


def format_chunk_preview(c: Dict) -> str:
    """格式化片段预览文本，带层级路径信息（如存在）"""
    content = c.get("content", "")
    preview = (content[:80] + "...") if len(content) > 80 else content
    meta = c.get("metadata")
    if meta and meta.get("path"):
        path_str = " > ".join([f"{p['number']} {p['title']}" for p in meta.get("path", [])])
        return f"[{c['chunk_index']}] {path_str} | {preview}"
    return f"[{c['chunk_index']}] {preview}"


def main():
    """启动知识库浏览器GUI：选择KB、文件并查看片段内容"""
    import tkinter as tk
    from tkinter import ttk

    kb = PersistentKnowledgeBaseController()
    kb_ids = list_kb_ids(kb.base_dir)

    root = tk.Tk()
    root.title("知识库浏览器")
    root.geometry("1100x700")

    top = ttk.Frame(root)
    top.pack(side=tk.TOP, fill=tk.X)

    ttk.Label(top, text="选择知识库ID:").pack(side=tk.LEFT, padx=5)
    kb_var = tk.StringVar()
    kb_combo = ttk.Combobox(top, textvariable=kb_var, values=[str(i) for i in kb_ids] or ["1"], width=10)
    kb_combo.pack(side=tk.LEFT)
    kb_combo.current(0)

    refresh_btn = ttk.Button(top, text="刷新", command=lambda: refresh_files())
    refresh_btn.pack(side=tk.LEFT, padx=5)

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    files_frame = ttk.Frame(main_frame)
    files_frame.pack(side=tk.LEFT, fill=tk.Y)
    ttk.Label(files_frame, text="文件列表").pack(anchor=tk.W)
    files_list = tk.Listbox(files_frame, width=40)
    files_list.pack(fill=tk.Y, expand=True)

    chunks_frame = ttk.Frame(main_frame)
    chunks_frame.pack(side=tk.LEFT, fill=tk.Y)
    ttk.Label(chunks_frame, text="片段列表").pack(anchor=tk.W)
    chunks_list = tk.Listbox(chunks_frame, width=50)
    chunks_list.pack(fill=tk.Y, expand=True)

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    ttk.Label(content_frame, text="片段内容").pack(anchor=tk.W)
    content_text = tk.Text(content_frame, wrap=tk.WORD)
    content_text.pack(fill=tk.BOTH, expand=True)

    state = {"files": [], "chunks": []}

    def get_current_kb_id() -> int:
        try:
            return int(kb_var.get())
        except Exception:
            return 1

    def refresh_files():
        files_list.delete(0, tk.END)
        state["files"] = kb.listFilesPaginated(get_current_kb_id(), page=0, page_size=10000)
        for f in state["files"]:
            files_list.insert(tk.END, f"[{f['id']}] {f['filename']} ({f['chunk_count']})")
        chunks_list.delete(0, tk.END)
        content_text.delete("1.0", tk.END)

    def on_file_select(evt):
        sel = files_list.curselection()
        if not sel:
            return
        f = state["files"][sel[0]]
        fid = f["id"]
        cnt = f["chunk_count"]
        state["chunks"] = kb.readFileChunks(get_current_kb_id(), [{"fileId": fid, "chunkIndex": i} for i in range(cnt)])
        chunks_list.delete(0, tk.END)
        for c in state["chunks"]:
            chunks_list.insert(tk.END, format_chunk_preview(c))
        content_text.delete("1.0", tk.END)

    def on_chunk_select(evt):
        sel = chunks_list.curselection()
        if not sel:
            return
        c = state["chunks"][sel[0]]
        content_text.delete("1.0", tk.END)
        content_text.insert("1.0", c.get("content", ""))

    kb_combo.bind("<<ComboboxSelected>>", lambda e: refresh_files())
    files_list.bind("<<ListboxSelect>>", on_file_select)
    chunks_list.bind("<<ListboxSelect>>", on_chunk_select)

    refresh_files()
    root.mainloop()


if __name__ == "__main__":
    main()

