"use server"

import { db } from "@/lib/prisma"
import { createClient } from "@/lib/supabase/server"

/**
 * Get the correction report for an exam session
 */
export async function getExamReport(sessionId: string) {
    try {
        const report = await db.correctionReport.findUnique({
            where: { examSessionId: sessionId },
            include: {
                examSession: {
                    include: {
                        document: true,
                        questionPaper: true,
                    }
                }
            }
        })

        if (!report) {
            return { success: false, error: "Report not found" }
        }

        return { success: true, report }
    } catch (error) {
        console.error("Failed to fetch exam report:", error)
        return { success: false, error: "Failed to fetch report" }
    }
}

/**
 * End an exam and trigger correction
 */
export async function endExamSession(data: {
    sessionId: string
    threadId: string
    qpId: string
    // userId removed - now comes from authenticated session
}) {
    try {
        // Get auth token from session
        const supabase = await createClient()
        const { data: { session } } = await supabase.auth.getSession()

        if (!session?.access_token) {
            return { success: false, error: "Not authenticated" }
        }

        // Call the Python API to generate correction
        const response = await fetch('http://localhost:8000/end-exam', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session.access_token}`
            },
            body: JSON.stringify({
                session_id: data.sessionId,
                thread_id: data.threadId,
                qp_id: data.qpId,
                // user_id removed - backend gets it from JWT
            })
        })

        const result = await response.json()

        if (!result.success) {
            return { success: false, error: result.error || "Failed to end exam" }
        }

        return {
            success: true,
            score: result.score,
            grade: result.grade,
        }
    } catch (error) {
        console.error("Failed to end exam:", error)
        return { success: false, error: "Failed to end exam" }
    }
}
