from typing import List, Dict
import json
from langchain_core.tools import tool
from kb.ingestion import ingest_pdf


def build_tools(kb_controller, kb_id: int):
    """构建工具列表：绑定知识库控制器与ID并返回可调用的工具集合"""

    @tool("query_knowledge_base")
    def query_knowledge_base(query: str) -> str:
        """语义检索当前知识库并返回候选片段列表"""
        results = kb_controller.search(kb_id, query)
        return json.dumps(results, ensure_ascii=False, indent=2)

    @tool("get_files_meta")
    def get_files_meta(fileIds: List[int]) -> str:
        """根据文件ID数组获取知识库中文件的元信息"""
        if not fileIds:
            return "请提供文件ID数组"
        results = kb_controller.getFilesMeta(kb_id, fileIds)
        return json.dumps(results, ensure_ascii=False, indent=2)

    @tool("read_file_chunks")
    def read_file_chunks(chunks: List[Dict[str, int]]) -> str:
        """读取指定文件的片段内容，支持多文件多片段"""
        if not chunks:
            return "请提供要读取的chunk信息数组"
        results = kb_controller.readFileChunks(kb_id, chunks)
        return json.dumps(results, ensure_ascii=False, indent=2)

    @tool("list_files")
    def list_files(page: int = 0, pageSize: int = 10) -> str:
        """分页列出知识库中的文件，返回文件ID、文件名与片段数量"""
        results = kb_controller.listFilesPaginated(kb_id, page, pageSize)
        return json.dumps(results, ensure_ascii=False, indent=2)

    return [query_knowledge_base, get_files_meta, read_file_chunks, list_files]

