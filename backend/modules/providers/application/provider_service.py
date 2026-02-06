from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.modules.providers.domain.models import ModelCategory
from backend.modules.providers.domain.models import LLMProvider, LLMProviderCreate, LLMProviderUpdate
from backend.modules.providers.domain.ports import ChatCompletionsTesterPort, LLMConfigRepositoryPort


@dataclass(frozen=True, slots=True)
class ProviderService:
    repo: LLMConfigRepositoryPort
    tester: ChatCompletionsTesterPort

    def get_default_llm(self) -> LLMProvider | None:
        return self.repo.get_default_by_category(ModelCategory.llm.value)

    def get_default_embedding(self) -> LLMProvider | None:
        return self.repo.get_default_by_category(ModelCategory.embedding.value)

    def get_default_reranker(self) -> LLMProvider | None:
        return self.repo.get_default_by_category(ModelCategory.reranker.value)

    def get_default_vll(self) -> LLMProvider | None:
        return self.repo.get_default_by_category(ModelCategory.vll.value)

    def set_default(self, provider_id: int) -> None:
        self.repo.set_default(provider_id)

    def get_default(self, provider_type: str) -> LLMProvider | None:
        return self.repo.get_default(provider_type)

    def list_providers(
        self,
        *,
        provider_type: str | None = None,
        enabled_only: bool = True,
        category: str | None = None,
    ) -> list[LLMProvider]:
        return self.repo.list_providers(provider_type=provider_type, enabled_only=enabled_only, category=category)

    def get_by_id(self, provider_id: int) -> LLMProvider | None:
        return self.repo.get_by_id(provider_id)

    def create(self, provider: LLMProviderCreate) -> LLMProvider:
        return self.repo.create(provider)

    def update(self, provider_id: int, update_data: LLMProviderUpdate) -> LLMProvider:
        return self.repo.update(provider_id, update_data)

    def delete(self, provider_id: int) -> None:
        self.repo.delete(provider_id)

    async def test_chat_completions(self, *, base_url: str, api_key: str = "", model: str, timeout_s: float = 10.0) -> dict[str, Any]:
        return await self.tester.test_chat_completions(base_url=base_url, api_key=api_key, model=model, timeout_s=timeout_s)
