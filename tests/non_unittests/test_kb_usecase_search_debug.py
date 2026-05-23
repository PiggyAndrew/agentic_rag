import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.entrypoints.composition.kb import build_kb_usecase, default_kb_base_dir

def test_kb_usecase_search():
    """测试通过 KnowledgeBaseUseCase 搜索"""
    print("=" * 60)
    print("测试: 通过 KnowledgeBaseUseCase 搜索")
    print("=" * 60)
    
    kb_usecase = build_kb_usecase(base_dir=default_kb_base_dir())
    kb_id = 1
    query = "Industry Standards"
    
    print(f"kb_id: {kb_id}")
    print(f"query: {query}")
    print(f"base_dir: {default_kb_base_dir()}")
    print()
    
    print(f"kb_usecase.search_usecase type: {type(kb_usecase.search_usecase)}")
    print(f"kb_usecase.search_usecase: {kb_usecase.search_usecase}")
    print()
    
    print(f"kb_usecase.search_usecase.search type: {type(kb_usecase.search_usecase.search)}")
    print(f"kb_usecase.search_usecase.search: {kb_usecase.search_usecase.search}")
    print()
    
    print(f"kb_usecase.search_usecase has search method: {hasattr(kb_usecase.search_usecase, 'search')}")
    print(f"kb_usecase.search_usecase.search is callable: {callable(kb_usecase.search_usecase.search)}")
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

if __name__ == "__main__":
    test_kb_usecase_search()
