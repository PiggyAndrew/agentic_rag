from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.models import ApiResponse, ConfigItem, ConfigSetRequest
from backend.config.config_repository import SqlAlchemyConfigRepository
from backend.config.types import SystemConfigCreate


router = APIRouter()
_repo = SqlAlchemyConfigRepository()


@router.get("/api/config", response_model=ApiResponse)
def list_configs():
    rows = _repo.list_configs()
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
def get_active_config():
    """获取当前激活的完整配置（按类别默认项解析）"""
    from backend.config.llm_config_repository import LLMConfigRepository
    from backend.config.llm_config import ModelCategory
    llm_repo = LLMConfigRepository()
    
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
        p = llm_repo.get_default_by_category(category.value)
        if p:
            resolved[target_key] = format_provider(p)

    resolve_by_category(ModelCategory.llm, "llm")
    resolve_by_category(ModelCategory.embedding, "embedding")
    resolve_by_category(ModelCategory.reranker, "reranker")
    resolve_by_category(ModelCategory.vll, "vll")

    api_base_row = _repo.get_config("api_base_url")
    if api_base_row:
        resolved["apiBaseUrl"] = api_base_row.value

    return ApiResponse(ok=True, data=resolved)




