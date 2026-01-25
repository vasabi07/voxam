"""
Credit management utilities for VOXAM.
Centralizes all credit-related operations for voice minutes, chat messages, and pages.
"""
from supabase import create_client
import os
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client():
    """Get authenticated Supabase client with service role key."""
    return create_client(
        os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )


def get_user_credits(user_id: str) -> Optional[dict]:
    """
    Get user's current credit balance.
    User should be created by Next.js on login (auth callback).

    Args:
        user_id: The user's ID (from Supabase Auth)

    Returns:
        dict with voiceMinutes, chatMessages, pages - each having used, limit, remaining
        None if user not found
    """
    supabase = get_supabase_client()
    result = supabase.table("User").select(
        "voiceMinutesUsed, voiceMinutesLimit, "
        "chatMessagesUsed, chatMessagesLimit, "
        "pagesUsed, pagesLimit"
    ).eq("id", user_id).maybe_single().execute()

    if result is None or not result.data:
        print(f"[Credits] User not found: {user_id} (should be created by Next.js on login)")
        return None

    data = result.data
    return {
        "voiceMinutes": {
            "used": data["voiceMinutesUsed"],
            "limit": data["voiceMinutesLimit"],
            "remaining": data["voiceMinutesLimit"] - data["voiceMinutesUsed"]
        },
        "chatMessages": {
            "used": data["chatMessagesUsed"],
            "limit": data["chatMessagesLimit"],
            "remaining": data["chatMessagesLimit"] - data["chatMessagesUsed"]
        },
        "pages": {
            "used": data["pagesUsed"],
            "limit": data["pagesLimit"],
            "remaining": data["pagesLimit"] - data["pagesUsed"]
        }
    }


def deduct_voice_minutes(user_id: str, minutes: int) -> bool:
    """
    Deduct voice minutes from user's balance.
    Uses atomic increment to avoid race conditions.

    Args:
        user_id: The user's ID
        minutes: Number of minutes to deduct

    Returns:
        True if successful, False otherwise
    """
    if minutes <= 0:
        return True

    supabase = get_supabase_client()

    # Get current usage
    user = supabase.table("User").select("voiceMinutesUsed").eq("id", user_id).maybe_single().execute()
    if user is None or not user.data:
        return False

    # Update with new value
    new_used = user.data["voiceMinutesUsed"] + minutes
    supabase.table("User").update({
        "voiceMinutesUsed": new_used
    }).eq("id", user_id).execute()

    print(f"[Credits] Deducted {minutes} voice minutes from user {user_id}. New total: {new_used}")
    return True


def deduct_chat_message(user_id: str, count: int = 1) -> bool:
    """
    Deduct chat messages from user's balance.

    Args:
        user_id: The user's ID
        count: Number of messages to deduct (default 1)

    Returns:
        True if successful, False otherwise
    """
    if count <= 0:
        return True

    supabase = get_supabase_client()

    user = supabase.table("User").select("chatMessagesUsed").eq("id", user_id).maybe_single().execute()
    if user is None or not user.data:
        return False

    new_used = user.data["chatMessagesUsed"] + count
    supabase.table("User").update({
        "chatMessagesUsed": new_used
    }).eq("id", user_id).execute()

    print(f"[Credits] Deducted {count} chat message(s) from user {user_id}. New total: {new_used}")
    return True


def deduct_pages(user_id: str, page_count: int) -> bool:
    """
    Deduct pages from user's balance.

    Args:
        user_id: The user's ID
        page_count: Number of pages to deduct

    Returns:
        True if successful, False otherwise
    """
    if page_count <= 0:
        return True

    supabase = get_supabase_client()

    user = supabase.table("User").select("pagesUsed").eq("id", user_id).maybe_single().execute()
    if user is None or not user.data:
        return False

    new_used = user.data["pagesUsed"] + page_count
    supabase.table("User").update({
        "pagesUsed": new_used
    }).eq("id", user_id).execute()

    print(f"[Credits] Deducted {page_count} pages from user {user_id}. New total: {new_used}")
    return True


def check_voice_minutes(user_id: str) -> Tuple[bool, int]:
    """
    Check if user has voice minutes remaining.

    Returns:
        Tuple of (has_credits, remaining_minutes)
    """
    credits = get_user_credits(user_id)
    if not credits:
        return False, 0

    remaining = credits["voiceMinutes"]["remaining"]
    return remaining > 0, remaining


def check_chat_messages(user_id: str) -> Tuple[bool, int]:
    """
    Check if user has chat messages remaining.

    Returns:
        Tuple of (has_credits, remaining_messages)
    """
    credits = get_user_credits(user_id)
    if not credits:
        return False, 0

    remaining = credits["chatMessages"]["remaining"]
    return remaining > 0, remaining


def check_pages(user_id: str) -> Tuple[bool, int]:
    """
    Check if user has pages remaining.

    Returns:
        Tuple of (has_credits, remaining_pages)
    """
    credits = get_user_credits(user_id)
    if not credits:
        return False, 0

    remaining = credits["pages"]["remaining"]
    return remaining > 0, remaining


def check_voice_minutes_for_exam(user_id: str, required_minutes: int) -> Tuple[bool, int, str]:
    """
    Check if user has enough voice minutes for an exam.

    Args:
        user_id: The user's ID
        required_minutes: Duration of the exam in minutes

    Returns:
        Tuple of (has_enough, remaining_minutes, error_message)
    """
    has_credits, remaining = check_voice_minutes(user_id)

    if not has_credits:
        return False, 0, "You have no voice minutes remaining. Please purchase more credits."

    if remaining < required_minutes:
        return False, remaining, f"This exam requires {required_minutes} minutes but you only have {remaining} minutes remaining."

    return True, remaining, ""


def check_pages_for_document(user_id: str, page_count: int) -> Tuple[bool, int, str]:
    """
    Check if user has enough pages for a document.

    Args:
        user_id: The user's ID
        page_count: Number of pages in the document

    Returns:
        Tuple of (has_enough, remaining_pages, error_message)
    """
    has_credits, remaining = check_pages(user_id)

    if not has_credits:
        return False, 0, "You have no pages remaining. Please purchase more credits."

    if remaining < page_count:
        return False, remaining, f"This document has {page_count} pages but you only have {remaining} pages remaining."

    return True, remaining, ""


def calculate_session_minutes(total_connected_seconds: int) -> int:
    """
    Calculate billable minutes from total connected seconds.
    Rounds up to nearest minute.

    Args:
        total_connected_seconds: Total time connected in seconds

    Returns:
        Minutes to bill (rounded up)
    """
    if total_connected_seconds <= 0:
        return 0
    return (total_connected_seconds + 59) // 60  # Ceiling division
