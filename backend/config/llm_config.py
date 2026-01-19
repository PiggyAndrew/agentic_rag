from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum
from datetime import datetime

class ModelCategory(str, Enum):
    """模型类别：用于区分用途"""
    llm = "llm"
    embedding = "embedding"
    reranker = "reranker"
    vll = "vll"


class LLMProviderType(str, Enum):
    """LLM提供者类型枚举"""

    openai = "openai"
    ollama = "ollama"
    vllm = "vllm"
    dashscope = "dashscope"
    deepseek = "deepseek"
    custom = "custom"


@dataclass
class LLMProvider:
    """LLM提供者配置"""

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
        """获取当前时间戳（毫秒）"""
        return int(datetime.now().timestamp() * 1000)


@dataclass
class LLMProviderCreate:
    """创建LLM提供者请求"""

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
    """更新LLM提供者请求"""

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
    """LLM配置预设"""

    name: str
    provider_type: LLMProviderType
    base_url: str
    default_model: str
    description: str
    required_params: list[str]
    supported_categories: list[str] = None
