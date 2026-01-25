"use client";

import { useState, useEffect, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";

export interface CreditBalance {
  used: number;
  limit: number;
  remaining: number;
}

export interface Credits {
  voiceMinutes: CreditBalance;
  chatMessages: CreditBalance;
  pages: CreditBalance;
}

interface UseCreditsReturn {
  credits: Credits | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch and track user credit balances.
 * Auto-refreshes every 60 seconds by default.
 */
export function useCredits(autoRefreshMs: number = 60000): UseCreditsReturn {
  const [credits, setCredits] = useState<Credits | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCredits = useCallback(async () => {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session?.access_token) {
        setError("Not authenticated");
        setLoading(false);
        return;
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/credits`, {
        headers: {
          "Authorization": `Bearer ${session.access_token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch credits: ${response.statusText}`);
      }

      const data = await response.json();

      // API returns { success: true, credits: {...} } or { error: "..." }
      if (data.error) {
        throw new Error(data.error);
      }

      setCredits(data.credits || data);  // Handle both wrapped and unwrapped response
      setError(null);
    } catch (err) {
      console.error("Error fetching credits:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch credits");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCredits();

    // Set up auto-refresh
    if (autoRefreshMs > 0) {
      const interval = setInterval(fetchCredits, autoRefreshMs);
      return () => clearInterval(interval);
    }
  }, [fetchCredits, autoRefreshMs]);

  return {
    credits,
    loading,
    error,
    refetch: fetchCredits,
  };
}
