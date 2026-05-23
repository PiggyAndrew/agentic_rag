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
    
    try:
        results = kb_usecase.search(kb_id, query)
        print(f"✓ 搜索成功，返回 {len(results)} 条结果")
        print()
        
        for i, result in enumerate(results):
            print(f"结果 {i + 1}:")
            print(f"  file_id: {result.get('file_id')}")
            print(f"  chunk_index: {result.get('chunk_index')}")
            print(f"  content: {result.get('content')}")
            print(f"  score: {result.get('score')}")
            print(f"  metadata: {result.get('metadata')}")
            print()
            
    except Exception as e:
        print(f"✗ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()

if __name__ == "__main__":
    test_kb_usecase_search()
