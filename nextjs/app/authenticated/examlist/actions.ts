"use server"

import { db } from "@/lib/prisma"
import { createClient } from "@/lib/supabase/server"

/**
 * Helper to get authenticated user from session
 * Returns null if not authenticated
 */
async function getAuthenticatedUser() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  return user
}

/**
 * Create a QuestionPaper record in Postgres.
 * Called BEFORE triggering the Python QP generation workflow.
 * The workflow will update status to READY when complete.
 *
 * SECURITY: userId is derived from session, not from client input
 */
export async function createQuestionPaper(data: {
  documentId: string
  duration: number
  numQuestions: number
  typeOfQp: string
  difficulty: string[]
  bloomLevel: string[]
  questionTypes: string[]
}) {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated" }
    }

    // Verify user owns the document
    const document = await db.document.findUnique({
      where: { id: data.documentId },
      select: { userId: true }
    })

    if (!document) {
      return { success: false, error: "Document not found" }
    }

    if (document.userId !== user.id) {
      return { success: false, error: "Unauthorized" }
    }

    const questionPaper = await db.questionPaper.create({
      data: {
        userId: user.id, // Use authenticated user ID
        documentId: data.documentId,
        duration: data.duration,
        numQuestions: data.numQuestions,
        typeOfQp: data.typeOfQp,
        difficulty: data.difficulty,
        bloomLevel: data.bloomLevel,
        questionTypes: data.questionTypes,
        status: "PENDING",
      }
    })

    return { success: true, questionPaper }
  } catch (error) {
    console.error("Failed to create question paper:", error)
    return { success: false, error: "Failed to create question paper" }
  }
}

/**
 * Update QuestionPaper status (e.g., to PROCESSING when workflow starts)
 *
 * SECURITY: Verifies user owns the question paper before updating
 */
export async function updateQuestionPaperStatus(
  qpId: string,
  status: "PENDING" | "PROCESSING" | "READY" | "FAILED"
) {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated" }
    }

    // Verify ownership
    const qp = await db.questionPaper.findUnique({
      where: { id: qpId },
      select: { userId: true }
    })

    if (!qp) {
      return { success: false, error: "Question paper not found" }
    }

    if (qp.userId !== user.id) {
      return { success: false, error: "Unauthorized" }
    }

    await db.questionPaper.update({
      where: { id: qpId },
      data: { status }
    })
    return { success: true }
  } catch (error) {
    console.error("Failed to update QP status:", error)
    return { success: false, error: "Failed to update status" }
  }
}

/**
 * Create an ExamSession linked to a QuestionPaper.
 * Status starts as SCHEDULED until user clicks "Start Exam".
 *
 * SECURITY: userId is derived from session, not from client input
 */
export async function createExamSession(data: {
  documentId: string
  questionPaperId: string
  threadId: string
  mode: "EXAM" | "LEARN"
}) {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated" }
    }

    // Verify user owns the document
    const document = await db.document.findUnique({
      where: { id: data.documentId },
      select: { userId: true }
    })

    if (!document) {
      return { success: false, error: "Document not found" }
    }

    if (document.userId !== user.id) {
      return { success: false, error: "Unauthorized" }
    }

    // Verify user owns the question paper
    const qp = await db.questionPaper.findUnique({
      where: { id: data.questionPaperId },
      select: { userId: true }
    })

    if (!qp) {
      return { success: false, error: "Question paper not found" }
    }

    if (qp.userId !== user.id) {
      return { success: false, error: "Unauthorized" }
    }

    const examSession = await db.examSession.create({
      data: {
        threadId: data.threadId,
        questionPaperId: data.questionPaperId,
        mode: data.mode,
        status: "SCHEDULED",
        userId: user.id, // Use authenticated user ID
        documentId: data.documentId,
      },
      include: {
        questionPaper: true,
        document: true,
      }
    })

    return { success: true, examSession }
  } catch (error) {
    console.error("Failed to create exam session:", error)
    return { success: false, error: "Failed to create exam session" }
  }
}

/**
 * Start an exam - update status to IN_PROGRESS and set startedAt
 *
 * SECURITY: Verifies user owns the session before starting
 */
export async function startExamSession(sessionId: string) {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated" }
    }

    // Verify ownership before updating
    const existingSession = await db.examSession.findUnique({
      where: { id: sessionId },
      select: { userId: true, status: true }
    })

    if (!existingSession) {
      return { success: false, error: "Session not found" }
    }

    if (existingSession.userId !== user.id) {
      return { success: false, error: "Unauthorized" }
    }

    if (existingSession.status !== "SCHEDULED") {
      return { success: false, error: `Session is ${existingSession.status}, cannot start` }
    }

    const session = await db.examSession.update({
      where: { id: sessionId },
      data: {
        status: "IN_PROGRESS",
        startedAt: new Date(),
      },
      include: {
        questionPaper: true,
        document: true,
      }
    })

    return { success: true, session }
  } catch (error) {
    console.error("Failed to start exam session:", error)
    return { success: false, error: "Failed to start exam" }
  }
}

/**
 * Get all exam sessions for the authenticated user
 *
 * SECURITY: userId is derived from session, not from client input
 */
export async function getExamSessions() {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated", sessions: [] }
    }

    const sessions = await db.examSession.findMany({
      where: { userId: user.id },
      orderBy: { createdAt: 'desc' },
      include: {
        document: true,
        questionPaper: true,
      }
    })

    return { success: true, sessions }
  } catch (error) {
    console.error("Failed to fetch exam sessions:", error)
    return { success: false, error: "Failed to fetch sessions", sessions: [] }
  }
}

/**
 * Get scheduled exams (created but not started)
 *
 * SECURITY: userId is derived from session, not from client input
 */
export async function getScheduledExams() {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated", sessions: [] }
    }

    const sessions = await db.examSession.findMany({
      where: {
        userId: user.id,
        status: "SCHEDULED"
      },
      orderBy: { createdAt: 'desc' },
      include: {
        document: true,
        questionPaper: true,
      }
    })

    return { success: true, sessions }
  } catch (error) {
    console.error("Failed to fetch scheduled exams:", error)
    return { success: false, error: "Failed to fetch exams", sessions: [] }
  }
}

/**
 * Get in-progress exams
 *
 * SECURITY: userId is derived from session, not from client input
 */
export async function getInProgressExams() {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated", sessions: [] }
    }

    const sessions = await db.examSession.findMany({
      where: {
        userId: user.id,
        status: "IN_PROGRESS"
      },
      orderBy: { startedAt: 'asc' },
      include: {
        document: true,
        questionPaper: true,
      }
    })

    return { success: true, sessions }
  } catch (error) {
    console.error("Failed to fetch in-progress exams:", error)
    return { success: false, error: "Failed to fetch exams", sessions: [] }
  }
}

/**
 * Get completed exams with reports
 *
 * SECURITY: userId is derived from session, not from client input
 */
export async function getCompletedExams() {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated", sessions: [] }
    }

    const sessions = await db.examSession.findMany({
      where: {
        userId: user.id,
        status: "COMPLETED"
      },
      orderBy: { endedAt: 'desc' },
      include: {
        document: true,
        questionPaper: true,
        report: true
      }
    })

    return { success: true, sessions }
  } catch (error) {
    console.error("Failed to fetch completed exams:", error)
    return { success: false, error: "Failed to fetch exams", sessions: [] }
  }
}

/**
 * Get user's documents for exam creation
 *
 * SECURITY: userId is derived from session, not from client input
 */
export async function getUserDocuments() {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated", documents: [] }
    }

    const documents = await db.document.findMany({
      where: {
        userId: user.id,
        status: "READY"  // Only show processed documents
      },
      orderBy: { createdAt: 'desc' }
    })

    return { success: true, documents }
  } catch (error) {
    console.error("Failed to fetch documents:", error)
    return { success: false, error: "Failed to fetch documents", documents: [] }
  }
}

/**
 * Get a single exam session by ID
 *
 * SECURITY: Verifies user owns the session before returning
 */
export async function getExamSession(sessionId: string) {
  try {
    const user = await getAuthenticatedUser()
    if (!user) {
      return { success: false, error: "Not authenticated" }
    }

    const session = await db.examSession.findUnique({
      where: { id: sessionId },
      include: {
        document: true,
        questionPaper: true,
        report: true,
      }
    })

    if (!session) {
      return { success: false, error: "Session not found" }
    }

    if (session.userId !== user.id) {
      return { success: false, error: "Unauthorized" }
    }

    return { success: true, session }
  } catch (error) {
    console.error("Failed to fetch exam session:", error)
    return { success: false, error: "Failed to fetch session" }
  }
}

// ============================================================
// Backward compatibility aliases (DEPRECATED)
// TODO: Remove these after updating examlist/page.tsx
// ============================================================

/** @deprecated Use createQuestionPaper + createExamSession instead */
export async function createMeeting(data: {
  title: string
  documentId: string
  duration: number
  numQuestions: number
  typeOfQp: string
  mode: string
}) {
  console.warn("createMeeting is deprecated - use createQuestionPaper + createExamSession")

  const user = await getAuthenticatedUser()
  if (!user) {
    return { success: false, error: "Not authenticated", meeting: null }
  }

  return {
    success: true,
    error: null as string | null,
    meeting: {
      id: `meeting_${Date.now()}`,
      threadId: `thread_${Date.now()}`,
      userId: user.id,
      ...data
    }
  }
}

/** @deprecated No longer needed */
export async function updateMeetingQpId(_meetingId: string, _qpId: string) {
  console.warn("updateMeetingQpId is deprecated")
  return { success: true }
}

/** @deprecated Use getScheduledExams or getInProgressExams instead */
export async function getUpcomingExams() {
  const scheduled = await getScheduledExams()
  const inProgress = await getInProgressExams()

  const allSessions = [
    ...(scheduled.sessions || []),
    ...(inProgress.sessions || [])
  ]

  const meetings = allSessions.map(session => ({
    id: session.id,
    title: session.document?.title || 'Untitled Exam',
    documentId: session.documentId,
    scheduledAt: session.startedAt || session.createdAt,
    status: session.status,
    mode: session.mode,
    qpStatus: session.questionPaper?.status,
  }))

  return {
    success: true,
    meetings,
    error: null
  }
}

/** @deprecated Use getCompletedExams instead */
export async function getPastExams() {
  const result = await getCompletedExams()
  const meetings = (result.sessions || []).map(session => ({
    id: session.id,
    title: session.document?.title || 'Untitled Exam',
    documentId: session.documentId,
    scheduledAt: session.endedAt || session.startedAt,
    status: session.status,
    mode: session.mode,
    score: session.report?.score,
  }))
  return {
    success: result.success,
    meetings,
    error: result.error
  }
}
