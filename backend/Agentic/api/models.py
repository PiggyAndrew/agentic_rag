from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Message(BaseModel):
    """聊天消息实体"""
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        s = (v or "").strip()
        if s not in {"user", "assistant", "system"}:
            raise ValueError("role 必须是 user/assistant/system")
        return s


class ChatRequest(BaseModel):
    """聊天请求载荷，支持可选知识库ID"""
    messages: List[Message]
    kbId: Optional[str] = None
    sessionId: Optional[str] = None
    skipSaveUser: Optional[bool] = None

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[Message]) -> List[Message]:
        if not v:
            raise ValueError("messages 不能为空")
        return v


class ChatSession(BaseModel):
    """聊天会话"""
    id: str
    title: str
    createdAt: int
    updatedAt: int


class ChatMessageResponse(BaseModel):
    """聊天消息响应"""
    id: int
    role: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    createdAt: int


class ChatMessageEditRequest(BaseModel):
    content: str


class ChatSessionCreateRequest(BaseModel):
    title: str = "New Chat"


class ChatSessionUpdateRequest(BaseModel):
    title: str


class KnowledgeBase(BaseModel):
    """知识库元数据"""
    id: str
    name: str
    description: Optional[str] = None
    createdAt: int


class KnowledgeBaseCreate(BaseModel):
    """创建知识库的请求体"""
    name: str
    description: Optional[str] = None


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库的请求体"""
    name: Optional[str] = None
    description: Optional[str] = None


class KBDocument(BaseModel):
    """知识库中文档的响应模型"""
    id: str
    kbId: str
    name: str
    type: str
    createdAt: int
    chunkCount: int
    status: str


class KBDocumentCreate(BaseModel):
    """上传文档的请求体（可携带 Base64 内容）"""
    name: str
    type: Optional[str] = "application/octet-stream"
    contentBase64: Optional[str] = None


class IngestRequest(BaseModel):
    """向量化处理请求体"""
    filename: str


class ApiError(BaseModel):
    code: int
    message: str


class ApiResponse(BaseModel):
    ok: bool
    data: Optional[Any] = None
    error: Optional[ApiError] = None


class ConfigItem(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    createdAt: int
    updatedAt: int


class ConfigSetRequest(BaseModel):
    value: Any
    description: Optional[str] = None


class LLMProviderCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    category: str = "llm"
    provider_type: str = Field(alias="providerType")
    base_url: Optional[str] = Field(default=None, alias="baseUrl")
    api_key: Optional[str] = Field(default=None, alias="apiKey")
    model_name: Optional[str] = Field(default=None, alias="modelName")
    config: Optional[Dict[str, Any]] = None
    is_default: bool = Field(default=False, alias="isDefault")
    description: Optional[str] = None


class LLMProviderUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    category: Optional[str] = None
    provider_type: Optional[str] = Field(default=None, alias="providerType")
    base_url: Optional[str] = Field(default=None, alias="baseUrl")
    api_key: Optional[str] = Field(default=None, alias="apiKey")
    model_name: Optional[str] = Field(default=None, alias="modelName")
    config: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = Field(default=None, alias="isDefault")
    is_enabled: Optional[bool] = Field(default=None, alias="isEnabled")
    description: Optional[str] = None


class SetActiveLLMRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    llm_id: Optional[int] = Field(default=None, alias="llmId")
    embedding_id: Optional[int] = Field(default=None, alias="embeddingId")
    reranker_id: Optional[int] = Field(default=None, alias="rerankerId")
    vll_id: Optional[int] = Field(default=None, alias="vllId")


class LLMTestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    base_url: str = Field(alias="baseUrl")
    api_key: str = Field(default="", alias="apiKey")
    model_name: str = Field(alias="modelName")
