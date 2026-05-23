from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from backend.shared.ids import parse_kb_id
from backend.modules.kb.domain.ports import (
    KnowledgeBaseControllerPort,
    KnowledgeRepositoryPort,
    SearchPort,
)


@dataclass(frozen=True, slots=True)
class KnowledgeSearchUseCase:
    controller: KnowledgeBaseControllerPort
    repo: KnowledgeRepositoryPort
    search_port: SearchPort

    def search(self, kb_id: int, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识库
        
        Args:
            kb_id: 知识库 ID
            query: 搜索查询
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        if self.search_port is None:
            return []
        kb_int = parse_kb_id(str(kb_id))
        self.controller.ensure_kb(kb_int)
        return self.search_port.search(kb_int, query, top_k)

    def get_documents_meta(self, kb_id: int, document_ids: List[int]) -> List[Dict[str, Any]]:
        """获取文件元数据
        
        Args:
            kb_id: 知识库 ID
            document_ids: 文档 ID 列表
            
        Returns:
            文件元数据列表
        """
        if self.search_port is None:
            return []
        kb_int = parse_kb_id(str(kb_id))
        self.controller.ensure_kb(kb_int)
        return self.search_port.get_documents_meta(kb_int, document_ids)

    def read_document_chunks(self, kb_id: int, chunks: List[Dict[str, int]]) -> List[Dict[str, Any]]:
        """读取文件块
        
        Args:
            kb_id: 知识库 ID
            chunks: 文档块列表，格式为 [{"documentId": int, "chunkIndex": int}, ...]
            
        Returns:
            文件块内容列表
        """
        if self.search_port is None:
            return []
        kb_int = parse_kb_id(str(kb_id))
        self.controller.ensure_kb(kb_int)
        return self.search_port.read_document_chunks(kb_int, chunks)

    def list_documents_paginated(self, kb_id: int, page: int, page_size: int) -> List[Dict[str, Any]]:
        """分页列出文件
        
        Args:
            kb_id: 知识库 ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            文件列表
        """
        if self.search_port is None:
            return []
        kb_int = parse_kb_id(str(kb_id))
        self.controller.ensure_kb(kb_int)
        return self.search_port.list_documents_paginated(kb_int, page, page_size)
