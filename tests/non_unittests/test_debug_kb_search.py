import os
import sys
import json
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.kb.knowledge_base import PersistentKnowledgeBaseController



def run_debug():
    kb = PersistentKnowledgeBaseController()
    chunks = [
        {"content": "Python naming conventions: variables use snake_case.", "metadata": {"topic": "naming", "lang": "en"}},
        {"content": "Class names use PascalCase; constants are UPPER_CASE.", "metadata": {"topic": "naming"}},
        "Good naming improves readability and maintainability.",
        {"content": "模块名应短小且小写，包名避免冲突。", "metadata": None},
    ]
    info = kb.add_file(1, "debug.txt", chunk_count=0, status="uploaded")
    kb.save_chunks(1, info.id, chunks)
    results = kb.search(1, "naming")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_debug()
