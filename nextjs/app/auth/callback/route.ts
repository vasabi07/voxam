import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')

  // If a "next" param was passed (e.g. /login?next=/dashboard), redirect there
  const next = searchParams.get('next') ?? '/authenticated/chat'

  if (code) {
    const supabase = await createClient()

    // Exchange the auth code for a user session
    const { error } = await supabase.auth.exchangeCodeForSession(code)

    if (!error) {
      // Success! Redirect to the dashboard or home page
      return NextResponse.redirect(`${origin}${next}`)
    }
  }

  // If something went wrong, redirect to an error page
  return NextResponse.redirect(`${origin}/auth/auth-code-error`)
}