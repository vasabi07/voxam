import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { createClient } from '@/lib/supabase/server'
import { db } from '@/lib/prisma'

// Free tier defaults (must match Python credits.py)
const FREE_TIER = {
  voiceMinutesLimit: 15,
  chatMessagesLimit: 100,  // 100 for testing
  pagesLimit: 3,
}

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')

  // If a "next" param was passed (e.g. /login?next=/dashboard), redirect there
  const next = searchParams.get('next') ?? '/authenticated/chat'

  if (code) {
    const supabase = await createClient()

    // Exchange the auth code for a user session
    const { error, data } = await supabase.auth.exchangeCodeForSession(code)

    if (!error && data.user) {
      // Get region from cookie (set by middleware geo-detection)
      const cookieStore = await cookies()
      const region = cookieStore.get('region')?.value || 'india'

      // Upsert User record with free tier credits
      try {
        await db.user.upsert({
          where: { id: data.user.id },
          update: {}, // Don't overwrite existing credits
          create: {
            id: data.user.id,
            email: data.user.email || '',
            name: data.user.email?.split('@')[0] || 'User',
            region: region,
            voiceMinutesUsed: 0,
            voiceMinutesLimit: FREE_TIER.voiceMinutesLimit,
            chatMessagesUsed: 0,
            chatMessagesLimit: FREE_TIER.chatMessagesLimit,
            pagesUsed: 0,
            pagesLimit: FREE_TIER.pagesLimit,
          },
        })
        console.log(`[Auth] User upserted: ${data.user.id} (${data.user.email})`)
      } catch (err) {
        console.error('[Auth] Error upserting user:', err)
        // Don't block login on user creation failure
      }

      // Success! Redirect to the dashboard or home page
      return NextResponse.redirect(`${origin}${next}`)
    }
  }

  // If something went wrong, redirect to an error page
  return NextResponse.redirect(`${origin}/auth/auth-code-error`)
}