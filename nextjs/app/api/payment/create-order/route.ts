import { NextRequest, NextResponse } from 'next/server';
import { razorpay } from '@/lib/razorpay';
import { db } from '@/lib/prisma';
import { getClaims } from '@/lib/session';

/**
 * Plan definitions for one-time purchases
 * No Razorpay dashboard setup needed - all defined in code
 *
 * Pricing based on cost analysis:
 * - India: ~38-50% margin after costs
 * - Global: ~42-72% margin after costs
 *
 * Amount in paise (INR) or cents (USD)
 */
const PLANS = {
    india: {
        starter: { name: 'Starter', amount: 39900, currency: 'INR', minutes: 100, pages: 100, chatMessages: 500 },
        standard: { name: 'Standard', amount: 69900, currency: 'INR', minutes: 200, pages: 250, chatMessages: 1000 },
        achiever: { name: 'Achiever', amount: 129900, currency: 'INR', minutes: 350, pages: 500, chatMessages: 1500 },
        topup: { name: 'Top-Up', amount: 19900, currency: 'INR', minutes: 60, pages: 0, chatMessages: 0 },
    },
    global: {
        starter: { name: 'Starter', amount: 999, currency: 'USD', minutes: 120, pages: 150, chatMessages: 500 },
        standard: { name: 'Standard', amount: 1999, currency: 'USD', minutes: 250, pages: 350, chatMessages: 1000 },
        achiever: { name: 'Achiever', amount: 2999, currency: 'USD', minutes: 400, pages: 700, chatMessages: 1500 },
        topup: { name: 'Top-Up', amount: 599, currency: 'USD', minutes: 60, pages: 0, chatMessages: 0 },
    }
};

/**
 * POST /api/payment/create-order
 * Creates a Razorpay order for one-time payment
 * 
 * Body: { planName: 'starter' | 'standard' | 'achiever' | 'topup' }
 * Region is determined by cookie or request header
 */
export async function POST(request: NextRequest) {
    try {
        // Get authenticated user
        const claims = await getClaims();
        if (!claims?.sub) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const userId = claims.sub;
        const { planName } = await request.json();

        if (!planName) {
            return NextResponse.json(
                { error: 'planName is required' },
                { status: 400 }
            );
        }

        // Determine region:
        // 1. For new users: Use cookie (set by middleware geo-detection)
        // 2. For existing users: Use stored User.region from DB
        const cookieRegion = request.cookies.get('region')?.value || 'india';

        // Upsert user, saving region on first create
        const user = await db.user.upsert({
            where: { id: userId },
            update: {},
            create: {
                id: userId,
                email: claims.email || '',
                name: claims.email?.split('@')[0] || 'User',
                region: cookieRegion,  // Save detected region on signup
            },
        });

        // Use stored region for pricing (not current location)
        const region = user.region || cookieRegion;
        const plans = region === 'india' ? PLANS.india : PLANS.global;

        const plan = plans[planName as keyof typeof plans];
        if (!plan) {
            return NextResponse.json(
                { error: 'Invalid plan name' },
                { status: 400 }
            );
        }

        // Create Razorpay order
        const order = await razorpay.orders.create({
            amount: plan.amount,
            currency: plan.currency,
            receipt: `ord_${Date.now()}`,  // Max 40 chars
            notes: {
                userId: userId,
                planName: planName,
                region: region,
                minutes: plan.minutes.toString(),
                pages: plan.pages.toString(),
                chatMessages: plan.chatMessages.toString(),
            },
        });

        return NextResponse.json({
            success: true,
            orderId: order.id,
            amount: order.amount,
            currency: order.currency,
            planName: plan.name,
            minutes: plan.minutes,
            keyId: process.env.RAZORPAY_KEY_ID,
        });

    } catch (error: unknown) {
        console.error('Error creating order:', error);
        const errorMessage = error instanceof Error ? error.message : 'Failed to create order';
        return NextResponse.json(
            { error: errorMessage },
            { status: 500 }
        );
    }
}
