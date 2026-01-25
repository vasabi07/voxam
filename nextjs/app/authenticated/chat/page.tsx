"use client"

import React, { useState, useEffect, Suspense, useCallback } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { Chat } from "@/components/Chat"
import { QuickActions } from "@/components/copilot/QuickActions"
import { PdfViewer } from "@/components/copilot/PdfViewer"
import { getDocumentFileUrl } from "@/app/actions/document"
import { PanelLeftClose, PanelLeft, Plus, Loader2 } from "lucide-react"

function ChatPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()

  // Separate concerns: doc = chat thread scope, view = PDF viewer document
  const docId = searchParams.get("doc")           // Chat thread scope (opt-in)
  const viewDocId = searchParams.get("view")      // PDF viewer document (from source clicks)
  const initialPage = searchParams.get("page")    // Page from URL for deep links

  // PDF viewer shows: viewDocId OR docId (fallback)
  const pdfDocId = viewDocId || docId

  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [documentTitle, setDocumentTitle] = useState<string>("")
  const [targetPage, setTargetPage] = useState<number | undefined>()
  const [showPdf, setShowPdf] = useState(true)
  const [loadingPdf, setLoadingPdf] = useState(false)

  // Chat session state - key forces re-mount of Chat component
  const [conversationKey, setConversationKey] = useState(Date.now())
  const [isClearing, setIsClearing] = useState(false)

  // Pending message state for QuickActions
  const [pendingMessage, setPendingMessage] = useState<string | null>(null)

  // Handle history loaded callback - redirect to clean chat if no history but doc param exists
  const handleHistoryLoaded = useCallback((hasMessages: boolean) => {
    if (!hasMessages && docId) {
      // No history but we have doc param - redirect to clean chat
      router.replace('/authenticated/chat')
    }
  }, [docId, router])

  // New Conversation handler - clears Redis checkpoint and resets UI
  const handleNewConversation = async () => {
    setIsClearing(true)
    try {
      // Clear Redis checkpoint via API
      await fetch('/api/chat/history', { method: 'DELETE' })
      // Force re-mount of Chat component by changing the key
      setConversationKey(Date.now())
    } catch (e) {
      console.error('Failed to clear history:', e)
    } finally {
      setIsClearing(false)
    }
  }

  // Load PDF URL when pdfDocId changes (either from view or doc param)
  useEffect(() => {
    if (!pdfDocId) {
      setPdfUrl(null)
      setDocumentTitle("")
      return
    }

    const loadPdfUrl = async () => {
      setLoadingPdf(true)
      console.log('[PDF] Loading PDF for pdfDocId:', pdfDocId)
      const result = await getDocumentFileUrl(pdfDocId)
      console.log('[PDF] URL result:', result.success, result.url?.substring(0, 80), result.error)
      if (result.success && result.url) {
        setPdfUrl(result.url)
        setDocumentTitle(result.title || "Document")
      } else {
        console.error('[PDF] Failed to load PDF:', result.error)
      }
      setLoadingPdf(false)
    }

    loadPdfUrl()
  }, [pdfDocId])

  // Handle initial page from URL (for cross-doc citation deep links)
  useEffect(() => {
    if (initialPage && pdfUrl) {
      const pageNum = parseInt(initialPage)
      if (!isNaN(pageNum) && pageNum > 0) {
        setTargetPage(pageNum)
        setShowPdf(true)
      }
    }
  }, [initialPage, pdfUrl])

  // Handle page click from source citations (opens PDF without changing chat thread)
  const handlePageClick = (page: number, targetDocId?: string) => {
    console.log('[PageClick] Handling page click:', { page, targetDocId, currentPdfDocId: pdfDocId })
    if (targetDocId && targetDocId !== pdfDocId) {
      // Different document - update view param only, preserve doc (chat scope)
      const params = new URLSearchParams(searchParams.toString())
      params.set("view", targetDocId)
      if (page) params.set("page", String(page))
      const url = `/authenticated/chat?${params.toString()}`
      console.log('[PageClick] Navigating to:', url)
      router.push(url)
    } else if (page) {
      // Same document - just scroll PDF
      setTargetPage(page)
      setShowPdf(true)
    }
  }

  // Handle "Chat on Document" button - switch to document-scoped chat
  const handleChatOnDocument = useCallback(() => {
    if (!pdfDocId) return
    const params = new URLSearchParams(searchParams.toString())
    params.set("doc", pdfDocId)  // Enable doc-scoped chat
    params.delete("view")        // No need for view if same as doc
    const url = `/authenticated/chat?${params.toString()}`
    console.log('[ChatOnDocument] Switching to doc-scoped chat:', url)
    router.push(url)
  }, [pdfDocId, searchParams, router])

  const hasPdf = !!pdfDocId
  const isChatScoped = !!docId && docId === pdfDocId  // Chat is scoped to the current PDF

  return (
    <div className="h-[calc(100vh-4rem)] w-full p-4 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <QuickActions
            onSendMessage={(msg) => setPendingMessage(msg)}
            disabled={!!pendingMessage}
          />
          <button
            onClick={handleNewConversation}
            disabled={isClearing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
            title="Start a new conversation"
          >
            {isClearing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">New Chat</span>
          </button>
        </div>
        {hasPdf && (
          <button
            onClick={() => setShowPdf(!showPdf)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
          >
            {showPdf ? (
              <>
                <PanelLeftClose className="w-4 h-4" />
                <span className="hidden sm:inline">Hide PDF</span>
              </>
            ) : (
              <>
                <PanelLeft className="w-4 h-4" />
                <span className="hidden sm:inline">Show PDF</span>
              </>
            )}
          </button>
        )}
      </div>

      <div className="flex-1 min-h-0 flex gap-4">
        {/* PDF Viewer Panel */}
        {hasPdf && showPdf && (
          <div className="w-1/2 lg:w-2/5 flex-shrink-0 hidden md:block">
            {loadingPdf ? (
              <div className="h-full flex items-center justify-center bg-muted/50 rounded-lg">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <PdfViewer
                url={pdfUrl}
                documentTitle={documentTitle}
                targetPage={targetPage}
                onClose={() => setShowPdf(false)}
                className="h-full"
                documentId={pdfDocId || undefined}
                onChatOnDocument={handleChatOnDocument}
                isChatScoped={isChatScoped}
              />
            )}
          </div>
        )}

        {/* Chat Panel */}
        <div className="flex-1 min-w-0 h-full">
          <Chat
            key={conversationKey}
            docId={docId || undefined}
            documentTitle={docId ? documentTitle : ""}
            onPageClick={handlePageClick}
            pendingMessage={pendingMessage}
            onMessageSent={() => setPendingMessage(null)}
            onHistoryLoaded={handleHistoryLoaded}
          />
        </div>
      </div>
    </div>
  )
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="h-[calc(100vh-4rem)] w-full p-4 flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    }>
      <ChatPageContent />
    </Suspense>
  )
}
