from typing import List, Dict, Any
import logging
from fastapi import APIRouter, HTTPException

from backend.api.models import KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate, KBFile, KBFileCreate, IngestRequest, ApiResponse
from backend.services import kb_service
from backend.kb.types import KnowledgeBasePatch


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/kb", response_model=ApiResponse)
def list_kbs():
    """列出所有知识库（读取持久化元数据）"""
    metas = kb_service.list_kbs()
    data = [
        KnowledgeBase(
            id=f"kb-{int(m.kb_id)}",
            name=m.name,
            description=m.description,
            createdAt=int(m.created_at_ms),
        )
        for m in metas
    ]
    return ApiResponse(ok=True, data=data)


@router.post("/api/kb", response_model=ApiResponse)
def create_kb(payload: KnowledgeBaseCreate):
    """创建知识库并持久化元数据"""
    meta = kb_service.create_kb(payload)
    return ApiResponse(
        ok=True,
        data=KnowledgeBase(
            id=f"kb-{int(meta.kb_id)}",
            name=meta.name,
            description=meta.description,
            createdAt=int(meta.created_at_ms),
        ),
    )


@router.put("/api/kb/{kb_id}", response_model=ApiResponse)
def update_kb(kb_id: str, payload: KnowledgeBaseUpdate):
    """更新知识库的名称或描述"""
    patch = KnowledgeBasePatch(name=payload.name, description=payload.description)
    meta = kb_service.update_kb(kb_id, patch)
    return ApiResponse(
        ok=True,
        data=KnowledgeBase(
            id=f"kb-{int(meta.kb_id)}",
            name=meta.name,
            description=meta.description,
            createdAt=int(meta.created_at_ms),
        ),
    )


@router.delete("/api/kb/{kb_id}", response_model=ApiResponse)
def delete_kb(kb_id: str):
    """删除指定知识库"""
    kb_service.delete_kb(kb_id)
    return ApiResponse(ok=True, data={"ok": True})


@router.get("/api/kb/{kb_id}/files", response_model=ApiResponse)
def list_files(kb_id: str):
    """列出知识库下的文件"""
    files = kb_service.list_files(kb_id)
    data = [
        KBFile(
            id=f"f-{int(f.file_id)}",
            kbId=f"kb-{int(f.kb_id)}",
            name=f.name,
            type=f.mime_type,
            createdAt=int(f.created_at_ms),
            chunkCount=int(f.chunk_count),
            status=str(f.status),
        )
        for f in files
    ]
    return ApiResponse(ok=True, data=data)


@router.post("/api/kb/{kb_id}/files", response_model=ApiResponse)
def upload_file(kb_id: str, payload: KBFileCreate):
    """上传文件（可选Base64），入库为未向量化"""
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    lower = name.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="仅支持上传 PDF 或 Excel(xlsx) 文件")
    info = kb_service.save_upload(kb_id, name, payload.contentBase64)
    return ApiResponse(
        ok=True,
        data=KBFile(
            id=f"f-{int(info.file_id)}",
            kbId=f"kb-{int(info.kb_id)}",
            name=info.name,
            type=info.mime_type,
            createdAt=int(info.created_at_ms),
            chunkCount=int(info.chunk_count),
            status=str(info.status),
        ),
    )


@router.get("/api/kb/{kb_id}/files/{file_id}/chunks", response_model=ApiResponse)
def read_file_chunks(kb_id: str, file_id: str):
    """读取指定文件的全部片段内容"""
    data = kb_service.read_file_chunks(kb_id, file_id)
    return ApiResponse(ok=True, data=data)


@router.post("/api/kb/{kb_id}/ingest", response_model=ApiResponse)
def ingest_uploaded_file(kb_id: str, payload: IngestRequest):
    """向量化处理已上传文件（PDF/Excel）"""
    name = (payload.filename or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="filename 不能为空")
    info = kb_service.ingest_uploaded_file(kb_id, name)
    return ApiResponse(
        ok=True,
        data=KBFile(
            id=f"f-{int(info.file_id)}",
            kbId=f"kb-{int(info.kb_id)}",
            name=info.name,
            type=info.mime_type,
            createdAt=int(info.created_at_ms),
            chunkCount=int(info.chunk_count),
            status=str(info.status),
        ),
    )


@router.delete("/api/files/{file_id}", response_model=ApiResponse)
def delete_file(file_id: str):
    """删除文件（在所有知识库中查找并删除）"""
    kb_service.delete_file_global(file_id)
    return ApiResponse(ok=True, data={"ok": True})

