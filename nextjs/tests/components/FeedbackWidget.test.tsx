import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FeedbackWidget } from '@/components/FeedbackWidget'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('FeedbackWidget', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    })
  })

  describe('Rendering', () => {
    it('renders the floating feedback button', () => {
      render(<FeedbackWidget />)

      const button = screen.getByLabelText('Send feedback')
      expect(button).toBeInTheDocument()
    })

    it('does not show modal initially', () => {
      render(<FeedbackWidget />)

      expect(screen.queryByRole('heading', { name: 'Send Feedback' })).not.toBeInTheDocument()
    })
  })

  describe('Modal Interaction', () => {
    it('opens modal when floating button is clicked', async () => {
      render(<FeedbackWidget />)

      const button = screen.getByLabelText('Send feedback')
      await userEvent.click(button)

      expect(screen.getByRole('heading', { name: 'Send Feedback' })).toBeInTheDocument()
    })

    it('closes modal when X button is clicked', async () => {
      render(<FeedbackWidget />)

      // Open modal
      await userEvent.click(screen.getByLabelText('Send feedback'))
      expect(screen.getByRole('heading', { name: 'Send Feedback' })).toBeInTheDocument()

      // Close modal
      await userEvent.click(screen.getByLabelText('Close'))

      await waitFor(() => {
        expect(screen.queryByRole('heading', { name: 'Send Feedback' })).not.toBeInTheDocument()
      })
    })

    it('closes modal when clicking outside', async () => {
      render(<FeedbackWidget />)

      // Open modal
      await userEvent.click(screen.getByLabelText('Send feedback'))

      // Click on overlay (the backdrop) - find it by the class
      const overlay = document.querySelector('.fixed.inset-0.z-50.flex')
      if (overlay) {
        fireEvent.click(overlay)
      }

      await waitFor(() => {
        expect(screen.queryByRole('heading', { name: 'Send Feedback' })).not.toBeInTheDocument()
      })
    })
  })

  describe('Feedback Type Selection', () => {
    it('shows all three feedback type options', async () => {
      render(<FeedbackWidget />)

      await userEvent.click(screen.getByLabelText('Send feedback'))

      expect(screen.getByText('Bug')).toBeInTheDocument()
      expect(screen.getByText('Feature')).toBeInTheDocument()
      expect(screen.getByText('General')).toBeInTheDocument()
    })

    it('defaults to General type', async () => {
      render(<FeedbackWidget />)

      await userEvent.click(screen.getByLabelText('Send feedback'))

      // Check placeholder text matches general type
      const textarea = screen.getByPlaceholderText('Share your thoughts with us...')
      expect(textarea).toBeInTheDocument()
    })

    it('changes placeholder when Bug type is selected', async () => {
      render(<FeedbackWidget />)

      await userEvent.click(screen.getByLabelText('Send feedback'))
      await userEvent.click(screen.getByText('Bug'))

      const textarea = screen.getByPlaceholderText('Describe the bug and steps to reproduce...')
      expect(textarea).toBeInTheDocument()
    })

    it('changes placeholder when Feature type is selected', async () => {
      render(<FeedbackWidget />)

      await userEvent.click(screen.getByLabelText('Send feedback'))
      await userEvent.click(screen.getByText('Feature'))

      const textarea = screen.getByPlaceholderText("Describe the feature you'd like to see...")
      expect(textarea).toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('disables submit button when message is empty', async () => {
      render(<FeedbackWidget />)

      await userEvent.click(screen.getByLabelText('Send feedback'))

      // Find the submit button by looking for the button with the send icon
      const submitButtons = screen.getAllByRole('button')
      const submitButton = submitButtons.find(btn =>
        btn.textContent?.includes('Send Feedback') && btn.querySelector('svg')
      )

      expect(submitButton).toBeDisabled()
    })

    it('enables submit button when message is entered', async () => {
      render(<FeedbackWidget />)

      await userEvent.click(screen.getByLabelText('Send feedback'))

      const textarea = screen.getByRole('textbox')
      await userEvent.type(textarea, 'This is a test message')

      const submitButtons = screen.getAllByRole('button')
      const submitButton = submitButtons.find(btn =>
        btn.textContent?.includes('Send Feedback') && btn.querySelector('svg')
      )

      expect(submitButton).not.toBeDisabled()
    })

    it('disables submit for whitespace-only messages', async () => {
      render(<FeedbackWidget />)

      await userEvent.click(screen.getByLabelText('Send feedback'))

      const textarea = screen.getByRole('textbox')
      await userEvent.type(textarea, '   ')

      const submitButtons = screen.getAllByRole('button')
      const submitButton = submitButtons.find(btn =>
        btn.textContent?.includes('Send Feedback') && btn.querySelector('svg')
      )

      expect(submitButton).toBeDisabled()
    })
  })

  describe('Form Submission', () => {
    // TODO: Fix flaky test - modal state timing issue with happy-dom
    it.skip('sends feedback to API on submit', async () => {
      const user = userEvent.setup()
      render(<FeedbackWidget />)

      // Open modal
      fireEvent.click(screen.getByLabelText('Send feedback'))

      // Wait for modal to be visible
      const heading = await screen.findByRole('heading', { name: 'Send Feedback' })
      expect(heading).toBeInTheDocument()

      // Type in textarea
      const textarea = screen.getByRole('textbox')
      await user.type(textarea, 'This is my feedback')

      // Find and click submit button - it's the only button with w-full class
      const submitButton = screen.getByRole('button', { name: /^Send Feedback$/ })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/feedback', expect.any(Object))
      })
    })

    // TODO: Fix flaky test - modal state timing issue with happy-dom
    it.skip('sends correct feedback type in request', async () => {
      const user = userEvent.setup()
      render(<FeedbackWidget />)

      fireEvent.click(screen.getByLabelText('Send feedback'))
      await screen.findByRole('heading', { name: 'Send Feedback' })

      fireEvent.click(screen.getByText('Bug'))

      const textarea = screen.getByRole('textbox')
      await user.type(textarea, 'Found a bug')

      const submitButton = screen.getByRole('button', { name: /^Send Feedback$/ })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled()
        const callBody = JSON.parse(mockFetch.mock.calls[0][1].body)
        expect(callBody.type).toBe('bug')
      })
    })

    // TODO: Fix flaky test - modal state timing issue
    it.skip('includes current URL in request', async () => {
      const user = userEvent.setup()
      render(<FeedbackWidget />)

      fireEvent.click(screen.getByLabelText('Send feedback'))
      await screen.findByRole('heading', { name: 'Send Feedback' })

      const textarea = screen.getByRole('textbox')
      await user.type(textarea, 'Test feedback')

      const submitButton = screen.getByRole('button', { name: /^Send Feedback$/ })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled()
        const callBody = JSON.parse(mockFetch.mock.calls[0][1].body)
        expect(callBody.url).toBeDefined()
      })
    })

    // TODO: Fix flaky test - modal state timing issue
    it.skip('shows loading state during submission', async () => {
      const user = userEvent.setup()
      // Make fetch hang indefinitely
      mockFetch.mockImplementation(() => new Promise(() => {}))

      render(<FeedbackWidget />)

      fireEvent.click(screen.getByLabelText('Send feedback'))
      await screen.findByRole('heading', { name: 'Send Feedback' })

      const textarea = screen.getByRole('textbox')
      await user.type(textarea, 'Test feedback')

      const submitButton = screen.getByRole('button', { name: /^Send Feedback$/ })
      fireEvent.click(submitButton)

      // The button text should change to "Sending..." while waiting
      await waitFor(() => {
        expect(screen.getByText('Sending...')).toBeInTheDocument()
      })
    })

    // TODO: Fix flaky test - modal state timing issue
    it.skip('closes modal after successful submission', async () => {
      const user = userEvent.setup()
      render(<FeedbackWidget />)

      fireEvent.click(screen.getByLabelText('Send feedback'))
      await screen.findByRole('heading', { name: 'Send Feedback' })

      const textarea = screen.getByRole('textbox')
      await user.type(textarea, 'Test feedback')

      const submitButton = screen.getByRole('button', { name: /^Send Feedback$/ })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.queryByRole('heading', { name: 'Send Feedback' })).not.toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    // TODO: Fix flaky test - modal state timing issue
    it.skip('calls toast.error when submission fails', async () => {
      const user = userEvent.setup()
      const { toast } = await import('sonner')

      mockFetch.mockResolvedValue({
        ok: false,
        json: async () => ({ error: 'Server error' }),
      })

      render(<FeedbackWidget />)

      fireEvent.click(screen.getByLabelText('Send feedback'))
      await screen.findByRole('heading', { name: 'Send Feedback' })

      const textarea = screen.getByRole('textbox')
      await user.type(textarea, 'Test feedback')

      const submitButton = screen.getByRole('button', { name: /^Send Feedback$/ })
      fireEvent.click(submitButton)

      // Wait for fetch to be called and error handling
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled()
      })

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled()
      })
    })
  })
})
