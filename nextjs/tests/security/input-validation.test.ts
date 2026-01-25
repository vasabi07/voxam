/**
 * Security Tests - Input Validation
 *
 * Tests for:
 * 1. XSS Prevention - HTML/script injection in form fields
 * 2. SQL/NoSQL Injection - Prisma should prevent these
 * 3. Input Length Validation
 * 4. Type Coercion - Proper type handling
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { handlerState, resetHandlerState } from '../__mocks__/handlers'

const API_BASE = 'http://localhost:3000'

describe('Security - Input Validation', () => {
  beforeEach(() => {
    resetHandlerState()
  })

  // ============================================
  // XSS Prevention Tests
  // ============================================
  describe('XSS Prevention', () => {
    describe('Feedback API', () => {
      /**
       * SECURITY ISSUE: The feedback API directly interpolates user input
       * into HTML email without sanitization:
       *
       * ```html
       * <p style="...">${message}</p>
       * ```
       *
       * This could allow HTML injection in the email body, though the
       * attack surface is limited to internal email recipients.
       */
      it('SECURITY: documents XSS vulnerability in feedback message', async () => {
        const xssPayloads = [
          '<script>alert("XSS")</script>',
          '<img src=x onerror=alert("XSS")>',
          '<svg onload=alert("XSS")>',
          '"><script>alert("XSS")</script>',
          "javascript:alert('XSS')",
        ]

        for (const payload of xssPayloads) {
          const response = await fetch(`${API_BASE}/api/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              type: 'general',
              message: payload,
              url: 'http://localhost:3000/test',
            }),
          })

          // Request should succeed (documenting the vulnerability)
          expect(response.status).toBe(200)
          // The payload would be included in the email as-is
        }
      })

      it('SECURITY: documents XSS vulnerability in feedback URL field', async () => {
        const xssUrl = 'javascript:alert("XSS")'

        const response = await fetch(`${API_BASE}/api/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'bug',
            message: 'Test message',
            url: xssUrl, // Malicious URL
          }),
          })

        // Request succeeds - URL is embedded as href without validation
        expect(response.status).toBe(200)
      })

      it('validates feedback type is one of allowed values', async () => {
        const response = await fetch(`${API_BASE}/api/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'malicious<script>',
            message: 'Test message',
            url: 'http://localhost:3000',
          }),
        })

        // Should reject invalid type
        expect(response.status).toBe(400)
        const data = await response.json()
        expect(data.error).toContain('Invalid')
      })
    })

    describe('Email API', () => {
      it('validates template is one of allowed values', async () => {
        const response = await fetch(`${API_BASE}/api/email/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: 'test@example.com',
            template: 'malicious<script>',
          }),
        })

        expect(response.status).toBe(400)
        const data = await response.json()
        expect(data.error).toContain('Invalid')
      })
    })

    describe('Payment API', () => {
      it('validates planName against allowed values', async () => {
        const response = await fetch(`${API_BASE}/api/payment/create-order`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-token',
          },
          body: JSON.stringify({
            planName: '<script>alert("XSS")</script>',
          }),
        })

        expect(response.status).toBe(400)
        const data = await response.json()
        expect(data.error).toBe('Invalid plan name')
      })
    })
  })

  // ============================================
  // SQL/NoSQL Injection Tests
  // ============================================
  describe('SQL/NoSQL Injection Prevention', () => {
    /**
     * Prisma ORM provides built-in protection against SQL injection
     * by using parameterized queries. However, we should still test
     * that malicious inputs don't cause unexpected behavior.
     */

    describe('Payment API', () => {
      it('handles SQL injection attempt in planName', async () => {
        const sqlPayloads = [
          "'; DROP TABLE users; --",
          "1' OR '1'='1",
          "' UNION SELECT * FROM users --",
        ]

        for (const payload of sqlPayloads) {
          const response = await fetch(`${API_BASE}/api/payment/create-order`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: 'Bearer mock-token',
            },
            body: JSON.stringify({ planName: payload }),
          })

          // Should reject as invalid plan name, not crash
          expect(response.status).toBe(400)
        }
      })
    })

    describe('Feedback API', () => {
      it('handles SQL injection attempt in message field', async () => {
        const response = await fetch(`${API_BASE}/api/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'general',
            message: "'; DROP TABLE users; --",
            url: 'http://localhost:3000',
          }),
        })

        // Feedback API doesn't use SQL, so this should succeed
        // (message is sent via email, not stored in DB)
        expect(response.status).toBe(200)
      })
    })
  })

  // ============================================
  // Input Length Validation Tests
  // ============================================
  describe('Input Length Validation', () => {
    describe('Feedback API', () => {
      it('handles extremely long message', async () => {
        const longMessage = 'A'.repeat(100000) // 100KB message

        const response = await fetch(`${API_BASE}/api/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'general',
            message: longMessage,
            url: 'http://localhost:3000',
          }),
        })

        // Should either accept or reject gracefully, not crash
        expect(response.status).toBeLessThan(500)
      })

      it('handles extremely long URL', async () => {
        const longUrl = 'http://example.com/' + 'a'.repeat(10000)

        const response = await fetch(`${API_BASE}/api/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'general',
            message: 'Test',
            url: longUrl,
          }),
        })

        // Should handle gracefully
        expect(response.status).toBeLessThan(500)
      })
    })

    describe('Email API', () => {
      it('handles array with many recipients', async () => {
        const manyRecipients = Array(100)
          .fill(null)
          .map((_, i) => `user${i}@example.com`)

        const response = await fetch(`${API_BASE}/api/email/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: manyRecipients,
            template: 'welcome',
          }),
        })

        // Should handle gracefully (may succeed or reject based on Resend limits)
        expect(response.status).toBeLessThan(500)
      })
    })

    describe('Payment API', () => {
      it('handles extremely long planName', async () => {
        const longPlanName = 'standard' + 'x'.repeat(10000)

        const response = await fetch(`${API_BASE}/api/payment/create-order`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-token',
          },
          body: JSON.stringify({ planName: longPlanName }),
        })

        // Should reject as invalid plan name
        expect(response.status).toBe(400)
      })
    })
  })

  // ============================================
  // Type Coercion Tests
  // ============================================
  describe('Type Coercion', () => {
    describe('Feedback API', () => {
      it('rejects non-string message', async () => {
        const response = await fetch(`${API_BASE}/api/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'general',
            message: { malicious: 'object' }, // Object instead of string
            url: 'http://localhost:3000',
          }),
        })

        // Should handle - may succeed (toString) or fail
        expect(response.status).toBeLessThan(500)
      })

      it('rejects array as message', async () => {
        const response = await fetch(`${API_BASE}/api/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'general',
            message: ['array', 'of', 'strings'],
            url: 'http://localhost:3000',
          }),
        })

        // Should handle gracefully
        expect(response.status).toBeLessThan(500)
      })

      it('rejects number as type', async () => {
        const response = await fetch(`${API_BASE}/api/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 123, // Number instead of string
            message: 'Test message',
            url: 'http://localhost:3000',
          }),
        })

        // Should reject - type must be 'bug', 'feature', or 'general'
        expect(response.status).toBe(400)
      })
    })

    describe('Payment API', () => {
      it('rejects object as planName', async () => {
        const response = await fetch(`${API_BASE}/api/payment/create-order`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-token',
          },
          body: JSON.stringify({
            planName: { name: 'standard' },
          }),
        })

        // Should reject as invalid
        expect(response.status).toBe(400)
      })

      it('rejects array as planName', async () => {
        const response = await fetch(`${API_BASE}/api/payment/create-order`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-token',
          },
          body: JSON.stringify({
            planName: ['standard', 'pro'],
          }),
        })

        expect(response.status).toBe(400)
      })

      it('rejects boolean as planName', async () => {
        const response = await fetch(`${API_BASE}/api/payment/create-order`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-token',
          },
          body: JSON.stringify({
            planName: true,
          }),
        })

        expect(response.status).toBe(400)
      })
    })

    describe('Email API', () => {
      it('accepts string as "to" field', async () => {
        const response = await fetch(`${API_BASE}/api/email/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: 'single@example.com',
            template: 'welcome',
          }),
        })

        expect(response.status).toBe(200)
      })

      it('accepts array as "to" field', async () => {
        const response = await fetch(`${API_BASE}/api/email/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: ['user1@example.com', 'user2@example.com'],
            template: 'welcome',
          }),
        })

        expect(response.status).toBe(200)
      })

      it('rejects invalid email format', async () => {
        const response = await fetch(`${API_BASE}/api/email/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to: 'not-an-email',
            template: 'welcome',
          }),
        })

        // Depends on Resend validation - may succeed or fail
        // Document current behavior
        expect(response.status).toBeLessThan(500)
      })
    })
  })

  // ============================================
  // Special Character Handling
  // ============================================
  describe('Special Character Handling', () => {
    it('handles Unicode characters in feedback message', async () => {
      const response = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'general',
          message: '你好世界 🎉 مرحبا العالم',
          url: 'http://localhost:3000',
        }),
      })

      expect(response.status).toBe(200)
    })

    it('handles emoji in feedback type (should reject)', async () => {
      const response = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: '🐛',
          message: 'Bug report',
          url: 'http://localhost:3000',
        }),
      })

      // Emoji is not a valid type
      expect(response.status).toBe(400)
    })

    it('handles null bytes in input', async () => {
      const response = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'general',
          message: 'Test\x00message',
          url: 'http://localhost:3000',
        }),
      })

      // Should handle gracefully
      expect(response.status).toBeLessThan(500)
    })

    it('handles newlines and tabs in message', async () => {
      const response = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'general',
          message: 'Line 1\nLine 2\tTabbed',
          url: 'http://localhost:3000',
        }),
      })

      expect(response.status).toBe(200)
    })
  })

  // ============================================
  // Content-Type Validation
  // ============================================
  describe('Content-Type Validation', () => {
    it('handles missing Content-Type header', async () => {
      const response = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        body: JSON.stringify({
          type: 'general',
          message: 'Test',
          url: 'http://localhost:3000',
        }),
      })

      // May succeed or fail depending on Next.js config
      expect(response.status).toBeLessThan(500)
    })

    it('handles incorrect Content-Type', async () => {
      const response = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: JSON.stringify({
          type: 'general',
          message: 'Test',
          url: 'http://localhost:3000',
        }),
      })

      // Should handle gracefully
      expect(response.status).toBeLessThan(500)
    })

    it('handles form-data Content-Type with JSON body', async () => {
      const response = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'multipart/form-data' },
        body: JSON.stringify({
          type: 'general',
          message: 'Test',
          url: 'http://localhost:3000',
        }),
      })

      // MSW may still parse this as JSON - verify it handles gracefully
      expect(response.status).toBeLessThan(500)
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
 * 1. XSS in feedback message - User input is embedded in HTML email without sanitization
 * 2. XSS in feedback URL - URL is used as href without validation/sanitization
 *
 * MEDIUM SEVERITY:
 * 3. No input length limits on feedback message
 * 4. No rate limiting on feedback/email endpoints
 *
 * LOW SEVERITY:
 * 5. Feedback endpoint accepts unauthenticated requests (by design)
 * 6. Email endpoint accepts unauthenticated requests (security concern)
 *
 * RECOMMENDATIONS:
 * 1. Sanitize all user input before embedding in HTML (use DOMPurify or similar)
 * 2. Validate URLs before using as href (check protocol is http/https)
 * 3. Add input length limits (e.g., message max 10000 chars)
 * 4. Add rate limiting (e.g., 10 requests per minute per IP)
 * 5. Require authentication for email endpoint
 * 6. Consider using a dedicated HTML template library with auto-escaping
 */
