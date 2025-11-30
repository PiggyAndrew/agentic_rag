import json
import time
import uuid
import asyncio
from typing import AsyncGenerator, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.schemas import RAGAnswer

# 尝试导入 Agent
# 如果 app.agent 里的代码有问题，这里会捕获异常，避免 Server 启动失败
try:
    from app.agent import agent
    # from app.dummy_agent import agent
    AGENT_AVAILABLE = True
    # For debugging crash:
    # AGENT_AVAILABLE = False
    if agent is None:
        print("Warning: Agent imported but is None. Check app/agent.py logic.")
        AGENT_AVAILABLE = False
except Exception as e:
    print(f"Error importing agent: {e}")
    AGENT_AVAILABLE = False
    agent = None

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境请限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str | None = None
    messages: List[Dict[str, Any]] | None = None
    runId: str | None = None
    threadId: str | None = None
    agentId: str | None = None
    agent: str | None = None

async def event_generator(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    生成符合 AG-UI 协议的 SSE 事件流
    """
    print(f"DEBUG: Received request: {request}")
    # CopilotKit/AG-UI 可能使用 threadId/runId/agent 字段
    run_id = request.runId or request.threadId or str(uuid.uuid4())
    agent_id = request.agentId or request.agent or "default-agent"
    message_id = str(uuid.uuid4())

    # Determine the input for the agent
    # CopilotKit sends 'messages' list
    input_messages = []
    user_message_content = ""

    if request.messages:
        input_messages = request.messages
        # Try to find the last user message for logging or fallback
        for msg in reversed(request.messages):
            if msg.get("role") == "user":
                user_message_content = msg.get("content", "")
                break
    elif request.message:
        user_message_content = request.message
        input_messages = [{"role": "user", "content": request.message}]
    
    print(f"DEBUG: Input messages: {input_messages}")

    # 1. 发送 text-message-start
    start_event = {
        "type": "text-message-start",
        "id": message_id,
        "runId": run_id,
        "agentId": agent_id,
        "role": "assistant",
        "timestamp": int(time.time() * 1000)
    }
    yield f"data: {json.dumps(start_event)}\n\n"

    # 如果没有任何输入（前端握手或协议不匹配），返回提示以验证前后端链路
    if not input_messages:
        hint = (
            "后端收到空消息。请检查前端是否按 AG-UI/CopilotKit 协议发送 body，"
            "例如包含 messages、runId/threadId、agent 字段。"
        )
        content_event = {
            "type": "text-message-content",
            "id": message_id,
            "runId": run_id,
            "agentId": agent_id,
            "delta": hint,
            "timestamp": int(time.time() * 1000)
        }
        yield f"data: {json.dumps(content_event)}\n\n"
    elif AGENT_AVAILABLE and agent:
        try:
            # 调用 Agent 进行流式输出
            # 构造 input_data
            # LangGraph 通常接受 {"messages": [...]}
            input_data = {"messages": input_messages}
            
            # 如果是 LangGraph 的 CompiledGraph
            if hasattr(agent, "stream"):
                # 使用 astream (async stream) 如果可用，否则用 stream
                # 注意：LangChain 的 stream 通常是同步的生成器，astream 是异步的
                # 这里为了通用，我们尝试检测或直接用同步转异步
                
                # 简单的同步 stream 包装（如果在 async def 里调用同步生成器可能会阻塞，但在 FastAPI 里还好）
                # 更好的做法是使用 astream
                # Force sync stream for debugging
                if hasattr(agent, "astream"):
                    print(f"DEBUG: Starting astream with input: {input_data}")
                    async for chunk in agent.astream(input_data):
                        print(f"DEBUG: Received chunk keys: {chunk.keys() if isinstance(chunk, dict) else 'not dict'}")
                        
                        # Iterate over all node outputs in the chunk
                        for node_name, node_content in chunk.items():
                            # Check for structured_response in the node content
                            if "structured_response" in node_content:
                                print(f"DEBUG: Found structured_response in node {node_name}")
                                answer = node_content["structured_response"]
                                if isinstance(answer, RAGAnswer):
                                    yield f'data: {json.dumps({"type": "text-message-content", "id": message_id, "runId": run_id, "agentId": agent_id, "delta": answer.answer, "timestamp": int(time.time() * 1000)})}\n\n'
                                    
                                    if answer.citations:
                                        # Format citations/sources
                                        # CopilotKit expects citations in a specific way or we can append to content
                                        # For now, let's send a separate text message with citations or append
                                        sources_text = "\n\nSources:\n" + "\n".join([f"- {c.filename} (ID: {c.file_id}): {c.content[:50]}..." for c in answer.citations])
                                        yield f'data: {json.dumps({"type": "text-message-content", "id": message_id, "runId": run_id, "agentId": agent_id, "delta": sources_text, "timestamp": int(time.time() * 1000)})}\n\n'
                            
                            # Check for messages in the node content
                            elif "messages" in node_content:
                                messages = node_content["messages"]
                                if not isinstance(messages, list):
                                    messages = [messages]
                                
                                for msg in messages:
                                    if hasattr(msg, "content") and msg.content:
                                        print(f"DEBUG: Yielding content from message: {msg.content[:20]}...")
                                        yield f'data: {json.dumps({"type": "text-message-content", "id": message_id, "runId": run_id, "agentId": agent_id, "delta": msg.content, "timestamp": int(time.time() * 1000)})}\n\n'

                        # Legacy check (if chunk itself has keys, though less likely with updates mode)
                        if "structured_response" in chunk:
                            print(f"DEBUG: Received chunk keys: {chunk.keys() if isinstance(chunk, dict) else 'not dict'}")
                            
                            # 解析 chunk，提取文本内容
                            # LangGraph/LangChain 的 chunk 格式各异，这里做简单处理
                            content = ""
                            if isinstance(chunk, dict):
                                # 可能是 LangGraph 的状态更新
                                # 需要根据具体 graph 结构解析
                                # 这里做一个假设性的解析
                                if "structured_response" in chunk:
                                    resp = chunk["structured_response"]
                                    if hasattr(resp, "answer"):
                                        content = resp.answer
                                elif "messages" in chunk:
                                    last_msg = chunk["messages"][-1]
                                    if hasattr(last_msg, "content") and last_msg.content:
                                        content = last_msg.content
                                elif "output" in chunk:
                                    content = str(chunk["output"])
                                else:
                                    # 尝试直接转 string
                                    # content = str(chunk)
                                    pass
                            elif hasattr(chunk, "content"):
                                content = chunk.content
                            elif isinstance(chunk, str):
                                content = chunk
                            
                            # 发送增量内容
                            if content:
                                content_event = {
                                    "type": "text-message-content",
                                    "id": message_id,
                                    "runId": run_id,
                                    "agentId": agent_id,
                                    "delta": content,
                                    "timestamp": int(time.time() * 1000)
                                }
                                yield f"data: {json.dumps(content_event)}\n\n"
                            await asyncio.sleep(0.01) # 让出控制权

            else:
                # Agent 没有 stream 方法，直接 invoke
                result = await agent.ainvoke(input_data)
                content = str(result.get("output", result))
                content_event = {
                    "type": "text-message-content",
                    "id": message_id,
                    "runId": run_id,
                    "agentId": agent_id,
                    "delta": content,
                    "timestamp": int(time.time() * 1000)
                }
                yield f"data: {json.dumps(content_event)}\n\n"

        except Exception as e:
            # 发生错误，发送错误消息
            print(f"DEBUG: Error: {e}")
            error_msg = f"\n[System Error] Agent execution failed: {str(e)}"
            content_event = {
                "type": "text-message-content",
                "id": message_id,
                "runId": run_id,
                "agentId": agent_id,
                "delta": error_msg,
                "timestamp": int(time.time() * 1000)
            }
            yield f"data: {json.dumps(content_event)}\n\n"
            print(f"Agent Execution Error: {e}")
    else:
        print(f"DEBUG: Agent not available")
        # Fallback: 如果 Agent 不可用，发送 Mock 数据
        mock_responses = [
            "后端 Agent 尚未就绪，这是 Mock 响应。",
            "收到消息: " + user_message_content,
            "请检查 app/agent.py 是否正确配置及 DEEPSEEK_API_KEY 是否设置。"
        ]
        for text in mock_responses:
            content_event = {
                "type": "text-message-content",
                "id": message_id,
                "runId": run_id,
                "agentId": agent_id,
                "delta": text + "\n",
                "timestamp": int(time.time() * 1000)
            }
            yield f"data: {json.dumps(content_event)}\n\n"
            await asyncio.sleep(0.5)

    # 3. 发送 text-message-end
    end_event = {
        "type": "text-message-end",
        "id": message_id,
        "runId": run_id,
        "agentId": agent_id,
        "timestamp": int(time.time() * 1000)
    }
    yield f"data: {json.dumps(end_event)}\n\n"
    print(f"DEBUG: Yielded end_event")

    # 4. 发送 run-finished（AG-UI 生命周期事件，便于前端关闭一次运行）
    run_finished_event = {
        "type": "run-finished",
        "runId": run_id,
        "agentId": agent_id,
        "timestamp": int(time.time() * 1000)
    }
    yield f"data: {json.dumps(run_finished_event)}\n\n"

@app.post("/chat")
async def chat(request: ChatRequest, request_raw: Request):
    try:
        # 基础调试信息：方法、头、原始体大小
        raw_body = await request_raw.body()
        print(
            "DEBUG: /chat headers:", dict(request_raw.headers),
            "body_len:", len(raw_body) if raw_body else 0
        )
    except Exception as e:
        print("DEBUG: Failed to read raw request body:", e)

    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream"
    )

@app.get("/health")
async def health():
    return {"status": "ok", "agent_available": AGENT_AVAILABLE}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)










