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
