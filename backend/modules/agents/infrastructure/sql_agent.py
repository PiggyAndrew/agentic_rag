import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from backend.modules.providers.domain.models import ModelCategory
from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository
from backend.tools.sql import build_sql_tools


def _system_prompt() -> str:
    return (
        "你是一个 SQL 助手。你只能通过工具与数据库交互，不要编造表结构或数据。\n"
        "工作流程：\n"
        "1) 先调用 sql_db_list_tables 获取表名\n"
        "2) 再调用 sql_db_schema 获取相关表的字段\n"
        "3) 生成只读 SQL（SELECT/WITH），再调用 sql_db_query_checker 检查\n"
        "4) 最后调用 sql_db_query 执行并基于结果回答\n"
        "如果工具返回未配置数据库或数据库文件不存在，直接说明如何设置 SQL_DB_PATH 或 SQL_DB_URI。\n"
    )


def _build_model():
    load_dotenv()
    repo = LLMConfigRepository()
    p = repo.get_default_by_category(ModelCategory.llm.value) or repo.get_default_by_category(ModelCategory.vll.value)
    api_key = (p.api_key if p else None) or (os.getenv("LLM_API_KEY") or "").strip()
    base_url = (p.base_url if p else None) or (os.getenv("LLM_BASE_URL") or "").strip()
    model = (p.model_name if p else None) or (os.getenv("LLM_MODEL") or "").strip()
    return ChatOpenAI(
        temperature=0,
        max_retries=3,
        base_url=base_url,
        model=model,
        api_key=api_key,
    )


def create_sql_agent():
    llm = _build_model()
    tools = build_sql_tools()
    return create_agent(
        llm,
        tools,
        system_prompt=_system_prompt(),
    )


try:
    sql_agent = create_sql_agent()
except Exception:
    sql_agent = None

