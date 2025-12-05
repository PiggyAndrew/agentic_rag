"""Demo"""

import os
import sys
sys.path.append("D:\\GitHub\\agentic_rag")
from dotenv import load_dotenv
load_dotenv() # pylint: disable=wrong-import-position

from fastapi import FastAPI
import uvicorn
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAGUIAgent
from app.agent import agent
from app.agent_graph import graph

app = FastAPI()
sdk = CopilotKitRemoteEndpoint(
        agents=[
            LangGraphAGUIAgent(
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
