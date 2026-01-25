import { NextRequest, NextResponse } from 'next/server';
import { verifyWebhookSignature } from '@/lib/razorpay';
import { db } from '@/lib/prisma';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type WebhookPayload = any;

/**
 * POST /api/webhooks/payment
 * Handles Razorpay webhook for one-time payments
 */
export async function POST(request: NextRequest) {
    try {
        const body = await request.text();
        const signature = request.headers.get('x-razorpay-signature');

        if (!signature) {
            console.error('Webhook: Missing signature');
            return NextResponse.json({ error: 'Missing signature' }, { status: 400 });
        }

        // Verify signature
        const isValid = verifyWebhookSignature(body, signature);
        if (!isValid) {
            console.error('Webhook: Invalid signature');
            return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
        }

        const payload = JSON.parse(body);
        const eventType = payload.event;

        console.log(`Payment webhook received: ${eventType}`);

        switch (eventType) {
            case 'payment.captured':
                await handlePaymentCaptured(payload);
                break;

            case 'payment.failed':
                await handlePaymentFailed(payload);
                break;

            default:
                console.log(`Unhandled webhook event: ${eventType}`);
        }

        return NextResponse.json({ received: true });

    } catch (error) {
        console.error('Webhook error:', error);
        return NextResponse.json(
            { error: 'Webhook processing failed' },
            { status: 500 }
        );
    }
}

/**
 * Handle successful payment - grant minutes to user
 */
async function handlePaymentCaptured(payload: WebhookPayload) {
    const payment = payload.payload.payment.entity;
    const paymentId = payment.id;
    const orderId = payment.order_id;
    const notes = payment.notes || {};

    const userId = notes.userId;
    const minutes = parseInt(notes.minutes || '0');
    const pages = parseInt(notes.pages || '0');
    const chatMessages = parseInt(notes.chatMessages || '0');
    const planName = notes.planName;
    const region = notes.region;

    if (!userId) {
        console.error('Payment captured but no userId in notes:', orderId);
        return;
    }

    // Idempotency check: skip if this payment was already processed
    const existingTransaction = await db.transaction.findUnique({
        where: { razorpayPaymentId: paymentId },
    });

    if (existingTransaction) {
        console.log(`Payment ${paymentId} already processed, skipping duplicate webhook`);
        return;
    }

    console.log(`Payment captured for user ${userId}: ${minutes} mins, ${pages} pages, ${chatMessages} chat messages`);

    // Update user's balance
    const user = await db.user.findUnique({ where: { id: userId } });

    if (!user) {
        console.error('User not found:', userId);
        return;
    }

    // Add credits to user's balance
    await db.user.update({
        where: { id: userId },
        data: {
            voiceMinutesLimit: (user.voiceMinutesLimit || 0) + minutes,
            pagesLimit: (user.pagesLimit || 0) + pages,
            chatMessagesLimit: (user.chatMessagesLimit || 0) + chatMessages,
        },
    });

    // Create transaction record
    await db.transaction.create({
        data: {
            userId: userId,
            razorpayPaymentId: payment.id,
            razorpayOrderId: orderId,
            amount: payment.amount,
            currency: payment.currency || 'INR',
            status: 'SUCCESS',
            type: 'PACK_PURCHASE',
            metadata: {
                planName,
                minutes,
                pages,
                chatMessages,
                region,
            },
        },
    });

    console.log(`User ${userId} credited: ${minutes} mins, ${pages} pages, ${chatMessages} chat messages`);
}

/**
 * Handle failed payment
 */
async function handlePaymentFailed(payload: WebhookPayload) {
    const payment = payload.payload.payment.entity;
    const notes = payment.notes || {};

    console.log(`Payment failed for user ${notes.userId}:`, payment.error_description);

    // Optionally create a failed transaction record
    if (notes.userId) {
        await db.transaction.create({
            data: {
                userId: notes.userId,
                razorpayPaymentId: payment.id,
                razorpayOrderId: payment.order_id,
                amount: payment.amount,
                currency: payment.currency || 'INR',
                status: 'FAILED',
                type: 'PACK_PURCHASE',
                metadata: {
                    error: payment.error_description,
                },
            },
        });
    }
}
