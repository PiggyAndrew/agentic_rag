
import sys
sys.path.append("D:\\Gitspace\\agentic_rag")
import os
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 导入你的 Agent
from app.agent import agent as rag_agent

load_dotenv()

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

def convert_messages(messages: List[Message]):
    """将 Pydantic 消息转换为 LangChain 消息对象"""
    lc_messages = []
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            lc_messages.append(SystemMessage(content=msg.content))
    return lc_messages

async def stream_generator(messages):
    """生成符合 Vercel AI SDK 协议的流式响应"""
    print(f"Start streaming for messages: {len(messages)}")
    if not rag_agent:
        yield "Error: Agent not initialized"
        return

    inputs = {"messages": convert_messages(messages)}
    print(f"Inputs prepared: {inputs}")
    
    try:
        # 使用 astream_events 获取详细的流式事件
        print("Calling rag_agent.astream_events...")
        async for event in rag_agent.astream_events(inputs, version="v1"):
            kind = event["event"]
            # print(f"Event received: {kind}")
            
            # 监听 LLM 生成的 token
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    # 直接输出文本内容，符合 text/plain 流式格式（简单模式）
                    # 或者也可以封装为 data: ... 格式，取决于前端处理
                    # 这里我们使用简单的文本流，配合前端 fetch reader 处理
                    print(f"Yielding content: {content}")
                    yield content

            # 也可以监听工具调用等其他事件进行处理
            # elif kind == "on_tool_start": ...
            
    except Exception as e:
        print(f"Error in stream_generator: {e}")
        yield f"\n[Error: {str(e)}]"

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        stream_generator(request.messages),
        media_type="text/plain"
    )

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

if __name__ == "__main__":
    main()
