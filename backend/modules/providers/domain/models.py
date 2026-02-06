from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ModelCategory(str, Enum):
    llm = "llm"
    embedding = "embedding"
    reranker = "reranker"
    vll = "vll"


class LLMProviderType(str, Enum):
    openai = "openai"
    ollama = "ollama"
    dashscope = "dashscope"
    deepseek = "deepseek"
    custom = "custom"


@dataclass
class LLMProvider:
    id: int
    name: str
    provider_type: LLMProviderType
    category: Optional[ModelCategory] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_default: bool = False
    is_enabled: bool = True
    description: Optional[str] = None
    created_at_ms: int = 0
    updated_at_ms: int = 0

    @classmethod
    def now_ms(cls) -> int:
        return int(datetime.now().timestamp() * 1000)


@dataclass
class LLMProviderCreate:
    name: str
    category: ModelCategory
    provider_type: LLMProviderType
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_default: bool = False
    description: Optional[str] = None


@dataclass
class LLMProviderUpdate:
    name: Optional[str] = None
    category: Optional[ModelCategory] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None


@dataclass
class LLMPreset:
    name: str
    provider_type: LLMProviderType
    base_url: str
    default_model: str
    description: str
    required_params: list[str]
    supported_categories: list[str] = None
