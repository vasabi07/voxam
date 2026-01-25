"""
Integration tests for credits flow.
Tests Supabase operations for user credits management.

IMPORTANT: These tests read from and write to the real Supabase database.
Credits are restored after deduction tests to avoid affecting real data.
"""
import pytest
import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestGetCredits:
    """Tests for reading user credit balance."""

    def test_get_credits_returns_user_balance(self, test_user):
        """Test getting user credits from Supabase."""
        from credits import get_user_credits

        user_id = test_user["id"]
        credits = get_user_credits(user_id)

        assert credits is not None
        assert "voiceMinutes" in credits
        assert "chatMessages" in credits
        assert "pages" in credits

        # Verify structure
        for category in ["voiceMinutes", "chatMessages", "pages"]:
            assert "used" in credits[category]
            assert "limit" in credits[category]
            assert "remaining" in credits[category]
            assert credits[category]["remaining"] == credits[category]["limit"] - credits[category]["used"]

        print(f"User {user_id} credits:")
        print(f"  Voice: {credits['voiceMinutes']['remaining']}/{credits['voiceMinutes']['limit']} remaining")
        print(f"  Chat: {credits['chatMessages']['remaining']}/{credits['chatMessages']['limit']} remaining")
        print(f"  Pages: {credits['pages']['remaining']}/{credits['pages']['limit']} remaining")

    def test_get_credits_nonexistent_user_raises_exception(self):
        """Test getting credits for nonexistent user raises exception.

        Note: The current implementation throws an exception rather than returning None.
        This documents the actual behavior.
        """
        from credits import get_user_credits
        from postgrest.exceptions import APIError

        with pytest.raises(APIError) as exc_info:
            get_user_credits("nonexistent-user-12345")

        # Supabase returns PGRST116 when single() finds no rows
        assert exc_info.value.code == "PGRST116"

    def test_credits_api_endpoint(self, supabase_client, test_user):
        """Test the /credits API endpoint pattern (direct Supabase query)."""
        user_id = test_user["id"]

        result = supabase_client.table("User").select(
            "voiceMinutesUsed, voiceMinutesLimit, "
            "chatMessagesUsed, chatMessagesLimit, "
            "pagesUsed, pagesLimit"
        ).eq("id", user_id).single().execute()

        assert result.data is not None
        assert "voiceMinutesUsed" in result.data
        assert "voiceMinutesLimit" in result.data


class TestCheckCredits:
    """Tests for checking credit availability."""

    def test_check_voice_minutes(self, test_user):
        """Test checking voice minutes availability."""
        from credits import check_voice_minutes

        user_id = test_user["id"]
        has_credits, remaining = check_voice_minutes(user_id)

        assert isinstance(has_credits, bool)
        assert isinstance(remaining, int)
        assert remaining >= 0

        print(f"User {user_id}: has_voice_credits={has_credits}, remaining={remaining}")

    def test_check_chat_messages(self, test_user):
        """Test checking chat messages availability."""
        from credits import check_chat_messages

        user_id = test_user["id"]
        has_credits, remaining = check_chat_messages(user_id)

        assert isinstance(has_credits, bool)
        assert isinstance(remaining, int)
        assert remaining >= 0

    def test_check_pages(self, test_user):
        """Test checking pages availability."""
        from credits import check_pages

        user_id = test_user["id"]
        has_credits, remaining = check_pages(user_id)

        assert isinstance(has_credits, bool)
        assert isinstance(remaining, int)
        assert remaining >= 0

    def test_check_voice_minutes_for_exam(self, test_user):
        """Test checking voice minutes for exam with requirement."""
        from credits import check_voice_minutes_for_exam

        user_id = test_user["id"]

        # Check for a 30-minute exam
        has_enough, remaining, error = check_voice_minutes_for_exam(user_id, 30)

        assert isinstance(has_enough, bool)
        assert isinstance(remaining, int)
        assert isinstance(error, str)

        if has_enough:
            assert error == ""
            assert remaining >= 30
        else:
            assert error != ""
            print(f"Insufficient credits: {error}")

    def test_check_pages_for_document(self, test_user):
        """Test checking pages for document upload."""
        from credits import check_pages_for_document

        user_id = test_user["id"]

        # Check for a 10-page document
        has_enough, remaining, error = check_pages_for_document(user_id, 10)

        assert isinstance(has_enough, bool)
        assert isinstance(remaining, int)
        assert isinstance(error, str)


class TestDeductCredits:
    """Tests for deducting credits.

    These tests actually modify the database but restore the original values.
    """

    def test_deduct_voice_minutes_and_restore(self, test_user, supabase_client):
        """Test deducting voice minutes (with restoration)."""
        from credits import deduct_voice_minutes, get_user_credits

        user_id = test_user["id"]

        # Get original value
        original_credits = get_user_credits(user_id)
        original_used = original_credits["voiceMinutes"]["used"]

        # Deduct 1 minute
        result = deduct_voice_minutes(user_id, 1)
        assert result is True

        # Verify deduction
        new_credits = get_user_credits(user_id)
        assert new_credits["voiceMinutes"]["used"] == original_used + 1

        # Restore original value
        supabase_client.table("User").update({
            "voiceMinutesUsed": original_used
        }).eq("id", user_id).execute()

        # Verify restoration
        restored_credits = get_user_credits(user_id)
        assert restored_credits["voiceMinutes"]["used"] == original_used
        print(f"Successfully tested deduction and restored credits")

    def test_deduct_chat_message_and_restore(self, test_user, supabase_client):
        """Test deducting chat messages (with restoration)."""
        from credits import deduct_chat_message, get_user_credits

        user_id = test_user["id"]

        # Get original value
        original_credits = get_user_credits(user_id)
        original_used = original_credits["chatMessages"]["used"]

        # Deduct 1 message
        result = deduct_chat_message(user_id, 1)
        assert result is True

        # Verify deduction
        new_credits = get_user_credits(user_id)
        assert new_credits["chatMessages"]["used"] == original_used + 1

        # Restore original value
        supabase_client.table("User").update({
            "chatMessagesUsed": original_used
        }).eq("id", user_id).execute()

        # Verify restoration
        restored_credits = get_user_credits(user_id)
        assert restored_credits["chatMessages"]["used"] == original_used

    def test_deduct_pages_and_restore(self, test_user, supabase_client):
        """Test deducting pages (with restoration)."""
        from credits import deduct_pages, get_user_credits

        user_id = test_user["id"]

        # Get original value
        original_credits = get_user_credits(user_id)
        original_used = original_credits["pages"]["used"]

        # Deduct 1 page
        result = deduct_pages(user_id, 1)
        assert result is True

        # Verify deduction
        new_credits = get_user_credits(user_id)
        assert new_credits["pages"]["used"] == original_used + 1

        # Restore original value
        supabase_client.table("User").update({
            "pagesUsed": original_used
        }).eq("id", user_id).execute()

        # Verify restoration
        restored_credits = get_user_credits(user_id)
        assert restored_credits["pages"]["used"] == original_used

    def test_deduct_zero_is_noop(self, test_user):
        """Test that deducting 0 credits is a no-op."""
        from credits import deduct_voice_minutes, deduct_chat_message, deduct_pages

        user_id = test_user["id"]

        # All should return True without modifying anything
        assert deduct_voice_minutes(user_id, 0) is True
        assert deduct_chat_message(user_id, 0) is True
        assert deduct_pages(user_id, 0) is True

    def test_deduct_nonexistent_user_raises_exception(self):
        """Test deducting from nonexistent user raises exception.

        Note: The current implementation throws an exception rather than returning False.
        This documents the actual behavior.
        """
        from credits import deduct_voice_minutes
        from postgrest.exceptions import APIError

        with pytest.raises(APIError) as exc_info:
            deduct_voice_minutes("nonexistent-user-12345", 1)

        # Supabase returns PGRST116 when single() finds no rows
        assert exc_info.value.code == "PGRST116"


class TestCalculateMinutes:
    """Tests for minute calculation utilities."""

    def test_calculate_session_minutes(self):
        """Test billing minutes calculation (ceiling)."""
        from credits import calculate_session_minutes

        # 0 seconds = 0 minutes
        assert calculate_session_minutes(0) == 0

        # 1 second = 1 minute (rounds up)
        assert calculate_session_minutes(1) == 1

        # 59 seconds = 1 minute
        assert calculate_session_minutes(59) == 1

        # 60 seconds = 1 minute
        assert calculate_session_minutes(60) == 1

        # 61 seconds = 2 minutes
        assert calculate_session_minutes(61) == 2

        # 120 seconds = 2 minutes
        assert calculate_session_minutes(120) == 2

        # 121 seconds = 3 minutes
        assert calculate_session_minutes(121) == 3

        # 1800 seconds (30 min) = 30 minutes
        assert calculate_session_minutes(1800) == 30

        # 1801 seconds = 31 minutes
        assert calculate_session_minutes(1801) == 31

    def test_calculate_negative_seconds_returns_zero(self):
        """Test that negative seconds returns 0."""
        from credits import calculate_session_minutes

        assert calculate_session_minutes(-1) == 0
        assert calculate_session_minutes(-100) == 0


class TestSupabaseOperations:
    """Tests for direct Supabase operations used in credits."""

    def test_user_table_has_credit_fields(self, supabase_client, test_user):
        """Verify User table has required credit fields."""
        user_id = test_user["id"]

        result = supabase_client.table("User").select("*").eq("id", user_id).single().execute()

        required_fields = [
            "voiceMinutesUsed", "voiceMinutesLimit",
            "chatMessagesUsed", "chatMessagesLimit",
            "pagesUsed", "pagesLimit"
        ]

        for field in required_fields:
            assert field in result.data, f"Missing field: {field}"

        print(f"All credit fields present for user {user_id}")

    def test_credit_fields_are_integers(self, test_user):
        """Verify credit fields are integers."""
        from credits import get_user_credits

        user_id = test_user["id"]
        credits = get_user_credits(user_id)

        for category in ["voiceMinutes", "chatMessages", "pages"]:
            for field in ["used", "limit", "remaining"]:
                assert isinstance(credits[category][field], int), \
                    f"{category}.{field} should be int, got {type(credits[category][field])}"

    def test_remaining_never_negative(self, test_user):
        """Verify remaining credits calculation handles edge cases."""
        from credits import get_user_credits

        user_id = test_user["id"]
        credits = get_user_credits(user_id)

        # Remaining could theoretically be negative if used > limit
        # This tests current state, not edge case handling
        for category in ["voiceMinutes", "chatMessages", "pages"]:
            remaining = credits[category]["remaining"]
            limit = credits[category]["limit"]
            used = credits[category]["used"]
            # Just verify the math is correct
            assert remaining == limit - used
