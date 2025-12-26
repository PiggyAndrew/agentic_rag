from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from backend.api.models import KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate, KBFile, KBFileCreate
from backend.services import kb_service


router = APIRouter()


@router.get("/api/kb", response_model=List[KnowledgeBase])
def list_kbs():
    """列出所有知识库（读取持久化元数据）"""
    metas = kb_service.list_kbs()
    return [KnowledgeBase(**m) for m in metas]


@router.post("/api/kb", response_model=KnowledgeBase)
def create_kb(payload: KnowledgeBaseCreate):
    """创建知识库并持久化元数据"""
    meta = kb_service.create_kb(payload.model_dump())
    return KnowledgeBase(**meta)


@router.put("/api/kb/{kb_id}", response_model=KnowledgeBase)
def update_kb(kb_id: str, payload: KnowledgeBaseUpdate):
    """更新知识库的名称或描述"""
    meta = kb_service.update_kb(kb_id, payload.model_dump())
    return KnowledgeBase(**meta)


@router.delete("/api/kb/{kb_id}")
def delete_kb(kb_id: str):
    """删除指定知识库"""
    kb_service.delete_kb(kb_id)
    return {"ok": True}


@router.get("/api/kb/{kb_id}/files", response_model=List[KBFile])
def list_files(kb_id: str):
    """列出知识库下的文件"""
    files = kb_service.list_files(kb_id)
    return [KBFile(**f) for f in files]


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
    return KBFile(**info)


@router.get("/api/kb/{kb_id}/files/{file_id}/chunks")
def read_file_chunks(kb_id: str, file_id: str):
    """读取指定文件的全部片段内容"""
    try:
        return kb_service.read_file_chunks(kb_id, file_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/kb/{kb_id}/ingest", response_model=KBFile)
def ingest_uploaded_file(kb_id: str, payload: Dict[str, Any]):
    """向量化处理已上传文件（PDF/Excel）"""
    name = (str(payload.get("filename", "")).strip())
    if not name:
        raise HTTPException(status_code=400, detail="filename 不能为空")
    try:
        info = kb_service.ingest_uploaded_file(kb_id, name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"向量化失败: {e}")
    return KBFile(**info)


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

