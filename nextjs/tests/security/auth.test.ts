/**
 * Security Tests - Authentication & Authorization
 *
 * Tests for:
 * 1. API Route Protection - verifying auth requirements
 * 2. Server Action Authorization - IDOR prevention
 * 3. Token Handling - expired, malformed, missing tokens
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { handlerState, resetHandlerState } from '../__mocks__/handlers'

// ============================================
// Mock Setup - Use vi.hoisted to define mocks
// ============================================

const {
  mockGetUser,
  mockGetSession,
  mockPrismaDocument,
  mockPrismaQuestionPaper,
  mockPrismaExamSession,
} = vi.hoisted(() => {
  return {
    mockGetUser: vi.fn(),
    mockGetSession: vi.fn(),
    mockPrismaDocument: {
      findUnique: vi.fn(),
      findMany: vi.fn(),
      delete: vi.fn(),
      update: vi.fn(),
    },
    mockPrismaQuestionPaper: {
      create: vi.fn(),
      update: vi.fn(),
      findUnique: vi.fn(),
    },
    mockPrismaExamSession: {
      create: vi.fn(),
      update: vi.fn(),
      findUnique: vi.fn(),
      findMany: vi.fn(),
    },
  }
})

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getUser: mockGetUser,
      getSession: mockGetSession,
    },
  })),
}))

vi.mock('@/lib/prisma', () => ({
  db: {
    document: mockPrismaDocument,
    questionPaper: mockPrismaQuestionPaper,
    examSession: mockPrismaExamSession,
  },
}))

// Mock revalidatePath
vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
}))

// Import server actions after mocking
import {
  getDocuments,
  deleteDocument,
  getDocumentDetails,
  archiveDocument,
  restoreDocument,
  getDocumentFileUrl,
} from '@/app/actions/document'

import {
  createQuestionPaper,
  createExamSession,
  updateQuestionPaperStatus,
  startExamSession,
  getExamSession,
} from '@/app/authenticated/examlist/actions'

describe('Security - Authentication', () => {
  beforeEach(() => {
    resetHandlerState()
    vi.clearAllMocks()

    // Default: authenticated user
    mockGetUser.mockResolvedValue({
      data: { user: { id: 'test-user-id', email: 'test@example.com' } },
      error: null,
    })
    mockGetSession.mockResolvedValue({
      data: {
        session: {
          access_token: 'mock-token',
          user: { id: 'test-user-id' },
        },
      },
      error: null,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // ============================================
  // API Route Protection Tests
  // ============================================
  describe('API Route Protection', () => {
    describe('POST /api/copilot', () => {
      it('returns 401 when no session exists', async () => {
        handlerState.authenticated = false

        const response = await fetch('http://localhost:3000/api/copilot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        })

        expect(response.status).toBe(401)
      })

      it('returns 401 when Authorization header is missing', async () => {
        const response = await fetch('http://localhost:3000/api/copilot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        })

        // Without proper auth header, should be rejected
        expect(response.status).toBe(401)
      })
    })

    describe('POST /api/payment/create-order', () => {
      it('returns 401 when not authenticated', async () => {
        handlerState.authenticated = false

        const response = await fetch('http://localhost:3000/api/payment/create-order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ planName: 'standard' }),
        })

        expect(response.status).toBe(401)
      })

      it('accepts request with valid authentication', async () => {
        const response = await fetch('http://localhost:3000/api/payment/create-order', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-token',
          },
          body: JSON.stringify({ planName: 'standard' }),
        })

        expect(response.status).toBe(200)
        const data = await response.json()
        expect(data.success).toBe(true)
      })
    })

    describe('GET /api/user/region', () => {
      it('returns 401 when not authenticated', async () => {
        handlerState.authenticated = false

        const response = await fetch('http://localhost:3000/api/user/region')

        expect(response.status).toBe(401)
      })

      it('returns region when authenticated', async () => {
        const response = await fetch('http://localhost:3000/api/user/region', {
          headers: { Authorization: 'Bearer mock-token' },
        })

        expect(response.status).toBe(200)
        const data = await response.json()
        expect(data.region).toBe('india')
      })
    })

    describe('POST /api/feedback', () => {
      it('allows unauthenticated users (by design)', async () => {
        handlerState.authenticated = false

        const response = await fetch('http://localhost:3000/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'general',
            message: 'Test feedback',
            url: 'http://localhost:3000/test',
          }),
        })

        // Should accept even without auth
        expect(response.status).toBe(200)
      })

      it('includes user info when authenticated', async () => {
        const response = await fetch('http://localhost:3000/api/feedback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-token',
          },
          body: JSON.stringify({
            type: 'bug',
            message: 'Found a bug',
            url: 'http://localhost:3000/documents',
          }),
        })

        expect(response.status).toBe(200)
      })
    })

    describe('POST /api/email/send', () => {
      // SECURITY NOTE: This endpoint currently has NO authentication
      // This is a potential vulnerability for email abuse
      it('SECURITY: allows unauthenticated access (needs review)', async () => {
        const response = await fetch('http://localhost:3000/api/email/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: 'test@example.com',
            template: 'welcome',
          }),
        })

        // Currently accepts - this should be reviewed
        expect(response.status).toBe(200)
      })
    })
  })

  // ============================================
  // Server Action Authorization (IDOR Prevention)
  // ============================================
  describe('Server Action Authorization - Document Actions', () => {
    describe('getDocuments()', () => {
      it('returns error when not authenticated', async () => {
        mockGetUser.mockResolvedValue({
          data: { user: null },
          error: null,
        })

        const result = await getDocuments()

        expect(result.success).toBe(false)
        expect(result.error).toBe('Not authenticated')
        expect(result.documents).toEqual([])
      })

      it('only returns documents belonging to the authenticated user', async () => {
        mockPrismaDocument.findMany.mockResolvedValue([
          { id: 'doc-1', title: 'My Doc', userId: 'test-user-id' },
        ])

        const result = await getDocuments()

        expect(result.success).toBe(true)
        // Verify the query filters by userId
        expect(mockPrismaDocument.findMany).toHaveBeenCalledWith(
          expect.objectContaining({
            where: expect.objectContaining({
              userId: 'test-user-id',
            }),
          })
        )
      })
    })

    describe('deleteDocument() - IDOR Prevention', () => {
      it('returns error when document does not exist', async () => {
        mockPrismaDocument.findUnique.mockResolvedValue(null)

        const result = await deleteDocument('non-existent-id')

        expect(result.success).toBe(false)
        expect(result.error).toBe('Document not found')
      })

      it('returns error when user does not own the document', async () => {
        // Document exists but belongs to different user
        mockPrismaDocument.findUnique.mockResolvedValue({
          id: 'doc-123',
          userId: 'other-user-id', // Different user!
          fileKey: 'documents/test.pdf',
        })

        const result = await deleteDocument('doc-123')

        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
        // Verify delete was NOT called
        expect(mockPrismaDocument.delete).not.toHaveBeenCalled()
      })

      it('allows deletion when user owns the document', async () => {
        mockPrismaDocument.findUnique.mockResolvedValue({
          id: 'doc-123',
          userId: 'test-user-id', // Same user
          fileKey: 'documents/test.pdf',
        })

        global.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        })

        mockPrismaDocument.delete.mockResolvedValue({})

        const result = await deleteDocument('doc-123')

        expect(result.success).toBe(true)
        expect(mockPrismaDocument.delete).toHaveBeenCalled()
      })
    })

    describe('getDocumentDetails() - IDOR Prevention', () => {
      it('returns error when document belongs to another user', async () => {
        mockPrismaDocument.findUnique.mockResolvedValue({
          id: 'doc-123',
          userId: 'other-user-id',
          title: "Someone else's document",
        })

        const result = await getDocumentDetails('doc-123')

        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
        expect(result.document).toBeNull()
      })

      it('returns document when user owns it', async () => {
        const mockDoc = {
          id: 'doc-123',
          userId: 'test-user-id',
          title: 'My Document',
          questionPapers: [],
          examSessions: [],
          learnSessions: [],
        }
        mockPrismaDocument.findUnique.mockResolvedValue(mockDoc)

        const result = await getDocumentDetails('doc-123')

        expect(result.success).toBe(true)
        expect(result.document).toEqual(mockDoc)
      })
    })

    describe('archiveDocument() - IDOR Prevention', () => {
      it('returns error when user does not own the document', async () => {
        mockPrismaDocument.findUnique.mockResolvedValue({
          id: 'doc-123',
          userId: 'other-user-id',
        })

        const result = await archiveDocument('doc-123')

        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
        expect(mockPrismaDocument.update).not.toHaveBeenCalled()
      })
    })

    describe('restoreDocument() - IDOR Prevention', () => {
      it('returns error when user does not own the document', async () => {
        mockPrismaDocument.findUnique.mockResolvedValue({
          id: 'doc-123',
          userId: 'other-user-id',
          archivedAt: new Date(),
        })

        const result = await restoreDocument('doc-123')

        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
        expect(mockPrismaDocument.update).not.toHaveBeenCalled()
      })
    })

    describe('getDocumentFileUrl() - IDOR Prevention', () => {
      it('returns error when user does not own the document', async () => {
        mockPrismaDocument.findUnique.mockResolvedValue({
          id: 'doc-123',
          userId: 'other-user-id',
          fileKey: 'documents/secret.pdf',
          title: 'Secret Document',
        })

        const result = await getDocumentFileUrl('doc-123')

        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
        expect(result.url).toBeNull()
      })
    })
  })

  // ============================================
  // Server Action Authorization - Exam Actions
  // IDOR VULNERABILITIES FIXED
  // ============================================
  describe('Server Action Authorization - Exam Actions (IDOR FIXED)', () => {
    describe('createQuestionPaper() - IDOR FIXED', () => {
      /**
       * FIX VERIFIED: This function now derives userId from session
       * and verifies document ownership before creating QP.
       */
      it('FIXED: rejects when user does not own document', async () => {
        // Document owned by different user
        mockPrismaDocument.findUnique.mockResolvedValue({
          id: 'doc-123',
          userId: 'other-user-id',
        })

        const result = await createQuestionPaper({
          documentId: 'doc-123',
          duration: 30,
          numQuestions: 10,
          typeOfQp: 'practice',
          difficulty: ['medium'],
          bloomLevel: ['understand'],
          questionTypes: ['mcq'],
        })

        // FIXED: Now properly rejects unauthorized access
        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
        expect(mockPrismaQuestionPaper.create).not.toHaveBeenCalled()
      })
    })

    describe('createExamSession() - IDOR FIXED', () => {
      /**
       * FIX VERIFIED: This function now derives userId from session
       * and verifies document + QP ownership before creating session.
       */
      it('FIXED: rejects when user does not own document', async () => {
        // Document owned by different user
        mockPrismaDocument.findUnique.mockResolvedValue({
          id: 'doc-123',
          userId: 'other-user-id',
        })

        const result = await createExamSession({
          documentId: 'doc-123',
          questionPaperId: 'qp-123',
          threadId: 'thread-123',
          mode: 'EXAM',
        })

        // FIXED: Now properly rejects unauthorized access
        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
      })
    })

    describe('updateQuestionPaperStatus() - OWNERSHIP CHECK ADDED', () => {
      /**
       * FIX VERIFIED: This function now verifies the caller owns
       * the question paper before updating.
       */
      it('FIXED: rejects when user does not own QP', async () => {
        // QP owned by different user
        mockPrismaQuestionPaper.findUnique.mockResolvedValue({
          id: 'qp-123',
          userId: 'other-user-id',
        })

        const result = await updateQuestionPaperStatus('qp-123', 'READY')

        // FIXED: Now properly rejects unauthorized access
        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
      })
    })

    describe('startExamSession() - OWNERSHIP CHECK ADDED', () => {
      /**
       * FIX VERIFIED: This function now verifies the caller owns
       * the session before starting it.
       */
      it('FIXED: rejects when user does not own session', async () => {
        // Session owned by different user
        mockPrismaExamSession.findUnique.mockResolvedValue({
          id: 'session-123',
          userId: 'other-user-id',
          status: 'SCHEDULED',
        })

        const result = await startExamSession('session-123')

        // FIXED: Now properly rejects unauthorized access
        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
      })
    })

    describe('getExamSession() - OWNERSHIP CHECK ADDED', () => {
      /**
       * FIX VERIFIED: This function now verifies the caller owns
       * the session before returning it.
       */
      it('FIXED: rejects access to other users session', async () => {
        // Session owned by different user
        mockPrismaExamSession.findUnique.mockResolvedValue({
          id: 'session-123',
          userId: 'other-user-id', // Different user's session!
          status: 'COMPLETED',
          document: { title: 'Secret Document' },
          questionPaper: { questions: { q1: 'secret question' } },
          report: { score: 95 },
        })

        const result = await getExamSession('session-123')

        // FIXED: Now properly rejects unauthorized access
        expect(result.success).toBe(false)
        expect(result.error).toBe('Unauthorized')
      })
    })
  })

  // ============================================
  // Token Handling Tests
  // ============================================
  describe('Token Handling', () => {
    describe('Missing tokens', () => {
      // Note: These tests are handled by individual API route tests in tests/api/
      // The MSW handlers properly return 401 when handlerState.authenticated = false
      // Skipping here to avoid test isolation issues with fetch mocking
      it.skip('API routes reject requests when not authenticated', async () => {
        handlerState.authenticated = false

        // Test payment endpoint
        const paymentResponse = await fetch('http://localhost:3000/api/payment/create-order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ planName: 'standard' }),
        })
        expect(paymentResponse.status).toBe(401)

        // Test user region endpoint
        const regionResponse = await fetch('http://localhost:3000/api/user/region')
        expect(regionResponse.status).toBe(401)

        // Test copilot endpoint
        const copilotResponse = await fetch('http://localhost:3000/api/copilot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        })
        expect(copilotResponse.status).toBe(401)
      })
    })

    describe('Server action authentication', () => {
      it('document actions return error when session is null', async () => {
        mockGetUser.mockResolvedValue({
          data: { user: null },
          error: null,
        })

        const results = await Promise.all([
          getDocuments(),
          deleteDocument('any-id'),
          getDocumentDetails('any-id'),
          archiveDocument('any-id'),
          restoreDocument('any-id'),
          getDocumentFileUrl('any-id'),
        ])

        for (const result of results) {
          expect(result.success).toBe(false)
          expect(result.error).toBe('Not authenticated')
        }
      })
    })
  })
})

// ============================================
// Security Issue Summary
// ============================================
/**
 * SECURITY ISSUES IDENTIFIED:
 *
 * HIGH SEVERITY:
 * 1. createQuestionPaper() - Accepts userId from client (IDOR)
 * 2. createExamSession() - Accepts userId from client (IDOR)
 * 3. updateQuestionPaperStatus() - No ownership verification
 * 4. startExamSession() - No ownership verification
 * 5. getExamSession() - No ownership verification
 *
 * MEDIUM SEVERITY:
 * 6. /api/email/send - No authentication required (abuse potential)
 *
 * LOW SEVERITY:
 * 7. /api/feedback - No auth required (by design, but could be abused)
 *
 * RECOMMENDATIONS:
 * - All server actions should get userId from session, not client
 * - All data access should verify ownership before returning/modifying
 * - Email endpoint should require authentication
 * - Consider rate limiting on feedback endpoint
 */
