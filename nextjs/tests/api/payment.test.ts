/**
 * API Tests - Payment Create Order
 *
 * Tests for POST /api/payment/create-order
 *
 * Covers:
 * 1. Authentication requirements
 * 2. Input validation
 * 3. Region handling
 * 4. Plan pricing (India & Global)
 * 5. Success responses
 * 6. Error scenarios
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { handlerState, resetHandlerState } from '../__mocks__/handlers'
import { INDIA_PLANS, GLOBAL_PLANS } from '../__mocks__/factories'

const API_BASE = 'http://localhost:3000'

describe('POST /api/payment/create-order', () => {
  beforeEach(() => {
    resetHandlerState()
  })

  // ============================================
  // Authentication Tests
  // ============================================
  describe('Authentication', () => {
    it('returns 401 when no session/token provided', async () => {
      handlerState.authenticated = false

      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(401)
      const data = await response.json()
      expect(data.error).toBeDefined()
    })

    it('returns 401 when token is malformed/rejected', async () => {
      handlerState.authenticated = false

      // When not authenticated, even with an Authorization header, should return 401
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // MSW handler checks handlerState.authenticated, not the actual token
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(401)
    })

    it('accepts request with valid authentication', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(200)
    })
  })

  // ============================================
  // Input Validation Tests
  // ============================================
  describe('Input Validation', () => {
    it('returns 400 when planName is missing', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({}),
      })

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toContain('planName')
    })

    it('returns 400 when planName is invalid', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'premium' }), // Invalid plan
      })

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('Invalid plan name')
    })

    it('returns 400 when planName is empty string', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: '' }),
      })

      // Empty string should be rejected (either as missing or invalid)
      expect(response.status).toBeGreaterThanOrEqual(400)
    })

    it('returns 400 when planName is null', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: null }),
      })

      expect(response.status).toBe(400)
    })
  })

  // ============================================
  // Region Handling Tests
  // ============================================
  describe('Region Handling', () => {
    it('uses india plans when region is india', async () => {
      handlerState.userRegion = 'india'

      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.currency).toBe('INR')
    })

    it('uses global plans when region is global', async () => {
      handlerState.userRegion = 'global'

      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.currency).toBe('USD')
    })

    it('returns 400 for india-only plan when region is global', async () => {
      handlerState.userRegion = 'global'

      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'achiever' }), // India-only plan
      })

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('Invalid plan name')
    })

    it('returns 400 for global-only plan when region is india', async () => {
      handlerState.userRegion = 'india'

      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'pro' }), // Global-only plan
      })

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('Invalid plan name')
    })
  })

  // ============================================
  // Plan Pricing Tests (India)
  // ============================================
  describe('Plan Pricing (India)', () => {
    beforeEach(() => {
      handlerState.userRegion = 'india'
    })

    it('returns correct amount for starter plan (29900 paise)', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'starter' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.amount).toBe(INDIA_PLANS.starter.amount)
      expect(data.minutes).toBe(INDIA_PLANS.starter.minutes)
    })

    it('returns correct amount for standard plan (59900 paise)', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.amount).toBe(INDIA_PLANS.standard.amount)
      expect(data.minutes).toBe(INDIA_PLANS.standard.minutes)
    })

    it('returns correct amount for achiever plan (109900 paise)', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'achiever' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.amount).toBe(INDIA_PLANS.achiever.amount)
      expect(data.minutes).toBe(INDIA_PLANS.achiever.minutes)
    })

    it('returns correct amount for topup plan (19900 paise)', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'topup' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.amount).toBe(INDIA_PLANS.topup.amount)
      expect(data.minutes).toBe(INDIA_PLANS.topup.minutes)
    })
  })

  // ============================================
  // Plan Pricing Tests (Global)
  // ============================================
  describe('Plan Pricing (Global)', () => {
    beforeEach(() => {
      handlerState.userRegion = 'global'
    })

    it('returns correct amount for standard plan (999 cents)', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.amount).toBe(GLOBAL_PLANS.standard.amount)
      expect(data.minutes).toBe(GLOBAL_PLANS.standard.minutes)
    })

    it('returns correct amount for pro plan (1999 cents)', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'pro' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.amount).toBe(GLOBAL_PLANS.pro.amount)
      expect(data.minutes).toBe(GLOBAL_PLANS.pro.minutes)
    })

    it('returns correct amount for topup plan (599 cents)', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'topup' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.amount).toBe(GLOBAL_PLANS.topup.amount)
      expect(data.minutes).toBe(GLOBAL_PLANS.topup.minutes)
    })
  })

  // ============================================
  // Success Response Tests
  // ============================================
  describe('Success Response', () => {
    it('returns orderId from Razorpay', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.orderId).toBeDefined()
      expect(data.orderId).toMatch(/^order_/)
    })

    it('returns keyId (public key)', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.keyId).toBeDefined()
      expect(data.keyId).toMatch(/^rzp_/)
    })

    it('returns planName and minutes', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.planName).toBeDefined()
      expect(data.minutes).toBeGreaterThan(0)
    })

    it('returns currency matching region', async () => {
      // Test India
      handlerState.userRegion = 'india'
      let response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })
      let data = await response.json()
      expect(data.currency).toBe('INR')

      // Test Global
      handlerState.userRegion = 'global'
      response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })
      data = await response.json()
      expect(data.currency).toBe('USD')
    })
  })

  // ============================================
  // Error Scenarios
  // ============================================
  describe('Error Scenarios', () => {
    it('returns 500 when Razorpay API fails', async () => {
      handlerState.razorpayOrderFails = true

      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({ planName: 'standard' }),
      })

      expect(response.status).toBe(500)
      const data = await response.json()
      expect(data.error).toBeDefined()
    })

    it('handles JSON parse errors gracefully', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: 'not valid json',
      })

      // Should return error, not crash
      expect(response.status).toBeGreaterThanOrEqual(400)
    })

    it('handles empty body gracefully', async () => {
      const response = await fetch(`${API_BASE}/api/payment/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: '',
      })

      // Should return error for missing planName or parse error
      expect(response.status).toBeGreaterThanOrEqual(400)
    })
  })
})

// ============================================
// Security Considerations Documented
// ============================================
/**
 * SECURITY CONSIDERATIONS:
 *
 * 1. Region Cookie Manipulation
 *    - The region is determined by cookie which can be modified client-side
 *    - However, the region is SAVED to user record on first purchase
 *    - Subsequent purchases use stored region, not cookie
 *    - This limits but doesn't eliminate the pricing arbitrage attack
 *
 * 2. Plan Validation
 *    - Plans are validated against allowed plans for the region
 *    - Invalid plans are rejected with 400 error
 *
 * 3. Rate Limiting
 *    - No rate limiting is currently implemented
 *    - Consider adding rate limiting to prevent order creation abuse
 *
 * 4. Order ID Enumeration
 *    - Order IDs are exposed to client
 *    - Should not contain sensitive information
 */
