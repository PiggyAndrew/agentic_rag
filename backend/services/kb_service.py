import os
from typing import  List, Optional

from backend.kb.knowledge_base import PersistentKnowledgeBaseController
from backend.kb.knowledge_service import get_default_knowledge_service
from backend.kb.types import KnowledgeBasePatch, KnowledgeBaseCreate
from backend.kb.types.legacy import FileChunk
from backend.kb.types.file import KnowledgeFile as KBFileMeta
from backend.kb.types.kb import KnowledgeBase as KBMeta


KB_CTRL = PersistentKnowledgeBaseController(base_dir=os.path.join("data", "kb"))
_KB_SVC = None


def _svc():
    global _KB_SVC
    if _KB_SVC is None:
        _KB_SVC = get_default_knowledge_service(controller=KB_CTRL)
    return _KB_SVC


def list_kbs() -> List[KBMeta]:
    """列出所有知识库的元数据集合（领域对象）"""
    return _svc().list_kbs()


def create_kb(payload: KnowledgeBaseCreate) -> KBMeta:
    """创建新的知识库并写入元数据（接收领域补丁对象）"""
    return _svc().create_kb(payload)


def update_kb(kb_id: str, payload: KnowledgeBasePatch) -> KBMeta:
    """更新指定知识库的元数据（领域补丁对象）"""
    return _svc().update_kb(kb_id, payload)


def delete_kb(kb_id: str) -> None:
    """删除指定知识库及其内容"""
    _svc().delete_kb(kb_id)


def list_files(kb_id: str) -> List[KBFileMeta]:
    """列出指定知识库下的文件信息（领域对象）"""
    return _svc().list_files(kb_id)


def save_upload(kb_id: str, name: str, content_b64: Optional[str]) -> KBFileMeta:
    """保存上传文件（可选Base64内容）并入库为未向量化，返回领域对象"""
    return _svc().save_upload(kb_id, name, content_b64)


def read_file_chunks(kb_id: str, file_id: str) -> List[FileChunk]:
    """读取指定文件的全部片段内容（领域片段对象）"""
    return _svc().read_file_chunks(kb_id, file_id)


def ingest_uploaded_file(kb_id: str, filename: str) -> KBFileMeta:
    """向量化处理上传到uploads目录的PDF或Excel文件，返回领域对象"""
    return _svc().ingest_uploaded_file(kb_id, filename)


def delete_file_global(file_id: str) -> None:
    """在所有知识库中查找并删除指定文件ID"""
    _svc().delete_file_global(file_id)
