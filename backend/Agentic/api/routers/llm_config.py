from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api.models import ApiResponse, LLMProviderCreateRequest, LLMProviderUpdateRequest, LLMTestRequest, SetActiveLLMRequest
from backend.modules.providers.domain.models import (
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMProviderType,
    ModelCategory,
)
from backend.modules.providers.domain.presets import list_presets
from backend.modules.providers.application.provider_service import ProviderService
from backend.api.deps import get_provider_service


router = APIRouter()


@router.get("/api/llm/presets", response_model=ApiResponse)
def list_llm_presets():
    """获取LLM配置预设列表"""
    presets = list_presets()
    data = [
        {
            "name": p.name,
            "providerType": p.provider_type,
            "baseUrl": p.base_url,
            "defaultModel": p.default_model,
            "description": p.description,
            "requiredParams": p.required_params,
            "supportedCategories": p.supported_categories or [],
        }
        for p in presets
    ]
    return ApiResponse(ok=True, data=data)


@router.get("/api/llm/providers", response_model=ApiResponse)
def list_llm_providers(
    provider_type: str = None,
    enabled_only: bool = True,
    category: str = None,
    providers: ProviderService = Depends(get_provider_service),
):
    """获取LLM提供者配置列表"""
    items = providers.list_providers(
        provider_type=provider_type,
        enabled_only=enabled_only,
        category=category,
    )
    data = [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "providerType": p.provider_type,
            "baseUrl": p.base_url,
            "apiKey": "***" if p.api_key else None,
            "modelName": p.model_name,
            "config": p.config,
            "isDefault": p.is_default,
            "isEnabled": p.is_enabled,
            "description": p.description,
            "createdAt": p.created_at_ms,
            "updatedAt": p.updated_at_ms,
        }
        for p in items
    ]
    return ApiResponse(ok=True, data=data)


@router.get("/api/llm/providers/{provider_id}", response_model=ApiResponse)
def get_llm_provider(
    provider_id: int,
    providers: ProviderService = Depends(get_provider_service),
):
    """获取指定LLM提供者配置"""
    provider = providers.get_by_id(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="LLM配置不存在")

    return ApiResponse(
        ok=True,
        data={
            "id": provider.id,
            "name": provider.name,
            "providerType": provider.provider_type,
            "baseUrl": provider.base_url,
            "apiKey": "***" if provider.api_key else None,
            "modelName": provider.model_name,
            "config": provider.config,
            "isDefault": provider.is_default,
            "isEnabled": provider.is_enabled,
            "description": provider.description,
            "createdAt": provider.created_at_ms,
            "updatedAt": provider.updated_at_ms,
        },
    )


@router.post("/api/llm/providers", response_model=ApiResponse)
def create_llm_provider(
    payload: LLMProviderCreateRequest,
    providers: ProviderService = Depends(get_provider_service),
):
    """创建LLM提供者配置"""
    try:
        create_data = LLMProviderCreate(
            name=payload.name,
            category=ModelCategory(payload.category),
            provider_type=LLMProviderType(payload.provider_type),
            base_url=payload.base_url,
            api_key=payload.api_key,
            model_name=payload.model_name,
            config=payload.config,
            is_default=payload.is_default,
            description=payload.description,
        )
        result = providers.create(create_data)
        return ApiResponse(ok=True, data={"id": result.id})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/api/llm/providers/{provider_id}", response_model=ApiResponse)
def update_llm_provider(
    provider_id: int,
    payload: LLMProviderUpdateRequest,
    providers: ProviderService = Depends(get_provider_service),
):
    """更新LLM提供者配置"""
    try:
        update_data = LLMProviderUpdate(
            name=payload.name,
            category=ModelCategory(payload.category) if payload.category else None,
            base_url=payload.base_url,
            api_key=payload.api_key,
            model_name=payload.model_name,
            config=payload.config,
            is_default=payload.is_default,
            is_enabled=payload.is_enabled,
            description=payload.description,
        )
        result = providers.update(provider_id, update_data)
        return ApiResponse(ok=True, data={"id": result.id})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/api/llm/providers/{provider_id}", response_model=ApiResponse)
def delete_llm_provider(
    provider_id: int,
    providers: ProviderService = Depends(get_provider_service),
):
    """删除LLM提供者配置"""
    providers.delete(provider_id)
    return ApiResponse(ok=True, data={"ok": True})


@router.post("/api/llm/providers/{provider_id}/set-default", response_model=ApiResponse)
def set_default_llm_provider(
    provider_id: int,
    providers: ProviderService = Depends(get_provider_service),
):
    """设置为默认LLM配置"""
    try:
        providers.set_default(provider_id)
        return ApiResponse(ok=True, data={"id": provider_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/llm/default/{provider_type}", response_model=ApiResponse)
def get_default_llm_provider(
    provider_type: str,
    providers: ProviderService = Depends(get_provider_service),
):
    """获取指定类型的默认LLM配置"""
    provider = providers.get_default(provider_type)
    if not provider:
        raise HTTPException(
            status_code=404, detail=f"未找到 {provider_type} 的默认配置"
        )

    return ApiResponse(
        ok=True,
        data={
            "id": provider.id,
            "name": provider.name,
            "providerType": provider.provider_type,
            "baseUrl": provider.base_url,
            "apiKey": "***" if provider.api_key else None,
            "modelName": provider.model_name,
            "config": provider.config,
            "isDefault": provider.is_default,
            "isEnabled": provider.is_enabled,
            "description": provider.description,
            "createdAt": provider.created_at_ms,
            "updatedAt": provider.updated_at_ms,
        },
    )

def _get_active_llm_config(providers: ProviderService) -> dict:
    """获取按类别解析的当前激活配置（与 /api/config/active 等价）"""
    resolved = {
        "llm": {},
        "embedding": {},
        "reranker": {},
        "vll": {},
    }

    def fill(key: str, p):
        if not p:
            return
        resolved[key] = {
            "id": p.id,
            "baseUrl": p.base_url,
            "apiKey": p.api_key,
            "model": p.model_name,
            "providerType": p.provider_type,
        }

    fill("llm", providers.get_default_llm())
    fill("embedding", providers.get_default_embedding())
    fill("reranker", providers.get_default_reranker())
    fill("vll", providers.get_default_vll())

    return resolved


@router.get("/api/llm/active", response_model=ApiResponse)
def get_active_llm_config(providers: ProviderService = Depends(get_provider_service)):
    resolved = _get_active_llm_config(providers)

    return ApiResponse(ok=True, data=resolved)

@router.post("/api/llm/active", response_model=ApiResponse)
def set_active_llm_config(
    payload: SetActiveLLMRequest,
    providers: ProviderService = Depends(get_provider_service),
):
    """设置按类别的当前激活配置，更新数据库默认项"""
    for pid in [payload.llm_id, payload.embedding_id, payload.reranker_id, payload.vll_id]:
        if pid is not None:
            providers.set_default(int(pid))

    return ApiResponse(ok=True, data=_get_active_llm_config(providers))


@router.post("/api/llm/test", response_model=ApiResponse)
async def test_llm_connection(payload: LLMTestRequest, providers: ProviderService = Depends(get_provider_service)):
    """测试LLM连接"""
    base_url = (payload.base_url or "").rstrip("/")
    api_key = payload.api_key or ""
    model = payload.model_name or ""
    
    if not base_url or not model:
        raise HTTPException(status_code=400, detail="缺少必要参数: baseUrl, modelName")

    try:
        result = await providers.test_chat_completions(base_url=base_url, api_key=api_key, model=model)
        if int(result["status_code"]) == 200:
            return ApiResponse(ok=True, data={"message": "连接成功", "details": result["details"]})
        return ApiResponse(ok=False, error={"code": int(result["status_code"]), "message": f"连接失败: {result['details']}"})
    except Exception as e:
        return ApiResponse(ok=False, error={"code": 500, "message": f"请求异常: {str(e)}"})
