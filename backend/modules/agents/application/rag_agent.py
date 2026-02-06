from langchain.agents import create_agent
from langchain.agents.middleware import (
    ContextEditingMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)

from backend.modules.kb.application.usecase import KnowledgeBaseUseCase
from backend.modules.providers.application.provider_service import ProviderService
from backend.shared.prompts.system import get_system_prompt
from backend.tools.runtime import build_tools


def _build_chat_llm(*, providers: ProviderService | None, llm_config: dict | None):
    from langchain_openai import ChatOpenAI
    import os

    key = ""
    base_url = ""
    model = ""

    if llm_config:
        key = llm_config.get("api_key", "")
        base_url = llm_config.get("base_url", "")
        model = llm_config.get("model", "")
    else:
        p = None
        if providers is not None:
            p = providers.get_default_llm() or providers.get_default_vll()
        if p:
            key = p.api_key or ""
            base_url = p.base_url or ""
            model = p.model_name or ""
        else:
            key = (os.getenv("LLM_API_KEY") or "").strip()
            base_url = (os.getenv("LLM_BASE_URL") or "").strip()
            model = (os.getenv("LLM_MODEL") or "").strip()

    return ChatOpenAI(
        temperature=0,
        max_retries=5,
        base_url=base_url,
        model=model,
        api_key=key,
    )


def create_agentic_rag_system(
    kb_id: int,
    *,
    kb: KnowledgeBaseUseCase,
    providers: ProviderService | None = None,
    llm_config: dict | None = None,
):
    tools = build_tools(kb.controller, kb_id)
    system_prompt = get_system_prompt()
    llm = _build_chat_llm(providers=providers, llm_config=llm_config)
    return create_agent(
        llm,
        tools,
        system_prompt=system_prompt,
        middleware=[
            ContextEditingMiddleware(),
            ToolCallLimitMiddleware(thread_limit=20, run_limit=15),
            ToolRetryMiddleware(max_retries=5, backoff_factor=2.0, initial_delay=1.0),
        ],
    )


agent = None
