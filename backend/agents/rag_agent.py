import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ContextEditingMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)

from backend.tools.runtime import build_tools, build_tools_multi
from backend.prompts.system import get_system_prompt
from backend.kb.knowledge_base import PersistentKnowledgeBaseController
from backend.config.settings import get_settings


def _get_api_key() -> str:
    """获取并校验 DEEPSEEK_API_KEY"""
    load_dotenv()
    settings = get_settings()
    return settings.DEEPSEEK_API_KEY


def create_agentic_rag_system(kb_id: int):
    """创建基于单个知识库的 Agent：绑定工具并返回实例"""
    _kb_controller_default = PersistentKnowledgeBaseController()
    tools = build_tools(_kb_controller_default, kb_id)
    SYSTEM_PROMPT = get_system_prompt()
    key = _get_api_key()
    llm = ChatOpenAI(
        temperature=0,
        max_retries=3,
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key=key,
    )
    agent = create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[
            ContextEditingMiddleware(),
            ToolCallLimitMiddleware(thread_limit=20, run_limit=10),
            ToolRetryMiddleware(max_retries=3, backoff_factor=2.0, initial_delay=1.0),
        ],
    )
    return agent


def create_agentic_rag_system_for_kbs(kb_ids: list[int]):
    """创建基于多个知识库的 Agent：绑定多KB工具并返回实例"""
    _kb_controller_default = PersistentKnowledgeBaseController()
    tools = build_tools_multi(_kb_controller_default, [int(k) for k in kb_ids or []])
    SYSTEM_PROMPT = get_system_prompt()
    key = _get_api_key()
    llm = ChatOpenAI(
        temperature=0,
        max_retries=3,
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key=key,
    )
    agent = create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[
            ContextEditingMiddleware(),
            ToolCallLimitMiddleware(thread_limit=20, run_limit=10),
            ToolRetryMiddleware(max_retries=3, backoff_factor=2.0, initial_delay=1.0),
        ],
    )
    return agent


try:
    _DEFAULT_KB_ID = 1
    agent = create_agentic_rag_system(_DEFAULT_KB_ID)
except Exception:
    agent = None
