import { createClient } from "@/lib/supabase/server"
import { NextRequest, NextResponse } from "next/server"

const PYTHON_API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function GET(req: NextRequest) {
  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  try {
    // Forward doc_id query parameter for document-specific chat history
    const docId = req.nextUrl.searchParams.get("doc_id")
    const url = docId
      ? `${PYTHON_API}/chat/history?doc_id=${encodeURIComponent(docId)}`
      : `${PYTHON_API}/chat/history`

    const res = await fetch(url, {
      headers: { "Authorization": `Bearer ${session.access_token}` }
    })

    const data = await res.json()
    return NextResponse.json(data)
  } catch (e) {
    console.error("Failed to fetch chat history:", e)
    return NextResponse.json({ messages: [], error: "Failed to fetch history" })
  }
}

export async function DELETE(req: NextRequest) {
  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  try {
    // Parse doc_id from request body and forward to Python API
    const body = await req.json().catch(() => ({}))

    const res = await fetch(`${PYTHON_API}/chat/history`, {
      method: "DELETE",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    })

    const data = await res.json()
    return NextResponse.json(data)
  } catch (e) {
    console.error("Failed to clear chat history:", e)
    return NextResponse.json({ error: "Failed to clear history" }, { status: 500 })
  }
}
