import { Resend } from 'resend'
import { NextRequest, NextResponse } from 'next/server'
import { getEmailTemplate, getEmailSubject, EmailTemplate } from '@/lib/email-templates'

const resend = new Resend(process.env.RESEND_API_KEY)

// From address - must be verified in Resend
const FROM_EMAIL = process.env.RESEND_FROM_EMAIL || 'VOXAM <noreply@voxam.app>'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { to, template, data, subject: customSubject } = body

    if (!to || !template) {
      return NextResponse.json(
        { error: 'Missing required fields: to, template' },
        { status: 400 }
      )
    }

    // Generate HTML and subject from template
    const html = getEmailTemplate(template as EmailTemplate, data)
    const subject = customSubject || getEmailSubject(template as EmailTemplate, data)

    const { data: result, error } = await resend.emails.send({
      from: FROM_EMAIL,
      to: Array.isArray(to) ? to : [to],
      subject,
      html,
    })

    if (error) {
      console.error('Resend error:', error)
      return NextResponse.json(
        { error: error.message || 'Failed to send email' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      id: result?.id,
    })
  } catch (error) {
    console.error('Email send error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to send email' },
      { status: 500 }
    )
  }
}
