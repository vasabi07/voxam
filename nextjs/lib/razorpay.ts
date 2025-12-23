import Razorpay from 'razorpay';

// Initialize Razorpay client
export const razorpay = new Razorpay({
    key_id: process.env.RAZORPAY_KEY_ID!,
    key_secret: process.env.RAZORPAY_KEY_SECRET!,
});

// Webhook secret for signature verification
export const RAZORPAY_WEBHOOK_SECRET = process.env.RAZORPAY_WEBHOOK_SECRET!;

// Helper to verify webhook signature
import crypto from 'crypto';

export function verifyWebhookSignature(
    body: string,
    signature: string
): boolean {
    const expectedSignature = crypto
        .createHmac('sha256', RAZORPAY_WEBHOOK_SECRET)
        .update(body)
        .digest('hex');

    return expectedSignature === signature;
}
