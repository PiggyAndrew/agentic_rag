import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
# from langchain.agents import create_agent
from langgraph.prebuilt import create_react_agent
# from langchain.agents.structured_output import ToolStrategy
from app.tools import build_tools
from app.prompts import get_system_prompt
from kb.knowledge_base import PersistentKnowledgeBaseController
from app.schemas import RAGAnswer
# 内置中间件（用于上下文治理与稳健性提升）
# from langchain.agents.middleware import (
#     SummarizationMiddleware,
#     ContextEditingMiddleware,
#     ToolCallLimitMiddleware,
#     ToolRetryMiddleware,
# )



def create_agentic_rag_system(kb_id: int):
    """创建 Agentic RAG 系统：绑定工具、加载模型并返回Agent实例"""
    _kb_controller_default = PersistentKnowledgeBaseController()
    
    tools = build_tools(_kb_controller_default, kb_id)

    SYSTEM_PROMPT = get_system_prompt()

    load_dotenv()
    if not os.getenv("DEEPSEEK_API_KEY"):
        # raise ValueError("请设置 DEEPSEEK_API_KEY 环境变量")
        pass

    llm = ChatOpenAI(
        temperature=0,
        max_retries=3,
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
    )

    # agent = create_agent(
    #     llm,
    #     tools,
    #     system_prompt=SYSTEM_PROMPT,
    #     middleware=[
    #         #SummarizationMiddleware(model=llm, trigger={"tokens": 4000}, keep={"messages": 20}),
    #         # 使用 llm 实例传入，触发条件仅使用整数 tokens，避免跨版本解析问题
    #         ContextEditingMiddleware(),
    #         ToolCallLimitMiddleware(thread_limit=20,run_limit=10),
    #         ToolRetryMiddleware( max_retries=3,
    #         backoff_factor=2.0,
    #         initial_delay=1.0,),
    #     ],
    #     response_format=RAGAnswer
    # )
    
    # Use standard LangGraph create_react_agent
    agent = create_react_agent(
        model=llm,
        tools=tools,
        messages_modifier=SYSTEM_PROMPT,
        response_format=RAGAnswer
    )
    return agent

# 为 LangGraph CLI 暴露一个可直接使用的 graph 符号
# 默认绑定持久化知识库控制器与 KB ID=1
try:
    _DEFAULT_KB_ID = 1
    agent = create_agentic_rag_system(_DEFAULT_KB_ID)
except Exception as e:
    # 如果初始化失败（例如缺少环境变量），保留模块可导入性
    print(f"Agent init failed: {e}")
    agent = None
