from typing import List, Dict
import json
from langchain_core.tools import tool


def build_tools(kb_controller, kb_id: int, kb_name: str = "知识库"):
    """构建绑定单个知识库的工具列表

    Args:
        kb_controller: 知识库控制器实例
        kb_id: 知识库 ID
        kb_name: 知识库名称，用于工具描述

    Returns:
        LangChain 工具列表
    """

    @tool("query_knowledge_base")
    def query_knowledge_base(query: str) -> str:
        """语义检索当前知识库并返回候选片段列表

        Args:
            query: 用于搜索知识库的查询字符串

        Returns:
            包含匹配的文档片段列表的 JSON 字符串，每个结果包含文件 ID、块索引和相关性得分
        """
        results = kb_controller.search(kb_id, query)
        return json.dumps(results, ensure_ascii=False, indent=2)

    @tool("get_files_meta")
    def get_files_meta(fileIds: List[int]) -> str:
        """获取知识库中指定文件的元数据信息

        使用此工具可以获取从搜索返回的文件的详细信息，例如文件名、大小和块总数。

        Args:
            fileIds: 要获取元数据的文件 ID 数组

        Returns:
            包含文件元数据的 JSON 字符串，包括文件名、块数量、状态等信息
        """
        if not fileIds:
            return "请提供文件 ID 数组"
        results = kb_controller.getFilesMeta(kb_id, fileIds)
        return json.dumps(results, ensure_ascii=False, indent=2)

    @tool("read_file_chunks")
    def read_file_chunks(chunks: List[Dict[str, int]]) -> str:
        """读取知识库中指定文件的文本块内容

        使用此工具获取文档的文本内容。输入应包含文件 ID 和块索引的数组。

        Args:
            chunks: 要读取的文件和块索引对数组，格式为 [{"fileId": int, "chunkIndex": int}, ...]
                 chunkIndex 从 0 开始

        Returns:
            包含请求的文件块内容的 JSON 字符串，每个块包含文本内容和元数据
        """
        if not chunks:
            return "请提供要读取的 chunk 信息数组"
        results = kb_controller.readFileChunks(kb_id, chunks)
        return json.dumps(results, ensure_ascii=False, indent=2)

    @tool("list_files")
    def list_files(page: int = 0, pageSize: int = 10) -> str:
        """分页列出知识库中的所有文件

        返回文件 ID、文件名和每个文件的块数量。仅返回状态为完成（done）的文件。

        Args:
            page: 页码，从 0 开始
            pageSize: 每页显示的文件数量

        Returns:
            包含文件列表的 JSON 字符串，每个文件包含 ID、文件名和块数量
        """
        results = kb_controller.listFilesPaginated(kb_id, page, pageSize)
        filtered = [f for f in results if f.get("status") == "done"]
        return json.dumps(
            [
                {
                    "id": f.get("id"),
                    "filename": f.get("filename"),
                    "chunkCount": f.get("chunk_count", 0),
                }
                for f in filtered
            ],
            ensure_ascii=False,
            indent=2,
        )

    def get_toolset_description() -> str:
        return f"""用于与知识库「{kb_name}」交互的工具集。包含查询知识库、获取文件元数据、读取文件块和列出文件的工具。

可用工具：
1. query_knowledge_base: 使用搜索查询检索知识库
2. get_files_meta: 获取知识库中文件的元数据
3. read_file_chunks: 读取知识库中指定文件的文本块内容
4. list_files: 列出知识库中的所有文件"""

    # 存储工具集描述供外部使用
    query_knowledge_base.description = f"语义检索知识库「{kb_name}」并返回候选片段列表"
    get_files_meta.description = f"获取知识库「{kb_name}」中指定文件的元数据信息（文件名、大小、块总数等）"
    read_file_chunks.description = f"读取知识库「{kb_name}」中指定文件的文本块内容"
    list_files.description = f"分页列出知识库「{kb_name}」中的所有文件"

    return [query_knowledge_base, get_files_meta, read_file_chunks, list_files]


def get_toolset_description(kb_id: int, kb_name: str = "知识库") -> str:
    """获取工具集的描述文本

    Args:
        kb_id: 知识库 ID
        kb_name: 知识库名称

    Returns:
        工具集描述字符串
    """
    return f"""用于与知识库「{kb_name}」(ID: {kb_id}) 交互的工具集。包含查询知识库、获取文件元数据、读取文件块和列出文件的工具。

可用工具：
1. query_knowledge_base: 使用搜索查询检索知识库，返回匹配的文档片段
2. get_files_meta: 获取知识库中文件的元数据（文件名、块数量、状态等）
3. read_file_chunks: 读取知识库中指定文件的文本块内容
4. list_files: 分页列出知识库中的所有文件，返回文件 ID、文件名和块数量"""
