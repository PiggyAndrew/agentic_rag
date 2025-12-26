import os
import re
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.kb.knowledge_base import PersistentKnowledgeBaseController


KB_CTRL = PersistentKnowledgeBaseController(base_dir=os.path.join("data", "kb"))


def now_ts() -> int:
    """返回当前UTC时间戳（毫秒）"""
    return int(datetime.utcnow().timestamp() * 1000)


def format_kb_id(kb_int: int) -> str:
    """将整型KB ID格式化为带前缀的字符串"""
    return f"kb-{kb_int}"


def parse_kb_id(kb_id: str) -> int:
    """解析字符串KB ID为整数，支持 'kb-123' 与 '123'"""
    m = re.match(r"^kb-(\d+)$", str(kb_id))
    if m:
        return int(m.group(1))
    return int(kb_id)


def kb_meta_path(kb_int: int) -> str:
    """返回KB元数据文件路径"""
    return os.path.join(KB_CTRL._kb_dir(kb_int), "kb.json")


def read_kb_meta(kb_int: int) -> Dict[str, Any]:
    """读取KB元数据，若不存在则返回默认值"""
    path = kb_meta_path(kb_int)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "id": format_kb_id(kb_int),
        "name": f"知识库 {kb_int}",
        "description": None,
        "createdAt": int(os.path.getmtime(KB_CTRL._kb_dir(kb_int))) * 1000
        if os.path.exists(KB_CTRL._kb_dir(kb_int))
        else now_ts(),
    }


def write_kb_meta(kb_int: int, meta: Dict[str, Any]) -> None:
    """写入KB元数据到磁盘"""
    os.makedirs(KB_CTRL._kb_dir(kb_int), exist_ok=True)
    path = kb_meta_path(kb_int)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def list_kbs() -> List[Dict[str, Any]]:
    """列出所有知识库的元数据集合"""
    kbs: List[Dict[str, Any]] = []
    if not os.path.exists(KB_CTRL.base_dir):
        os.makedirs(KB_CTRL.base_dir, exist_ok=True)
    for name in os.listdir(KB_CTRL.base_dir):
        try:
            kb_int = int(name)
        except Exception:
            continue
        kbs.append(read_kb_meta(kb_int))
    kbs.sort(key=lambda m: m.get("createdAt", 0), reverse=True)
    return kbs


def create_kb(payload: Dict[str, Any]) -> Dict[str, Any]:
    """创建新的知识库并写入元数据"""
    existing: List[int] = []
    if os.path.exists(KB_CTRL.base_dir):
        for n in os.listdir(KB_CTRL.base_dir):
            try:
                existing.append(int(n))
            except Exception:
                continue
    next_id = (max(existing) + 1) if existing else 1
    KB_CTRL.createKnowledgeBase(next_id)
    meta = {
        "id": format_kb_id(next_id),
        "name": str(payload.get("name", "")).strip(),
        "description": (str(payload.get("description", "")).strip() or None),
        "createdAt": now_ts(),
    }
    write_kb_meta(next_id, meta)
    return meta


def update_kb(kb_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """更新指定知识库的元数据"""
    kb_int = parse_kb_id(kb_id)
    KB_CTRL._ensure_kb(kb_int)
    meta = read_kb_meta(kb_int)
    if "name" in payload and payload["name"] is not None:
        meta["name"] = str(payload["name"]).strip()
    if "description" in payload and payload["description"] is not None:
        meta["description"] = str(payload["description"]).strip()
    write_kb_meta(kb_int, meta)
    return meta


def delete_kb(kb_id: str) -> None:
    """删除指定知识库及其内容"""
    kb_int = parse_kb_id(kb_id)
    KB_CTRL.deleteKnowledgeBase(kb_int)


def list_files(kb_id: str) -> List[Dict[str, Any]]:
    """列出指定知识库下的文件信息"""
    kb_int = parse_kb_id(kb_id)
    KB_CTRL._ensure_kb(kb_int)
    meta = KB_CTRL._load_files(kb_int)
    files = meta.get("files", [])
    out: List[Dict[str, Any]] = []
    for f in files:
        fid = int(f.get("id"))
        filename = f.get("filename")
        chunk_count = int(f.get("chunk_count", 0))
        chunks_path = os.path.join(KB_CTRL._chunks_dir(kb_int), f"{fid}.json")
        created_at = int(os.path.getmtime(chunks_path)) * 1000 if os.path.exists(chunks_path) else now_ts()
        lower = (str(filename or "")).lower()
        if lower.endswith(".pdf"):
            ftype = "application/pdf"
        elif lower.endswith(".xlsx"):
            ftype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            ftype = "application/octet-stream"
        status = str(f.get("status", "done"))
        out.append({
            "id": f"f-{fid}",
            "kbId": format_kb_id(kb_int),
            "name": filename,
            "type": ftype,
            "createdAt": created_at,
            "chunkCount": chunk_count,
            "status": status,
        })
    return out


def save_upload(kb_id: str, name: str, content_b64: Optional[str]) -> Dict[str, Any]:
    """保存上传文件（可选Base64内容）并入库为未向量化"""
    kb_int = parse_kb_id(kb_id)
    KB_CTRL._ensure_kb(kb_int)
    lower = name.lower()
    uploads_dir = os.path.join(KB_CTRL._kb_dir(kb_int), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    saved_path = os.path.join(uploads_dir, name)
    if content_b64:
        import base64
        with open(saved_path, "wb") as f:
            f.write(base64.b64decode(content_b64))
    meta = KB_CTRL._load_files(kb_int)
    files = meta.get("files", [])
    existing = None
    for f in files:
        if str(f.get("filename")) == name:
            existing = f
            break
    if existing:
        existing["chunk_count"] = 0
        existing["status"] = "uploaded"
        KB_CTRL._save_files(kb_int, meta)
        fid = int(existing.get("id"))
    else:
        info = KB_CTRL.add_file(kb_int, filename=name, chunk_count=0, status="uploaded")
        fid = int(info.id)
    ftype = "application/pdf" if lower.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return {
        "id": f"f-{fid}",
        "kbId": format_kb_id(kb_int),
        "name": name,
        "type": ftype,
        "createdAt": now_ts(),
        "chunkCount": 0,
        "status": "uploaded",
    }


def read_file_chunks(kb_id: str, file_id: str) -> List[Dict[str, Any]]:
    """读取指定文件的全部片段内容"""
    kb_int = parse_kb_id(kb_id)
    m = re.match(r"^f-(\d+)$", str(file_id))
    if not m:
        raise ValueError("文件ID格式错误")
    fid = int(m.group(1))
    chunks = KB_CTRL._load_file_chunks(kb_int, fid)
    return [c.__dict__ for c in chunks]


def ingest_uploaded_file(kb_id: str, filename: str) -> Dict[str, Any]:
    """向量化处理上传到uploads目录的PDF或Excel文件"""
    kb_int = parse_kb_id(kb_id)
    KB_CTRL._ensure_kb(kb_int)
    lower = filename.lower()
    uploads_dir = os.path.join(KB_CTRL._kb_dir(kb_int), "uploads")
    src_path = os.path.join(uploads_dir, filename)
    if not os.path.exists(src_path):
        raise FileNotFoundError("文件不存在，请先上传")
    from kb.ingestion import ingest_pdf, ingest_excel
    if lower.endswith(".pdf"):
        info = ingest_pdf(KB_CTRL, kb_int, src_path)
        ftype = "application/pdf"
    elif lower.endswith(".xlsx"):
        info = ingest_excel(KB_CTRL, kb_int, src_path)
        ftype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise ValueError("仅支持 PDF 或 Excel(xlsx)")
    meta = KB_CTRL._load_files(kb_int)
    files = meta.get("files", [])
    chunk_count = 0
    for f in files:
        if int(f.get("id")) == int(info.id):
            chunk_count = int(f.get("chunk_count", 0))
            break
    return {
        "id": f"f-{info.id}",
        "kbId": format_kb_id(kb_int),
        "name": info.filename,
        "type": ftype,
        "createdAt": now_ts(),
        "chunkCount": chunk_count,
        "status": "done",
    }


def delete_file_global(file_id: str) -> None:
    """在所有知识库中查找并删除指定文件ID"""
    m = re.match(r"^f-(\d+)$", str(file_id))
    if not m:
        raise ValueError("文件ID格式错误")
    fid = int(m.group(1))
    if not os.path.exists(KB_CTRL.base_dir):
        raise FileNotFoundError("文件不存在")
    for name in os.listdir(KB_CTRL.base_dir):
        try:
            kb_int = int(name)
        except Exception:
            continue
        if KB_CTRL.deleteFile(kb_int, fid):
            return
    raise FileNotFoundError("文件不存在")
