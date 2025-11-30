"""
Agentic RAG MVP 示例
实现一个最小可用的 Agentic RAG 系统，演示如何通过工具组合实现"先粗后细"的证据收集策略
"""

import os

from kb.knowledge_base import PersistentKnowledgeBaseController
from app.agent import create_agentic_rag_system

# 初始化持久化的知识库控制器
kb_controller = PersistentKnowledgeBaseController()
knowledge_base_id = 1  # 知识库ID（持久化）

 


def main():
    """主函数 - 演示 Agentic RAG 的工作流程"""
    agent = create_agentic_rag_system(knowledge_base_id)

    files = kb_controller.listFilesPaginated(knowledge_base_id, page=0, page_size=100)
    for f in files:
        print(f"  - {f['filename']} ({f['chunk_count']} chunks)")

    print("💬 开始问答演示")

    # 测试问题
    question = "请告诉我文件里这个项目工作集应当如何命名？并帮我解释每个参数的含义，我看到结果里有5.1所以5.1里具体说啥告诉我"
    print(f"\n❓ 问题: {question}")
    print("\n🤔 Agent 思考与行动过程:")
    print("-" * 50)
    # 调用 Agent（设置递归上限，避免模型反复调用工具不收敛）
    result = agent.invoke({"messages": [("user", question)]})
    final_answer = result["messages"][-1].content
    print(final_answer)


if __name__ == "__main__":
    main()
