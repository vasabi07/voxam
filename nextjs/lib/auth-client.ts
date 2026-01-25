"use client"

import { createClient } from "@/lib/supabase/client"
import { useEffect, useState } from "react"
import type { User, Session } from "@supabase/supabase-js"

type SessionData = {
    user: User | null
    session: Session | null
}

export function useSession() {
    const [data, setData] = useState<SessionData | null>(null)
    const [isPending, setIsPending] = useState(true)

    useEffect(() => {
        const supabase = createClient()

        // Get initial session
        supabase.auth.getSession().then(({ data: { session } }) => {
            setData({
                user: session?.user ?? null,
                session: session,
            })
            setIsPending(false)
        })

        // Listen for auth changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            (_event, session) => {
                setData({
                    user: session?.user ?? null,
                    session: session,
                })
                setIsPending(false)
            }
        )

        return () => subscription.unsubscribe()
    }, [])

    return { data, isPending }
}

// Auth callback options type
type AuthCallbacks = {
    onRequest?: () => void
    onResponse?: () => void
    onSuccess?: () => void
    onError?: (ctx: { error: { message: string } }) => void
}

// Compatibility API matching better-auth style
export const signIn = {
    email: async (
        credentials: { email: string; password: string },
        callbacks?: AuthCallbacks
    ) => {
        callbacks?.onRequest?.()
        const supabase = createClient()
        const { data, error } = await supabase.auth.signInWithPassword({
            email: credentials.email,
            password: credentials.password,
        })
        callbacks?.onResponse?.()

        if (error) {
            callbacks?.onError?.({ error: { message: error.message } })
            return { error }
        }
        callbacks?.onSuccess?.()
        return { data }
    },

    social: async (options: { provider: "google" | "github" | "discord" }) => {
        const supabase = createClient()
        return await supabase.auth.signInWithOAuth({
            provider: options.provider,
            options: {
                redirectTo: `${window.location.origin}/auth/callback`,
            },
        })
    },
}

export const signUp = {
    email: async (
        credentials: { email: string; password: string; name?: string },
        callbacks?: AuthCallbacks
    ) => {
        callbacks?.onRequest?.()
        const supabase = createClient()
        const { data, error } = await supabase.auth.signUp({
            email: credentials.email,
            password: credentials.password,
            options: credentials.name ? { data: { name: credentials.name } } : undefined,
        })
        callbacks?.onResponse?.()

        if (error) {
            callbacks?.onError?.({ error: { message: error.message } })
            return { error }
        }
        callbacks?.onSuccess?.()
        return { data }
    },
}

export async function signOut() {
    const supabase = createClient()
    return await supabase.auth.signOut()
}

// Password reset functions
export const passwordReset = {
    request: async (
        email: string,
        callbacks?: AuthCallbacks
    ) => {
        callbacks?.onRequest?.()
        const supabase = createClient()
        const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
            redirectTo: `${window.location.origin}/auth/reset-password`,
        })
        callbacks?.onResponse?.()

        if (error) {
            callbacks?.onError?.({ error: { message: error.message } })
            return { error }
        }
        callbacks?.onSuccess?.()
        return { data }
    },

    update: async (
        newPassword: string,
        callbacks?: AuthCallbacks
    ) => {
        callbacks?.onRequest?.()
        const supabase = createClient()
        const { data, error } = await supabase.auth.updateUser({
            password: newPassword,
        })
        callbacks?.onResponse?.()

        if (error) {
            callbacks?.onError?.({ error: { message: error.message } })
            return { error }
        }
        callbacks?.onSuccess?.()
        return { data }
    },
}

// Re-export for compatibility
export { useSession as default }
