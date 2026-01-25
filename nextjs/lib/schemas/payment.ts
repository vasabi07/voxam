import { z } from "zod"

export const regionSchema = z.enum(["india", "global"])

export const planIdSchema = z.enum([
  "starter_india",
  "pro_india",
  "topup_india",
  "starter_global",
  "pro_global",
  "topup_global",
])

export const createOrderSchema = z.object({
  planId: planIdSchema,
  region: regionSchema,
})

export const verifyPaymentSchema = z.object({
  razorpay_order_id: z.string().min(1, "Order ID is required"),
  razorpay_payment_id: z.string().min(1, "Payment ID is required"),
  razorpay_signature: z.string().min(1, "Signature is required"),
})

export type Region = z.infer<typeof regionSchema>
export type PlanId = z.infer<typeof planIdSchema>
export type CreateOrderInput = z.infer<typeof createOrderSchema>
export type VerifyPaymentInput = z.infer<typeof verifyPaymentSchema>
