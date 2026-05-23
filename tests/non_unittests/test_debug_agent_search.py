import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.entrypoints.composition.kb import build_kb_usecase, default_kb_base_dir
from backend.tools.runtime import build_tools

def test_direct_search():
    """测试直接调用 search 方法"""
    print("=" * 60)
    print("测试 1: 直接调用 KnowledgeBaseUseCase.search()")
    print("=" * 60)
    
    kb_usecase = build_kb_usecase(base_dir=default_kb_base_dir())
    kb_id = 1
    query = "Industry Standards"
    
    print(f"kb_id: {kb_id}")
    print(f"query: {query}")
    print(f"base_dir: {default_kb_base_dir()}")
    print()
    
    try:
        results = kb_usecase.search(kb_id, query)
        print(f"✓ 搜索成功，返回 {len(results)} 条结果")
        if results:
            print(f"第一条结果: {results[0]}")
        else:
            print("⚠ 返回空结果")
    except Exception as e:
        print(f"✗ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def test_tool_search():
    """测试通过 tool 调用"""
    print("=" * 60)
    print("测试 2: 通过 tool 调用 query_knowledge_base")
    print("=" * 60)
    
    kb_usecase = build_kb_usecase(base_dir=default_kb_base_dir())
    kb_id = 1
    query = "Industry Standards"
    
    print(f"kb_id: {kb_id}")
    print(f"query: {query}")
    print(f"base_dir: {default_kb_base_dir()}")
    print()
    
    try:
        tools = build_tools(kb_usecase, kb_id)
        query_tool = None
        for tool in tools:
            if tool.name == "query_knowledge_base":
                query_tool = tool
                break
        
        if query_tool is None:
            print("✗ 未找到 query_knowledge_base tool")
            return
        
        print(f"✓ 找到 tool: {query_tool.name}")
        print(f"  描述: {query_tool.description}")
        print()
        
        result = query_tool.func(query)
        print(f"✓ Tool 调用成功")
        print(f"  返回结果长度: {len(result)}")
        print(f"  返回结果: {result[:500]}...")
        
    except Exception as e:
        print(f"✗ Tool 调用失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def test_search_adapter():
    """测试 SearchAdapter 的 top_k 参数传递"""
    print("=" * 60)
    print("测试 3: 检查 SearchAdapter 的 top_k 参数传递")
    print("=" * 60)
    
    from backend.modules.kb.infrastructure.adapters.search_adapter import SearchAdapter
    from backend.database.sqlite import get_default_sqlite_manager
    from backend.modules.kb.infrastructure.legacy_kb.knowledge_repository import SqlAlchemyKnowledgeRepository
    
    manager = get_default_sqlite_manager()
    repo = SqlAlchemyKnowledgeRepository(manager=manager)
    search_adapter = SearchAdapter(repo=repo, manager=manager, base_dir=default_kb_base_dir())
    
    print(f"SearchAdapter.search 方法签名:")
    import inspect
    sig = inspect.signature(search_adapter.search)
    print(f"  {sig}")
    print()
    
    print(f"检查 PersistentKnowledgeBaseController.search 方法:")
    kb_controller = search_adapter._get_kb_controller()
    sig2 = inspect.signature(kb_controller.search)
    print(f"  {sig2}")
    print()
    
    print(f"⚠ 注意: SearchAdapter.search 接收 top_k 参数，但没有传递给 kb_controller.search")
    print()

def test_vector_store_paths():
    """测试向量库路径"""
    print("=" * 60)
    print("测试 4: 检查向量库路径")
    print("=" * 60)
    
    from backend.modules.kb.infrastructure.legacy_kb.knowledge_base import PersistentKnowledgeBaseController
    from backend.modules.kb.infrastructure.legacy_kb.vector_store import ChromaVectorStore
    
    base_dir = default_kb_base_dir()
    print(f"base_dir: {base_dir}")
    print()
    
    # 测试 PersistentKnowledgeBaseController 的向量库路径
    kb_controller = PersistentKnowledgeBaseController(base_dir=base_dir)
    vstore_path = kb_controller._vstore._persist_dir
    print(f"PersistentKnowledgeBaseController._vstore._persist_dir:")
    print(f"  {vstore_path}")
    print()
    
    # 测试直接创建 ChromaVectorStore 的路径
    vstore = ChromaVectorStore(base_dir=base_dir)
    vstore_path2 = vstore._persist_dir
    print(f"ChromaVectorStore(base_dir=base_dir)._persist_dir:")
    print(f"  {vstore_path2}")
    print()
    
    # 检查路径是否一致
    if vstore_path == vstore_path2:
        print("✓ 向量库路径一致")
    else:
        print(f"✗ 向量库路径不一致!")
        print(f"  路径 1: {vstore_path}")
        print(f"  路径 2: {vstore_path2}")
    print()

if __name__ == "__main__":
    test_vector_store_paths()
    test_direct_search()
    test_tool_search()
    test_search_adapter()
