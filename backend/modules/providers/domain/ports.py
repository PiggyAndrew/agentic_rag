from __future__ import annotations

from typing import Any, Protocol

from backend.modules.providers.domain.models import LLMProvider, LLMProviderCreate, LLMProviderUpdate


class LLMConfigRepositoryPort(Protocol):
    def create(self, provider: LLMProviderCreate) -> LLMProvider: ...

    def get_by_id(self, provider_id: int) -> LLMProvider | None: ...

    def get_default(self, provider_type: str) -> LLMProvider | None: ...

    def get_default_by_category(self, category: str) -> LLMProvider | None: ...

    def list_providers(
        self,
        provider_type: str | None = None,
        enabled_only: bool = True,
        category: str | None = None,
    ) -> list[LLMProvider]: ...

    def update(self, provider_id: int, update_data: LLMProviderUpdate) -> LLMProvider: ...

    def delete(self, provider_id: int) -> None: ...

    def set_default(self, provider_id: int) -> LLMProvider: ...


class ChatCompletionsTesterPort(Protocol):
    async def test_chat_completions(self, *, base_url: str, api_key: str, model: str, timeout_s: float) -> dict[str, Any]: ...
