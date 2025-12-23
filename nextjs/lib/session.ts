import { createClient } from '@/lib/supabase/server';

/**
 * Get the current user's claims from Supabase auth
 * For use in API routes
 */
export async function getClaims() {
    const supabase = await createClient();
    const { data } = await supabase.auth.getUser();

    if (!data.user) {
        return null;
    }

    return {
        sub: data.user.id,
        email: data.user.email,
    };
}
