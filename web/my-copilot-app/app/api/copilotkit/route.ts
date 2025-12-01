import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
  LangGraphAgent
} from "@copilotkit/runtime";
import OpenAI from "openai";
import { NextRequest } from "next/server";

const openai = new OpenAI();
const serviceAdapter = new OpenAIAdapter({ openai } as any);

// const runtime = new CopilotRuntime({
//   agents: {
//     'my_agent': new LangGraphAgent({
//       deploymentUrl: "your-api-url", // make sure to replace with your real deployment url
//       langsmithApiKey: process.env.LANGSMITH_API_KEY, // only used in LangGraph Platform deployments
//       graphId: 'my_agent', // usually the same as agent name
//     })
//   },
// });

const runtime = new CopilotRuntime({
  remoteEndpoints: [
    {
      url: "http://localhost:8000/copilotkit",
    },
  ],
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};