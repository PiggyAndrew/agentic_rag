from typing import Any, Dict, List
import json
from langchain_core.tools import tool


def serialize_tool_output(payload: Any) -> str:
    """统一序列化工具输出，保持 LangChain 与 MCP 返回格式一致。"""
    return json.dumps(payload, ensure_ascii=False, indent=2)


def query_knowledge_base_payload(kb_usecase, kb_id: int, query: str) -> List[Dict[str, Any]]:
    """语义检索当前知识库并返回候选片段列表。"""
    return kb_usecase.search(kb_id, query)


def get_documents_meta_payload(
    kb_usecase, kb_id: int, document_ids: List[int]
) -> List[Dict[str, Any]]:
    """获取指定文档的元数据信息。"""
    return kb_usecase.get_documents_meta(kb_id, document_ids)


def read_document_chunks_payload(
    kb_usecase, kb_id: int, chunks: List[Dict[str, int]]
) -> List[Dict[str, Any]]:
    """读取指定文档块内容。"""
    return kb_usecase.read_document_chunks_dict(kb_id, chunks)


def list_documents_payload(
    kb_usecase, kb_id: int, page: int = 0, page_size: int = 10
) -> List[Dict[str, Any]]:
    """分页列出知识库中状态为 done 的文档。"""
    results = kb_usecase.list_documents_paginated(kb_id, page, page_size)
    filtered = [f for f in results if f.get("status") == "done"]
    return [
        {
            "id": f.get("id"),
            "filename": f.get("filename"),
            "chunkCount": f.get("chunk_count", 0),
        }
        for f in filtered
    ]

def build_tools(kb_usecase, kb_id: int, kb_name: str = "知识库"):
    """构建绑定单个知识库的工具列表

    Args:
        kb_usecase: 知识库应用层用例
        kb_id: 知识库 ID
        kb_name: 知识库名称，用于工具描述

    Returns:
        LangChain 工具列表
    """

    @tool("query_knowledge_base")
    def query_knowledge_base(query: str) -> str:
        """语义检索当前知识库并返回候选片段列表

        Args:
            query: 用于搜索知识库的查询字符串

        Returns:
            包含匹配的文档片段列表的 JSON 字符串，每个结果包含文档 ID、块索引和相关性得分
        """
        results = query_knowledge_base_payload(kb_usecase, kb_id, query)
        return serialize_tool_output(results)

    @tool("get_documents_meta")
    def get_documents_meta(documentIds: List[int]) -> str:
        """获取知识库中指定文档的元数据信息

        使用此工具可以获取从搜索返回的文档的详细信息，例如文件名和块总数。

        Args:
            documentIds: 要获取元数据的文档 ID 数组

        Returns:
            包含文档元数据的 JSON 字符串，包括文件名、块数量、状态等信息
        """
        if not documentIds:
            return "请提供文档 ID 数组"
        results = get_documents_meta_payload(kb_usecase, kb_id, documentIds)
        return serialize_tool_output(results)
    
    @tool("read_document_chunks")
    def read_document_chunks(chunks: List[Dict[str, int]]) -> str:
        """读取知识库中指定文档的文本块内容

        使用此工具获取文档的文本内容。输入应包含文档 ID 和块索引的数组。

        Args:
            chunks: 要读取的文档和块索引对数组，格式为 [{"documentId": int, "chunkIndex": int}, ...]
                 chunkIndex 从 0 开始

        Returns:
            包含请求的文档块内容的 JSON 字符串，每个块包含文本内容和元数据
        """
        if not chunks:
            return "请提供要读取的 chunk 信息数组"
        results = read_document_chunks_payload(kb_usecase, kb_id, chunks)
        return serialize_tool_output(results)
    
    @tool("list_documents")
    def list_documents(page: int = 0, pageSize: int = 10) -> str:
        """分页列出知识库中的所有文档

        返回文档 ID、文件名和每个文档的块数量。仅返回状态为完成（done）的文档。

        Args:
            page: 页码，从 0 开始
            pageSize: 每页显示的文件数量

        Returns:
            包含文档列表的 JSON 字符串，每个文档包含 ID、文件名和块数量
        """
        results = list_documents_payload(kb_usecase, kb_id, page, pageSize)
        return serialize_tool_output(results)
    
    return [query_knowledge_base, get_documents_meta, read_document_chunks, list_documents]
