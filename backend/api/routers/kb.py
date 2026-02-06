from typing import List, Dict, Any
import logging
from fastapi import APIRouter, Depends, HTTPException

from backend.api.models import KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate, KBFile, KBFileCreate, IngestRequest, ApiResponse
from backend.api.mappers.kb import kb_file_to_api, kb_meta_to_api
from backend.api.deps import get_kb_usecase
from backend.modules.kb.application.usecase import KnowledgeBaseUseCase


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/kb", response_model=ApiResponse)
def list_kbs(kb: KnowledgeBaseUseCase = Depends(get_kb_usecase)):
    """列出所有知识库（读取持久化元数据）"""
    metas = kb.list_kbs()
    data = [kb_meta_to_api(m) for m in metas]
    return ApiResponse(ok=True, data=data)


@router.post("/api/kb", response_model=ApiResponse)
def create_kb(payload: KnowledgeBaseCreate, kb: KnowledgeBaseUseCase = Depends(get_kb_usecase)):
    """创建知识库并持久化元数据"""
    meta = kb.create_kb(payload)
    return ApiResponse(
        ok=True,
        data=kb_meta_to_api(meta),
    )


@router.put("/api/kb/{kb_id}", response_model=ApiResponse)
def update_kb(kb_id: str, payload: KnowledgeBaseUpdate, kb: KnowledgeBaseUseCase = Depends(get_kb_usecase)):
    """更新知识库的名称或描述"""
    meta = kb.update_kb(kb_id, payload)
    return ApiResponse(
        ok=True,
        data=kb_meta_to_api(meta),
    )


@router.delete("/api/kb/{kb_id}", response_model=ApiResponse)
def delete_kb(kb_id: str, kb: KnowledgeBaseUseCase = Depends(get_kb_usecase)):
    """删除指定知识库"""
    kb.delete_kb(kb_id)
    return ApiResponse(ok=True, data={"ok": True})


@router.get("/api/kb/{kb_id}/files", response_model=ApiResponse)
def list_files(kb_id: str, kb: KnowledgeBaseUseCase = Depends(get_kb_usecase)):
    """列出知识库下的文件"""
    files = kb.list_files(kb_id)
    data = [kb_file_to_api(f) for f in files]
    return ApiResponse(ok=True, data=data)


@router.post("/api/kb/{kb_id}/files", response_model=ApiResponse)
def upload_file(kb_id: str, payload: KBFileCreate, kb: KnowledgeBaseUseCase = Depends(get_kb_usecase)):
    """上传文件（可选Base64），入库为未向量化"""
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    lower = name.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="仅支持上传 PDF 或 Excel(xlsx) 文件")
    info = kb.save_upload(kb_id, name, payload.contentBase64)
    return ApiResponse(
        ok=True,
        data=kb_file_to_api(info),
    )


@router.get("/api/kb/{kb_id}/files/{file_id}/chunks", response_model=ApiResponse)
def read_file_chunks(kb_id: str, file_id: str, kb: KnowledgeBaseUseCase = Depends(get_kb_usecase)):
    """读取指定文件的全部片段内容"""
    data = kb.read_file_chunks(kb_id, file_id)
    return ApiResponse(ok=True, data=data)


@router.post("/api/kb/{kb_id}/ingest", response_model=ApiResponse)
def ingest_uploaded_file(kb_id: str, payload: IngestRequest, kb: KnowledgeBaseUseCase = Depends(get_kb_usecase)):
    """向量化处理已上传文件（PDF/Excel）"""
    name = (payload.filename or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="filename 不能为空")
    info = kb.ingest_uploaded_file(kb_id, name)
    return ApiResponse(
        ok=True,
        data=kb_file_to_api(info),
    )


@router.delete("/api/files/{file_id}", response_model=ApiResponse)
def delete_file(file_id: str, kb: KnowledgeBaseUseCase = Depends(get_kb_usecase)):
    """删除文件（在所有知识库中查找并删除）"""
    kb.delete_file_global(file_id)
    return ApiResponse(ok=True, data={"ok": True})

