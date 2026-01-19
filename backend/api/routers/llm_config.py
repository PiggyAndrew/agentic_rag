from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.models import ApiResponse
from backend.config.llm_config import (
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMProviderType,
    ModelCategory,
)
from backend.config.llm_config_repository import LLMConfigRepository
from backend.config.llm_presets import list_presets


router = APIRouter()
_repo = LLMConfigRepository()


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
def list_llm_providers(provider_type: str = None, enabled_only: bool = True, category: str = None):
    """获取LLM提供者配置列表"""
    providers = _repo.list_providers(
        provider_type=provider_type, enabled_only=enabled_only, category=category
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
        for p in providers
    ]
    return ApiResponse(ok=True, data=data)


@router.get("/api/llm/providers/{provider_id}", response_model=ApiResponse)
def get_llm_provider(provider_id: int):
    """获取指定LLM提供者配置"""
    provider = _repo.get_by_id(provider_id)
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
def create_llm_provider(provider: dict):
    """创建LLM提供者配置"""
    try:
        create_data = LLMProviderCreate(
            name=provider.get("name"),
            category=ModelCategory(provider.get("category", "llm")),
            provider_type=LLMProviderType(provider.get("providerType")),
            base_url=provider.get("baseUrl"),
            api_key=provider.get("apiKey"),
            model_name=provider.get("modelName"),
            config=provider.get("config"),
            is_default=provider.get("isDefault", False),
            description=provider.get("description"),
        )
        result = _repo.create(create_data)
        return ApiResponse(ok=True, data={"id": result.id})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/api/llm/providers/{provider_id}", response_model=ApiResponse)
def update_llm_provider(provider_id: int, provider: dict):
    """更新LLM提供者配置"""
    try:
        update_data = LLMProviderUpdate(
            name=provider.get("name"),
            category=ModelCategory(provider.get("category")) if provider.get("category") else None,
            base_url=provider.get("baseUrl"),
            api_key=provider.get("apiKey"),
            model_name=provider.get("modelName"),
            config=provider.get("config"),
            is_default=provider.get("isDefault"),
            is_enabled=provider.get("isEnabled"),
            description=provider.get("description"),
        )
        result = _repo.update(provider_id, update_data)
        return ApiResponse(ok=True, data={"id": result.id})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/api/llm/providers/{provider_id}", response_model=ApiResponse)
def delete_llm_provider(provider_id: int):
    """删除LLM提供者配置"""
    _repo.delete(provider_id)
    return ApiResponse(ok=True, data={"ok": True})


@router.post("/api/llm/providers/{provider_id}/set-default", response_model=ApiResponse)
def set_default_llm_provider(provider_id: int):
    """设置为默认LLM配置"""
    try:
        result = _repo.set_default(provider_id)
        return ApiResponse(ok=True, data={"id": result.id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/llm/default/{provider_type}", response_model=ApiResponse)
def get_default_llm_provider(provider_type: str):
    """获取指定类型的默认LLM配置"""
    provider = _repo.get_default(provider_type)
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

@router.get("/api/llm/active", response_model=ApiResponse)
def get_active_llm_config():
    """获取按类别解析的当前激活配置（与 /api/config/active 等价）"""
    resolved = {
        "llm": {},
        "embedding": {},
        "reranker": {},
        "vll": {},
    }

    for category, key in [
        (ModelCategory.llm, "llm"),
        (ModelCategory.embedding, "embedding"),
        (ModelCategory.reranker, "reranker"),
        (ModelCategory.vll, "vll"),
    ]:
        p = _repo.get_default_by_category(category.value)
        if p:
            resolved[key] = {
                "id": p.id,
                "baseUrl": p.base_url,
                "apiKey": p.api_key,
                "model": p.model_name,
                "providerType": p.provider_type,
            }

    return ApiResponse(ok=True, data=resolved)

@router.post("/api/llm/active", response_model=ApiResponse)
def set_active_llm_config(payload: dict):
    """设置按类别的当前激活配置，更新数据库默认项"""
    llm_id = payload.get("llmId")
    embedding_id = payload.get("embeddingId")
    reranker_id = payload.get("rerankerId")
    vll_id = payload.get("vllId")

    for pid in [llm_id, embedding_id, reranker_id, vll_id]:
        if isinstance(pid, int):
            _repo.set_default(pid)

    return get_active_llm_config()


@router.post("/api/llm/test", response_model=ApiResponse)
async def test_llm_connection(config: dict):
    """测试LLM连接"""
    import httpx
    
    base_url = config.get("baseUrl", "").rstrip("/")
    api_key = config.get("apiKey", "")
    model = config.get("modelName", "")
    
    if not base_url or not model:
        raise HTTPException(status_code=400, detail="缺少必要参数: baseUrl, modelName")

    # Construct the chat completions URL
    # If base_url already ends with /v1, don't append it again if not needed, 
    # but standard is usually base_url/chat/completions
    # Common cases: 
    # https://api.openai.com/v1 -> https://api.openai.com/v1/chat/completions
    # https://api.deepseek.com -> https://api.deepseek.com/chat/completions (often requires /v1)
    
    # We will try to be smart or just assume the user provided a valid base_url for the client
    # If user input 'https://api.openai.com/v1', we append '/chat/completions'
    
    url = f"{base_url}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello, are you working?"}],
        "max_tokens": 5
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                return ApiResponse(ok=True, data={"message": "连接成功", "details": response.json()})
            else:
                return ApiResponse(ok=False, error={"code": response.status_code, "message": f"连接失败: {response.text}"})
    except Exception as e:
        return ApiResponse(ok=False, error={"code": 500, "message": f"请求异常: {str(e)}"})
