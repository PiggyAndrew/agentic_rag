from typing import List
from pydantic import BaseModel, Field


class Citation(BaseModel):
    file_id: int = Field(description="知识库中文件的ID")
    chunk_index: int = Field(description="文件内片段索引")
    filename: str = Field(description="原始文件名")
    content: str = Field(default="", description="引用的具体内容")


class RAGAnswer(BaseModel):
    answer: str = Field(description="最终回答文本")
    citations: List[Citation] = Field(default_factory=list, description="用于回答的证据片段列表")