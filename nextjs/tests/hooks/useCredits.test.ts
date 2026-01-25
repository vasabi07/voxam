import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'

// Mock the module before importing the hook
vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: {
          session: {
            access_token: 'mock-token',
            user: { id: 'test-user-id' },
          },
        },
        error: null,
      }),
    },
  })),
}))

// Now import after mocking
import { useCredits } from '@/hooks/useCredits'
import { createClient } from '@/lib/supabase/client'

const mockCreditsResponse = {
  voiceMinutes: { used: 10, limit: 60, remaining: 50 },
  chatMessages: { used: 100, limit: 1000, remaining: 900 },
  pages: { used: 5, limit: 50, remaining: 45 },
}

describe('useCredits', () => {
  let originalFetch: typeof global.fetch

  beforeEach(() => {
    vi.useFakeTimers()
    // Save original fetch
    originalFetch = global.fetch
    // Mock fetch
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockCreditsResponse,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    // Restore original fetch
    global.fetch = originalFetch
    vi.clearAllMocks()
  })

  describe('Initial State', () => {
    it('starts with loading state', () => {
      const { result } = renderHook(() => useCredits(0))

      expect(result.current.loading).toBe(true)
      expect(result.current.credits).toBeNull()
      expect(result.current.error).toBeNull()
    })
  })

  describe('Successful Fetch', () => {
    it('fetches credits and updates state', async () => {
      vi.useRealTimers()

      const { result } = renderHook(() => useCredits(0))

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.credits).toEqual(mockCreditsResponse)
      expect(result.current.error).toBeNull()
    })

    it('includes auth token in request', async () => {
      vi.useRealTimers()

      renderHook(() => useCredits(0))

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled()
      })

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/credits'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer mock-token',
          }),
        })
      )
    })
  })

  describe('Error Handling', () => {
    it('sets error when API returns non-ok response', async () => {
      vi.useRealTimers()

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
      })

      const { result } = renderHook(() => useCredits(0))

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.error).toContain('Failed to fetch credits')
      expect(result.current.credits).toBeNull()
    })

    it('sets error when network fails', async () => {
      vi.useRealTimers()

      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useCredits(0))

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.error).toBe('Network error')
      expect(result.current.credits).toBeNull()
    })

    it('sets error when not authenticated', async () => {
      vi.useRealTimers()

      // Mock no session
      vi.mocked(createClient).mockReturnValue({
        auth: {
          getSession: vi.fn().mockResolvedValue({
            data: { session: null },
            error: null,
          }),
        },
      } as unknown as ReturnType<typeof createClient>)

      const { result } = renderHook(() => useCredits(0))

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.error).toBe('Not authenticated')
    })
  })

  describe('Auto-refresh', () => {
    it('accepts auto-refresh interval parameter', () => {
      // Just verify the hook accepts the parameter without errors
      const { result } = renderHook(() => useCredits(60000))
      expect(result.current).toBeDefined()
    })

    it('works with auto-refresh disabled', () => {
      const { result } = renderHook(() => useCredits(0))
      expect(result.current).toBeDefined()
    })
  })

  describe('Refetch', () => {
    it('provides refetch function', async () => {
      vi.useRealTimers()

      const { result } = renderHook(() => useCredits(0))

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(typeof result.current.refetch).toBe('function')
    })
  })
})
