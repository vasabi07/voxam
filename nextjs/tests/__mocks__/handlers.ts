import { http, HttpResponse } from 'msw'

// Base URLs
const API_BASE = 'http://localhost:3000'
const PYTHON_API_BASE = 'http://localhost:8000'

// ============================================
// Handler State (for dynamic test scenarios)
// ============================================
export let handlerState = {
  authenticated: true,
  userRegion: 'india' as 'india' | 'global',
  razorpayOrderFails: false,
  resendFails: false,
}

export const resetHandlerState = () => {
  handlerState = {
    authenticated: true,
    userRegion: 'india',
    razorpayOrderFails: false,
    resendFails: false,
  }
}

export const handlers = [
  // ============================================
  // Python Backend API (credits, etc.)
  // ============================================
  http.get(`${PYTHON_API_BASE}/credits`, () => {
    return HttpResponse.json({
      voiceMinutes: { used: 10, limit: 60, remaining: 50 },
      chatMessages: { used: 100, limit: 1000, remaining: 900 },
      pages: { used: 5, limit: 50, remaining: 45 },
    })
  }),

  // ============================================
  // Supabase Auth Mocks
  // ============================================
  http.get('*/auth/v1/user', () => {
    if (!handlerState.authenticated) {
      return HttpResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      )
    }
    return HttpResponse.json({
      id: 'test-user-id',
      email: 'test@example.com',
      user_metadata: { name: 'Test User' }
    })
  }),

  // ============================================
  // Next.js API Route Mocks
  // ============================================

  // Feedback API
  http.post(`${API_BASE}/api/feedback`, async ({ request }) => {
    const body = await request.json() as { type?: string; message?: string }

    if (!body.message || !body.type) {
      return HttpResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    const validTypes = ['bug', 'feature', 'general']
    if (!validTypes.includes(body.type)) {
      return HttpResponse.json(
        { error: 'Invalid feedback type' },
        { status: 400 }
      )
    }

    if (handlerState.resendFails) {
      return HttpResponse.json(
        { error: 'Failed to send email' },
        { status: 500 }
      )
    }

    return HttpResponse.json({ success: true })
  }),

  // Email API
  http.post(`${API_BASE}/api/email/send`, async ({ request }) => {
    const body = await request.json() as { to?: string; template?: string }

    if (!body.to || !body.template) {
      return HttpResponse.json(
        { error: 'Missing required fields: to, template' },
        { status: 400 }
      )
    }

    const validTemplates = ['welcome', 'exam-results', 'document-ready', 'password-reset']
    if (!validTemplates.includes(body.template)) {
      return HttpResponse.json(
        { error: 'Invalid template' },
        { status: 400 }
      )
    }

    if (handlerState.resendFails) {
      return HttpResponse.json(
        { error: 'Failed to send email' },
        { status: 500 }
      )
    }

    return HttpResponse.json({ success: true, id: 'mock-email-id' })
  }),

  // User Region API
  http.get(`${API_BASE}/api/user/region`, ({ request }) => {
    const authHeader = request.headers.get('Authorization')
    if (!authHeader && !handlerState.authenticated) {
      return HttpResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    return HttpResponse.json({
      region: handlerState.userRegion
    })
  }),

  // Payment Create Order API
  http.post(`${API_BASE}/api/payment/create-order`, async ({ request }) => {
    const authHeader = request.headers.get('Authorization')
    if (!authHeader && !handlerState.authenticated) {
      return HttpResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      )
    }

    const body = await request.json() as { planName?: string }

    if (!body.planName) {
      return HttpResponse.json(
        { error: 'planName is required' },
        { status: 400 }
      )
    }

    // Validate plan names based on region
    const indiaPlans = ['starter', 'standard', 'achiever', 'topup']
    const globalPlans = ['standard', 'pro', 'topup']
    const validPlans = handlerState.userRegion === 'india' ? indiaPlans : globalPlans

    if (!validPlans.includes(body.planName)) {
      return HttpResponse.json(
        { error: 'Invalid plan name' },
        { status: 400 }
      )
    }

    if (handlerState.razorpayOrderFails) {
      return HttpResponse.json(
        { error: 'Failed to create order' },
        { status: 500 }
      )
    }

    // Plan pricing
    const pricing: Record<string, Record<string, { amount: number; minutes: number; pages: number }>> = {
      india: {
        starter: { amount: 29900, minutes: 90, pages: 50 },
        standard: { amount: 59900, minutes: 250, pages: 200 },
        achiever: { amount: 109900, minutes: 500, pages: 500 },
        topup: { amount: 19900, minutes: 60, pages: 0 },
      },
      global: {
        standard: { amount: 999, minutes: 120, pages: 100 },
        pro: { amount: 1999, minutes: 300, pages: 300 },
        topup: { amount: 599, minutes: 60, pages: 0 },
      },
    }

    const plan = pricing[handlerState.userRegion][body.planName]

    return HttpResponse.json({
      success: true,
      orderId: 'order_mock123456789',
      amount: plan.amount,
      currency: handlerState.userRegion === 'india' ? 'INR' : 'USD',
      planName: body.planName,
      minutes: plan.minutes,
      keyId: 'rzp_test_mock123',
    })
  }),

  // Payment Webhook API
  http.post(`${API_BASE}/api/webhooks/payment`, async ({ request }) => {
    const signature = request.headers.get('x-razorpay-signature')

    if (!signature) {
      return HttpResponse.json(
        { error: 'Missing signature header' },
        { status: 400 }
      )
    }

    // For testing, we accept any signature that matches 'valid-test-signature'
    // In real tests, we'll generate proper HMAC signatures
    if (signature !== 'valid-test-signature' && !signature.startsWith('sha256=')) {
      return HttpResponse.json(
        { error: 'Invalid signature' },
        { status: 401 }
      )
    }

    const body = await request.json() as { event?: string; payload?: unknown }

    if (!body.event) {
      return HttpResponse.json(
        { error: 'Missing event type' },
        { status: 400 }
      )
    }

    return HttpResponse.json({ received: true })
  }),

  // CopilotKit API (requires auth)
  http.post(`${API_BASE}/api/copilot`, ({ request }) => {
    const authHeader = request.headers.get('Authorization')
    if (!authHeader) {
      return HttpResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    return HttpResponse.json({ success: true })
  }),

  // ============================================
  // Supabase Database Mocks (for useCredits etc.)
  // ============================================
  http.get('*/rest/v1/User*', ({ request }) => {
    const url = new URL(request.url)
    const select = url.searchParams.get('select')

    // Mock credits data
    if (select?.includes('pagesRemaining') || select?.includes('voiceMinutes')) {
      return HttpResponse.json({
        id: 'test-user-id',
        pagesRemaining: 100,
        voiceMinutes: 60,
        subscriptionTier: 'FREE',
        region: handlerState.userRegion,
      })
    }

    return HttpResponse.json({
      id: 'test-user-id',
      email: 'test@example.com',
      name: 'Test User',
      region: handlerState.userRegion,
    })
  }),

  // ============================================
  // Python Backend API Mocks
  // ============================================
  http.post(`${PYTHON_API_BASE}/upload/presign`, () => {
    return HttpResponse.json({
      url: 'https://mock-r2.example.com/upload',
      key: 'documents/test-user-id/mock-file.pdf'
    })
  }),

  http.post(`${PYTHON_API_BASE}/ingest`, () => {
    return HttpResponse.json({
      task_id: 'mock-task-id',
      status: 'PENDING'
    })
  }),

  http.get(`${PYTHON_API_BASE}/task/*/status`, () => {
    return HttpResponse.json({
      status: 'SUCCESS',
      progress: 100
    })
  }),

  // Topics endpoint for Learn mode
  http.get(`${PYTHON_API_BASE}/topics/*`, () => {
    return HttpResponse.json([
      { id: 'topic-1', title: 'Introduction', chunks: 5 },
      { id: 'topic-2', title: 'Core Concepts', chunks: 8 },
      { id: 'topic-3', title: 'Advanced Topics', chunks: 12 },
    ])
  }),

  // Create Question Paper
  http.post(`${PYTHON_API_BASE}/create-qp`, () => {
    return HttpResponse.json({
      task_id: 'qp-task-123',
      status: 'PENDING'
    })
  }),

  // Start Exam Session
  http.post(`${PYTHON_API_BASE}/start-exam-session`, () => {
    return HttpResponse.json({
      token: 'mock-livekit-token-12345',
      room: 'exam-room-test-123'
    })
  }),

  // End Exam Session
  http.post(`${PYTHON_API_BASE}/end-exam`, () => {
    return HttpResponse.json({
      success: true,
      score: 85,
      grade: 'B'
    })
  }),

  // Create Learn Pack
  http.post(`${PYTHON_API_BASE}/create-lp`, () => {
    return HttpResponse.json({
      lp_id: 'lp-123',
      status: 'READY'
    })
  }),

  // Start Learn Session
  http.post(`${PYTHON_API_BASE}/start-learn-session`, () => {
    return HttpResponse.json({
      token: 'mock-livekit-token-learn-12345',
      room: 'learn-room-test-123'
    })
  }),

  // Document cleanup (delete)
  http.delete(`${PYTHON_API_BASE}/documents/*`, () => {
    return HttpResponse.json({ success: true })
  }),

  // Document retry
  http.post(`${PYTHON_API_BASE}/documents/*/retry`, () => {
    return HttpResponse.json({
      task_id: 'retry-task-123',
      status: 'PENDING'
    })
  }),

  // Document URL (presigned)
  http.get(`${PYTHON_API_BASE}/documents/*/url`, () => {
    return HttpResponse.json({
      url: 'https://mock-r2.example.com/documents/test-user-id/document.pdf?signed=true',
      expiresIn: 3600
    })
  }),

  // CopilotKit Resume (HITL)
  http.post(`${PYTHON_API_BASE}/copilotkit/resume/*`, () => {
    return HttpResponse.json({ success: true })
  }),

  // ============================================
  // External Service Mocks
  // ============================================

  // Razorpay Order Creation
  http.post('https://api.razorpay.com/v1/orders', () => {
    if (handlerState.razorpayOrderFails) {
      return HttpResponse.json(
        { error: { code: 'BAD_REQUEST_ERROR', description: 'Failed to create order' } },
        { status: 400 }
      )
    }

    return HttpResponse.json({
      id: 'order_mock123456789',
      entity: 'order',
      amount: 59900,
      amount_paid: 0,
      amount_due: 59900,
      currency: 'INR',
      receipt: 'receipt_test_123',
      status: 'created',
      attempts: 0,
      created_at: Math.floor(Date.now() / 1000),
    })
  }),

  // Resend Email API
  http.post('https://api.resend.com/emails', () => {
    if (handlerState.resendFails) {
      return HttpResponse.json(
        { statusCode: 500, message: 'Internal server error' },
        { status: 500 }
      )
    }

    return HttpResponse.json({
      id: 'email-mock-id-123',
    })
  }),
]
