from __future__ import annotations

import os
import time

from sqlalchemy import update

from backend.database.sqlite import SqliteSessionManager
from backend.modules.config.infrastructure.boot_config import AppEnv, get_boot_config
from backend.modules.providers.domain.models import LLMProviderCreate, LLMProviderType, ModelCategory, LLMProviderUpdate
from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository
from backend.modules.providers.infrastructure.persistence.models import LLMProviderORM


def seed_providers(*, manager: SqliteSessionManager | None = None) -> None:
    repo = LLMConfigRepository(manager=manager)
    env = get_boot_config().APP_ENV or AppEnv.development
    is_production = env == AppEnv.production

    now_ms = int(time.time() * 1000)
    with repo._manager.session_scope() as session:
        session.execute(
            update(LLMProviderORM)
            .values(provider_type=LLMProviderType.ollama.value, updated_at_ms=now_ms)
            .where(LLMProviderORM.provider_type.in_(["vllm", "vll"]))
        )

    def getenv(name: str, default: str = "") -> str:
        return (os.getenv(name) or default).strip()

    dashscope_base_url = getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    dashscope_api_key = getenv("DASHSCOPE_API_KEY", "sk-7576587807914f3db18eaa1787704614")
    deepseek_api_key = getenv("DEEPSEEK_API_KEY", "sk-7582a5657fc042519669979db6cabd71")

    desired_by_category: dict[ModelCategory, LLMProviderType] = {
        ModelCategory.llm: LLMProviderType.deepseek,
        ModelCategory.embedding: LLMProviderType.dashscope if is_production else LLMProviderType.ollama,
        ModelCategory.reranker: LLMProviderType.dashscope if is_production else LLMProviderType.ollama,
        ModelCategory.vll: LLMProviderType.dashscope,
    }

    def ensure(category: ModelCategory, provider_type: LLMProviderType) -> None:
        existing = repo.list_providers(category=category.value, enabled_only=False)
        picked = next((p for p in existing if p.provider_type == provider_type), None)

        if not picked:
            if provider_type == LLMProviderType.deepseek:
                picked = repo.create(
                    LLMProviderCreate(
                        name="DeepSeek LLM",
                        category=category,
                        provider_type=LLMProviderType.deepseek,
                        base_url="https://api.deepseek.com/v1",
                        api_key=deepseek_api_key,
                        model_name=getenv("LLM_MODEL", "deepseek-chat"),
                        description="Default LLM (DeepSeek)",
                        is_default=True,
                    )
                )
            elif provider_type == LLMProviderType.dashscope:
                if category == ModelCategory.embedding:
                    model_name = getenv("DASHSCOPE_EMBED_MODEL", "text-embedding-v4")
                elif category == ModelCategory.reranker:
                    model_name = getenv("DASHSCOPE_RERANK_MODEL", "qwen3-rerank")
                elif category == ModelCategory.vll:
                    model_name = getenv("VLL_MODEL", "qwen-vl-flash")
                else:
                    model_name = getenv("LLM_MODEL", "qwen-plus")

                picked = repo.create(
                    LLMProviderCreate(
                        name=f"DashScope {category.value}",
                        category=category,
                        provider_type=LLMProviderType.dashscope,
                        base_url=dashscope_base_url,
                        api_key=dashscope_api_key,
                        model_name=model_name,
                        description="Default Provider (DashScope)",
                        is_default=True,
                    )
                )
            else:
                if category == ModelCategory.embedding:
                    base_url = getenv("EMBEDDING_BASE_URL", "http://localhost:11434")
                    model_name = getenv("EMBEDDING_MODEL", "qwen3-embedding")
                elif category == ModelCategory.reranker:
                    base_url = getenv("RERANKER_BASE_URL", "http://localhost:11434")
                    model_name = getenv("RERANKER_MODEL", "dengcao/Qwen3-Reranker-8B:Q3_K_M")
                elif category == ModelCategory.vll:
                    base_url = getenv("VLL_BASE_URL", "http://localhost:11434")
                    model_name = getenv("VLL_MODEL", "qwen3-vl:2b")
                else:
                    base_url = getenv("LLM_BASE_URL", "http://localhost:11434")
                    model_name = getenv("LLM_MODEL", "")

                picked = repo.create(
                    LLMProviderCreate(
                        name=f"Ollama {category.value}",
                        category=category,
                        provider_type=LLMProviderType.ollama,
                        base_url=base_url,
                        api_key="",
                        model_name=model_name,
                        description="Default Provider (Ollama)",
                        is_default=True,
                    )
                )

        if not picked.is_enabled:
            repo.update(picked.id, LLMProviderUpdate(is_enabled=True))
        if not picked.is_default:
            repo.set_default(picked.id)

    for cat, ptype in desired_by_category.items():
        ensure(cat, ptype)
