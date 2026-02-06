from __future__ import annotations

from fastapi import Request

from backend.modules.chat.application.usecase import ChatUseCase
from backend.modules.kb.application.usecase import KnowledgeBaseUseCase
from backend.modules.config.application.config_service import ConfigService
from backend.modules.providers.application.provider_service import ProviderService


def get_chat_usecase(request: Request) -> ChatUseCase:
    return request.app.state.chat_usecase


def get_kb_usecase(request: Request) -> KnowledgeBaseUseCase:
    return request.app.state.kb_usecase


def get_config_service(request: Request) -> ConfigService:
    return request.app.state.config_service


def get_provider_service(request: Request) -> ProviderService:
    return request.app.state.provider_service


def get_llm_config_from_headers(request: Request) -> dict | None:
    api_key = (request.headers.get("x-llm-api-key") or "").strip()
    base_url = (request.headers.get("x-llm-base-url") or "").strip()
    model = (request.headers.get("x-llm-model") or "").strip()
    if not api_key and not base_url and not model:
        return None
    return {"api_key": api_key, "base_url": base_url, "model": model}
