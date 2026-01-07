import json
import urllib.request

from backend.services import kb_service

def list_kbs():
    """列出所有知识库（读取持久化元数据）"""
    metas = kb_service.list_kbs()
    return metas
    
if __name__ == "__main__":
    metas = list_kbs()
    print(metas)
