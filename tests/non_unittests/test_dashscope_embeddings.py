import os
import sys
import numpy as np

# 确保可以导入项目根目录下的 backend 包
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv
from backend.kb.embeddings import AliyunDashScopeEmbeddingProvider


def test_dashscope_embedding_provider():
    """验证阿里云百炼 DashScope 嵌入提供者的基本可用性

    - 加载 .env，读取 DASHSCOPE_API_KEY
    - 当存在有效密钥时，分别测试单条与批量嵌入
    - 断言返回向量维度一致且为非零向量
    """
    load_dotenv()
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        # 若未配置密钥则跳过测试（不视为失败）
        assert True
        return

    provider = AliyunDashScopeEmbeddingProvider()

    vec_single = provider.embed_text("衣服的质量杠杠的")
    print(vec_single)
    assert isinstance(vec_single, np.ndarray)
    assert vec_single.size > 0
    assert np.linalg.norm(vec_single) > 0

    batch = ["质量很好", "尺码合适"]
    vec_batch = provider.embed_texts(batch)
    print(vec_batch)
    assert isinstance(vec_batch, np.ndarray)
    assert vec_batch.shape[0] == len(batch)
    assert vec_batch.shape[1] == vec_single.size
    # 每条向量应为非零
    norms = np.linalg.norm(vec_batch, axis=1)
    assert np.all(norms > 0)


def main():
    test_dashscope_embedding_provider()



if __name__ == "__main__":
    main()
