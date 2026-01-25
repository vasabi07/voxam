import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll, vi } from 'vitest'
import { server } from './__mocks__/server'

// ============================================
// Mock Next.js modules
// ============================================

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/authenticated/documents',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}))

// Mock next/headers (for server components/actions)
vi.mock('next/headers', () => ({
  headers: () => new Map(),
  cookies: () => ({
    get: vi.fn(),
    set: vi.fn(),
    delete: vi.fn(),
  }),
}))

// ============================================
// Mock Supabase client
// ============================================
vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: {
          session: {
            user: {
              id: 'test-user-id',
              email: 'test@example.com',
            },
            access_token: 'mock-token',
          },
        },
        error: null,
      }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: {
              id: 'test-user-id',
              pagesRemaining: 100,
              voiceMinutes: 60,
            },
            error: null,
          }),
        }),
      }),
    }),
    channel: vi.fn().mockReturnValue({
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockReturnValue({ unsubscribe: vi.fn() }),
    }),
  }),
}))

// ============================================
// Mock auth-client
// ============================================
vi.mock('@/lib/auth-client', () => ({
  useSession: () => ({
    data: {
      user: {
        id: 'test-user-id',
        email: 'test@example.com',
        name: 'Test User',
      },
      session: {
        access_token: 'mock-token',
      },
    },
    isPending: false,
    error: null,
  }),
  authClient: {
    signIn: {
      email: vi.fn(),
    },
    signUp: {
      email: vi.fn(),
    },
    signOut: vi.fn(),
  },
}))

// ============================================
// Mock sonner toast
// ============================================
vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
    loading: vi.fn(),
    promise: vi.fn(),
    dismiss: vi.fn(),
  }),
  Toaster: () => null,
}))

// ============================================
// MSW Server Lifecycle
// ============================================

// Start server before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'bypass' })
})

// Reset handlers after each test
afterEach(() => {
  server.resetHandlers()
  vi.clearAllMocks()
})

// Close server after all tests
afterAll(() => {
  server.close()
})

// ============================================
// Global test utilities
// ============================================

// Suppress console errors in tests (optional)
// vi.spyOn(console, 'error').mockImplementation(() => {})

// Add custom matchers or utilities here if needed
