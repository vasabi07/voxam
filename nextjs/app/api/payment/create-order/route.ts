import { NextRequest, NextResponse } from 'next/server';
import { razorpay } from '@/lib/razorpay';
import { db } from '@/lib/prisma';
import { getClaims } from '@/lib/session';

/**
 * Plan definitions for one-time purchases
 * No Razorpay dashboard setup needed - all defined in code
 */
const PLANS = {
    india: {
        starter: { name: 'Starter', amount: 29900, currency: 'INR', minutes: 90, pages: 50 },
        standard: { name: 'Standard', amount: 59900, currency: 'INR', minutes: 250, pages: 200 },
        achiever: { name: 'Achiever', amount: 109900, currency: 'INR', minutes: 500, pages: 500 },
        topup: { name: 'Top-Up', amount: 19900, currency: 'INR', minutes: 60, pages: 0 },
    },
    global: {
        starter: { name: 'Standard', amount: 999, currency: 'USD', minutes: 120, pages: 100 },
        standard: { name: 'Pro Scholar', amount: 1999, currency: 'USD', minutes: 300, pages: 300 },
        topup: { name: 'Top-Up', amount: 599, currency: 'USD', minutes: 60, pages: 0 },
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

        // Determine region from query param (for testing) or cookie (set by middleware)
        const url = new URL(request.url);
        const region = url.searchParams.get('region') || request.cookies.get('region')?.value || 'india';
        const plans = region === 'india' ? PLANS.india : PLANS.global;

        const plan = plans[planName as keyof typeof plans];
        if (!plan) {
            return NextResponse.json(
                { error: 'Invalid plan name' },
                { status: 400 }
            );
        }

        // Ensure user exists in DB
        await db.user.upsert({
            where: { id: userId },
            update: {},
            create: {
                id: userId,
                email: claims.email || '',
                name: claims.email?.split('@')[0] || 'User',
            },
        });

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
