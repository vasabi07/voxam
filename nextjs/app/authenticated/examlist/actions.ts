"use server"

import { db } from "@/lib/prisma"

export async function createExamSession(data: {
  title: string
  userId: string
  documentId: string
  duration: number
  numQuestions: number
  typeOfQp: string
  mode: "EXAM" | "LEARN"
  threadId: string
  qpId: string
}) {
  try {
    const examSession = await db.examSession.create({
      data: {
        threadId: data.threadId,
        qpId: data.qpId,
        mode: data.mode,
        status: "IN_PROGRESS",
        duration: data.duration,
        numQuestions: data.numQuestions,
        typeOfQp: data.typeOfQp,
        userId: data.userId,
        documentId: data.documentId,
      }
    })

    return { success: true, examSession }
  } catch (error) {
    console.error("Failed to create exam session:", error)
    return { success: false, error: "Failed to create exam session" }
  }
}

export async function getExamSessions(userId: string) {
  try {
    const sessions = await db.examSession.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
      include: { document: true }
    })

    return { success: true, sessions }
  } catch (error) {
    console.error("Failed to fetch exam sessions:", error)
    return { success: false, error: "Failed to fetch sessions", sessions: [] }
  }
}

export async function getInProgressExams(userId: string) {
  try {
    const sessions = await db.examSession.findMany({
      where: {
        userId,
        status: "IN_PROGRESS"
      },
      orderBy: { startedAt: 'asc' },
      include: { document: true }
    })

    return { success: true, sessions }
  } catch (error) {
    console.error("Failed to fetch in-progress exams:", error)
    return { success: false, error: "Failed to fetch exams", sessions: [] }
  }
}

export async function getCompletedExams(userId: string) {
  try {
    const sessions = await db.examSession.findMany({
      where: {
        userId,
        status: "COMPLETED"
      },
      orderBy: { endedAt: 'desc' },
      include: {
        document: true,
        report: true
      }
    })

    return { success: true, sessions }
  } catch (error) {
    console.error("Failed to fetch completed exams:", error)
    return { success: false, error: "Failed to fetch exams", sessions: [] }
  }
}

export async function getUserDocuments(userId: string) {
  try {
    const documents = await db.document.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' }
    })

    return { success: true, documents }
  } catch (error) {
    console.error("Failed to fetch documents:", error)
    return { success: false, error: "Failed to fetch documents", documents: [] }
  }
}

// Backward compatibility aliases for page.tsx
// TODO: Update page.tsx to use new function names and remove these

export async function createMeeting(data: {
  title: string
  userId: string
  documentId: string
  duration: number
  numQuestions: number
  typeOfQp: string
  mode: string
}) {
  // For now, return a mock meeting - this page needs to be refactored
  // to use the new exam session flow
  console.warn("createMeeting is deprecated - use createExamSession instead")
  return {
    success: true,
    error: null as string | null,
    meeting: {
      id: `meeting_${Date.now()}`,
      threadId: `thread_${Date.now()}`,
      ...data
    }
  }
}

export async function updateMeetingQpId(_meetingId: string, _qpId: string) {
  console.warn("updateMeetingQpId is deprecated")
  return { success: true }
}

export async function getUpcomingExams(userId: string) {
  // Map to new function but return in old format
  const result = await getInProgressExams(userId)
  const meetings = (result.sessions || []).map(session => ({
    id: session.id,
    title: session.document?.title || 'Untitled Exam',
    documentId: session.documentId,
    scheduledAt: session.startedAt,
    status: session.status,
    mode: session.mode,
  }))
  return {
    success: result.success,
    meetings,
    error: result.error
  }
}

export async function getPastExams(userId: string) {
  // Map to new function but return in old format
  const result = await getCompletedExams(userId)
  const meetings = (result.sessions || []).map(session => ({
    id: session.id,
    title: session.document?.title || 'Untitled Exam',
    documentId: session.documentId,
    scheduledAt: session.endedAt || session.startedAt,
    status: session.status,
    mode: session.mode,
  }))
  return {
    success: result.success,
    meetings,
    error: result.error
  }
}
