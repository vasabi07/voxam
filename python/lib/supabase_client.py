"""
Supabase client for Python backend.
Uses SERVICE_ROLE_KEY which bypasses RLS for admin operations.
"""

import os
from supabase import create_client, Client
from functools import lru_cache


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    """
    Returns a Supabase client with SERVICE_ROLE permissions.
    This client bypasses RLS and has full database access.
    
    Use this for:
    - Celery task updates (document status, exam results)
    - Backend operations that span multiple users
    - Admin functions
    
    DO NOT use this for user-initiated requests where you want RLS.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables"
        )
    
    return create_client(url, key)


def get_supabase_for_user(access_token: str) -> Client:
    """
    Returns a Supabase client that acts on behalf of a specific user.
    RLS policies WILL apply.
    
    Use this when you want to respect RLS from the backend
    (e.g., user-initiated API requests where you have their JWT).
    
    Args:
        access_token: The user's JWT access token from frontend
    """
    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not anon_key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")
    
    client = create_client(url, anon_key)
    client.auth.set_session(access_token, "")  # Set user context
    return client
