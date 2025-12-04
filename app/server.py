"""Demo"""

import os
import sys
sys.path.append("D:\\GitHub\\agentic_rag")
from dotenv import load_dotenv
load_dotenv() # pylint: disable=wrong-import-position

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from app.agent import agent
from app.agent_graph import graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatInput(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(data: ChatInput):
    inputs = {"messages": [("user", data.message)]}
    result = await agent.ainvoke(inputs)
    return result

sdk = CopilotKitRemoteEndpoint(
        agents=[
            LangGraphAgent(
                name="agentic_rag", 
                description="This agent sends emails",
                graph=graph,
            )
        ],
    )
add_fastapi_endpoint(app, sdk, "/copilotkit")


def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

if __name__ == "__main__":
    main()
