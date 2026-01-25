import { Resend } from 'resend'
import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/lib/auth'
import { headers } from 'next/headers'

const resend = new Resend(process.env.RESEND_API_KEY)

// Your email to receive feedback
const FEEDBACK_EMAIL = process.env.FEEDBACK_EMAIL || 'feedback@voxam.app'
const FROM_EMAIL = process.env.RESEND_FROM_EMAIL || 'VOXAM Feedback <feedback@voxam.app>'

export async function POST(req: NextRequest) {
  try {
    const headersList = await headers()
    const session = await auth.api.getSession({ headers: headersList })
    const { type, message, url } = await req.json()

    if (!message || !type) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    const userEmail = session?.user?.email || 'Anonymous'
    const userName = session?.user?.name || 'Anonymous User'
    const userId = session?.user?.id || 'N/A'

    const typeEmojiMap: Record<string, string> = {
      bug: '🐛',
      feature: '💡',
      general: '💬',
    }
    const typeEmoji = typeEmojiMap[type] || '📝'

    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>New Feedback</title>
      </head>
      <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1F2937; border-bottom: 2px solid #EA580C; padding-bottom: 10px;">
          ${typeEmoji} New ${type.charAt(0).toUpperCase() + type.slice(1)} Feedback
        </h2>

        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
          <tr>
            <td style="padding: 8px 0; color: #6B7280; width: 100px;">User:</td>
            <td style="padding: 8px 0; color: #1F2937; font-weight: 500;">${userName}</td>
          </tr>
          <tr>
            <td style="padding: 8px 0; color: #6B7280;">Email:</td>
            <td style="padding: 8px 0; color: #1F2937;">${userEmail}</td>
          </tr>
          <tr>
            <td style="padding: 8px 0; color: #6B7280;">User ID:</td>
            <td style="padding: 8px 0; color: #1F2937; font-family: monospace; font-size: 12px;">${userId}</td>
          </tr>
          <tr>
            <td style="padding: 8px 0; color: #6B7280;">Page:</td>
            <td style="padding: 8px 0;">
              <a href="${url}" style="color: #EA580C; text-decoration: none;">${url}</a>
            </td>
          </tr>
          <tr>
            <td style="padding: 8px 0; color: #6B7280;">Time:</td>
            <td style="padding: 8px 0; color: #1F2937;">${new Date().toISOString()}</td>
          </tr>
        </table>

        <div style="background-color: #F9FAFB; border-radius: 8px; padding: 20px; margin-top: 20px;">
          <h3 style="color: #374151; margin: 0 0 12px 0; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">
            Message
          </h3>
          <p style="color: #1F2937; margin: 0; white-space: pre-wrap; line-height: 1.6;">
            ${message}
          </p>
        </div>

        <p style="color: #9CA3AF; font-size: 12px; margin-top: 24px; text-align: center;">
          Sent from VOXAM Feedback Widget
        </p>
      </body>
      </html>
    `

    const { error } = await resend.emails.send({
      from: FROM_EMAIL,
      to: FEEDBACK_EMAIL,
      subject: `[${type.toUpperCase()}] Feedback from ${userEmail}`,
      html,
    })

    if (error) {
      console.error('Failed to send feedback email:', error)
      return NextResponse.json(
        { error: 'Failed to send feedback' },
        { status: 500 }
      )
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Feedback error:', error)
    return NextResponse.json(
      { error: 'Failed to process feedback' },
      { status: 500 }
    )
  }
}
