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
from backend.config.llm_config_repository import LLMConfigRepository
from backend.config.llm_config import ModelCategory


def create_agentic_rag_system(
    kb_id: int,
    llm_config: dict = None
):
    """创建基于单个知识库的 Agent：绑定工具并返回实例"""
    _kb_controller_default = PersistentKnowledgeBaseController()
    tools = build_tools(_kb_controller_default, kb_id)
    SYSTEM_PROMPT = get_system_prompt()
    settings = get_settings()
    
    key = ""
    base_url = ""
    model = ""
    
    if llm_config:
        key = llm_config.get("api_key", "")
        base_url = llm_config.get("base_url", "")
        model = llm_config.get("model", "")
    else:
        repo = LLMConfigRepository()
        p = repo.get_default_by_category(ModelCategory.llm.value) or repo.get_default_by_category(ModelCategory.vll.value)
        if p:
            key = p.api_key or ""
            base_url = p.base_url or ""
            model = p.model_name or ""
        else:
            key = settings.get_config("llm.apiKey", "")
            base_url = settings.get_config("llm.baseUrl", "")
            model = settings.get_config("llm.model", "")
        
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
