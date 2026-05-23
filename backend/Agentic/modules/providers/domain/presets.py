from __future__ import annotations

from backend.modules.providers.domain.models import LLMProviderType, LLMPreset, ModelCategory


LLM_PRESETS: dict[LLMProviderType, LLMPreset] = {
    LLMProviderType.ollama: LLMPreset(
        name="Ollama (Embedding/Reranker)",
        provider_type=LLMProviderType.ollama,
        base_url="http://localhost:11434",
        default_model="",
        description="Ollama 本地服务 (Embedding/Reranker)",
        required_params=["base_url", "model_name"],
        supported_categories=[ModelCategory.embedding, ModelCategory.reranker, ModelCategory.vll, ModelCategory.llm],
    ),
    LLMProviderType.dashscope: LLMPreset(
        name="DashScope (通义千问)",
        provider_type=LLMProviderType.dashscope,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="",
        description="阿里云百炼千问 API",
        required_params=["api_key", "model_name"],
        supported_categories=[ModelCategory.llm, ModelCategory.embedding, ModelCategory.vll, ModelCategory.reranker],
    ),
    LLMProviderType.deepseek: LLMPreset(
        name="DeepSeek",
        provider_type=LLMProviderType.deepseek,
        base_url="https://api.deepseek.com/v1",
        default_model="",
        description="DeepSeek 官方 API",
        required_params=["api_key", "model_name"],
        supported_categories=[ModelCategory.llm],
    ),
    LLMProviderType.custom: LLMPreset(
        name="自定义API",
        provider_type=LLMProviderType.custom,
        base_url="",
        default_model="",
        description="自定义OpenAI兼容API",
        required_params=["base_url", "model_name"],
        supported_categories=[ModelCategory.llm, ModelCategory.embedding, ModelCategory.reranker],
    ),
}


def get_preset(provider_type: LLMProviderType) -> LLMPreset | None:
    return LLM_PRESETS.get(provider_type)


def list_presets() -> list[LLMPreset]:
    return list(LLM_PRESETS.values())

