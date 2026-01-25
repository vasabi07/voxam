'use client'

import { createClient } from '@/lib/supabase/client'
import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Mic, ArrowLeft, Mail, CheckCircle2 } from "lucide-react"
import Link from 'next/link'
import { toast } from 'sonner'

export default function ForgotPasswordPage() {
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const supabase = createClient()
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      })

      if (error) throw error

      setSent(true)
      toast.success('Reset link sent!')
    } catch (error) {
      console.error('Reset error:', error)
      toast.error('Failed to send reset link', {
        description: error instanceof Error ? error.message : 'Please try again',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/30 p-4">
      <Link
        href="/login"
        className="absolute left-4 top-4 flex items-center text-sm font-medium text-muted-foreground hover:text-foreground md:left-8 md:top-8"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Login
      </Link>

      <Card className="w-full max-w-md border-border/50 bg-background/95 shadow-xl backdrop-blur-sm supports-backdrop-filter:bg-background/60">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {sent ? <CheckCircle2 className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
          </div>
          <CardTitle className="text-2xl font-bold">
            {sent ? 'Check your email' : 'Reset password'}
          </CardTitle>
          <CardDescription>
            {sent
              ? `We sent a password reset link to ${email}`
              : 'Enter your email and we\'ll send you a reset link'
            }
          </CardDescription>
        </CardHeader>

        <CardContent className="grid gap-4">
          {sent ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground text-center">
                Click the link in the email to reset your password. If you don&apos;t see it, check your spam folder.
              </p>
              <div className="flex flex-col gap-2">
                <Button
                  variant="outline"
                  onClick={() => setSent(false)}
                  className="w-full"
                >
                  Try a different email
                </Button>
                <Link href="/login" className="w-full">
                  <Button variant="ghost" className="w-full">
                    Back to login
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    className="pl-10"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={loading}
                    autoFocus
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full h-11"
                disabled={loading}
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                    <span>Sending...</span>
                  </div>
                ) : (
                  'Send reset link'
                )}
              </Button>

              <p className="text-center text-sm text-muted-foreground">
                Remember your password?{' '}
                <Link href="/login" className="text-primary hover:underline font-medium">
                  Sign in
                </Link>
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
