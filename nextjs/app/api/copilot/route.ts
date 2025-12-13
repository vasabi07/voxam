import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  LangGraphHttpAgent,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";


// You can use any service adapter here for multi-agent support.
import { createClient } from "@/lib/supabase/server";

export const POST = async (req: NextRequest) => {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return new Response("Unauthorized", { status: 401 });
  }

  const serviceAdapter = new ExperimentalEmptyAdapter();

  const runtime = new CopilotRuntime({
    agents: {
      'chat_agent': new LangGraphHttpAgent({
        url: "http://localhost:8000/copilotkit",
        headers: {
          "Authorization": `Bearer ${session.access_token}`
        }
      }),
    },
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilot",
  });

  return handleRequest(req);
};