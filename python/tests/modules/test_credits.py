"""
Tests for the credits module - balance calculations, deductions, and validation.
"""
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from credits import (
    get_user_credits,
    deduct_voice_minutes,
    deduct_chat_message,
    deduct_pages,
    check_voice_minutes,
    check_chat_messages,
    check_pages,
    check_voice_minutes_for_exam,
    check_pages_for_document,
    calculate_session_minutes,
)


class TestGetUserCredits:
    """Tests for get_user_credits function."""

    def test_returns_correct_voice_minutes_structure(self, mock_supabase, test_user_id):
        """Test that voiceMinutes structure is correct."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 10,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 5,
                "chatMessagesLimit": 100,
                "pagesUsed": 10,
                "pagesLimit": 50,
            }
        )

        result = get_user_credits(test_user_id)

        assert result["voiceMinutes"]["used"] == 10
        assert result["voiceMinutes"]["limit"] == 60
        assert result["voiceMinutes"]["remaining"] == 50

    def test_returns_correct_chat_messages_structure(self, mock_supabase, test_user_id):
        """Test that chatMessages structure is correct."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 0,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 25,
                "chatMessagesLimit": 100,
                "pagesUsed": 0,
                "pagesLimit": 50,
            }
        )

        result = get_user_credits(test_user_id)

        assert result["chatMessages"]["used"] == 25
        assert result["chatMessages"]["limit"] == 100
        assert result["chatMessages"]["remaining"] == 75

    def test_returns_correct_pages_structure(self, mock_supabase, test_user_id):
        """Test that pages structure is correct."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 0,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 0,
                "chatMessagesLimit": 100,
                "pagesUsed": 30,
                "pagesLimit": 50,
            }
        )

        result = get_user_credits(test_user_id)

        assert result["pages"]["used"] == 30
        assert result["pages"]["limit"] == 50
        assert result["pages"]["remaining"] == 20

    def test_calculates_remaining_correctly(self, mock_supabase, test_user_id):
        """Test that remaining = limit - used."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 45,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 80,
                "chatMessagesLimit": 100,
                "pagesUsed": 40,
                "pagesLimit": 50,
            }
        )

        result = get_user_credits(test_user_id)

        assert result["voiceMinutes"]["remaining"] == 15  # 60 - 45
        assert result["chatMessages"]["remaining"] == 20  # 100 - 80
        assert result["pages"]["remaining"] == 10  # 50 - 40

    def test_returns_none_when_user_not_found(self, mock_supabase, test_user_id):
        """Test that None is returned when user doesn't exist."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = get_user_credits(test_user_id)

        assert result is None


class TestCheckFunctions:
    """Tests for credit check functions."""

    def test_check_voice_minutes_returns_true_when_available(self, mock_supabase, test_user_id):
        """Test check_voice_minutes returns (True, remaining) when credits available."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 10,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 0,
                "chatMessagesLimit": 100,
                "pagesUsed": 0,
                "pagesLimit": 50,
            }
        )

        has_credits, remaining = check_voice_minutes(test_user_id)

        assert has_credits is True
        assert remaining == 50

    def test_check_voice_minutes_returns_false_when_exhausted(self, mock_supabase, test_user_id):
        """Test check_voice_minutes returns (False, 0) when exhausted."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 60,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 0,
                "chatMessagesLimit": 100,
                "pagesUsed": 0,
                "pagesLimit": 50,
            }
        )

        has_credits, remaining = check_voice_minutes(test_user_id)

        assert has_credits is False
        assert remaining == 0

    def test_check_chat_messages_returns_true_when_available(self, mock_supabase, test_user_id):
        """Test check_chat_messages returns (True, remaining) when credits available."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 0,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 50,
                "chatMessagesLimit": 100,
                "pagesUsed": 0,
                "pagesLimit": 50,
            }
        )

        has_credits, remaining = check_chat_messages(test_user_id)

        assert has_credits is True
        assert remaining == 50

    def test_check_pages_returns_true_when_available(self, mock_supabase, test_user_id):
        """Test check_pages returns (True, remaining) when credits available."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 0,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 0,
                "chatMessagesLimit": 100,
                "pagesUsed": 20,
                "pagesLimit": 50,
            }
        )

        has_credits, remaining = check_pages(test_user_id)

        assert has_credits is True
        assert remaining == 30

    def test_all_checks_handle_user_not_found(self, mock_supabase, test_user_id):
        """Test that all check functions handle user not found."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        has_voice, remaining_voice = check_voice_minutes(test_user_id)
        has_chat, remaining_chat = check_chat_messages(test_user_id)
        has_pages, remaining_pages = check_pages(test_user_id)

        assert has_voice is False
        assert remaining_voice == 0
        assert has_chat is False
        assert remaining_chat == 0
        assert has_pages is False
        assert remaining_pages == 0


class TestValidationFunctions:
    """Tests for credit validation functions with error messages."""

    def test_check_voice_minutes_for_exam_validates_required_minutes(self, mock_supabase, test_user_id):
        """Test that check_voice_minutes_for_exam validates required minutes."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 10,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 0,
                "chatMessagesLimit": 100,
                "pagesUsed": 0,
                "pagesLimit": 50,
            }
        )

        # User has 50 minutes remaining, exam requires 30
        has_enough, remaining, error = check_voice_minutes_for_exam(test_user_id, 30)

        assert has_enough is True
        assert remaining == 50
        assert error == ""

    def test_check_voice_minutes_for_exam_returns_error_when_insufficient(self, mock_supabase, test_user_id):
        """Test that insufficient minutes returns appropriate error."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 50,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 0,
                "chatMessagesLimit": 100,
                "pagesUsed": 0,
                "pagesLimit": 50,
            }
        )

        # User has 10 minutes remaining, exam requires 30
        has_enough, remaining, error = check_voice_minutes_for_exam(test_user_id, 30)

        assert has_enough is False
        assert remaining == 10
        assert "30 minutes" in error
        assert "10 minutes" in error

    def test_check_pages_for_document_validates_page_count(self, mock_supabase, test_user_id):
        """Test that check_pages_for_document validates page count."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 0,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 0,
                "chatMessagesLimit": 100,
                "pagesUsed": 10,
                "pagesLimit": 50,
            }
        )

        # User has 40 pages remaining, document has 20 pages
        has_enough, remaining, error = check_pages_for_document(test_user_id, 20)

        assert has_enough is True
        assert remaining == 40
        assert error == ""

    def test_check_pages_for_document_returns_error_when_insufficient(self, mock_supabase, test_user_id):
        """Test that insufficient pages returns appropriate error."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "voiceMinutesUsed": 0,
                "voiceMinutesLimit": 60,
                "chatMessagesUsed": 0,
                "chatMessagesLimit": 100,
                "pagesUsed": 45,
                "pagesLimit": 50,
            }
        )

        # User has 5 pages remaining, document has 20 pages
        has_enough, remaining, error = check_pages_for_document(test_user_id, 20)

        assert has_enough is False
        assert remaining == 5
        assert "20 pages" in error
        assert "5 pages" in error


class TestDeductionLogic:
    """Tests for credit deduction functions."""

    def test_deduct_voice_minutes_increments_used(self, mock_supabase, test_user_id):
        """Test that deduct_voice_minutes increments voiceMinutesUsed."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"voiceMinutesUsed": 10}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = deduct_voice_minutes(test_user_id, 5)

        assert result is True
        # Verify update was called with incremented value
        mock_supabase.table.return_value.update.assert_called_once()
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["voiceMinutesUsed"] == 15  # 10 + 5

    def test_deduct_voice_minutes_returns_true_when_successful(self, mock_supabase, test_user_id):
        """Test that successful deduction returns True."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"voiceMinutesUsed": 10}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = deduct_voice_minutes(test_user_id, 5)

        assert result is True

    def test_deduct_voice_minutes_handles_zero_minutes(self, mock_supabase, test_user_id):
        """Test that zero minutes deduction returns True without DB call."""
        result = deduct_voice_minutes(test_user_id, 0)

        assert result is True
        # Should not make any DB calls for 0 minutes
        mock_supabase.table.assert_not_called()

    def test_deduct_voice_minutes_handles_negative_minutes(self, mock_supabase, test_user_id):
        """Test that negative minutes deduction returns True without DB call."""
        result = deduct_voice_minutes(test_user_id, -5)

        assert result is True
        mock_supabase.table.assert_not_called()

    def test_deduct_chat_message_increments_by_count(self, mock_supabase, test_user_id):
        """Test that deduct_chat_message increments by count."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"chatMessagesUsed": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = deduct_chat_message(test_user_id, 3)

        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["chatMessagesUsed"] == 53  # 50 + 3

    def test_deduct_chat_message_defaults_to_count_1(self, mock_supabase, test_user_id):
        """Test that deduct_chat_message defaults to count=1."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"chatMessagesUsed": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = deduct_chat_message(test_user_id)  # No count parameter

        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["chatMessagesUsed"] == 51  # 50 + 1

    def test_deduct_pages_increments_by_page_count(self, mock_supabase, test_user_id):
        """Test that deduct_pages increments by page_count."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"pagesUsed": 20}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = deduct_pages(test_user_id, 10)

        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["pagesUsed"] == 30  # 20 + 10

    def test_deduct_returns_false_when_user_not_found(self, mock_supabase, test_user_id):
        """Test that deduction returns False when user not found."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = deduct_voice_minutes(test_user_id, 5)

        assert result is False


class TestTimeCalculations:
    """Tests for session minutes calculation."""

    def test_calculate_session_minutes_0_seconds(self):
        """Test that 0 seconds returns 0 minutes."""
        assert calculate_session_minutes(0) == 0

    def test_calculate_session_minutes_1_second(self):
        """Test that 1 second rounds up to 1 minute."""
        assert calculate_session_minutes(1) == 1

    def test_calculate_session_minutes_60_seconds(self):
        """Test that 60 seconds equals 1 minute."""
        assert calculate_session_minutes(60) == 1

    def test_calculate_session_minutes_61_seconds(self):
        """Test that 61 seconds rounds up to 2 minutes."""
        assert calculate_session_minutes(61) == 2

    def test_calculate_session_minutes_119_seconds(self):
        """Test that 119 seconds rounds up to 2 minutes."""
        assert calculate_session_minutes(119) == 2

    def test_calculate_session_minutes_120_seconds(self):
        """Test that 120 seconds equals 2 minutes."""
        assert calculate_session_minutes(120) == 2

    def test_calculate_session_minutes_3600_seconds(self):
        """Test that 3600 seconds equals 60 minutes."""
        assert calculate_session_minutes(3600) == 60

    def test_calculate_session_minutes_negative_returns_0(self):
        """Test that negative seconds returns 0."""
        assert calculate_session_minutes(-10) == 0


class TestRaceConditions:
    """Tests for potential race conditions in credit deduction.

    NOTE: The current implementation uses read-modify-write pattern
    which is NOT atomic and can lead to lost updates under concurrent load.
    These tests document the expected behavior and the potential issue.
    """

    def test_concurrent_deductions_documented_race_condition(self, mock_supabase, test_user_id):
        """
        Document the race condition in current implementation.

        Current flow:
        1. Read current value: 10
        2. Calculate new value: 10 + 5 = 15
        3. Write new value: 15

        If two requests happen concurrently:
        - Request A reads: 10
        - Request B reads: 10
        - Request A writes: 15 (10 + 5)
        - Request B writes: 15 (10 + 5) -- Lost update! Should be 20

        This test documents this behavior as a known issue.
        """
        # Setup: User has 10 minutes used
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"voiceMinutesUsed": 10}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        # Simulate two deductions
        deduct_voice_minutes(test_user_id, 5)
        deduct_voice_minutes(test_user_id, 5)

        # In current implementation, both will read 10 and write 15
        # The second call should ideally write 20, but will write 15
        # This documents the race condition

        # Verify update was called twice
        assert mock_supabase.table.return_value.update.call_count == 2

        # Both calls will try to set voiceMinutesUsed to 15 (10 + 5)
        # This is the documented race condition behavior
        calls = mock_supabase.table.return_value.update.call_args_list
        # Note: In a real concurrent scenario, both would write 15
        # but in this serial test, the mock doesn't persist state
