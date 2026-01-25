"use client"

import { useState, useEffect, useTransition } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import {
  FileText,
  ArrowLeft,
  Clock,
  CheckCircle2,
  AlertCircle,
  Trash2,
  RotateCcw,
  Calendar,
  HardDrive,
  FileStack,
  GraduationCap,
  MessageSquare,
  PlayCircle,
  BookOpen,
  Trophy,
  ChevronRight,
  Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { getDocumentDetails, deleteDocument, retryDocument } from "@/app/actions/document"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

type DocumentStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED"
type ExamStatus = "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "ABANDONED"
type QPStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED"

type DocumentDetails = {
  id: string
  title: string
  fileName: string | null
  fileSize: number | null
  mimeType: string | null
  status: DocumentStatus
  createdAt: Date
  pageCount: number | null
  questionPapers: {
    id: string
    status: QPStatus
    duration: number
    numQuestions: number
    difficulty: string[]
    questionTypes: string[]
    createdAt: Date
  }[]
  examSessions: {
    id: string
    mode: string
    status: ExamStatus
    startedAt: Date | null
    endedAt: Date | null
    createdAt: Date
    questionPaper: {
      id: string
      numQuestions: number
      duration: number
    }
    report: {
      id: string
      score: number
      grade: string
    } | null
  }[]
  learnSessions: {
    id: string
    title: string
    status: string
    topicsCompleted: number
    topicsPlanned: number
    overallUnderstanding: number
    createdAt: Date
    completedAt: Date | null
  }[]
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return "Unknown"
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

function formatDateTime(date: Date): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(date))
}

export default function DocumentDetailsPage() {
  const params = useParams()
  const router = useRouter()
  const documentId = params.id as string

  const [document, setDocument] = useState<DocumentDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [isPending, startTransition] = useTransition()

  useEffect(() => {
    fetchDocument()
  }, [documentId])

  async function fetchDocument() {
    setLoading(true)
    const result = await getDocumentDetails(documentId)
    if (result.success && result.document) {
      setDocument(result.document as DocumentDetails)
    } else {
      toast.error(result.error || "Document not found")
      router.push("/authenticated/documents")
    }
    setLoading(false)
  }

  const handleDelete = async () => {
    if (!document) return
    if (!confirm(`Are you sure you want to delete "${document.title}"? This cannot be undone.`)) {
      return
    }

    startTransition(async () => {
      const result = await deleteDocument(documentId)
      if (result.success) {
        toast.success("Document deleted")
        router.push("/authenticated/documents")
      } else {
        toast.error(result.error || "Failed to delete document")
      }
    })
  }

  const handleRetry = async () => {
    if (!document) return
    startTransition(async () => {
      const result = await retryDocument(documentId)
      if (result.success) {
        toast.success("Retrying document processing")
        fetchDocument()
      } else {
        toast.error(result.error || "Failed to retry")
      }
    })
  }

  const getStatusDisplay = (status: DocumentStatus) => {
    switch (status) {
      case "READY":
        return { label: "Ready", icon: CheckCircle2, className: "bg-green-50 text-green-700 border-green-200" }
      case "PROCESSING":
        return { label: "Processing", icon: Clock, className: "bg-yellow-50 text-yellow-700 border-yellow-200" }
      case "PENDING":
        return { label: "Pending", icon: Clock, className: "bg-blue-50 text-blue-700 border-blue-200" }
      case "FAILED":
        return { label: "Failed", icon: AlertCircle, className: "bg-red-50 text-red-700 border-red-200" }
      default:
        return { label: status, icon: Clock, className: "bg-gray-50 text-gray-700 border-gray-200" }
    }
  }

  const getExamStatusBadge = (status: ExamStatus) => {
    switch (status) {
      case "COMPLETED":
        return <Badge variant="default" className="bg-green-100 text-green-700">Completed</Badge>
      case "IN_PROGRESS":
        return <Badge variant="default" className="bg-yellow-100 text-yellow-700">In Progress</Badge>
      case "ABANDONED":
        return <Badge variant="default" className="bg-gray-100 text-gray-600">Abandoned</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  if (!document) {
    return null
  }

  const status = getStatusDisplay(document.status)
  const StatusIcon = status.icon
  const isReady = document.status === "READY"
  const readyQPs = document.questionPapers.filter(qp => qp.status === "READY")

  return (
    <div className="flex flex-col gap-6 p-6 md:p-10 max-w-5xl mx-auto">
      {/* Back Button */}
      <Link
        href="/authenticated/documents"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Documents
      </Link>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex items-center justify-center w-14 h-14 rounded-xl bg-blue-50 text-blue-600">
            <FileText className="w-7 h-7" />
          </div>
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-bold text-foreground">{document.title}</h1>
            <p className="text-sm text-muted-foreground">{document.fileName}</p>
            <div className={cn(
              "mt-2 px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 w-fit border",
              status.className
            )}>
              <StatusIcon className={cn("w-3.5 h-3.5", document.status === "PROCESSING" && "animate-pulse")} />
              <span>{status.label}</span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {document.status === "FAILED" && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              disabled={isPending}
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleDelete}
            disabled={isPending}
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Metadata Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <HardDrive className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">File Size</p>
                <p className="font-medium">{formatFileSize(document.fileSize)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <FileStack className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Pages</p>
                <p className="font-medium">{document.pageCount || "—"}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Uploaded</p>
                <p className="font-medium">{formatDate(document.createdAt)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Exams Taken</p>
                <p className="font-medium">{document.examSessions.filter(e => e.status === "COMPLETED").length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      {isReady && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              <Link href={`/authenticated/examlist?doc=${documentId}`}>
                <Button className="bg-primary hover:bg-primary/90">
                  <PlayCircle className="w-4 h-4 mr-2" />
                  Start Exam
                </Button>
              </Link>
              <Link href={`/authenticated/learn?doc=${documentId}`}>
                <Button variant="outline">
                  <BookOpen className="w-4 h-4 mr-2" />
                  Learn Mode
                </Button>
              </Link>
              <Link href={`/authenticated/chat?doc=${documentId}`}>
                <Button variant="outline">
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Chat
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Processing Status */}
      {!isReady && (
        <Card className="border-yellow-200 bg-yellow-50/50">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              {document.status === "PROCESSING" ? (
                <>
                  <Loader2 className="w-8 h-8 text-yellow-600 animate-spin" />
                  <div>
                    <p className="font-medium text-yellow-900">Processing Document</p>
                    <p className="text-sm text-yellow-700">
                      Your document is being analyzed. This may take a few minutes.
                    </p>
                  </div>
                </>
              ) : document.status === "FAILED" ? (
                <>
                  <AlertCircle className="w-8 h-8 text-red-600" />
                  <div>
                    <p className="font-medium text-red-900">Processing Failed</p>
                    <p className="text-sm text-red-700">
                      There was an error processing your document. Click retry to try again.
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <Clock className="w-8 h-8 text-blue-600" />
                  <div>
                    <p className="font-medium text-blue-900">Pending Processing</p>
                    <p className="text-sm text-blue-700">
                      Your document is queued for processing.
                    </p>
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Question Papers */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Question Papers
          </CardTitle>
          <CardDescription>
            {readyQPs.length} generated question paper{readyQPs.length !== 1 ? "s" : ""}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {document.questionPapers.length > 0 ? (
            <div className="space-y-3">
              {document.questionPapers.map((qp) => (
                <div
                  key={qp.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <FileText className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">
                        {qp.numQuestions} Questions - {qp.duration} min
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {qp.difficulty.join(", ")} | {formatDate(qp.createdAt)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={qp.status === "READY" ? "default" : "secondary"}>
                      {qp.status}
                    </Badge>
                    {qp.status === "READY" && (
                      <Link href={`/authenticated/examlist?qp=${qp.id}`}>
                        <Button variant="ghost" size="sm">
                          <ChevronRight className="w-4 h-4" />
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No question papers generated yet</p>
              {isReady && (
                <Link href={`/authenticated/examlist?doc=${documentId}`}>
                  <Button variant="link" size="sm" className="mt-2">
                    Generate your first QP
                  </Button>
                </Link>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Exam History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Trophy className="w-5 h-5" />
            Exam History
          </CardTitle>
          <CardDescription>
            {document.examSessions.filter(e => e.status === "COMPLETED").length} completed exam{document.examSessions.filter(e => e.status === "COMPLETED").length !== 1 ? "s" : ""}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {document.examSessions.length > 0 ? (
            <div className="space-y-3">
              {document.examSessions.map((exam) => (
                <div
                  key={exam.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "w-10 h-10 rounded-full flex items-center justify-center",
                      exam.report ? "bg-green-100" : "bg-gray-100"
                    )}>
                      {exam.report ? (
                        <span className="text-lg font-bold text-green-700">{exam.report.grade}</span>
                      ) : (
                        <GraduationCap className="w-5 h-5 text-gray-500" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-sm">
                        {exam.mode === "EXAM" ? "Formal Exam" : "Learn Mode"} - {exam.questionPaper.numQuestions} Q
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {exam.startedAt ? formatDateTime(exam.startedAt) : formatDateTime(exam.createdAt)}
                        {exam.report && ` - Score: ${exam.report.score}%`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {getExamStatusBadge(exam.status)}
                    {exam.report && (
                      <Link href={`/authenticated/exam/results/${exam.id}`}>
                        <Button variant="ghost" size="sm">
                          <ChevronRight className="w-4 h-4" />
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <GraduationCap className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No exams taken yet</p>
              {isReady && (
                <Link href={`/authenticated/examlist?doc=${documentId}`}>
                  <Button variant="link" size="sm" className="mt-2">
                    Take your first exam
                  </Button>
                </Link>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Learn Sessions */}
      {document.learnSessions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              Learn Sessions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {document.learnSessions.map((session) => (
                <div
                  key={session.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <BookOpen className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{session.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {session.topicsCompleted}/{session.topicsPlanned} topics | {session.overallUnderstanding}% understanding
                      </p>
                    </div>
                  </div>
                  <Badge variant={session.status === "COMPLETED" ? "default" : "secondary"}>
                    {session.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
