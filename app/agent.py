import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from app.tools import build_tools
from app.prompts import get_system_prompt


def create_agentic_rag_system(kb_controller, kb_id: int):
    """创建 Agentic RAG 系统：绑定工具、加载模型并返回Agent实例"""

    tools = build_tools(kb_controller, kb_id)

    SYSTEM_PROMPT = get_system_prompt()

    load_dotenv()
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise ValueError("请设置 DEEPSEEK_API_KEY 环境变量")

    llm = ChatOpenAI(
        temperature=0,
        max_retries=3,
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
    )

    agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
    return agent
