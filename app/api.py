
import sys
import os
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OTEL_PYTHON_DISABLED", "true")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_TRACING", "false")
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime
import uuid
import re
import os
from kb.knowledge_base import PersistentKnowledgeBaseController
import uvicorn
from dotenv import load_dotenv

# 导入你的 Agent
from app.agent import agent as rag_agent

load_dotenv()

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    kbId: Optional[str] = None

from app.protocol import stream_generator as protocol_stream_generator

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """聊天接口：支持指定单个参与检索的知识库ID"""
    return StreamingResponse(
        protocol_stream_generator(request.messages, request.kbId),
        media_type="text/plain; charset=utf-8"
    )

# =========================
# 知识库管理接口（内存存储）
# =========================

class KnowledgeBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    createdAt: int

class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class KBFile(BaseModel):
    id: str
    kbId: str
    name: str
    type: str
    createdAt: int
    chunkCount: int
    status: str

class KBFileCreate(BaseModel):
    name: str
    type: Optional[str] = "application/octet-stream"
    contentBase64: Optional[str] = None
KB_CTRL = PersistentKnowledgeBaseController(base_dir=os.path.join("data", "kb"))

def _now_ts() -> int:
    """获取当前时间戳（毫秒）"""
    return int(datetime.utcnow().timestamp() * 1000)

def _format_kb_id(kb_int: int) -> str:
    """将整型知识库ID格式化为字符串ID"""
    return f"kb-{kb_int}"

def _parse_kb_id(kb_id: str) -> int:
    """解析字符串知识库ID为整数ID，支持 'kb-123' 或 '123'"""
    m = re.match(r"^kb-(\d+)$", str(kb_id))
    if m:
        return int(m.group(1))
    return int(kb_id)

def _kb_meta_path(kb_int: int) -> str:
    """KB 元数据路径"""
    return os.path.join(KB_CTRL._kb_dir(kb_int), "kb.json")

def _read_kb_meta(kb_int: int) -> Dict[str, Any]:
    """读取 KB 元数据，不存在时返回默认值"""
    path = _kb_meta_path(kb_int)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # 默认元数据
    return {
        "id": _format_kb_id(kb_int),
        "name": f"知识库 {kb_int}",
        "description": None,
        "createdAt": int(os.path.getmtime(KB_CTRL._kb_dir(kb_int))) if os.path.exists(KB_CTRL._kb_dir(kb_int)) else _now_ts(),
    }

def _write_kb_meta(kb_int: int, meta: Dict[str, Any]) -> None:
    """写入 KB 元数据"""
    os.makedirs(KB_CTRL._kb_dir(kb_int), exist_ok=True)
    path = _kb_meta_path(kb_int)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

@app.get("/api/kb", response_model=List[KnowledgeBase])
def list_kbs():
    """列出所有知识库（扫描持久化目录并读取元数据）"""
    kbs: List[KnowledgeBase] = []
    if not os.path.exists(KB_CTRL.base_dir):
        os.makedirs(KB_CTRL.base_dir, exist_ok=True)
    for name in os.listdir(KB_CTRL.base_dir):
        try:
            kb_int = int(name)
        except Exception:
            continue
        meta = _read_kb_meta(kb_int)
        kbs.append(KnowledgeBase(**meta))
    # 按创建时间倒序
    kbs.sort(key=lambda x: x.createdAt, reverse=True)
    return kbs

@app.post("/api/kb", response_model=KnowledgeBase)
def create_kb(payload: KnowledgeBaseCreate):
    """创建知识库（持久化目录与元数据）"""
    # 选择下一个可用整型ID
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
        "id": _format_kb_id(next_id),
        "name": payload.name.strip(),
        "description": (payload.description or "").strip() or None,
        "createdAt": _now_ts(),
    }
    _write_kb_meta(next_id, meta)
    return KnowledgeBase(**meta)

@app.put("/api/kb/{kb_id}", response_model=KnowledgeBase)
def update_kb(kb_id: str, payload: KnowledgeBaseUpdate):
    """更新知识库名称或描述（持久化元数据）"""
    kb_int = _parse_kb_id(kb_id)
    KB_CTRL._ensure_kb(kb_int)
    meta = _read_kb_meta(kb_int)
    if payload.name is not None:
        meta["name"] = payload.name.strip()
    if payload.description is not None:
        meta["description"] = payload.description.strip()
    _write_kb_meta(kb_int, meta)
    return KnowledgeBase(**meta)

@app.delete("/api/kb/{kb_id}")
def delete_kb(kb_id: str):
    """删除知识库及其文件（持久化删除）"""
    kb_int = _parse_kb_id(kb_id)
    KB_CTRL.deleteKnowledgeBase(kb_int)
    return {"ok": True}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.api:app",
        host="127.0.0.1",
        port=port,
        reload=False
    )

@app.get("/api/kb/{kb_id}/files", response_model=List[KBFile])
def list_files(kb_id: str):
    """列出知识库下的文件（从持久化文件列表构建响应）"""
    kb_int = _parse_kb_id(kb_id)
    KB_CTRL._ensure_kb(kb_int)
    meta = KB_CTRL._load_files(kb_int)
    files = meta.get("files", [])
    out: List[KBFile] = []
    for f in files:
        fid = int(f.get("id"))
        filename = f.get("filename")
        chunk_count = int(f.get("chunk_count", 0))
        # 估算 createdAt 为 chunks 文件的 mtime 或当前时间
        chunks_path = os.path.join(KB_CTRL._chunks_dir(kb_int), f"{fid}.json")
        created_at = int(os.path.getmtime(chunks_path)) * 1000 if os.path.exists(chunks_path) else _now_ts()
        lower = (filename or "").lower()
        if lower.endswith(".pdf"):
            ftype = "application/pdf"
        elif lower.endswith(".xlsx"):
            ftype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            ftype = "application/octet-stream"
        status = str(f.get("status", "done"))
        out.append(KBFile(
            id=f"f-{fid}",
            kbId=_format_kb_id(kb_int),
            name=filename,
            type=ftype,
            createdAt=created_at,
            chunkCount=chunk_count,
            status=status,
        ))
    return out

@app.post("/api/kb/{kb_id}/files", response_model=KBFile)
def upload_file(kb_id: str, payload: KBFileCreate):
    """上传文件元数据（JSON），可选 base64 内容写入 uploads 目录；同时入库为未向量化"""
    kb_int = _parse_kb_id(kb_id)
    KB_CTRL._ensure_kb(kb_int)
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    lower = name.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="仅支持上传 PDF 或 Excel(xlsx) 文件")
    uploads_dir = os.path.join(KB_CTRL._kb_dir(kb_int), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    saved_path = os.path.join(uploads_dir, name)
    if payload.contentBase64:
        try:
            import base64
            with open(saved_path, "wb") as f:
                f.write(base64.b64decode(payload.contentBase64))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存文件失败: {e}")
    # 入库：同名文件更新为未向量化，否则新增
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
    return KBFile(
        id=f"f-{fid}",
        kbId=_format_kb_id(kb_int),
        name=name,
        type=ftype,
        createdAt=_now_ts(),
        chunkCount=0,
        status="uploaded",
    )

@app.get("/api/kb/{kb_id}/files/{file_id}/chunks")
def read_file_chunks(kb_id: str, file_id: str):
    """读取指定文件的全部片段内容"""
    kb_int = _parse_kb_id(kb_id)
    m = re.match(r"^f-(\d+)$", str(file_id))
    if not m:
        raise HTTPException(status_code=400, detail="文件ID格式错误")
    fid = int(m.group(1))
    chunks = KB_CTRL._load_file_chunks(kb_int, fid)
    return [c.__dict__ for c in chunks]

@app.post("/api/kb/{kb_id}/ingest", response_model=KBFile)
def ingest_uploaded_file(kb_id: str, payload: Dict[str, Any]):
    """向量化处理上传到 uploads 目录的文件（PDF/Excel）"""
    kb_int = _parse_kb_id(kb_id)
    KB_CTRL._ensure_kb(kb_int)
    name = (payload.get("filename") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="filename 不能为空")
    lower = name.lower()
    uploads_dir = os.path.join(KB_CTRL._kb_dir(kb_int), "uploads")
    src_path = os.path.join(uploads_dir, name)
    if not os.path.exists(src_path):
        raise HTTPException(status_code=404, detail="文件不存在，请先上传")
    # 删除未向量化的同名占位，以避免重复
    try:
        meta0 = KB_CTRL._load_files(kb_int)
        for f in list(meta0.get("files", [])):
            if str(f.get("filename")) == name and str(f.get("status", "")) == "uploaded":
                KB_CTRL.deleteFile(kb_int, int(f.get("id")))
    except Exception:
        pass
    # 选择合适的摄取器
    try:
        from kb.ingestion import ingest_pdf, ingest_excel
        if lower.endswith(".pdf"):
            info = ingest_pdf(KB_CTRL, kb_int, src_path)
            ftype = "application/pdf"
        elif lower.endswith(".xlsx"):
            info = ingest_excel(KB_CTRL, kb_int, src_path)
            ftype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            raise HTTPException(status_code=400, detail="仅支持 PDF 或 Excel(xlsx)")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"向量化失败: {e}")
    # 从 files.json 获取 chunk_count
    meta = KB_CTRL._load_files(kb_int)
    files = meta.get("files", [])
    chunk_count = 0
    for f in files:
        if int(f.get("id")) == int(info.id):
            chunk_count = int(f.get("chunk_count", 0))
            break
    return KBFile(
        id=f"f-{info.id}",
        kbId=_format_kb_id(kb_int),
        name=info.filename,
        type=ftype,
        createdAt=_now_ts(),
        chunkCount=chunk_count,
        status="done",
    )

@app.delete("/api/files/{file_id}")
def delete_file(file_id: str):
    """删除文件"""
    m = re.match(r"^f-(\d+)$", str(file_id))
    if not m:
        raise HTTPException(status_code=400, detail="文件ID格式错误")
    fid = int(m.group(1))
    # 文件ID无法直接推断 KB，需要在各 KB 中尝试删除
    # 为简化，这里扫描所有 KB
    if not os.path.exists(KB_CTRL.base_dir):
        raise HTTPException(status_code=404, detail="文件不存在")
    ok = False
    for name in os.listdir(KB_CTRL.base_dir):
        try:
            kb_int = int(name)
        except Exception:
            continue
        if KB_CTRL.deleteFile(kb_int, fid):
            ok = True
            break
    if not ok:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"ok": True}

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

if __name__ == "__main__":
    main()
