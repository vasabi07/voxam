"use client"

import { useState, useEffect, useTransition, useMemo, useCallback, useRef } from "react"
import Link from "next/link"
import { CloudUpload, FileText, Trash2, CheckCircle2, Clock, AlertCircle, RefreshCw, RotateCcw, Search, X, ChevronRight, Archive, ArchiveRestore, Loader2, Volume2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { getDocuments, deleteDocument, retryDocument, archiveDocument, restoreDocument, getArchivedDocuments, createDocumentRecord } from "@/app/actions/document"
import { toast } from "sonner"
import { createClient } from "@/lib/supabase/client"
import { motion } from "motion/react"

type DocumentStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED"

type Document = {
  id: string
  title: string
  fileName: string | null
  fileSize: number | null
  mimeType: string | null
  status: DocumentStatus
  createdAt: Date
  pageCount: number | null
  archivedAt?: Date | null
}

type ViewMode = "active" | "archived"

function formatFileSize(bytes: number | null): string {
  if (!bytes) return "Unknown size"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(date: Date): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(date))
}

type StatusFilter = "ALL" | DocumentStatus

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [isPending, startTransition] = useTransition()
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL")
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [viewMode, setViewMode] = useState<ViewMode>("active")

  // Upload state
  const [uploadState, setUploadState] = useState<{
    status: "idle" | "uploading" | "processing"
    progress: number
    fileName: string | null
  }>({ status: "idle", progress: 0, fileName: null })
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Handle file upload with progress tracking
  const handleFileUpload = useCallback(async (file: File) => {
    if (!file) return

    // Validate file type
    const allowedTypes = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if (!allowedTypes.includes(file.type)) {
      toast.error("Invalid file type", { description: "Only PDF and DOCX files are accepted" })
      return
    }

    // Validate file size (50MB limit)
    if (file.size > 50 * 1024 * 1024) {
      toast.error("File too large", { description: "Maximum file size is 50MB" })
      return
    }

    setUploadState({ status: "uploading", progress: 0, fileName: file.name })

    try {
      // 1. Authenticate
      const supabase = createClient()
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        toast.error("Login required")
        setUploadState({ status: "idle", progress: 0, fileName: null })
        return
      }

      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        throw new Error("Not authenticated")
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

      // 2. Get presigned URL
      setUploadState(prev => ({ ...prev, progress: 10 }))
      const presignRes = await fetch(`${apiUrl}/upload/presign`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type
        }),
      })

      const presignData = await presignRes.json()
      if (!presignData.success) {
        throw new Error(presignData.error || "Failed to get upload URL")
      }

      const { upload_url, file_key: fileKey } = presignData

      // 3. Upload file with progress tracking using XMLHttpRequest
      setUploadState(prev => ({ ...prev, progress: 15 }))
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest()

        xhr.upload.addEventListener("progress", (event) => {
          if (event.lengthComputable) {
            // Map upload progress to 15-80% range
            const uploadPercent = 15 + Math.round((event.loaded / event.total) * 65)
            setUploadState(prev => ({ ...prev, progress: uploadPercent }))
          }
        })

        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve()
          } else {
            reject(new Error(`Upload failed: ${xhr.status}`))
          }
        })

        xhr.addEventListener("error", () => reject(new Error("Upload failed")))
        xhr.addEventListener("abort", () => reject(new Error("Upload aborted")))

        xhr.open("PUT", upload_url)
        xhr.setRequestHeader("Content-Type", file.type)
        xhr.send(file)
      })

      setUploadState(prev => ({ ...prev, progress: 85 }))
      toast.success("File uploaded!")

      // 4. Create DB Record
      const res = await createDocumentRecord({
        title: file.name,
        fileKey: fileKey,
        fileName: file.name,
        fileSize: file.size,
        mimeType: file.type,
        userId: user.id
      })

      if (!res.success || !res.docId) {
        throw new Error(res.error)
      }

      setUploadState(prev => ({ ...prev, progress: 90, status: "processing" }))

      // 5. Trigger Ingestion
      const ingestRes = await fetch(`${apiUrl}/ingest`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          file_key: fileKey,
          document_id: res.docId,
          page_count: 0 // Will be determined during processing
        }),
      })

      const ingestData = await ingestRes.json()
      if (ingestData.error) {
        toast.error(ingestData.error)
        setUploadState({ status: "idle", progress: 0, fileName: null })
        return
      }

      setUploadState(prev => ({ ...prev, progress: 100 }))
      toast.success("Document processing started", {
        description: "You'll be notified when it's ready."
      })

      // Reset upload state after brief delay
      setTimeout(() => {
        setUploadState({ status: "idle", progress: 0, fileName: null })
        fetchDocuments()
      }, 1500)

    } catch (e) {
      console.error(e)
      toast.error("Upload failed", {
        description: e instanceof Error ? e.message : "Unknown error"
      })
      setUploadState({ status: "idle", progress: 0, fileName: null })
    }
  }, [])

  // Handle drag and drop
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    const file = e.dataTransfer.files[0]
    if (file) handleFileUpload(file)
  }, [handleFileUpload])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  // Filter documents based on search query and status filter
  const filteredDocuments = useMemo(() => {
    return documents.filter(doc => {
      // Search filter - match title or filename
      const searchLower = searchQuery.toLowerCase().trim()
      const matchesSearch = searchLower === "" ||
        (doc.title?.toLowerCase().includes(searchLower)) ||
        (doc.fileName?.toLowerCase().includes(searchLower))

      // Status filter
      const matchesStatus = statusFilter === "ALL" || doc.status === statusFilter

      return matchesSearch && matchesStatus
    })
  }, [documents, searchQuery, statusFilter])

  // Count documents by status for filter badges
  const statusCounts = useMemo(() => {
    return {
      ALL: documents.length,
      READY: documents.filter(d => d.status === "READY").length,
      PROCESSING: documents.filter(d => d.status === "PROCESSING").length,
      PENDING: documents.filter(d => d.status === "PENDING").length,
      FAILED: documents.filter(d => d.status === "FAILED").length,
    }
  }, [documents])

  // Selection helpers
  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const selectAll = () => {
    setSelectedIds(new Set(filteredDocuments.map(d => d.id)))
  }

  const clearSelection = () => {
    setSelectedIds(new Set())
  }

  const isAllSelected = filteredDocuments.length > 0 && filteredDocuments.every(d => selectedIds.has(d.id))
  const hasSelection = selectedIds.size > 0

  // Batch delete handler
  const handleBatchDelete = async () => {
    const count = selectedIds.size
    if (!confirm(`Are you sure you want to delete ${count} document${count !== 1 ? "s" : ""}? This cannot be undone.`)) {
      return
    }

    startTransition(async () => {
      let successCount = 0
      let failCount = 0

      for (const id of selectedIds) {
        const result = await deleteDocument(id)
        if (result.success) {
          successCount++
        } else {
          failCount++
        }
      }

      // Update local state
      setDocuments(docs => docs.filter(doc => !selectedIds.has(doc.id)))
      setSelectedIds(new Set())

      if (failCount === 0) {
        toast.success(`Deleted ${successCount} document${successCount !== 1 ? "s" : ""}`)
      } else {
        toast.error(`Deleted ${successCount}, failed ${failCount}`)
      }
    })
  }

  // Fetch documents when viewMode changes
  useEffect(() => {
    fetchDocuments()
  }, [viewMode])

  // Set up realtime subscription for document status updates
  useEffect(() => {
    const supabase = createClient()

    const channel = supabase
      .channel("document-updates")
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "Document",
        },
        (payload) => {
          const newDoc = payload.new as { id: string; title: string; status: string }
          const oldDoc = payload.old as { status?: string }

          // Show toast for status transitions
          if (newDoc.status === "READY" && oldDoc?.status === "PROCESSING") {
            toast.success(`"${newDoc.title || 'Document'}" is ready!`, {
              action: {
                label: "Open",
                onClick: () => window.location.href = `/authenticated/documents/${newDoc.id}`
              }
            })
          } else if (newDoc.status === "FAILED" && oldDoc?.status === "PROCESSING") {
            toast.error(`"${newDoc.title || 'Document'}" failed to process`, {
              description: "Click retry to try again."
            })
          }

          // Refetch documents
          fetchDocuments()
        }
      )
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "Document",
        },
        () => {
          fetchDocuments()
        }
      )
      .on(
        "postgres_changes",
        {
          event: "DELETE",
          schema: "public",
          table: "Document",
        },
        () => {
          fetchDocuments()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  async function fetchDocuments() {
    setLoading(true)
    setSelectedIds(new Set()) // Clear selection when switching views
    const result = viewMode === "active"
      ? await getDocuments()
      : await getArchivedDocuments()
    if (result.success) {
      setDocuments(result.documents as Document[])
    } else {
      toast.error(result.error || "Failed to load documents")
    }
    setLoading(false)
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"? This cannot be undone.`)) {
      return
    }

    startTransition(async () => {
      const result = await deleteDocument(id)
      if (result.success) {
        setDocuments(documents.filter(doc => doc.id !== id))
        toast.success("Document deleted")
      } else {
        toast.error(result.error || "Failed to delete document")
      }
    })
  }

  const handleRetry = async (id: string, name: string) => {
    startTransition(async () => {
      const result = await retryDocument(id)
      if (result.success) {
        toast.success(`Retrying "${name}"`, {
          description: "Document processing has been restarted."
        })
        // Update local state to show processing
        setDocuments(docs =>
          docs.map(doc =>
            doc.id === id ? { ...doc, status: "PROCESSING" as DocumentStatus } : doc
          )
        )
      } else {
        toast.error(result.error || "Failed to retry document")
      }
    })
  }

  const handleArchive = async (id: string, name: string) => {
    startTransition(async () => {
      const result = await archiveDocument(id)
      if (result.success) {
        setDocuments(docs => docs.filter(doc => doc.id !== id))
        toast.success(`"${name}" moved to archive`)
      } else {
        toast.error(result.error || "Failed to archive document")
      }
    })
  }

  const handleRestore = async (id: string, name: string) => {
    startTransition(async () => {
      const result = await restoreDocument(id)
      if (result.success) {
        setDocuments(docs => docs.filter(doc => doc.id !== id))
        toast.success(`"${name}" restored`)
      } else {
        toast.error(result.error || "Failed to restore document")
      }
    })
  }

  // Batch archive handler
  const handleBatchArchive = async () => {
    const count = selectedIds.size
    startTransition(async () => {
      let successCount = 0
      for (const id of selectedIds) {
        const result = await archiveDocument(id)
        if (result.success) successCount++
      }
      setDocuments(docs => docs.filter(doc => !selectedIds.has(doc.id)))
      setSelectedIds(new Set())
      toast.success(`Archived ${successCount} document${successCount !== 1 ? "s" : ""}`)
    })
  }

  const getStatusDisplay = (status: DocumentStatus) => {
    switch (status) {
      case "READY":
        return { label: "Ready", icon: CheckCircle2, className: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" }
      case "PROCESSING":
        return { label: "Processing", icon: Clock, className: "bg-amber-500/10 text-amber-400 border border-amber-500/20" }
      case "PENDING":
        return { label: "Pending", icon: Clock, className: "bg-accent/10 text-accent border border-accent/20" }
      case "FAILED":
        return { label: "Failed", icon: AlertCircle, className: "bg-destructive/10 text-destructive border border-destructive/20" }
      default:
        return { label: status, icon: Clock, className: "bg-muted text-muted-foreground border border-border" }
    }
  }

  return (
    <div className="relative min-h-screen bg-background">
      {/* Floating Orbs Background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute w-[500px] h-[500px] rounded-full bg-primary/10 blur-[120px]"
          style={{ top: "10%", left: "20%" }}
          animate={{ y: [-20, 20, -20], x: [-10, 10, -10] }}
          transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute w-[400px] h-[400px] rounded-full bg-accent/10 blur-[100px]"
          style={{ bottom: "20%", right: "15%" }}
          animate={{ y: [20, -20, 20], x: [10, -10, 10] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 2 }}
        />
      </div>

      <div className="flex flex-col gap-10 p-6 md:p-10 max-w-5xl mx-auto">

        {/* Header Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-3"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-primary/40 blur-xl" />
                <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
                  <Volume2 className="h-6 w-6" />
                </div>
              </div>
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-foreground">
                  Study Materials
                </h1>
                <p className="text-muted-foreground">
                  Upload notes to generate voice exams
                </p>
              </div>
            </div>
            <button
              onClick={() => fetchDocuments()}
              className="p-2.5 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-xl transition-all"
              aria-label="Refresh documents"
            >
              <RefreshCw className={cn("w-5 h-5", loading && "animate-spin")} />
            </button>
          </div>

          {/* View Mode Tabs */}
          <div className="flex gap-1 mt-2 p-1 bg-secondary/50 rounded-xl w-fit backdrop-blur-sm border border-border/50">
            <button
              onClick={() => setViewMode("active")}
              className={cn(
                "px-5 py-2.5 text-sm font-medium rounded-lg transition-all",
                viewMode === "active"
                  ? "bg-card text-foreground shadow-lg"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              Active
            </button>
            <button
              onClick={() => setViewMode("archived")}
              className={cn(
                "px-5 py-2.5 text-sm font-medium rounded-lg transition-all flex items-center gap-2",
                viewMode === "archived"
                  ? "bg-card text-foreground shadow-lg"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Archive className="w-4 h-4" />
              Archived
            </button>
          </div>
        </motion.div>

        {/* Upload Zone - Only show for active view */}
        {viewMode === "active" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleFileUpload(file)
                e.target.value = ""
              }}
              className="hidden"
            />
            <div
              onClick={() => uploadState.status === "idle" && fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className={cn(
                "group relative flex flex-col items-center justify-center w-full h-56 rounded-2xl border-2 border-dashed transition-all overflow-hidden",
                uploadState.status === "idle"
                  ? "bg-card/50 border-border hover:border-primary/50 hover:bg-card/80 cursor-pointer"
                  : "bg-card/80 border-primary/50 cursor-default"
              )}
            >
              {/* Gradient shimmer on hover */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
              </div>

              {uploadState.status === "idle" ? (
                <div className="relative flex flex-col items-center gap-5 text-center p-6">
                  <div className="relative">
                    <div className="absolute inset-0 bg-primary/30 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative p-4 rounded-2xl bg-secondary group-hover:bg-primary/20 transition-colors">
                      <CloudUpload className="w-8 h-8 text-primary" />
                    </div>
                  </div>
                  <div className="flex flex-col gap-1">
                    <p className="text-lg font-semibold text-foreground">
                      Drop your study materials
                    </p>
                    <p className="text-muted-foreground text-sm">
                      PDF or DOCX up to 50MB
                    </p>
                  </div>
                  <div className="px-5 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium border border-primary/20 group-hover:bg-primary group-hover:text-primary-foreground transition-all">
                    Browse files
                  </div>
                </div>
              ) : (
                <div className="relative flex flex-col items-center gap-5 text-center p-6 w-full max-w-sm">
                  <div className="p-4 rounded-2xl bg-primary/20">
                    <Loader2 className="w-8 h-8 text-primary animate-spin" />
                  </div>
                  <div className="flex flex-col gap-1 w-full">
                    <p className="text-foreground font-semibold truncate">
                      {uploadState.fileName}
                    </p>
                    <p className="text-muted-foreground text-sm">
                      {uploadState.status === "uploading" ? "Uploading..." : "Processing..."}
                    </p>
                  </div>
                  <div className="w-full space-y-2">
                    <div className="relative h-2 bg-secondary rounded-full overflow-hidden">
                      <motion.div
                        className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary to-accent rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${uploadState.progress}%` }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground text-center">
                      {uploadState.progress}% complete
                    </p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Document List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col gap-5"
        >
          <div className="flex flex-col gap-4">
            <h2 className="text-xl font-semibold text-foreground">
              {viewMode === "active" ? "Your Binder" : "Archived Documents"}
            </h2>

            {/* Search and Filters */}
            <div className="flex flex-col sm:flex-row gap-3">
              {/* Search Input */}
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search documents..."
                  className="w-full pl-11 pr-10 py-3 text-sm border border-border rounded-xl bg-card/50 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Status Filter Chips */}
              <div className="flex gap-2 overflow-x-auto pb-1">
                {(["ALL", "READY", "PROCESSING", "FAILED"] as StatusFilter[]).map((status) => {
                  const isActive = statusFilter === status
                  const count = statusCounts[status]
                  const labels: Record<StatusFilter, string> = {
                    ALL: "All",
                    READY: "Ready",
                    PROCESSING: "Processing",
                    PENDING: "Pending",
                    FAILED: "Failed",
                  }

                  // Skip showing filter if count is 0 (except ALL)
                  if (status !== "ALL" && count === 0) return null

                  return (
                    <button
                      key={status}
                      onClick={() => setStatusFilter(status)}
                      className={cn(
                        "px-4 py-2 rounded-xl text-xs font-medium flex items-center gap-2 transition-all whitespace-nowrap border",
                        isActive
                          ? "bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/20"
                          : "bg-card/50 text-muted-foreground border-border hover:border-primary/30 hover:text-foreground"
                      )}
                    >
                      <span>{labels[status]}</span>
                      <span className={cn(
                        "px-1.5 py-0.5 rounded-md text-[10px]",
                        isActive ? "bg-primary-foreground/20" : "bg-secondary"
                      )}>
                        {count}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Selection Toolbar */}
          {hasSelection && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-between p-4 bg-primary/10 rounded-xl border border-primary/20"
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-primary">
                  {selectedIds.size} selected
                </span>
                <button
                  onClick={clearSelection}
                  className="text-sm text-primary/70 hover:text-primary underline underline-offset-2"
                >
                  Clear
                </button>
              </div>
              <div className="flex items-center gap-2">
                {viewMode === "active" && (
                  <button
                    onClick={handleBatchArchive}
                    disabled={isPending}
                    className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 text-foreground text-sm font-medium rounded-xl transition-colors disabled:opacity-50"
                  >
                    <Archive className="w-4 h-4" />
                    Archive
                  </button>
                )}
                <button
                  onClick={handleBatchDelete}
                  disabled={isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-destructive/10 hover:bg-destructive/20 text-destructive text-sm font-medium rounded-xl transition-colors disabled:opacity-50 border border-destructive/20"
                >
                  <Trash2 className="w-4 h-4" />
                  {viewMode === "archived" ? "Delete" : "Delete"}
                </button>
              </div>
            </motion.div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="relative">
                <div className="absolute inset-0 bg-primary/30 blur-2xl" />
                <RefreshCw className="relative w-8 h-8 text-primary animate-spin" />
              </div>
              <span className="mt-4 text-muted-foreground">Loading documents...</span>
            </div>
          ) : documents.length > 0 ? (
            filteredDocuments.length > 0 ? (
              <div className="flex flex-col gap-3">
                {/* Select All Header */}
                {filteredDocuments.length > 1 && (
                  <div className="flex items-center gap-3 px-4 py-2">
                    <input
                      type="checkbox"
                      checked={isAllSelected}
                      onChange={() => isAllSelected ? clearSelection() : selectAll()}
                      className="w-4 h-4 rounded border-border bg-card text-primary focus:ring-primary/50 cursor-pointer accent-primary"
                    />
                    <span className="text-sm text-muted-foreground">
                      {isAllSelected ? "Deselect all" : "Select all"}
                    </span>
                  </div>
                )}
                {filteredDocuments.map((doc, index) => {
                  const status = getStatusDisplay(doc.status)
                  const StatusIcon = status.icon
                  const isSelected = selectedIds.has(doc.id)

                  return (
                    <motion.div
                      key={doc.id}
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className={cn(
                        "group flex items-center p-4 rounded-xl border transition-all",
                        isSelected
                          ? "border-primary/40 bg-primary/5"
                          : "border-border bg-card/50 hover:bg-card hover:border-border/80"
                      )}
                    >
                      {/* Checkbox */}
                      <div className="mr-4">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(doc.id)}
                          onClick={(e) => e.stopPropagation()}
                          className="w-4 h-4 rounded border-border bg-card text-primary focus:ring-primary/50 cursor-pointer accent-primary"
                        />
                      </div>

                      <Link
                        href={`/authenticated/documents/${doc.id}`}
                        className="flex items-center gap-4 flex-1 min-w-0"
                      >
                        {/* Icon */}
                        <div className="relative shrink-0">
                          <div className="absolute inset-0 bg-primary/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
                          <div className="relative flex items-center justify-center w-12 h-12 rounded-xl bg-secondary text-primary">
                            <FileText className="w-5 h-5" />
                          </div>
                        </div>

                        {/* Info */}
                        <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                          <p className="text-foreground font-medium truncate">
                            {doc.title || doc.fileName || "Untitled Document"}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span>{formatFileSize(doc.fileSize)}</span>
                            <span className="text-border">•</span>
                            <span>{formatDate(doc.createdAt)}</span>
                            {doc.pageCount && (
                              <>
                                <span className="text-border">•</span>
                                <span>{doc.pageCount} pages</span>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Chevron */}
                        <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 transition-all shrink-0" />
                      </Link>

                      {/* Status & Actions */}
                      <div className="flex items-center gap-3 ml-4">
                        {/* Status Badge */}
                        <div className={cn(
                          "px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5",
                          status.className
                        )}>
                          <StatusIcon className={cn("w-3.5 h-3.5", doc.status === "PROCESSING" && "animate-pulse")} />
                          <span>{status.label}</span>
                        </div>

                        {/* Retry Action */}
                        {viewMode === "active" && doc.status === "FAILED" && (
                          <button
                            onClick={() => handleRetry(doc.id, doc.title || doc.fileName || "document")}
                            disabled={isPending}
                            className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition-all opacity-0 group-hover:opacity-100 focus:opacity-100 disabled:opacity-50"
                            aria-label="Retry processing"
                          >
                            <RotateCcw className="w-4 h-4" />
                          </button>
                        )}

                        {/* Archive Action */}
                        {viewMode === "active" && (
                          <button
                            onClick={() => handleArchive(doc.id, doc.title || doc.fileName || "document")}
                            disabled={isPending}
                            className="p-2 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-all opacity-0 group-hover:opacity-100 focus:opacity-100 disabled:opacity-50"
                            aria-label="Archive document"
                          >
                            <Archive className="w-4 h-4" />
                          </button>
                        )}

                        {/* Restore Action */}
                        {viewMode === "archived" && (
                          <button
                            onClick={() => handleRestore(doc.id, doc.title || doc.fileName || "document")}
                            disabled={isPending}
                            className="p-2 text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-all opacity-0 group-hover:opacity-100 focus:opacity-100 disabled:opacity-50"
                            aria-label="Restore document"
                          >
                            <ArchiveRestore className="w-4 h-4" />
                          </button>
                        )}

                        {/* Delete Action */}
                        <button
                          onClick={() => handleDelete(doc.id, doc.title || doc.fileName || "document")}
                          disabled={isPending}
                          className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-all opacity-0 group-hover:opacity-100 focus:opacity-100 disabled:opacity-50"
                          aria-label="Delete document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            ) : (
              /* No Results State */
              <div className="flex flex-col items-center justify-center py-20 text-center bg-card/30 rounded-2xl border border-border">
                <div className="p-5 rounded-2xl bg-secondary mb-4">
                  <Search className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="text-foreground font-semibold text-lg">No documents found</h3>
                <p className="text-muted-foreground text-sm mt-1">
                  Try adjusting your search or filters.
                </p>
                <button
                  onClick={() => { setSearchQuery(""); setStatusFilter("ALL") }}
                  className="mt-5 px-5 py-2.5 text-sm font-medium bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 transition-colors"
                >
                  Clear filters
                </button>
              </div>
            )
          ) : (
            /* Empty State */
            <div className="flex flex-col items-center justify-center py-20 text-center bg-card/20 rounded-2xl border-2 border-dashed border-border">
              <div className="relative mb-4">
                <div className="absolute inset-0 bg-primary/20 blur-2xl" />
                <div className="relative p-5 rounded-2xl bg-secondary">
                  {viewMode === "active" ? (
                    <FileText className="w-10 h-10 text-muted-foreground" />
                  ) : (
                    <Archive className="w-10 h-10 text-muted-foreground" />
                  )}
                </div>
              </div>
              <h3 className="text-foreground font-semibold text-lg">
                {viewMode === "active" ? "Your library is empty" : "No archived documents"}
              </h3>
              <p className="text-muted-foreground text-sm mt-1 max-w-xs">
                {viewMode === "active"
                  ? "Upload your study materials to start generating voice exams."
                  : "Documents you archive will appear here."}
              </p>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
