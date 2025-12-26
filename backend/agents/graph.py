from typing import List, Any, Optional
import os

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph import MessagesState
from langgraph.types import Command


class AgentState(MessagesState):
    """LangGraph 状态定义"""
    tools: List[Any]


async def chat_node(state: AgentState, config: Optional[RunnableConfig] = None):
    """单节点对话流程，绑定工具与系统消息并生成响应"""
    model = ChatOpenAI(
        temperature=0,
        max_retries=3,
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
    )
    if config is None:
        config = RunnableConfig(recursion_limit=25)
    model_with_tools = model.bind_tools(
        [*state["tools"]],
        parallel_tool_calls=False,
    )
    system_message = SystemMessage(content="You are a helpful assistant.")
    response = await model_with_tools.ainvoke([system_message, *state["messages"]], config)
    return Command(goto=END, update={"messages": response})


workflow = StateGraph(AgentState)
workflow.add_node("chat_node", chat_node)
workflow.set_entry_point("chat_node")
workflow.add_edge(START, "chat_node")
workflow.add_edge("chat_node", END)

is_fast_api = os.environ.get("LANGGRAPH_FAST_API", "false").lower() == "true"
if is_fast_api:
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
else:
    graph = workflow.compile()

