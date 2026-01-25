/**
 * Test Data Factories
 *
 * Provides consistent mock data for all tests.
 * Use these factories to create test fixtures with sensible defaults
 * that can be overridden as needed.
 */

// ============================================
// User Factories
// ============================================

export const createMockUser = (overrides: Partial<MockUser> = {}): MockUser => ({
  id: 'test-user-id',
  email: 'test@example.com',
  name: 'Test User',
  region: 'india',
  voiceMinutesUsed: 10,
  voiceMinutesLimit: 60,
  chatMessagesUsed: 100,
  chatMessagesLimit: 1000,
  pagesUsed: 5,
  pagesLimit: 50,
  subscriptionTier: 'FREE',
  createdAt: new Date('2024-01-01'),
  updatedAt: new Date('2024-01-01'),
  ...overrides,
})

export interface MockUser {
  id: string
  email: string
  name: string
  region: 'india' | 'global'
  voiceMinutesUsed: number
  voiceMinutesLimit: number
  chatMessagesUsed: number
  chatMessagesLimit: number
  pagesUsed: number
  pagesLimit: number
  subscriptionTier: string
  createdAt: Date
  updatedAt: Date
}

// ============================================
// Document Factories
// ============================================

export type DocumentStatus = 'PENDING' | 'PROCESSING' | 'READY' | 'FAILED'

export const createMockDocument = (overrides: Partial<MockDocument> = {}): MockDocument => ({
  id: 'doc-123',
  title: 'Test Document',
  fileName: 'test-document.pdf',
  fileKey: 'documents/test-user-id/test-document.pdf',
  fileSize: 1024000,
  mimeType: 'application/pdf',
  status: 'READY',
  userId: 'test-user-id',
  pageCount: 10,
  archivedAt: null,
  createdAt: new Date('2024-01-01'),
  updatedAt: new Date('2024-01-01'),
  ...overrides,
})

export interface MockDocument {
  id: string
  title: string
  fileName: string
  fileKey: string
  fileSize: number
  mimeType: string
  status: DocumentStatus
  userId: string
  pageCount: number | null
  archivedAt: Date | null
  createdAt: Date
  updatedAt: Date
}

// ============================================
// Question Paper Factories
// ============================================

export type QPStatus = 'PENDING' | 'PROCESSING' | 'READY' | 'FAILED'

export const createMockQuestionPaper = (overrides: Partial<MockQuestionPaper> = {}): MockQuestionPaper => ({
  id: 'qp-123',
  status: 'READY',
  duration: 30,
  numQuestions: 10,
  difficulty: ['medium'],
  bloomLevel: ['understand', 'apply'],
  questionTypes: ['mcq', 'short'],
  typeOfQp: 'practice',
  questions: null,
  documentId: 'doc-123',
  userId: 'test-user-id',
  createdAt: new Date('2024-01-01'),
  updatedAt: new Date('2024-01-01'),
  ...overrides,
})

export interface MockQuestionPaper {
  id: string
  status: QPStatus
  duration: number
  numQuestions: number
  difficulty: string[]
  bloomLevel: string[]
  questionTypes: string[]
  typeOfQp: string
  questions: unknown | null
  documentId: string
  userId: string
  createdAt: Date
  updatedAt: Date
}

// ============================================
// Exam Session Factories
// ============================================

export type ExamSessionStatus = 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
export type ExamMode = 'EXAM' | 'LEARN'

export const createMockExamSession = (overrides: Partial<MockExamSession> = {}): MockExamSession => ({
  id: 'session-123',
  status: 'SCHEDULED',
  mode: 'EXAM',
  threadId: 'thread-123',
  roomName: null,
  startedAt: null,
  endedAt: null,
  userId: 'test-user-id',
  documentId: 'doc-123',
  questionPaperId: 'qp-123',
  createdAt: new Date('2024-01-01'),
  updatedAt: new Date('2024-01-01'),
  ...overrides,
})

export interface MockExamSession {
  id: string
  status: ExamSessionStatus
  mode: ExamMode
  threadId: string
  roomName: string | null
  startedAt: Date | null
  endedAt: Date | null
  userId: string
  documentId: string
  questionPaperId: string
  createdAt: Date
  updatedAt: Date
}

// ============================================
// Correction Report Factories
// ============================================

export const createMockCorrectionReport = (overrides: Partial<MockCorrectionReport> = {}): MockCorrectionReport => ({
  id: 'report-123',
  score: 85,
  grade: 'B',
  totalQuestions: 10,
  correctAnswers: 8,
  incorrectAnswers: 2,
  feedback: 'Good performance overall. Review weak areas.',
  detailedResults: [],
  examSessionId: 'session-123',
  createdAt: new Date('2024-01-01'),
  ...overrides,
})

export interface MockCorrectionReport {
  id: string
  score: number
  grade: string
  totalQuestions: number
  correctAnswers: number
  incorrectAnswers: number
  feedback: string
  detailedResults: unknown[]
  examSessionId: string
  createdAt: Date
}

// ============================================
// Transaction Factories
// ============================================

export type TransactionType = 'PACK_PURCHASE' | 'SUBSCRIPTION' | 'REFUND'
export type TransactionStatus = 'SUCCESS' | 'FAILED' | 'PENDING'

export const createMockTransaction = (overrides: Partial<MockTransaction> = {}): MockTransaction => ({
  id: 'txn-123',
  type: 'PACK_PURCHASE',
  status: 'SUCCESS',
  amount: 59900,
  currency: 'INR',
  razorpayOrderId: 'order_123',
  razorpayPaymentId: 'pay_123',
  metadata: {
    planName: 'standard',
    minutes: 250,
    pages: 200,
    region: 'india',
  },
  userId: 'test-user-id',
  createdAt: new Date('2024-01-01'),
  ...overrides,
})

export interface MockTransaction {
  id: string
  type: TransactionType
  status: TransactionStatus
  amount: number
  currency: string
  razorpayOrderId: string
  razorpayPaymentId: string | null
  metadata: Record<string, unknown>
  userId: string
  createdAt: Date
}

// ============================================
// Credits Response Factory
// ============================================

export const createMockCreditsResponse = (overrides: Partial<MockCreditsResponse> = {}): MockCreditsResponse => ({
  voiceMinutes: {
    used: 10,
    limit: 60,
    remaining: 50,
  },
  chatMessages: {
    used: 100,
    limit: 1000,
    remaining: 900,
  },
  pages: {
    used: 5,
    limit: 50,
    remaining: 45,
  },
  ...overrides,
})

export interface MockCreditsResponse {
  voiceMinutes: { used: number; limit: number; remaining: number }
  chatMessages: { used: number; limit: number; remaining: number }
  pages: { used: number; limit: number; remaining: number }
}

// ============================================
// Razorpay Webhook Payload Factories
// ============================================

export const createMockRazorpayWebhookPayload = (
  event: 'payment.captured' | 'payment.failed',
  overrides: Partial<RazorpayPaymentEntity> = {}
): RazorpayWebhookPayload => ({
  event,
  payload: {
    payment: {
      entity: {
        id: 'pay_123456789',
        order_id: 'order_123456789',
        amount: 59900,
        currency: 'INR',
        status: event === 'payment.captured' ? 'captured' : 'failed',
        method: 'card',
        email: 'test@example.com',
        contact: '+919876543210',
        notes: {
          userId: 'test-user-id',
          planName: 'standard',
          minutes: '250',
          pages: '200',
          region: 'india',
        },
        created_at: Math.floor(Date.now() / 1000),
        ...overrides,
      },
    },
  },
})

export interface RazorpayPaymentEntity {
  id: string
  order_id: string
  amount: number
  currency: string
  status: string
  method: string
  email: string
  contact: string
  notes: Record<string, string>
  created_at: number
}

export interface RazorpayWebhookPayload {
  event: string
  payload: {
    payment: {
      entity: RazorpayPaymentEntity
    }
  }
}

// ============================================
// Razorpay Order Response Factory
// ============================================

export const createMockRazorpayOrderResponse = (overrides: Partial<RazorpayOrderResponse> = {}): RazorpayOrderResponse => ({
  id: 'order_123456789',
  entity: 'order',
  amount: 59900,
  amount_paid: 0,
  amount_due: 59900,
  currency: 'INR',
  receipt: 'receipt_123',
  status: 'created',
  attempts: 0,
  created_at: Math.floor(Date.now() / 1000),
  ...overrides,
})

export interface RazorpayOrderResponse {
  id: string
  entity: string
  amount: number
  amount_paid: number
  amount_due: number
  currency: string
  receipt: string
  status: string
  attempts: number
  created_at: number
}

// ============================================
// HITL Interrupt Factory
// ============================================

export const createMockHITLInterrupt = (overrides: Partial<MockHITLInterrupt> = {}): MockHITLInterrupt => ({
  type: 'approval',
  message: 'Do you want to proceed with this action?',
  data: {},
  threadId: 'thread-123',
  ...overrides,
})

export interface MockHITLInterrupt {
  type: string
  message: string
  data: Record<string, unknown>
  threadId: string
}

// ============================================
// Supabase Session Factory
// ============================================

export const createMockSupabaseSession = (overrides: Partial<MockSupabaseSession> = {}): MockSupabaseSession => ({
  access_token: 'mock-access-token-12345',
  refresh_token: 'mock-refresh-token-12345',
  expires_in: 3600,
  expires_at: Math.floor(Date.now() / 1000) + 3600,
  token_type: 'bearer',
  user: {
    id: 'test-user-id',
    email: 'test@example.com',
    user_metadata: {
      name: 'Test User',
    },
    app_metadata: {},
    aud: 'authenticated',
    created_at: '2024-01-01T00:00:00.000Z',
  },
  ...overrides,
})

export interface MockSupabaseSession {
  access_token: string
  refresh_token: string
  expires_in: number
  expires_at: number
  token_type: string
  user: {
    id: string
    email: string
    user_metadata: Record<string, unknown>
    app_metadata: Record<string, unknown>
    aud: string
    created_at: string
  }
}

// ============================================
// API Error Response Factory
// ============================================

export const createMockErrorResponse = (message: string, statusCode = 500) => ({
  error: message,
  statusCode,
  timestamp: new Date().toISOString(),
})

// ============================================
// Helper: Generate Valid Razorpay Signature
// ============================================

import crypto from 'crypto'

export const generateRazorpaySignature = (payload: string, secret: string): string => {
  return crypto.createHmac('sha256', secret).update(payload).digest('hex')
}

// ============================================
// Plan Configuration (matches actual pricing)
// ============================================

export const INDIA_PLANS = {
  starter: { amount: 29900, minutes: 90, pages: 50 },
  standard: { amount: 59900, minutes: 250, pages: 200 },
  achiever: { amount: 109900, minutes: 500, pages: 500 },
  topup: { amount: 19900, minutes: 60, pages: 0 },
} as const

export const GLOBAL_PLANS = {
  standard: { amount: 999, minutes: 120, pages: 100 },
  pro: { amount: 1999, minutes: 300, pages: 300 },
  topup: { amount: 599, minutes: 60, pages: 0 },
} as const
