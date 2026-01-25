/**
 * Server Action Tests - Document Actions
 *
 * Tests for app/actions/document.ts
 *
 * Covers:
 * 1. getDocuments - list user's documents
 * 2. createDocumentRecord - create new document
 * 3. deleteDocument - delete with cleanup
 * 4. getDocumentDetails - get with relations
 * 5. retryDocument - retry failed ingestion
 * 6. archiveDocument / restoreDocument - soft delete
 * 7. getDocumentFileUrl - get presigned URL
 * 8. getArchivedDocuments - list archived
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createMockDocument } from '../__mocks__/factories'

// ============================================
// Mock Setup - Use vi.hoisted to define mocks
// ============================================

const { mockGetUser, mockGetSession, mockPrismaDocument, mockFetch } = vi.hoisted(() => {
  return {
    mockGetUser: vi.fn(),
    mockGetSession: vi.fn(),
    mockPrismaDocument: {
      findMany: vi.fn(),
      findUnique: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    mockFetch: vi.fn(),
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
  },
}))

vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
}))

// Note: We use mockFetch directly in tests that need it
// Don't stubGlobal as it can interfere with other tests

// Import after mocking
import {
  getDocuments,
  createDocumentRecord,
  deleteDocument,
  getDocumentDetails,
  retryDocument,
  archiveDocument,
  restoreDocument,
  getDocumentFileUrl,
  getArchivedDocuments,
} from '@/app/actions/document'

describe('Document Server Actions', () => {
  // Store original fetch
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    vi.clearAllMocks()
    // Override fetch for this test suite
    globalThis.fetch = mockFetch

    // Default: authenticated user
    mockGetUser.mockResolvedValue({
      data: { user: { id: 'test-user-id', email: 'test@example.com' } },
      error: null,
    })
    mockGetSession.mockResolvedValue({
      data: {
        session: { access_token: 'mock-token' },
      },
      error: null,
    })

    // Default: fetch succeeds
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    })
  })

  afterEach(() => {
    // Restore original fetch to avoid polluting other tests
    globalThis.fetch = originalFetch
  })

  // ============================================
  // getDocuments Tests
  // ============================================
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

    it('returns only user own documents (not other users)', async () => {
      const mockDocs = [
        createMockDocument({ id: 'doc-1', title: 'My Doc 1' }),
        createMockDocument({ id: 'doc-2', title: 'My Doc 2' }),
      ]
      mockPrismaDocument.findMany.mockResolvedValue(mockDocs)

      const result = await getDocuments()

      expect(result.success).toBe(true)
      expect(result.documents).toHaveLength(2)

      // Verify query filters by userId
      expect(mockPrismaDocument.findMany).toHaveBeenCalledWith(
        expect.objectContaining({
          where: expect.objectContaining({
            userId: 'test-user-id',
          }),
        })
      )
    })

    it('filters out archived documents', async () => {
      mockPrismaDocument.findMany.mockResolvedValue([])

      await getDocuments()

      expect(mockPrismaDocument.findMany).toHaveBeenCalledWith(
        expect.objectContaining({
          where: expect.objectContaining({
            archivedAt: null,
          }),
        })
      )
    })

    it('returns empty array when no documents', async () => {
      mockPrismaDocument.findMany.mockResolvedValue([])

      const result = await getDocuments()

      expect(result.success).toBe(true)
      expect(result.documents).toEqual([])
    })

    it('handles database error gracefully', async () => {
      mockPrismaDocument.findMany.mockRejectedValue(new Error('Database error'))

      const result = await getDocuments()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Failed to fetch documents')
    })
  })

  // ============================================
  // createDocumentRecord Tests
  // ============================================
  describe('createDocumentRecord()', () => {
    it('creates document with PENDING status', async () => {
      mockPrismaDocument.create.mockResolvedValue({
        id: 'new-doc-123',
        status: 'PENDING',
      })

      const params = {
        title: 'New Document',
        fileKey: 'documents/test-user-id/new-doc.pdf',
        fileName: 'new-doc.pdf',
        fileSize: 1024000,
        mimeType: 'application/pdf',
        userId: 'test-user-id',
      }

      const result = await createDocumentRecord(params)

      expect(result.success).toBe(true)
      expect(result.docId).toBe('new-doc-123')

      expect(mockPrismaDocument.create).toHaveBeenCalledWith({
        data: expect.objectContaining({
          status: 'PENDING',
          title: 'New Document',
          userId: 'test-user-id',
        }),
      })
    })

    it('returns error on database failure', async () => {
      mockPrismaDocument.create.mockRejectedValue(new Error('Create failed'))

      const result = await createDocumentRecord({
        title: 'Test',
        fileKey: 'test',
        fileName: 'test.pdf',
        fileSize: 100,
        mimeType: 'application/pdf',
        userId: 'test-user-id',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Failed to start ingestion.')
    })
  })

  // ============================================
  // deleteDocument Tests
  // ============================================
  describe('deleteDocument()', () => {
    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: null,
      })

      const result = await deleteDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when document not found', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(null)

      const result = await deleteDocument('non-existent')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Document not found')
    })

    it('returns error when user does not own document (IDOR test)', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'other-user-id', // Different user!
        fileKey: 'documents/other-user/doc.pdf',
      })

      const result = await deleteDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
      expect(mockPrismaDocument.delete).not.toHaveBeenCalled()
    })

    it('calls Python API to cleanup Neo4j/R2', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'test-user-id',
        fileKey: 'documents/test-user/doc.pdf',
      })
      mockPrismaDocument.delete.mockResolvedValue({})

      await deleteDocument('doc-123')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/documents/doc-123'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })

    it('continues with Postgres deletion even if Python API fails', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'test-user-id',
        fileKey: 'documents/test-user/doc.pdf',
      })
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ error: 'Backend error' }),
      })
      mockPrismaDocument.delete.mockResolvedValue({})

      const result = await deleteDocument('doc-123')

      // Should still succeed and delete from Postgres
      expect(result.success).toBe(true)
      expect(mockPrismaDocument.delete).toHaveBeenCalled()
    })
  })

  // ============================================
  // getDocumentDetails Tests
  // ============================================
  describe('getDocumentDetails()', () => {
    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: null,
      })

      const result = await getDocumentDetails('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when document not found', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(null)

      const result = await getDocumentDetails('non-existent')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Document not found')
    })

    it('returns error when user does not own document (IDOR test)', async () => {
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

    it('returns full document with relations when owned', async () => {
      const mockDoc = {
        id: 'doc-123',
        userId: 'test-user-id',
        title: 'My Document',
        questionPapers: [{ id: 'qp-1', status: 'READY' }],
        examSessions: [{ id: 'session-1', status: 'COMPLETED' }],
        learnSessions: [],
      }
      mockPrismaDocument.findUnique.mockResolvedValue(mockDoc)

      const result = await getDocumentDetails('doc-123')

      expect(result.success).toBe(true)
      expect(result.document).toEqual(mockDoc)
    })
  })

  // ============================================
  // retryDocument Tests
  // ============================================
  describe('retryDocument()', () => {
    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: null,
      })

      const result = await retryDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when document not found', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(null)

      const result = await retryDocument('non-existent')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Document not found')
    })

    it('returns error when user does not own document (IDOR test)', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'other-user-id',
        status: 'FAILED',
      })

      const result = await retryDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
    })

    it('only allows FAILED or PENDING status', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'test-user-id',
        status: 'READY', // Cannot retry READY documents
      })

      const result = await retryDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toContain('Only FAILED or PENDING')
    })

    it('calls Python API to restart ingestion', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'test-user-id',
        status: 'FAILED',
      })
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, task_id: 'task-123' }),
      })

      const result = await retryDocument('doc-123')

      expect(result.success).toBe(true)
      expect(result.taskId).toBe('task-123')
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/documents/doc-123/retry'),
        expect.objectContaining({ method: 'POST' })
      )
    })
  })

  // ============================================
  // archiveDocument Tests
  // ============================================
  describe('archiveDocument()', () => {
    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: null,
      })

      const result = await archiveDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when document not found', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(null)

      const result = await archiveDocument('non-existent')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Document not found')
    })

    it('returns error when user does not own document (IDOR test)', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'other-user-id',
      })

      const result = await archiveDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
      expect(mockPrismaDocument.update).not.toHaveBeenCalled()
    })

    it('sets archivedAt timestamp when owned', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'test-user-id',
      })
      mockPrismaDocument.update.mockResolvedValue({})

      const result = await archiveDocument('doc-123')

      expect(result.success).toBe(true)
      expect(mockPrismaDocument.update).toHaveBeenCalledWith({
        where: { id: 'doc-123' },
        data: { archivedAt: expect.any(Date) },
      })
    })
  })

  // ============================================
  // restoreDocument Tests
  // ============================================
  describe('restoreDocument()', () => {
    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: null,
      })

      const result = await restoreDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when document not found', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(null)

      const result = await restoreDocument('non-existent')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Document not found')
    })

    it('returns error when user does not own document (IDOR test)', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'other-user-id',
        archivedAt: new Date(),
      })

      const result = await restoreDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
    })

    it('returns error when document is not archived', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'test-user-id',
        archivedAt: null, // Not archived
      })

      const result = await restoreDocument('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Document is not archived')
    })

    it('clears archivedAt when restoring', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'test-user-id',
        archivedAt: new Date(),
      })
      mockPrismaDocument.update.mockResolvedValue({})

      const result = await restoreDocument('doc-123')

      expect(result.success).toBe(true)
      expect(mockPrismaDocument.update).toHaveBeenCalledWith({
        where: { id: 'doc-123' },
        data: { archivedAt: null },
      })
    })
  })

  // ============================================
  // getDocumentFileUrl Tests
  // ============================================
  describe('getDocumentFileUrl()', () => {
    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: null,
      })

      const result = await getDocumentFileUrl('doc-123')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns error when document not found', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue(null)

      const result = await getDocumentFileUrl('non-existent')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Document not found')
    })

    it('returns error when user does not own document (IDOR test)', async () => {
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

    it('returns presigned URL from Python API', async () => {
      mockPrismaDocument.findUnique.mockResolvedValue({
        id: 'doc-123',
        userId: 'test-user-id',
        fileKey: 'documents/test.pdf',
        title: 'Test Document',
      })
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ url: 'https://r2.example.com/signed-url' }),
      })

      const result = await getDocumentFileUrl('doc-123')

      expect(result.success).toBe(true)
      expect(result.url).toBe('https://r2.example.com/signed-url')
    })
  })

  // ============================================
  // getArchivedDocuments Tests
  // ============================================
  describe('getArchivedDocuments()', () => {
    it('returns error when not authenticated', async () => {
      mockGetUser.mockResolvedValue({
        data: { user: null },
        error: null,
      })

      const result = await getArchivedDocuments()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Not authenticated')
    })

    it('returns only archived documents for the user', async () => {
      const archivedDocs = [
        createMockDocument({ id: 'doc-1', archivedAt: new Date() }),
      ]
      mockPrismaDocument.findMany.mockResolvedValue(archivedDocs)

      const result = await getArchivedDocuments()

      expect(result.success).toBe(true)
      expect(mockPrismaDocument.findMany).toHaveBeenCalledWith(
        expect.objectContaining({
          where: expect.objectContaining({
            userId: 'test-user-id',
            archivedAt: { not: null },
          }),
        })
      )
    })
  })
})
