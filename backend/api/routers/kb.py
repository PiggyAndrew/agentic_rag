from typing import List, Dict, Any
import logging
from fastapi import APIRouter, HTTPException

from backend.api.models import KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate, KBFile, KBFileCreate, IngestRequest
from backend.services import kb_service
from backend.kb.types import KnowledgeBasePatch


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/kb", response_model=List[KnowledgeBase])
def list_kbs():
    """列出所有知识库（读取持久化元数据）"""
    metas = kb_service.list_kbs()
    return [
        KnowledgeBase(
            id=f"kb-{int(m.kb_id)}",
            name=m.name,
            description=m.description,
            createdAt=int(m.created_at_ms),
        )
        for m in metas
    ]


@router.post("/api/kb", response_model=KnowledgeBase)
def create_kb(payload: KnowledgeBaseCreate):
    """创建知识库并持久化元数据"""
    meta = kb_service.create_kb(payload)
    return KnowledgeBase(
        id=f"kb-{int(meta.kb_id)}",
        name=meta.name,
        description=meta.description,
        createdAt=int(meta.created_at_ms),
    )


@router.put("/api/kb/{kb_id}", response_model=KnowledgeBase)
def update_kb(kb_id: str, payload: KnowledgeBaseUpdate):
    """更新知识库的名称或描述"""
    patch = KnowledgeBasePatch(name=payload.name, description=payload.description)
    meta = kb_service.update_kb(kb_id, patch)
    return KnowledgeBase(
        id=f"kb-{int(meta.kb_id)}",
        name=meta.name,
        description=meta.description,
        createdAt=int(meta.created_at_ms),
    )


@router.delete("/api/kb/{kb_id}")
def delete_kb(kb_id: str):
    """删除指定知识库"""
    kb_service.delete_kb(kb_id)
    return {"ok": True}


@router.get("/api/kb/{kb_id}/files", response_model=List[KBFile])
def list_files(kb_id: str):
    """列出知识库下的文件"""
    files = kb_service.list_files(kb_id)
    return [
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


@router.post("/api/kb/{kb_id}/files", response_model=KBFile)
def upload_file(kb_id: str, payload: KBFileCreate):
    """上传文件（可选Base64），入库为未向量化"""
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    lower = name.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="仅支持上传 PDF 或 Excel(xlsx) 文件")
    info = kb_service.save_upload(kb_id, name, payload.contentBase64)
    return KBFile(
        id=f"f-{int(info.file_id)}",
        kbId=f"kb-{int(info.kb_id)}",
        name=info.name,
        type=info.mime_type,
        createdAt=int(info.created_at_ms),
        chunkCount=int(info.chunk_count),
        status=str(info.status),
    )


@router.get("/api/kb/{kb_id}/files/{file_id}/chunks")
def read_file_chunks(kb_id: str, file_id: str):
    """读取指定文件的全部片段内容"""
    try:
        return kb_service.read_file_chunks(kb_id, file_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/kb/{kb_id}/ingest", response_model=KBFile)
def ingest_uploaded_file(kb_id: str, payload: IngestRequest):
    """向量化处理已上传文件（PDF/Excel）"""
    name = (payload.filename or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="filename 不能为空")
    try:
        info = kb_service.ingest_uploaded_file(kb_id, name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("kb ingest failed: kb_id=%s filename=%s", kb_id, name)
        raise HTTPException(status_code=500, detail=f"向量化失败: {type(e).__name__}: {e}")
    return KBFile(
        id=f"f-{int(info.file_id)}",
        kbId=f"kb-{int(info.kb_id)}",
        name=info.name,
        type=info.mime_type,
        createdAt=int(info.created_at_ms),
        chunkCount=int(info.chunk_count),
        status=str(info.status),
    )


@router.delete("/api/files/{file_id}")
def delete_file(file_id: str):
    """删除文件（在所有知识库中查找并删除）"""
    try:
        kb_service.delete_file_global(file_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

