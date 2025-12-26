from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class Message(BaseModel):
    """聊天消息实体"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """聊天请求载荷，支持可选知识库ID"""
    messages: List[Message]
    kbId: Optional[str] = None


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


class KBFile(BaseModel):
    """知识库中文件的响应模型"""
    id: str
    kbId: str
    name: str
    type: str
    createdAt: int
    chunkCount: int
    status: str


class KBFileCreate(BaseModel):
    """上传文件的请求体（可携带 Base64 内容）"""
    name: str
    type: Optional[str] = "application/octet-stream"
    contentBase64: Optional[str] = None

