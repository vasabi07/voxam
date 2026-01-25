/**
 * Email templates for VOXAM transactional emails
 */

export type EmailTemplate = 'welcome' | 'exam-results' | 'document-ready' | 'password-reset'

export interface WelcomeEmailData {
  name: string
}

export interface ExamResultsEmailData {
  name: string
  examTitle: string
  score: number
  resultsUrl: string
}

export interface DocumentReadyEmailData {
  name: string
  documentTitle: string
  documentUrl: string
}

export interface PasswordResetEmailData {
  name: string
  resetUrl: string
}

type EmailData = WelcomeEmailData | ExamResultsEmailData | DocumentReadyEmailData | PasswordResetEmailData

const baseStyles = `
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.6;
  color: #374151;
`

const buttonStyles = `
  display: inline-block;
  padding: 12px 24px;
  background-color: #EA580C;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
  margin: 16px 0;
`

const containerStyles = `
  max-width: 600px;
  margin: 0 auto;
  padding: 40px 20px;
`

export function getEmailTemplate(template: EmailTemplate, data: EmailData): string {
  switch (template) {
    case 'welcome':
      return getWelcomeTemplate(data as WelcomeEmailData)
    case 'exam-results':
      return getExamResultsTemplate(data as ExamResultsEmailData)
    case 'document-ready':
      return getDocumentReadyTemplate(data as DocumentReadyEmailData)
    case 'password-reset':
      return getPasswordResetTemplate(data as PasswordResetEmailData)
    default:
      throw new Error(`Unknown email template: ${template}`)
  }
}

function getWelcomeTemplate(data: WelcomeEmailData): string {
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://voxam.app'

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Welcome to VOXAM</title>
    </head>
    <body style="${baseStyles} background-color: #f9fafb; margin: 0; padding: 0;">
      <div style="${containerStyles}">
        <div style="background-color: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <h1 style="color: #1F2937; margin: 0 0 16px 0; font-size: 24px;">
            Welcome to VOXAM!
          </h1>

          <p style="margin: 0 0 16px 0;">
            Hi ${data.name},
          </p>

          <p style="margin: 0 0 16px 0;">
            Your account is ready. VOXAM is your AI-powered study companion that helps you learn through voice-based exams and interactive study sessions.
          </p>

          <p style="margin: 0 0 24px 0;">
            Here's how to get started:
          </p>

          <ol style="margin: 0 0 24px 0; padding-left: 20px;">
            <li style="margin-bottom: 8px;">Upload your study materials (PDFs, notes)</li>
            <li style="margin-bottom: 8px;">Chat with your documents to understand concepts</li>
            <li style="margin-bottom: 8px;">Generate personalized exams</li>
            <li style="margin-bottom: 8px;">Take voice-based exams with AI feedback</li>
          </ol>

          <a href="${appUrl}/authenticated/documents" style="${buttonStyles}">
            Upload Your First Document
          </a>

          <p style="margin: 24px 0 0 0; color: #6B7280; font-size: 14px;">
            Happy studying!<br>
            The VOXAM Team
          </p>
        </div>

        <p style="text-align: center; color: #9CA3AF; font-size: 12px; margin-top: 24px;">
          &copy; ${new Date().getFullYear()} VOXAM. All rights reserved.
        </p>
      </div>
    </body>
    </html>
  `
}

function getExamResultsTemplate(data: ExamResultsEmailData): string {
  const scoreColor = data.score >= 70 ? '#10B981' : data.score >= 50 ? '#F59E0B' : '#EF4444'

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Your Exam Results</title>
    </head>
    <body style="${baseStyles} background-color: #f9fafb; margin: 0; padding: 0;">
      <div style="${containerStyles}">
        <div style="background-color: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <h1 style="color: #1F2937; margin: 0 0 16px 0; font-size: 24px;">
            Exam Results Ready
          </h1>

          <p style="margin: 0 0 16px 0;">
            Hi ${data.name},
          </p>

          <p style="margin: 0 0 24px 0;">
            Your exam <strong>"${data.examTitle}"</strong> has been graded.
          </p>

          <div style="text-align: center; padding: 24px; background-color: #f9fafb; border-radius: 8px; margin-bottom: 24px;">
            <p style="margin: 0 0 8px 0; color: #6B7280; font-size: 14px;">Your Score</p>
            <p style="margin: 0; font-size: 48px; font-weight: 700; color: ${scoreColor};">
              ${data.score}%
            </p>
          </div>

          <a href="${data.resultsUrl}" style="${buttonStyles}">
            View Detailed Results
          </a>

          <p style="margin: 24px 0 0 0; color: #6B7280; font-size: 14px;">
            Keep up the great work!<br>
            The VOXAM Team
          </p>
        </div>

        <p style="text-align: center; color: #9CA3AF; font-size: 12px; margin-top: 24px;">
          &copy; ${new Date().getFullYear()} VOXAM. All rights reserved.
        </p>
      </div>
    </body>
    </html>
  `
}

function getDocumentReadyTemplate(data: DocumentReadyEmailData): string {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Document Ready</title>
    </head>
    <body style="${baseStyles} background-color: #f9fafb; margin: 0; padding: 0;">
      <div style="${containerStyles}">
        <div style="background-color: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <h1 style="color: #1F2937; margin: 0 0 16px 0; font-size: 24px;">
            Document Ready
          </h1>

          <p style="margin: 0 0 16px 0;">
            Hi ${data.name},
          </p>

          <p style="margin: 0 0 24px 0;">
            Your document <strong>"${data.documentTitle}"</strong> has been processed and is ready for studying.
          </p>

          <a href="${data.documentUrl}" style="${buttonStyles}">
            Start Studying
          </a>

          <p style="margin: 24px 0 0 0; color: #6B7280; font-size: 14px;">
            Happy learning!<br>
            The VOXAM Team
          </p>
        </div>

        <p style="text-align: center; color: #9CA3AF; font-size: 12px; margin-top: 24px;">
          &copy; ${new Date().getFullYear()} VOXAM. All rights reserved.
        </p>
      </div>
    </body>
    </html>
  `
}

function getPasswordResetTemplate(data: PasswordResetEmailData): string {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Reset Your Password</title>
    </head>
    <body style="${baseStyles} background-color: #f9fafb; margin: 0; padding: 0;">
      <div style="${containerStyles}">
        <div style="background-color: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <h1 style="color: #1F2937; margin: 0 0 16px 0; font-size: 24px;">
            Reset Your Password
          </h1>

          <p style="margin: 0 0 16px 0;">
            Hi ${data.name},
          </p>

          <p style="margin: 0 0 24px 0;">
            We received a request to reset your password. Click the button below to choose a new password.
          </p>

          <a href="${data.resetUrl}" style="${buttonStyles}">
            Reset Password
          </a>

          <p style="margin: 24px 0 0 0; color: #6B7280; font-size: 14px;">
            If you didn't request this, you can safely ignore this email.
          </p>

          <p style="margin: 16px 0 0 0; color: #6B7280; font-size: 14px;">
            This link will expire in 1 hour.
          </p>
        </div>

        <p style="text-align: center; color: #9CA3AF; font-size: 12px; margin-top: 24px;">
          &copy; ${new Date().getFullYear()} VOXAM. All rights reserved.
        </p>
      </div>
    </body>
    </html>
  `
}

export function getEmailSubject(template: EmailTemplate, data?: EmailData): string {
  switch (template) {
    case 'welcome':
      return 'Welcome to VOXAM!'
    case 'exam-results':
      return `Your Exam Results: ${(data as ExamResultsEmailData)?.examTitle || 'Ready'}`
    case 'document-ready':
      return `Document Ready: ${(data as DocumentReadyEmailData)?.documentTitle || 'Your Document'}`
    case 'password-reset':
      return 'Reset Your VOXAM Password'
    default:
      return 'VOXAM Notification'
  }
}
