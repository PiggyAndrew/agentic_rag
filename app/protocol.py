import json
from app.agent import agent as rag_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

def convert_messages(messages):
    """将前端消息转换为 LangChain 消息对象用于 Agent 输入"""
    lc_messages = []
    for msg in messages:
        role = getattr(msg, 'role', None) or msg.get('role')
        content = getattr(msg, 'content', None) or msg.get('content')
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content))
    return lc_messages

async def stream_generator(messages):
    """
    生成符合 Vercel AI SDK Data Stream Protocol 的流式响应
    协议文档: https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#data-stream-protocol
    """
    if not rag_agent:
        # 0: text part
        yield '0:"Error: Agent not initialized"\n'
        return

    inputs = {"messages": convert_messages(messages)}
    
    try:
        async for event in rag_agent.astream_events(inputs, version="v1"):
            kind = event["event"]
            
            # 1. 处理文本生成流 (on_chat_model_stream)
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                # 如果是普通文本内容
                if chunk.content:
                    # 0: text part - 直接输出文本片段
                    # 格式: 0:"text_content"\n
                    yield f'0:{json.dumps(chunk.content)}\n'
                
                # 如果是工具调用片段 (tool_call_chunks)
                if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                     for tc_chunk in chunk.tool_call_chunks:
                         # 这里可以处理流式的工具调用参数，但 Vercel AI SDK 通常期望完整的工具调用
                         # 或者使用 9: stream data 自定义协议
                         pass

            # 2. 处理工具调用开始 (on_tool_start)
            elif kind == "on_tool_start":
                # 可以在这里发送工具调用的元数据，例如 "正在搜索知识库..."
                # 9: stream data (自定义数据)
                tool_name = event["name"]
                tool_inputs = event["data"].get("input")
                # 仅展示关键工具，避免展示内部实现细节
                if tool_name not in ["LangGraph", "__pregel_pull", "model"]:
                     data = {"type": "tool_start", "tool": tool_name, "input": tool_inputs}
                     yield f'8:{json.dumps([data])}\n' # 8: data message (draft) or 2: data

            # 3. 处理工具调用结束 (on_tool_end)
            elif kind == "on_tool_end":
                 tool_name = event["name"]
                 tool_output = event["data"].get("output")
                 # 同样仅处理关键工具
                 if tool_name not in ["LangGraph", "__pregel_pull", "model"]:
                     # 尝试解析 JSON 输出以便前端更好展示
                     try:
                         if isinstance(tool_output, str):
                             tool_output = json.loads(tool_output)
                     except:
                         pass
                     
                     data = {"type": "tool_end", "tool": tool_name, "output": tool_output}
                     # 发送工具结果数据
                     yield f'8:{json.dumps([data])}\n'

    except Exception as e:
        # 3: error part
        yield f'3:{json.dumps(str(e))}\n'
