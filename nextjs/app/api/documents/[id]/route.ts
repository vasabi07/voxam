import { NextRequest, NextResponse } from "next/server"
import { createClient } from "@/lib/supabase/server"
import { db } from "@/lib/prisma"

/**
 * Proxy PDF documents from R2 to avoid CORS issues.
 * GET /api/documents/[id] - Returns the PDF file
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: documentId } = await params

    // Authenticate user
    const supabase = await createClient()
    const { data: { user } } = await supabase.auth.getUser()

    if (!user) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 })
    }

    // Get document from database
    const document = await db.document.findUnique({
      where: { id: documentId },
      select: { userId: true, fileKey: true, title: true, mimeType: true },
    })

    if (!document) {
      return NextResponse.json({ error: "Document not found" }, { status: 404 })
    }

    // Verify ownership
    if (document.userId !== user.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 403 })
    }

    if (!document.fileKey) {
      return NextResponse.json({ error: "Document has no file" }, { status: 404 })
    }

    // Fetch from Python backend which has R2 credentials
    const { data: { session } } = await supabase.auth.getSession()
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

    // Get presigned URL from Python backend
    const urlRes = await fetch(`${apiUrl}/documents/${documentId}/url`, {
      headers: {
        "Authorization": `Bearer ${session?.access_token}`,
      },
    })

    if (!urlRes.ok) {
      console.error("[PDF Proxy] Failed to get presigned URL:", await urlRes.text())
      return NextResponse.json({ error: "Failed to get document URL" }, { status: 500 })
    }

    const urlData = await urlRes.json()
    if (!urlData.success || !urlData.url) {
      return NextResponse.json({ error: urlData.error || "Failed to get URL" }, { status: 500 })
    }

    // Fetch the PDF from R2
    console.log("[PDF Proxy] Fetching PDF from R2...")
    const pdfRes = await fetch(urlData.url)

    if (!pdfRes.ok) {
      console.error("[PDF Proxy] Failed to fetch PDF from R2:", pdfRes.status)
      return NextResponse.json({ error: "Failed to fetch PDF" }, { status: 500 })
    }

    // Stream the PDF to the client
    const pdfBuffer = await pdfRes.arrayBuffer()

    return new NextResponse(pdfBuffer, {
      status: 200,
      headers: {
        "Content-Type": document.mimeType || "application/pdf",
        "Content-Disposition": `inline; filename="${document.title || 'document.pdf'}"`,
        "Cache-Control": "private, max-age=3600", // Cache for 1 hour
      },
    })
  } catch (error) {
    console.error("[PDF Proxy] Error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
