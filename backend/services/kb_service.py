import os
from typing import Dict, List, Optional,Any

from backend.kb.knowledge_base import PersistentKnowledgeBaseController
from backend.kb.knowledge_service import get_default_knowledge_service


KB_CTRL = PersistentKnowledgeBaseController(base_dir=os.path.join("data", "kb"))
_KB_SVC = None


def _svc():
    global _KB_SVC
    if _KB_SVC is None:
        _KB_SVC = get_default_knowledge_service(controller=KB_CTRL)
    return _KB_SVC


def list_kbs() -> List[Dict[str, Any]]:
    """列出所有知识库的元数据集合"""
    return _svc().list_kbs()


def create_kb(payload: Dict[str, Any]) -> Dict[str, Any]:
    """创建新的知识库并写入元数据"""
    return _svc().create_kb(payload)


def update_kb(kb_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """更新指定知识库的元数据"""
    return _svc().update_kb(kb_id, payload)


def delete_kb(kb_id: str) -> None:
    """删除指定知识库及其内容"""
    _svc().delete_kb(kb_id)


def list_files(kb_id: str) -> List[Dict[str, Any]]:
    """列出指定知识库下的文件信息"""
    return _svc().list_files(kb_id)


def save_upload(kb_id: str, name: str, content_b64: Optional[str]) -> Dict[str, Any]:
    """保存上传文件（可选Base64内容）并入库为未向量化"""
    return _svc().save_upload(kb_id, name, content_b64)


def read_file_chunks(kb_id: str, file_id: str) -> List[Dict[str, Any]]:
    """读取指定文件的全部片段内容"""
    return _svc().read_file_chunks(kb_id, file_id)


def ingest_uploaded_file(kb_id: str, filename: str) -> Dict[str, Any]:
    """向量化处理上传到uploads目录的PDF或Excel文件"""
    return _svc().ingest_uploaded_file(kb_id, filename)


def delete_file_global(file_id: str) -> None:
    """在所有知识库中查找并删除指定文件ID"""
    _svc().delete_file_global(file_id)
