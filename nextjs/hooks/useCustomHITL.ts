"use client"

import { useState, useCallback } from "react"
import { createClient } from "@/lib/supabase/client"

interface HITLInterrupt {
    type: string
    message: string
    query: string
    options: string[]
}

interface UseCustomHITLReturn {
    interrupt: HITLInterrupt | null
    isInterrupted: boolean
    resolveInterrupt: (approved: boolean) => Promise<void>
    clearInterrupt: () => void
    setInterruptFromEvent: (data: HITLInterrupt) => void
}

/**
 * Custom HITL hook that bypasses AG-UI's buggy useLangGraphInterrupt.
 * Handles interrupt detection and resolution via direct API calls.
 */
export function useCustomHITL(threadId: string | null): UseCustomHITLReturn {
    const [interrupt, setInterrupt] = useState<HITLInterrupt | null>(null)
    const [isResolving, setIsResolving] = useState(false)

    const isInterrupted = interrupt !== null && !isResolving

    const setInterruptFromEvent = useCallback((data: HITLInterrupt) => {
        console.log("🔔 HITL interrupt received:", data)
        setInterrupt(data)
    }, [])

    const clearInterrupt = useCallback(() => {
        setInterrupt(null)
        setIsResolving(false)
    }, [])

    const resolveInterrupt = useCallback(async (approved: boolean) => {
        if (!threadId || !interrupt) {
            console.warn("Cannot resolve: no threadId or interrupt")
            return
        }

        setIsResolving(true)

        try {
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()

            if (!session?.access_token) {
                console.error("No auth token available")
                return
            }

            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/copilotkit/resume/${threadId}`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${session.access_token}`
                    },
                    body: JSON.stringify({ approved })
                }
            )

            const result = await response.json()
            console.log("✅ HITL resolved:", result)

            // Clear the interrupt after resolution
            clearInterrupt()

        } catch (error) {
            console.error("❌ Error resolving HITL:", error)
            setIsResolving(false)
        }
    }, [threadId, interrupt, clearInterrupt])

    return {
        interrupt,
        isInterrupted,
        resolveInterrupt,
        clearInterrupt,
        setInterruptFromEvent
    }
}
