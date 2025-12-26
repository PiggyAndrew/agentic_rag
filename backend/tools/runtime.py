from typing import List, Dict
import json
from langchain_core.tools import tool


def build_tools(kb_controller, kb_id: int):
    """构建绑定单个知识库的工具列表"""

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


def build_tools_multi(kb_controller, kb_ids: List[int]):
    """构建绑定多个知识库的工具列表"""

    @tool("query_knowledge_bases")
    def query_knowledge_bases(query: str) -> str:
        """语义检索多个知识库并返回合并候选片段列表"""
        merged = []
        for kid in kb_ids or []:
            try:
                res = kb_controller.search(kid, query) or []
                for item in res:
                    item = dict(item)
                    item["kb_id"] = int(kid)
                    merged.append(item)
            except Exception:
                continue
        return json.dumps(merged, ensure_ascii=False, indent=2)

    @tool("get_files_meta_multi")
    def get_files_meta_multi(fileIds: List[int]) -> str:
        """根据文件ID数组获取多个知识库中文件的元信息"""
        merged = []
        for kid in kb_ids or []:
            try:
                res = kb_controller.getFilesMeta(kid, fileIds or [])
                for item in res or []:
                    item = dict(item)
                    item["kb_id"] = int(kid)
                    merged.append(item)
            except Exception:
                continue
        return json.dumps(merged, ensure_ascii=False, indent=2)

    @tool("read_file_chunks_multi")
    def read_file_chunks_multi(chunks: List[Dict[str, int]]) -> str:
        """读取多个知识库的片段内容，支持多文件多片段"""
        merged = []
        for kid in kb_ids or []:
            try:
                res = kb_controller.readFileChunks(kid, chunks or [])
                for item in res or []:
                    item = dict(item)
                    item["kb_id"] = int(kid)
                    merged.append(item)
            except Exception:
                continue
        return json.dumps(merged, ensure_ascii=False, indent=2)

    @tool("list_files_multi")
    def list_files_multi(page: int = 0, pageSize: int = 10) -> str:
        """分页列出多个知识库中的文件"""
        merged = []
        for kid in kb_ids or []:
            try:
                res = kb_controller.listFilesPaginated(kid, page, pageSize)
                for item in res or []:
                    item = dict(item)
                    item["kb_id"] = int(kid)
                    merged.append(item)
            except Exception:
                continue
        return json.dumps(merged, ensure_ascii=False, indent=2)

    return [query_knowledge_bases, get_files_meta_multi, read_file_chunks_multi, list_files_multi]

