import os
import sys
import json

# 确保可导入顶层包 `kb`
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from kb.knowledge_base import PersistentKnowledgeBaseController


def run_search(kb_id: int, query: str, top_k: int = 5):
    """执行向量检索并打印Top-K结果"""
    kb = PersistentKnowledgeBaseController()
    results = kb.search(kb_id, query)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_search(1, "Industry Standards")

