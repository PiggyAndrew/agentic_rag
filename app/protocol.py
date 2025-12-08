import json
from app.agent import agent as rag_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

def convert_messages(messages):
    """
    将前端消息转换为 LangChain 消息对象用于 Agent 输入
    支持两种输入：
    1) Pydantic BaseModel（fastapi 请求体解析出的对象）
    2) 原始 dict（直接从 JSON 转换而来）
    """
    lc_messages = []
    for msg in messages:
        role = None
        content = None
        if isinstance(msg, dict):
            role = msg.get('role')
            content = msg.get('content')
        else:
            # Pydantic/BaseModel 或具备属性访问的对象
            role = getattr(msg, 'role', None)
            content = getattr(msg, 'content', None)

        if role == "user":
            lc_messages.append(HumanMessage(content=content or ""))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content or ""))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content or ""))
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
                tool_name = event.get("name") or event.get("data", {}).get("name")
                tool_inputs = event.get("data", {}).get("input")
                if tool_name not in ["LangGraph", "__pregel_pull", "model"]:
                     data = {"type": "tool_start", "tool": tool_name, "input": _to_jsonable(tool_inputs)}
                     yield f'8:{json.dumps([data])}\n'

            # 3. 处理工具调用结束 (on_tool_end)
            elif kind == "on_tool_end":
                 tool_name = event.get("name") or event.get("data", {}).get("name")
                 tool_output = event.get("data", {}).get("output")
                 if tool_name not in ["LangGraph", "__pregel_pull", "model"]:
                     data = {"type": "tool_end", "tool": tool_name, "output": _to_jsonable(tool_output)}
                     yield f'8:{json.dumps([data])}\n'
                     # 如果这是最终答案工具，尝试直接输出文本
                     txt = _extract_text(tool_output)
                     if txt:
                         yield f'0:{json.dumps(txt)}\n'

            # 4. 模型结束（可能包含整段文本）
            elif kind == "on_chat_model_end":
                out = event.get("data", {}).get("output")
                txt = _extract_text(out)
                if txt:
                    yield f'0:{json.dumps(txt)}\n'

            # 5. 整体链路结束（LangGraph/Agent 产出的最终结构化答案）
            elif kind == "on_chain_end":
                data = event.get("data", {})
                sr = data.get("structured_response")
                # 优先提取结构化响应中的 answer 字段
                if sr is not None:
                    ans = None
                    # pydantic / dataclass / dict 兼容提取
                    ans = getattr(sr, "answer", None)
                    if ans is None and hasattr(sr, "model_dump"):
                        try:
                            ans = sr.model_dump().get("answer")
                        except Exception:
                            pass
                    if ans is None and hasattr(sr, "dict"):
                        try:
                            ans = sr.dict().get("answer")
                        except Exception:
                            pass
                    if ans is None and isinstance(sr, dict):
                        ans = sr.get("answer")
                    if ans:
                        yield f'0:{json.dumps(ans)}\n'
                else:
                    # 退化：尝试从 output.messages 中取最后一条内容
                    out = data.get("output")
                    txt = _extract_text(out)
                    if txt:
                        yield f'0:{json.dumps(txt)}\n'

    except Exception as e:
        # 3: error part
        yield f'3:{json.dumps(str(e))}\n'

def _to_jsonable(obj):
    """将任意 Python/SDK 对象转为可 JSON 序列化的数据结构"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    # Pydantic BaseModel
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return _to_jsonable(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return _to_jsonable(obj.dict())
        except Exception:
            pass
    # LangChain Message 或通用对象，优先提取 content
    if hasattr(obj, "content"):
        try:
            return _to_jsonable(getattr(obj, "content"))
        except Exception:
            pass
    # 通用对象：展开 __dict__
    if hasattr(obj, "__dict__"):
        try:
            return {k: _to_jsonable(v) for k, v in obj.__dict__.items() if not str(k).startswith("_")}
        except Exception:
            pass
    return str(obj)

def _extract_text(obj):
    """尽可能从对象中提取可展示的文本内容"""
    if obj is None:
        return None
    # 直接字符串
    if isinstance(obj, str):
        return obj
    # LangChain Message 类：尝试 .content
    if hasattr(obj, "content"):
        try:
            c = getattr(obj, "content")
            return c if isinstance(c, str) else json.dumps(_to_jsonable(c))
        except Exception:
            pass
    # dict: 可能有 answer 或 content
    if isinstance(obj, dict):
        for key in ("answer", "content"):
            if key in obj and isinstance(obj[key], str):
                return obj[key]
        # 如果 output 是包含 messages 的结构
        msgs = obj.get("messages") or obj.get("message")
        if isinstance(msgs, list) and msgs:
            last = msgs[-1]
            if isinstance(last, dict) and isinstance(last.get("content"), str):
                return last.get("content")
        # 兜底：序列化为字符串
        try:
            return json.dumps(_to_jsonable(obj))
        except Exception:
            return str(obj)
    # pydantic / dataclass：尝试字典化
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            d = obj.model_dump()
            return _extract_text(d)
        except Exception:
            pass
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            d = obj.dict()
            return _extract_text(d)
        except Exception:
            pass
    return None
