"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, X, FileText, Loader2, MessageSquare } from "lucide-react"
import { cn } from "@/lib/utils"
import * as pdfjsLib from "pdfjs-dist"

// Set worker path - use local worker file for reliability
pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs"

interface PdfViewerProps {
  url: string | null
  documentTitle?: string
  targetPage?: number
  onClose?: () => void
  className?: string
  documentId?: string
  onChatOnDocument?: () => void
  isChatScoped?: boolean  // True when chat is already scoped to this document
}

export function PdfViewer({
  url,
  documentTitle,
  targetPage,
  onClose,
  className,
  documentId,
  onChatOnDocument,
  isChatScoped,
}: PdfViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [pdf, setPdf] = useState<pdfjsLib.PDFDocumentProxy | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [scale, setScale] = useState(1.0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load PDF when URL changes
  useEffect(() => {
    if (!url) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    const loadPdf = async () => {
      try {
        console.log("[PdfViewer] Loading PDF from URL:", url?.substring(0, 100) + "...")
        const loadingTask = pdfjsLib.getDocument(url)
        const pdfDoc = await loadingTask.promise
        console.log("[PdfViewer] PDF loaded successfully, pages:", pdfDoc.numPages)
        setPdf(pdfDoc)
        setTotalPages(pdfDoc.numPages)
        setCurrentPage(targetPage || 1)
        setLoading(false)
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : String(err)
        console.error("[PdfViewer] Failed to load PDF:", errorMessage, err)
        setError(`Failed to load PDF: ${errorMessage}`)
        setLoading(false)
      }
    }

    loadPdf()
  }, [url, targetPage])

  // Navigate to target page when it changes
  useEffect(() => {
    if (targetPage && targetPage >= 1 && targetPage <= totalPages) {
      setCurrentPage(targetPage)
    }
  }, [targetPage, totalPages])

  // Render page when page number or scale changes
  const renderPage = useCallback(async () => {
    if (!pdf || !canvasRef.current) return

    try {
      const page = await pdf.getPage(currentPage)
      const canvas = canvasRef.current
      const context = canvas.getContext("2d")
      if (!context) return

      // Calculate scale to fit container width
      const containerWidth = containerRef.current?.clientWidth || 600
      const viewport = page.getViewport({ scale: 1 })
      const fitScale = (containerWidth - 32) / viewport.width
      const actualScale = scale * fitScale

      const scaledViewport = page.getViewport({ scale: actualScale })
      canvas.height = scaledViewport.height
      canvas.width = scaledViewport.width

      await page.render({
        canvasContext: context,
        viewport: scaledViewport,
      }).promise
    } catch (err) {
      console.error("Failed to render page:", err)
    }
  }, [pdf, currentPage, scale])

  useEffect(() => {
    renderPage()
  }, [renderPage])

  const goToPrevPage = () => {
    if (currentPage > 1) setCurrentPage(currentPage - 1)
  }

  const goToNextPage = () => {
    if (currentPage < totalPages) setCurrentPage(currentPage + 1)
  }

  const zoomIn = () => setScale((s) => Math.min(s + 0.25, 3))
  const zoomOut = () => setScale((s) => Math.max(s - 0.25, 0.5))

  if (!url) {
    return (
      <div className={cn("flex flex-col items-center justify-center h-full bg-muted/30 rounded-lg border", className)}>
        <FileText className="w-12 h-12 text-muted-foreground/50 mb-3" />
        <p className="text-sm text-muted-foreground">No document selected</p>
        <p className="text-xs text-muted-foreground mt-1">
          Select a document to view it here
        </p>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col h-full bg-background border rounded-lg overflow-hidden", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          <span className="text-sm font-medium truncate">
            {documentTitle || "Document"}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {!isChatScoped && documentId && onChatOnDocument && (
            <button
              onClick={onChatOnDocument}
              className="flex items-center gap-1 px-2 py-1 text-xs text-blue-700 bg-blue-50 hover:bg-blue-100 rounded transition-colors"
              title="Start a document-scoped chat"
            >
              <MessageSquare className="w-3 h-3" />
              <span className="hidden sm:inline">Chat on Doc</span>
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-muted rounded transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-4 bg-muted/10"
      >
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full text-red-500">
            <p className="text-sm">{error}</p>
          </div>
        ) : (
          <div className="flex justify-center">
            <canvas
              ref={canvasRef}
              className="shadow-lg rounded bg-white"
            />
          </div>
        )}
      </div>

      {/* Controls */}
      {!loading && !error && totalPages > 0 && (
        <div className="flex items-center justify-between px-3 py-2 border-t bg-muted/30">
          {/* Page Navigation */}
          <div className="flex items-center gap-2">
            <button
              onClick={goToPrevPage}
              disabled={currentPage <= 1}
              className="p-1.5 hover:bg-muted rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm tabular-nums">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={goToNextPage}
              disabled={currentPage >= totalPages}
              className="p-1.5 hover:bg-muted rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center gap-1">
            <button
              onClick={zoomOut}
              disabled={scale <= 0.5}
              className="p-1.5 hover:bg-muted rounded transition-colors disabled:opacity-50"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-xs tabular-nums w-12 text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={zoomIn}
              disabled={scale >= 3}
              className="p-1.5 hover:bg-muted rounded transition-colors disabled:opacity-50"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
