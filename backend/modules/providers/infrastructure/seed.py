from __future__ import annotations

import os
import time

from sqlalchemy import update

from backend.database.sqlite import SqliteSessionManager
from backend.modules.config.infrastructure.boot_config import AppEnv, get_boot_config
from backend.modules.providers.domain.models import LLMProviderCreate, LLMProviderType, ModelCategory
from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository
from backend.modules.providers.infrastructure.persistence.models import LLMProviderORM


def seed_providers(*, manager: SqliteSessionManager | None = None) -> None:
    repo = LLMConfigRepository(manager=manager)
    providers = repo.list_providers(enabled_only=False)
    if providers:
        now_ms = int(time.time() * 1000)
        with repo._manager.session_scope() as session:
            session.execute(
                update(LLMProviderORM)
                .values(provider_type=LLMProviderType.ollama.value, updated_at_ms=now_ms)
                .where(LLMProviderORM.provider_type.in_(["vllm", "vll"]))
            )
        return

    env = get_boot_config().APP_ENV or AppEnv.development

    llm_base_url = (os.getenv("LLM_BASE_URL") or "").strip()
    llm_model = (os.getenv("LLM_MODEL") or "").strip()
    llm_api_key = (os.getenv("LLM_API_KEY") or "").strip()
    deepseek_api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()

    embedding_base_url = (os.getenv("EMBEDDING_BASE_URL") or "").strip() or "http://localhost:11434"
    embedding_model = (os.getenv("EMBEDDING_MODEL") or "").strip() or "qwen3-embedding"
    embedding_api_key = (os.getenv("EMBEDDING_API_KEY") or "").strip()

    reranker_base_url = (os.getenv("RERANKER_BASE_URL") or "").strip() or "http://localhost:11434"
    reranker_model = (os.getenv("RERANKER_MODEL") or "").strip() or "dengcao/Qwen3-Reranker-8B:Q3_K_M"
    reranker_api_key = (os.getenv("RERANKER_API_KEY") or "").strip()

    vll_base_url = (os.getenv("VLL_BASE_URL") or "").strip() or "http://localhost:11434"
    vll_model = (os.getenv("VLL_MODEL") or "").strip() or "qwen3-vl:2b"
    vll_api_key = (os.getenv("VLL_API_KEY") or "").strip()

    embedding_backend = (os.getenv("EMBEDDING_BACKEND") or "").strip().lower()
    if not embedding_backend:
        embedding_backend = "dashscope" if env == AppEnv.production else "ollama"

    if embedding_backend == "dashscope":
        repo.create(
            LLMProviderCreate(
                name="DashScope Embedding",
                category=ModelCategory.embedding,
                provider_type=LLMProviderType.dashscope,
                base_url=embedding_base_url,
                api_key=embedding_api_key,
                model_name=embedding_model,
                description="DashScope Embedding",
                is_default=True,
            )
        )
    else:
        repo.create(
            LLMProviderCreate(
                name="Ollama Embedding",
                category=ModelCategory.embedding,
                provider_type=LLMProviderType.ollama,
                base_url=embedding_base_url,
                api_key=embedding_api_key,
                model_name=embedding_model,
                description="Default Ollama Embedding",
                is_default=True,
            )
        )

    repo.create(
        LLMProviderCreate(
            name="Reranker",
            category=ModelCategory.reranker,
            provider_type=LLMProviderType.ollama,
            base_url=reranker_base_url,
            api_key=reranker_api_key,
            model_name=reranker_model,
            description="Default Reranker",
            is_default=True,
        )
    )

    repo.create(
        LLMProviderCreate(
            name="Ollama VLL",
            category=ModelCategory.vll,
            provider_type=LLMProviderType.ollama,
            base_url=vll_base_url,
            api_key=vll_api_key,
            model_name=vll_model,
            description="Default VLL (Ollama)",
            is_default=True,
        )
    )

    if deepseek_api_key:
        repo.create(
            LLMProviderCreate(
                name="DeepSeek Chat",
                category=ModelCategory.llm,
                provider_type=LLMProviderType.deepseek,
                base_url="https://api.deepseek.com/v1",
                api_key=deepseek_api_key,
                model_name=llm_model or "deepseek-chat",
                description="DeepSeek Official API",
                is_default=True,
            )
        )
    elif llm_base_url and llm_api_key:
        provider_type = LLMProviderType.openai if "openai" in llm_base_url.lower() else LLMProviderType.custom
        repo.create(
            LLMProviderCreate(
                name="LLM",
                category=ModelCategory.llm,
                provider_type=provider_type,
                base_url=llm_base_url,
                api_key=llm_api_key,
                model_name=llm_model or None,
                description="LLM from env",
                is_default=True,
            )
        )
    else:
        repo.create(
            LLMProviderCreate(
                name="LLM (Custom)",
                category=ModelCategory.llm,
                provider_type=LLMProviderType.custom,
                base_url=vll_base_url,
                api_key=vll_api_key,
                model_name=vll_model,
                description=f"Fallback LLM for {env.value}",
                is_default=True,
            )
        )
