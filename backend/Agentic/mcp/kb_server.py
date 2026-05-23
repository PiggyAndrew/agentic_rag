from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from backend.database.sqlite import build_sqlite_manager, init_sqlite_database
from backend.entrypoints.composition.kb import build_kb_usecase, default_kb_base_dir
from backend.modules.chat.infrastructure.persistence.models import ChatBase
from backend.modules.config.infrastructure.persistence.models import ConfigBase
from backend.tools.runtime import (
    get_documents_meta_payload,
    list_documents_payload,
    query_knowledge_base_payload,
    read_document_chunks_payload,
)
from backend.modules.kb.infrastructure.persistence.models import Base as KnowledgeBase
from backend.modules.providers.infrastructure.persistence.models import ProvidersBase
from backend.modules.providers.infrastructure.seed import seed_providers

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _resolve_kb_id() -> int:
    raw_value = (os.getenv("AGENTIC_RAG_MCP_KB_ID") or "").strip()
    if not raw_value:
        raise ValueError("缺少环境变量 AGENTIC_RAG_MCP_KB_ID")
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("环境变量 AGENTIC_RAG_MCP_KB_ID 必须是整数") from exc


def _build_kb_usecase():
    manager = build_sqlite_manager()
    init_sqlite_database(
        manager=manager,
        metadatas=[
            KnowledgeBase.metadata,
            ConfigBase.metadata,
            ProvidersBase.metadata,
            ChatBase.metadata,
        ],
    )
    seed_providers(manager=manager)
    return build_kb_usecase(manager=manager, base_dir=default_kb_base_dir())


load_dotenv(dotenv_path=ENV_FILE)

KB_ID = _resolve_kb_id()
KB_USECASE = _build_kb_usecase()

mcp = FastMCP("agentic_rag_kb_mcp", json_response=True)


@mcp.tool(
    name="query_knowledge_base",
    description="语义检索当前知识库，返回候选片段列表，结果包含文档 ID、chunk 索引和相关性得分。",
)
def query_knowledge_base(query: str) -> List[Dict]:
    return query_knowledge_base_payload(KB_USECASE, KB_ID, query)


@mcp.tool(
    name="get_documents_meta",
    description="根据文档 ID 列表获取文档元数据，例如文件名、块数量和状态。",
)
def get_documents_meta(documentIds: List[int]) -> List[Dict]:
    if not documentIds:
        raise ValueError("请提供文档 ID 数组")
    return get_documents_meta_payload(KB_USECASE, KB_ID, documentIds)


@mcp.tool(
    name="read_document_chunks",
    description="读取指定文档块内容，输入格式为 [{\"documentId\": int, \"chunkIndex\": int}]。",
)
def read_document_chunks(chunks: List[Dict[str, int]]) -> List[Dict]:
    if not chunks:
        raise ValueError("请提供要读取的 chunk 信息数组")
    return read_document_chunks_payload(KB_USECASE, KB_ID, chunks)


@mcp.tool(
    name="list_documents",
    description="分页列出当前知识库中状态为 done 的文档，返回文档 ID、文件名和 chunk 数量。",
)
def list_documents(page: int = 0, pageSize: int = 10) -> List[Dict]:
    return list_documents_payload(KB_USECASE, KB_ID, page, pageSize)


if __name__ == "__main__":
    mcp.run()
