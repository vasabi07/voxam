import { createClient } from "@/lib/supabase/server"
import { NextRequest } from "next/server"

const PYTHON_API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function POST(req: NextRequest) {
  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" }
    })
  }

  try {
    const body = await req.json()

    const res = await fetch(`${PYTHON_API}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`
      },
      body: JSON.stringify(body)
    })

    if (!res.ok) {
      const errorText = await res.text()
      console.error("Python API error:", res.status, errorText)
      return new Response(JSON.stringify({ error: `API error: ${res.status}` }), {
        status: res.status,
        headers: { "Content-Type": "application/json" }
      })
    }

    // Forward the SSE stream
    return new Response(res.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
      }
    })

  } catch (error) {
    console.error("Stream proxy error:", error)
    return new Response(JSON.stringify({ error: "Internal server error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    })
  }
}
