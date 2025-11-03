"use server"

import { db } from "@/lib/prisma"

export async function createMeeting(data: {
  title: string
  userId: string
  documentId: string
  duration: number
  numQuestions: number
  typeOfQp: string
  mode: string
}) {
  try {
    const meeting = await db.meeting.create({
      data: {
        title: data.title,
        userId: data.userId,
        documentId: data.documentId,
        duration: data.duration,
        numQuestions: data.numQuestions,
        typeOfQp: data.typeOfQp,
        mode: data.mode,
        scheduledAt: new Date(),
        status: "SCHEDULED"
      }
    })

    return { success: true, meeting }
  } catch (error) {
    console.error("Failed to create meeting:", error)
    return { success: false, error: "Failed to create meeting" }
  }
}

export async function updateMeetingQpId(meetingId: string, qpId: string) {
  try {
    await db.meeting.update({
      where: { id: meetingId },
      data: { qpId }
    })

    return { success: true }
  } catch (error) {
    console.error("Failed to update meeting:", error)
    return { success: false, error: "Failed to update meeting" }
  }
}

export async function getMeetings(userId: string) {
  try {
    const meetings = await db.meeting.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' }
    })

    return { success: true, meetings }
  } catch (error) {
    console.error("Failed to fetch meetings:", error)
    return { success: false, error: "Failed to fetch meetings", meetings: [] }
  }
}

export async function getUpcomingExams(userId: string) {
  try {
    const meetings = await db.meeting.findMany({
      where: { 
        userId,
        status: "SCHEDULED"
      },
      orderBy: { scheduledAt: 'asc' }
    })

    return { success: true, meetings }
  } catch (error) {
    console.error("Failed to fetch upcoming exams:", error)
    return { success: false, error: "Failed to fetch upcoming exams", meetings: [] }
  }
}

export async function getPastExams(userId: string) {
  try {
    const meetings = await db.meeting.findMany({
      where: { 
        userId,
        status: "COMPLETED"
      },
      orderBy: { scheduledAt: 'desc' }
    })

    return { success: true, meetings }
  } catch (error) {
    console.error("Failed to fetch past exams:", error)
    return { success: false, error: "Failed to fetch past exams", meetings: [] }
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
