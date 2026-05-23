import json
import os
import sys
from typing import Any

from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.api.main import create_app
from backend.database.sqlite import build_sqlite_manager, init_sqlite_database
from backend.entrypoints.composition.kb import build_kb_usecase, default_kb_base_dir
from backend.modules.chat.infrastructure.persistence.models import ChatBase
from backend.modules.config.infrastructure.persistence.models import ConfigBase
from backend.modules.kb.infrastructure.persistence.models import Base as KnowledgeBase
from backend.modules.providers.infrastructure.persistence.models import ProvidersBase
from backend.modules.providers.infrastructure.seed import seed_providers
from backend.tools.runtime import build_tools, list_documents_payload, query_knowledge_base_payload


def _resolve_kb_id() -> int:
    return int(os.getenv("KB_ID") or os.getenv("AGENTIC_RAG_MCP_KB_ID") or "1")


def _resolve_query() -> str:
    return (os.getenv("KB_QUERY") or "s1").strip()


def _print_json(title: str, payload: Any) -> None:
    print("=" * 80)
    print(title)
    print("=" * 80)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print()


def _build_mcp_style_kb_usecase():
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


def _run_search(kb_usecase, kb_id: int, query: str) -> None:
    documents = list_documents_payload(kb_usecase, kb_id, 0, 10)
    _print_json("Documents visible from runtime", documents)

    results = query_knowledge_base_payload(kb_usecase, kb_id, query)
    _print_json("query_knowledge_base_payload results", results)

    query_tool = next(tool for tool in build_tools(kb_usecase, kb_id) if tool.name == "query_knowledge_base")
    tool_results = json.loads(query_tool.func(query))
    _print_json("build_tools(query_knowledge_base) results", tool_results)


def run_debug() -> None:
    kb_id = _resolve_kb_id()
    query = _resolve_query()
    base_dir = default_kb_base_dir()

    print(f"kb_id={kb_id}")
    print(f"query={query}")
    print(f"base_dir={base_dir}")
    print()

    with TestClient(create_app()) as client:
        _run_search(client.app.state.kb_usecase, kb_id, query)

    _run_search(_build_mcp_style_kb_usecase(), kb_id, query)


if __name__ == "__main__":
    run_debug()
