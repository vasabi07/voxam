import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginForm from '@/components/login-form'

// Mock the auth-client module
const mockSignInEmail = vi.fn()
const mockSignInSocial = vi.fn()

vi.mock('@/lib/auth-client', () => ({
  signIn: {
    email: (credentials: unknown, callbacks: {
      onRequest?: () => void
      onResponse?: () => void
      onError?: (ctx: { error: { message: string } }) => void
      onSuccess?: () => void
    }) => {
      mockSignInEmail(credentials, callbacks)
      return Promise.resolve()
    },
    social: (options: unknown) => {
      mockSignInSocial(options)
      return Promise.resolve()
    },
  },
}))

// Mock router
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    refresh: vi.fn(),
  }),
}))

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders the login form', () => {
      render(<LoginForm />)

      expect(screen.getByText('Welcome back')).toBeInTheDocument()
      expect(screen.getByText('Sign in to your account')).toBeInTheDocument()
    })

    it('renders email and password inputs', () => {
      render(<LoginForm />)

      expect(screen.getByLabelText('Email')).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
    })

    it('renders login button', () => {
      render(<LoginForm />)

      expect(screen.getByRole('button', { name: 'Login' })).toBeInTheDocument()
    })

    it('renders Google sign-in button', () => {
      render(<LoginForm />)

      expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument()
    })

    it('renders link to register page', () => {
      render(<LoginForm />)

      const registerLink = screen.getByRole('link', { name: /create one/i })
      expect(registerLink).toBeInTheDocument()
      expect(registerLink).toHaveAttribute('href', '/register')
    })
  })

  describe('Form Validation', () => {
    it('shows inline error when email is empty', async () => {
      render(<LoginForm />)

      const submitButton = screen.getByRole('button', { name: 'Login' })
      await userEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument()
      })
    })

    it('shows inline error when password is empty', async () => {
      render(<LoginForm />)

      const emailInput = screen.getByLabelText('Email')
      await userEvent.type(emailInput, 'test@example.com')

      const submitButton = screen.getByRole('button', { name: 'Login' })
      await userEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Password is required')).toBeInTheDocument()
      })
    })

    it('shows inline error for invalid email format', async () => {
      render(<LoginForm />)

      const emailInput = screen.getByLabelText('Email')
      await userEvent.type(emailInput, 'invalid-email')

      const submitButton = screen.getByRole('button', { name: 'Login' })
      await userEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Invalid email address')).toBeInTheDocument()
      })
    })
  })

  describe('Form Submission', () => {
    it('calls signIn.email with correct credentials', async () => {
      render(<LoginForm />)

      await userEvent.type(screen.getByLabelText('Email'), 'test@example.com')
      await userEvent.type(screen.getByLabelText('Password'), 'password123')

      await userEvent.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(mockSignInEmail).toHaveBeenCalledWith(
          { email: 'test@example.com', password: 'password123' },
          expect.objectContaining({
            onRequest: expect.any(Function),
            onResponse: expect.any(Function),
            onError: expect.any(Function),
            onSuccess: expect.any(Function),
          })
        )
      })
    })

    it('disables button during pending state', async () => {
      // Mock signIn to simulate pending state
      mockSignInEmail.mockImplementation(async (credentials, callbacks) => {
        callbacks.onRequest?.()
        // Don't call onResponse to keep pending
        await new Promise(() => {}) // Never resolves
      })

      render(<LoginForm />)

      await userEvent.type(screen.getByLabelText('Email'), 'test@example.com')
      await userEvent.type(screen.getByLabelText('Password'), 'password123')

      const submitButton = screen.getByRole('button', { name: 'Login' })
      await userEvent.click(submitButton)

      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })
    })

    it('navigates to profile on successful login', async () => {
      mockSignInEmail.mockImplementation(async (credentials, callbacks) => {
        callbacks.onRequest?.()
        callbacks.onResponse?.()
        callbacks.onSuccess?.()
      })

      render(<LoginForm />)

      await userEvent.type(screen.getByLabelText('Email'), 'test@example.com')
      await userEvent.type(screen.getByLabelText('Password'), 'password123')

      await userEvent.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/profile')
      })
    })

    it('shows error toast on login failure', async () => {
      const { toast } = await import('sonner')

      mockSignInEmail.mockImplementation(async (credentials, callbacks) => {
        callbacks.onRequest?.()
        callbacks.onResponse?.()
        callbacks.onError?.({ error: { message: 'Invalid credentials' } })
      })

      render(<LoginForm />)

      await userEvent.type(screen.getByLabelText('Email'), 'test@example.com')
      await userEvent.type(screen.getByLabelText('Password'), 'wrongpassword')

      await userEvent.click(screen.getByRole('button', { name: 'Login' }))

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Invalid credentials')
      })
    })
  })

  describe('Social Sign-in', () => {
    it('calls signIn.social with Google provider', async () => {
      render(<LoginForm />)

      const googleButton = screen.getByRole('button', { name: /continue with google/i })
      await userEvent.click(googleButton)

      await waitFor(() => {
        expect(mockSignInSocial).toHaveBeenCalledWith({ provider: 'google' })
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper autocomplete attributes', () => {
      render(<LoginForm />)

      expect(screen.getByLabelText('Email')).toHaveAttribute('autocomplete', 'email')
      expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'current-password')
    })

    it('has proper input types', () => {
      render(<LoginForm />)

      expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password')
    })
  })
})
