import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ContextEditingMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)

from backend.tools.runtime import build_tools
from backend.prompts.system import get_system_prompt
from backend.kb.knowledge_base import PersistentKnowledgeBaseController
from backend.config.settings import get_settings


def _get_api_key() -> str:
    load_dotenv()
    settings = get_settings()
    return settings.DEEPSEEK_API_KEY


def create_agentic_rag_system(
    kb_id: int,
    *,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
):
    """创建基于单个知识库的 Agent：绑定工具并返回实例"""
    _kb_controller_default = PersistentKnowledgeBaseController()
    tools = build_tools(_kb_controller_default, kb_id)
    SYSTEM_PROMPT = get_system_prompt()
    load_dotenv()
    settings = get_settings()
    key = (llm_api_key or "").strip() or (settings.DEEPSEEK_API_KEY or "").strip() or (os.getenv("DEEPSEEK_API_KEY") or "").strip() or (os.getenv("OPENAI_API_KEY") or "").strip()
    base_url = (llm_base_url or "").strip() or (os.getenv("LLM_BASE_URL") or "").strip() or "https://api.deepseek.com/v1"
    model = (llm_model or "").strip() or (os.getenv("LLM_MODEL") or "").strip() or "deepseek-chat"
    llm = ChatOpenAI(
        temperature=0,
        max_retries=5,
        base_url=base_url,
        model=model,
        api_key=key,
    )
    agent = create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[
            ContextEditingMiddleware(),
            ToolCallLimitMiddleware(thread_limit=20, run_limit=15),
            ToolRetryMiddleware(max_retries=5, backoff_factor=2.0, initial_delay=1.0),
        ],
    )
    return agent



try:
    _DEFAULT_KB_ID = 1
    agent = create_agentic_rag_system(_DEFAULT_KB_ID)
except Exception:
    agent = None
