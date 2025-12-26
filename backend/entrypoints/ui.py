import os
import sys
from typing import List, Dict
from dotenv import load_dotenv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from backend.kb.knowledge_base import PersistentKnowledgeBaseController
from backend.kb.ingestion import ingest_pdf, ingest_excel


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


def launch_kb_viewer():
    """启动知识库浏览器GUI，支持导入PDF、删除文件、新建/删除知识库"""
    load_dotenv()
    kb = PersistentKnowledgeBaseController()
    kb_ids = list_kb_ids(kb.base_dir) or [1]

    root = tk.Tk()
    root.title("知识库浏览器")
    root.geometry("1200x760")

    top = ttk.Frame(root)
    top.pack(side=tk.TOP, fill=tk.X)

    ttk.Label(top, text="选择知识库ID:").pack(side=tk.LEFT, padx=5)
    kb_var = tk.StringVar()
    kb_combo = ttk.Combobox(top, textvariable=kb_var, values=[str(i) for i in kb_ids], width=10)
    kb_combo.pack(side=tk.LEFT)
    kb_combo.current(0)

    def get_current_kb_id() -> int:
        try:
            return int(kb_var.get())
        except Exception:
            return 1

    def do_refresh_files():
        files_list.delete(0, tk.END)
        state["files"] = kb.listFilesPaginated(get_current_kb_id(), page=0, page_size=10000)
        for f in state["files"]:
            files_list.insert(tk.END, f"[{f['id']}] {f['filename']} ({f['chunk_count']})")
        chunks_list.delete(0, tk.END)
        content_text.delete("1.0", tk.END)

    def do_create_kb():
        kid = kb_var.get().strip()
        if not kid.isdigit():
            messagebox.showerror("错误", "请输入数字KB ID")
            return
        kb.createKnowledgeBase(int(kid))
        messagebox.showinfo("成功", f"知识库 {kid} 已创建/重置")
        do_refresh_files()

    def do_delete_kb():
        kid = kb_var.get().strip()
        if not kid.isdigit():
            messagebox.showerror("错误", "请输入数字KB ID")
            return
        if not messagebox.askyesno("确认", f"确定删除知识库 {kid} 及其所有内容？"):
            return
        kb.deleteKnowledgeBase(int(kid))
        messagebox.showinfo("成功", f"知识库 {kid} 已删除")
        kb_combo["values"] = [v for v in kb_combo["values"] if v != kid] or ["1"]
        kb_combo.current(0)
        do_refresh_files()

    def do_ingest_pdf():
        path = filedialog.askopenfilename(title="选择PDF文件", filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        info = ingest_pdf(kb, get_current_kb_id(), path, chunk_size=600, overlap=120)
        messagebox.showinfo("成功", f"已导入: {info.filename} ({info.chunk_count} 片段)")
        do_refresh_files()

    def do_ingest_excel():
        """导入 Excel 文件到知识库（按 Sheet 拆分并可生成表格摘要）"""
        path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            info = ingest_excel(kb, get_current_kb_id(), path)
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {e}")
            return
        messagebox.showinfo("成功", f"已导入: {info.filename} ({info.chunk_count} 片段)")
        do_refresh_files()

    def do_delete_file():
        sel = files_list.curselection()
        if not sel:
            return
        f = state["files"][sel[0]]
        if not messagebox.askyesno("确认", f"删除文件 {f['filename']} (ID: {f['id']})？"):
            return
        ok = kb.deleteFile(get_current_kb_id(), int(f["id"]))
        if ok:
            messagebox.showinfo("成功", "文件已删除")
        else:
            messagebox.showerror("错误", "删除失败或文件不存在")
        do_refresh_files()

    refresh_btn = ttk.Button(top, text="刷新文件", command=do_refresh_files)
    refresh_btn.pack(side=tk.LEFT, padx=5)
    create_btn = ttk.Button(top, text="新建/重置KB", command=do_create_kb)
    create_btn.pack(side=tk.LEFT, padx=5)
    delete_kb_btn = ttk.Button(top, text="删除KB", command=do_delete_kb)
    delete_kb_btn.pack(side=tk.LEFT, padx=5)
    ingest_btn = ttk.Button(top, text="导入PDF", command=do_ingest_pdf)
    ingest_btn.pack(side=tk.LEFT, padx=5)
    ingest_excel_btn = ttk.Button(top, text="导入Excel", command=do_ingest_excel)
    ingest_excel_btn.pack(side=tk.LEFT, padx=5)

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    files_frame = ttk.Frame(main_frame)
    files_frame.pack(side=tk.LEFT, fill=tk.Y)
    ttk.Label(files_frame, text="文件列表").pack(anchor=tk.W)
    files_list = tk.Listbox(files_frame, width=40)
    files_list.pack(fill=tk.Y, expand=True)
    del_file_btn = ttk.Button(files_frame, text="删除选中文件", command=do_delete_file)
    del_file_btn.pack(fill=tk.X)

    chunks_frame = ttk.Frame(main_frame)
    chunks_frame.pack(side=tk.LEFT, fill=tk.Y)
    ttk.Label(chunks_frame, text="片段列表").pack(anchor=tk.W)
    chunks_list = tk.Listbox(chunks_frame, width=60)
    chunks_list.pack(fill=tk.Y, expand=True)

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    ttk.Label(content_frame, text="片段内容").pack(anchor=tk.W)
    content_text = tk.Text(content_frame, wrap=tk.WORD)
    content_text.pack(fill=tk.BOTH, expand=True)

    state = {"files": [], "chunks": []}

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

    kb_combo.bind("<<ComboboxSelected>>", lambda e: do_refresh_files())
    files_list.bind("<<ListboxSelect>>", on_file_select)
    chunks_list.bind("<<ListboxSelect>>", on_chunk_select)

    do_refresh_files()
    root.mainloop()


if __name__ == "__main__":
    launch_kb_viewer()

