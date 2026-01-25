import { NextResponse } from 'next/server';
import { db } from '@/lib/prisma';
import { getClaims } from '@/lib/session';

/**
 * GET /api/user/region
 * Returns the authenticated user's stored region for TTS routing
 */
export async function GET() {
    try {
        const claims = await getClaims();
        if (!claims?.sub) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const userId = claims.sub;

        // Get user's stored region
        const user = await db.user.findUnique({
            where: { id: userId },
            select: { region: true },
        });

        // Return stored region, or 'india' as default
        return NextResponse.json({
            region: user?.region || 'india',
        });

    } catch (error: unknown) {
        console.error('Error getting user region:', error);
        return NextResponse.json(
            { error: 'Failed to get user region' },
            { status: 500 }
        );
    }
}
