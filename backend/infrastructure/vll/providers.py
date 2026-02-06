import logging
from typing import Any, List

from backend.modules.providers.domain.models import LLMProviderType, ModelCategory
from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository
from backend.modules.agents.infrastructure.vision_ollama_qwen3_vl import OllamaVisionAgent


class NoopVisionAgent:
    def invoke(self, messages: List[Any]) -> dict:
        return {"error": "vll not configured"}

    def analyze_image(self, images: List[dict]) -> List[dict]:
        return []


def get_configured_vision_agent():
    repo = LLMConfigRepository()
    provider = repo.get_default_by_category(ModelCategory.vll.value)
    if not provider:
        logging.getLogger(__name__).warning("未找到激活的视觉模型配置，使用 NoopVisionAgent")
        return NoopVisionAgent()
    logging.getLogger(__name__).info("Initializing configured vll: %s (type=%s)", provider.name, provider.provider_type)
    if provider.provider_type == LLMProviderType.ollama:
        return OllamaVisionAgent(base_url=provider.base_url, model_name=provider.model_name)
    if provider.provider_type == LLMProviderType.dashscope:
        from backend.modules.agents.infrastructure.vision_dashscope_qwen3_vl import AliyunDashScopeVisionAgent
        return AliyunDashScopeVisionAgent(
            base_url=provider.base_url,
            api_key=provider.api_key,
            model_name=provider.model_name,
        )
    logging.getLogger(__name__).warning("不支持的视觉模型类型: %s，使用 NoopVisionAgent", provider.provider_type)
    return NoopVisionAgent()
