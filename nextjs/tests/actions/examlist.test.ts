/**
 * Server Action Tests - Exam List Actions
 *
 * Tests for app/authenticated/examlist/actions.ts
 *
 * Covers:
 * 1. createQuestionPaper - create QP record (requires auth)
 * 2. updateQuestionPaperStatus - update QP status (requires auth + ownership)
 * 3. createExamSession - create session (requires auth)
 * 4. startExamSession - start exam (requires auth + ownership)
 * 5. getExamSessions - list all sessions (requires auth)
 * 6. getScheduledExams / getInProgressExams / getCompletedExams - filtered lists
 * 7. getExamSession - get single session (requires auth + ownership)
 * 8. getUserDocuments - get user's ready documents (requires auth)
 *
 * SECURITY: All functions now derive userId from session (IDOR fixed)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  createMockQuestionPaper,
  createMockExamSession,
  createMockDocument,
} from '../__mocks__/factories'

// ============================================
// Mock Setup - Use vi.hoisted to define mocks
// ============================================

const {
  mockGetUser,
  mockPrismaQuestionPaper,
  mockPrismaExamSession,
  mockPrismaDocument,
} = vi.hoisted(() => {
  return {
    mockGetUser: vi.fn(),
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
    mockPrismaDocument: {
      findMany: vi.fn(),
      findUnique: vi.fn(),
    },
  }
})

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getUser: mockGetUser,
    },
  })),
}))

vi.mock('@/lib/prisma', () => ({
  db: {
    questionPaper: mockPrismaQuestionPaper,
    examSession: mockPrismaExamSession,
    document: mockPrismaDocument,
  },
}))

// Import after mocking
import {
  createQuestionPaper,
  updateQuestionPaperStatus,
  createExamSession,
  startExamSession,
  getExamSessions,
  getScheduledExams,
  getInProgressExams,
  getCompletedExams,
  getExamSession,
  getUserDocuments,
} from '@/app/authenticated/examlist/actions'

describe('Exam List Server Actions', () => {
  const TEST_USER_ID = 'test-user-id'
  const OTHER_USER_ID = 'other-user-id'

  beforeEach(() => {
    vi.clearAllMocks()

    // Default: authenticated user
    mockGetUser.mockResolvedValue({
      data: { user: { id: TEST_USER_ID, email: 'test@example.com' } },
    })
  })

  // ============================================
  // createQuestionPaper Tests
  // ============================================
  describe('createQuestionPaper()', () => {
    beforeEach(() => {
      // Default: document owned by test user
      mockPrismaDocument.findUnique.mockResolvedValue(
        createMockDocument({ userId: TEST_USER_ID })
      )
    })

    it('creates QP with PENDING status when authenticated', async () => {
      const mockQP = createMockQuestionPaper({ status: 'PENDING', userId: TEST_USER_ID })
      mockPrismaQuestionPaper.create.mockResolvedValue(mockQP)

      const result = await createQuestionPaper({
        documentId: 'doc-123',
        duration: 30,
        numQuestions: 10,
        typeOfQp: 'practice',
        difficulty: ['medium'],
        bloomLevel: ['understand', 'apply'],
        questionTypes: ['mcq', 'short'],
      })

      expect(result.success).toBe(true)
      expect(result.questionPaper).toBeDefined()

      expect(mockPrismaQuestionPaper.create).toHaveBeenCalledWith({
        data: expect.objectContaining({
          status: 'PENDING',
          duration: 30,
          numQuestions: 10,
          userId: TEST_USER_ID, // Derived from session, not client
        }),
      })
    })

    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } })

      const result = await createQuestionPaper({
        documentId: 'doc-123',
        duration: 30,
        numQuestions: 10,
        typeOfQp: 'practice',
        difficulty: ['medium'],
        bloomLevel: ['understand'],
        questionTypes: ['mcq'],
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
      expect(mockPrismaQuestionPaper.create).not.toHaveBeenCalled()
    })

    it('returns error when document not found', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(null)

      const result = await createQuestionPaper({
        documentId: 'non-existent-doc',
        duration: 30,
        numQuestions: 10,
        typeOfQp: 'practice',
        difficulty: ['medium'],
        bloomLevel: ['understand'],
        questionTypes: ['mcq'],
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Document not found')
    })

    it('returns error when user does not own the document (IDOR prevention)', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(
        createMockDocument({ userId: OTHER_USER_ID })
      )

      const result = await createQuestionPaper({
        documentId: 'doc-123',
        duration: 30,
        numQuestions: 10,
        typeOfQp: 'practice',
        difficulty: ['medium'],
        bloomLevel: ['understand'],
        questionTypes: ['mcq'],
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
      expect(mockPrismaQuestionPaper.create).not.toHaveBeenCalled()
    })

    it('stores arrays correctly', async () => {
      mockPrismaQuestionPaper.create.mockResolvedValue(createMockQuestionPaper())

      await createQuestionPaper({
        documentId: 'doc-123',
        duration: 30,
        numQuestions: 10,
        typeOfQp: 'practice',
        difficulty: ['easy', 'medium', 'hard'],
        bloomLevel: ['remember', 'understand', 'apply', 'analyze'],
        questionTypes: ['mcq', 'short', 'long'],
      })

      expect(mockPrismaQuestionPaper.create).toHaveBeenCalledWith({
        data: expect.objectContaining({
          difficulty: ['easy', 'medium', 'hard'],
          bloomLevel: ['remember', 'understand', 'apply', 'analyze'],
          questionTypes: ['mcq', 'short', 'long'],
        }),
      })
    })

    it('handles database error gracefully', async () => {
      mockPrismaQuestionPaper.create.mockRejectedValue(new Error('Database error'))

      const result = await createQuestionPaper({
        documentId: 'doc-123',
        duration: 30,
        numQuestions: 10,
        typeOfQp: 'practice',
        difficulty: ['medium'],
        bloomLevel: ['understand'],
        questionTypes: ['mcq'],
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Failed to create question paper')
    })
  })

  // ============================================
  // updateQuestionPaperStatus Tests
  // ============================================
  describe('updateQuestionPaperStatus()', () => {
    it('updates status when user owns the QP', async () => {
      mockPrismaQuestionPaper.findUnique.mockResolvedValue(
        createMockQuestionPaper({ userId: TEST_USER_ID })
      )
      mockPrismaQuestionPaper.update.mockResolvedValue(
        createMockQuestionPaper({ status: 'READY' })
      )

      const result = await updateQuestionPaperStatus('qp-123', 'READY')

      expect(result.success).toBe(true)
      expect(mockPrismaQuestionPaper.update).toHaveBeenCalledWith({
        where: { id: 'qp-123' },
        data: { status: 'READY' },
      })
    })

    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } })

      const result = await updateQuestionPaperStatus('qp-123', 'READY')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when QP not found', async () => {
      mockPrismaQuestionPaper.findUnique.mockResolvedValue(null)

      const result = await updateQuestionPaperStatus('non-existent', 'READY')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Question paper not found')
    })

    it('returns error when user does not own the QP', async () => {
      mockPrismaQuestionPaper.findUnique.mockResolvedValue(
        createMockQuestionPaper({ userId: OTHER_USER_ID })
      )

      const result = await updateQuestionPaperStatus('qp-123', 'READY')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
    })

    it('handles database error gracefully', async () => {
      mockPrismaQuestionPaper.findUnique.mockRejectedValue(new Error('Database error'))

      const result = await updateQuestionPaperStatus('qp-123', 'READY')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Failed to update status')
    })
  })

  // ============================================
  // createExamSession Tests
  // ============================================
  describe('createExamSession()', () => {
    beforeEach(() => {
      // Default: document and QP owned by test user
      mockPrismaDocument.findUnique.mockResolvedValue(
        createMockDocument({ userId: TEST_USER_ID })
      )
      mockPrismaQuestionPaper.findUnique.mockResolvedValue(
        createMockQuestionPaper({ userId: TEST_USER_ID })
      )
    })

    it('creates session with SCHEDULED status', async () => {
      const mockSession = createMockExamSession({
        status: 'SCHEDULED',
        userId: TEST_USER_ID,
      })
      mockPrismaExamSession.create.mockResolvedValue(mockSession)

      const result = await createExamSession({
        documentId: 'doc-123',
        questionPaperId: 'qp-123',
        threadId: 'thread-123',
        mode: 'EXAM',
      })

      expect(result.success).toBe(true)
      expect(result.examSession).toBeDefined()
      expect(mockPrismaExamSession.create).toHaveBeenCalledWith({
        data: expect.objectContaining({
          status: 'SCHEDULED',
          mode: 'EXAM',
          userId: TEST_USER_ID, // Derived from session
        }),
        include: expect.any(Object),
      })
    })

    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } })

      const result = await createExamSession({
        documentId: 'doc-123',
        questionPaperId: 'qp-123',
        threadId: 'thread-123',
        mode: 'EXAM',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when document not found', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(null)

      const result = await createExamSession({
        documentId: 'non-existent',
        questionPaperId: 'qp-123',
        threadId: 'thread-123',
        mode: 'EXAM',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Document not found')
    })

    it('returns error when user does not own document', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(
        createMockDocument({ userId: OTHER_USER_ID })
      )

      const result = await createExamSession({
        documentId: 'doc-123',
        questionPaperId: 'qp-123',
        threadId: 'thread-123',
        mode: 'EXAM',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
    })

    it('returns error when user does not own QP', async () => {
      mockPrismaQuestionPaper.findUnique.mockResolvedValue(
        createMockQuestionPaper({ userId: OTHER_USER_ID })
      )

      const result = await createExamSession({
        documentId: 'doc-123',
        questionPaperId: 'qp-123',
        threadId: 'thread-123',
        mode: 'EXAM',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
    })

    it('handles database error gracefully', async () => {
      mockPrismaExamSession.create.mockRejectedValue(new Error('Database error'))

      const result = await createExamSession({
        documentId: 'doc-123',
        questionPaperId: 'qp-123',
        threadId: 'thread-123',
        mode: 'EXAM',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Failed to create exam session')
    })
  })

  // ============================================
  // startExamSession Tests
  // ============================================
  describe('startExamSession()', () => {
    it('starts session when user owns it', async () => {
      mockPrismaExamSession.findUnique.mockResolvedValue(
        createMockExamSession({ userId: TEST_USER_ID, status: 'SCHEDULED' })
      )
      mockPrismaExamSession.update.mockResolvedValue(
        createMockExamSession({ status: 'IN_PROGRESS' })
      )

      const result = await startExamSession('session-123')

      expect(result.success).toBe(true)
      expect(mockPrismaExamSession.update).toHaveBeenCalledWith({
        where: { id: 'session-123' },
        data: expect.objectContaining({
          status: 'IN_PROGRESS',
          startedAt: expect.any(Date),
        }),
        include: expect.any(Object),
      })
    })

    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } })

      const result = await startExamSession('session-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when session not found', async () => {
      mockPrismaExamSession.findUnique.mockResolvedValue(null)

      const result = await startExamSession('non-existent')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Session not found')
    })

    it('returns error when user does not own session', async () => {
      mockPrismaExamSession.findUnique.mockResolvedValue(
        createMockExamSession({ userId: OTHER_USER_ID, status: 'SCHEDULED' })
      )

      const result = await startExamSession('session-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
    })

    it('returns error when session is not SCHEDULED', async () => {
      mockPrismaExamSession.findUnique.mockResolvedValue(
        createMockExamSession({ userId: TEST_USER_ID, status: 'IN_PROGRESS' })
      )

      const result = await startExamSession('session-123')

      expect(result.success).toBe(false)
      expect(result.error).toContain('cannot start')
    })

    it('handles database error gracefully', async () => {
      mockPrismaExamSession.findUnique.mockRejectedValue(new Error('Database error'))

      const result = await startExamSession('session-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Failed to start exam')
    })
  })

  // ============================================
  // getExamSessions Tests
  // ============================================
  describe('getExamSessions()', () => {
    it('returns sessions for authenticated user', async () => {
      const mockSessions = [
        createMockExamSession({ userId: TEST_USER_ID }),
        createMockExamSession({ userId: TEST_USER_ID }),
      ]
      mockPrismaExamSession.findMany.mockResolvedValue(mockSessions)

      const result = await getExamSessions()

      expect(result.success).toBe(true)
      expect(result.sessions).toHaveLength(2)
      expect(mockPrismaExamSession.findMany).toHaveBeenCalledWith({
        where: { userId: TEST_USER_ID },
        orderBy: { createdAt: 'desc' },
        include: expect.any(Object),
      })
    })

    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } })

      const result = await getExamSessions()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
      expect(result.sessions).toEqual([])
    })

    it('handles database error gracefully', async () => {
      mockPrismaExamSession.findMany.mockRejectedValue(new Error('Database error'))

      const result = await getExamSessions()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Failed to fetch sessions')
    })
  })

  // ============================================
  // getScheduledExams Tests
  // ============================================
  describe('getScheduledExams()', () => {
    it('returns only SCHEDULED sessions', async () => {
      const mockSessions = [
        createMockExamSession({ userId: TEST_USER_ID, status: 'SCHEDULED' }),
      ]
      mockPrismaExamSession.findMany.mockResolvedValue(mockSessions)

      const result = await getScheduledExams()

      expect(result.success).toBe(true)
      expect(mockPrismaExamSession.findMany).toHaveBeenCalledWith({
        where: { userId: TEST_USER_ID, status: 'SCHEDULED' },
        orderBy: { createdAt: 'desc' },
        include: expect.any(Object),
      })
    })

    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } })

      const result = await getScheduledExams()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })
  })

  // ============================================
  // getInProgressExams Tests
  // ============================================
  describe('getInProgressExams()', () => {
    it('returns only IN_PROGRESS sessions', async () => {
      const mockSessions = [
        createMockExamSession({ userId: TEST_USER_ID, status: 'IN_PROGRESS' }),
      ]
      mockPrismaExamSession.findMany.mockResolvedValue(mockSessions)

      const result = await getInProgressExams()

      expect(result.success).toBe(true)
      expect(mockPrismaExamSession.findMany).toHaveBeenCalledWith({
        where: { userId: TEST_USER_ID, status: 'IN_PROGRESS' },
        orderBy: { startedAt: 'asc' },
        include: expect.any(Object),
      })
    })
  })

  // ============================================
  // getCompletedExams Tests
  // ============================================
  describe('getCompletedExams()', () => {
    it('returns only COMPLETED sessions with reports', async () => {
      const mockSessions = [
        createMockExamSession({ userId: TEST_USER_ID, status: 'COMPLETED' }),
      ]
      mockPrismaExamSession.findMany.mockResolvedValue(mockSessions)

      const result = await getCompletedExams()

      expect(result.success).toBe(true)
      expect(mockPrismaExamSession.findMany).toHaveBeenCalledWith({
        where: { userId: TEST_USER_ID, status: 'COMPLETED' },
        orderBy: { endedAt: 'desc' },
        include: expect.objectContaining({
          report: true,
        }),
      })
    })
  })

  // ============================================
  // getExamSession Tests
  // ============================================
  describe('getExamSession()', () => {
    it('returns session when user owns it', async () => {
      const mockSession = createMockExamSession({ userId: TEST_USER_ID })
      mockPrismaExamSession.findUnique.mockResolvedValue(mockSession)

      const result = await getExamSession('session-123')

      expect(result.success).toBe(true)
      expect(result.session).toBeDefined()
    })

    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } })

      const result = await getExamSession('session-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when session not found', async () => {
      mockPrismaExamSession.findUnique.mockResolvedValue(null)

      const result = await getExamSession('non-existent')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Session not found')
    })

    it('returns error when user does not own session (IDOR prevention)', async () => {
      mockPrismaExamSession.findUnique.mockResolvedValue(
        createMockExamSession({ userId: OTHER_USER_ID })
      )

      const result = await getExamSession('session-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
    })

    it('handles database error gracefully', async () => {
      mockPrismaExamSession.findUnique.mockRejectedValue(new Error('Database error'))

      const result = await getExamSession('session-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Failed to fetch session')
    })
  })

  // ============================================
  // getUserDocuments Tests
  // ============================================
  describe('getUserDocuments()', () => {
    it('returns only READY documents for authenticated user', async () => {
      const mockDocs = [
        createMockDocument({ userId: TEST_USER_ID, status: 'READY' }),
        createMockDocument({ userId: TEST_USER_ID, status: 'READY' }),
      ]
      mockPrismaDocument.findMany.mockResolvedValue(mockDocs)

      const result = await getUserDocuments()

      expect(result.success).toBe(true)
      expect(result.documents).toHaveLength(2)
      expect(mockPrismaDocument.findMany).toHaveBeenCalledWith({
        where: { userId: TEST_USER_ID, status: 'READY' },
        orderBy: { createdAt: 'desc' },
      })
    })

    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } })

      const result = await getUserDocuments()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
      expect(result.documents).toEqual([])
    })

    it('handles database error gracefully', async () => {
      mockPrismaDocument.findMany.mockRejectedValue(new Error('Database error'))

      const result = await getUserDocuments()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Failed to fetch documents')
    })
  })
})
