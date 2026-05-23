from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.models import ApiResponse, ConfigItem
from backend.api.deps import get_config_service, get_provider_service
from backend.modules.providers.domain.models import ModelCategory
from backend.modules.config.application.config_service import ConfigService
from backend.modules.providers.application.provider_service import ProviderService


router = APIRouter()


@router.get("/api/config", response_model=ApiResponse)
def list_configs(config: ConfigService = Depends(get_config_service)):
    rows = config.list_configs()
    data = [
        ConfigItem(
            key=r.key,
            value=r.value,
            description=r.description,
            createdAt=int(r.created_at_ms),
            updatedAt=int(r.updated_at_ms),
        )
        for r in rows
    ]
    return ApiResponse(ok=True, data=data)


@router.get("/api/config/active", response_model=ApiResponse)
def get_active_config(
    config: ConfigService = Depends(get_config_service),
    providers: ProviderService = Depends(get_provider_service),
):
    """获取当前激活的完整配置（按类别默认项解析）"""
    resolved = {
        "llm": {},
        "embedding": {},
        "reranker": {},
        "vll": {},
    }

    def format_provider(p):
        return {
            "id": p.id,
            "baseUrl": p.base_url,
            "apiKey": p.api_key,
            "model": p.model_name,
            "providerType": p.provider_type
        }

    def resolve_by_category(category, target_key):
        if category == ModelCategory.llm:
            p = providers.get_default_llm()
        elif category == ModelCategory.embedding:
            p = providers.get_default_embedding()
        elif category == ModelCategory.reranker:
            p = providers.get_default_reranker()
        elif category == ModelCategory.vll:
            p = providers.get_default_vll()
        else:
            p = None
        if p:
            resolved[target_key] = format_provider(p)

    resolve_by_category(ModelCategory.llm, "llm")
    resolve_by_category(ModelCategory.embedding, "embedding")
    resolve_by_category(ModelCategory.reranker, "reranker")
    resolve_by_category(ModelCategory.vll, "vll")

    api_base_url = config.get("api_base_url", None)
    if api_base_url:
        resolved["apiBaseUrl"] = api_base_url

    return ApiResponse(ok=True, data=resolved)
