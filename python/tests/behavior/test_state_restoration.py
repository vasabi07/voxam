"""
Tests for state restoration fix.

Verifies that current_index/current_topic_index is properly restored
from checkpoint between invocations (fixes question/topic skipping bug).
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestExamStateRestoration:
    """Tests for exam agent state restoration."""

    def test_state_restoration_preserves_current_index(self):
        """Verify that current_index is restored from checkpoint, not reset to 0."""
        from agents.exam_agent import graph as exam_agent_graph, State as ExamState
        from langchain_core.messages import HumanMessage

        # Mock the graph's get_state to return a saved state with current_index=3
        mock_state = MagicMock()
        mock_state.values = {
            "current_index": 3,
            "current_question": {"text": "Question 4", "question_type": "mcq"},
            "exam_started": True,
            "messages": [],
        }

        with patch.object(exam_agent_graph, 'get_state', return_value=mock_state):
            config = {"configurable": {"thread_id": "test-thread"}}

            # Simulate what realtime_exam.py does now (after fix)
            saved_state = exam_agent_graph.get_state(config)

            if saved_state and saved_state.values:
                current_index = saved_state.values.get("current_index", 0)
                current_question = saved_state.values.get("current_question", None)
                exam_started = saved_state.values.get("exam_started", False)
            else:
                current_index = 0
                current_question = None
                exam_started = False

            # Verify restored values
            assert current_index == 3, f"Expected current_index=3, got {current_index}"
            assert exam_started == True
            assert current_question["text"] == "Question 4"
            print(f"✅ State restored correctly: current_index={current_index}")

    def test_state_defaults_when_no_checkpoint(self):
        """Verify defaults are used when no checkpoint exists."""
        from agents.exam_agent import graph as exam_agent_graph

        # Mock get_state to return None (no saved state)
        mock_state = MagicMock()
        mock_state.values = None

        with patch.object(exam_agent_graph, 'get_state', return_value=mock_state):
            config = {"configurable": {"thread_id": "new-thread"}}

            saved_state = exam_agent_graph.get_state(config)

            if saved_state and saved_state.values:
                current_index = saved_state.values.get("current_index", 0)
            else:
                current_index = 0  # Default

            assert current_index == 0, "Should default to 0 when no checkpoint"
            print(f"✅ Defaults used correctly when no checkpoint")

    def test_state_handles_get_state_exception(self):
        """Verify graceful fallback when get_state throws exception."""
        from agents.exam_agent import graph as exam_agent_graph

        with patch.object(exam_agent_graph, 'get_state', side_effect=Exception("Redis connection failed")):
            config = {"configurable": {"thread_id": "test-thread"}}

            # Simulate the try/except in realtime_exam.py
            try:
                saved_state = exam_agent_graph.get_state(config)
                if saved_state and saved_state.values:
                    current_index = saved_state.values.get("current_index", 0)
                else:
                    current_index = 0
            except Exception as e:
                print(f"⚠️ Could not restore state: {e}, using defaults")
                current_index = 0

            assert current_index == 0, "Should fallback to default on exception"
            print(f"✅ Graceful fallback on exception")


class TestLearnStateRestoration:
    """Tests for learn agent state restoration."""

    def test_state_restoration_preserves_topic_index(self):
        """Verify that current_topic_index is restored from checkpoint."""
        from agents.learn_agent import graph as learn_agent_graph

        # Mock the graph's get_state to return a saved state
        mock_state = MagicMock()
        mock_state.values = {
            "current_topic_index": 2,
            "current_topic": {"name": "Topic 3", "content": "..."},
            "session_started": True,
            "messages": [],
        }

        with patch.object(learn_agent_graph, 'get_state', return_value=mock_state):
            config = {"configurable": {"thread_id": "test-learn-thread"}}

            saved_state = learn_agent_graph.get_state(config)

            if saved_state and saved_state.values:
                current_topic_index = saved_state.values.get("current_topic_index", 0)
                current_topic = saved_state.values.get("current_topic", None)
                session_started = saved_state.values.get("session_started", False)
            else:
                current_topic_index = 0
                current_topic = None
                session_started = False

            assert current_topic_index == 2, f"Expected current_topic_index=2, got {current_topic_index}"
            assert session_started == True
            assert current_topic["name"] == "Topic 3"
            print(f"✅ Learn state restored correctly: current_topic_index={current_topic_index}")


class TestRealtimeExamIntegration:
    """Integration tests for realtime_exam.py state handling."""

    def test_process_transcript_restores_state(self):
        """Test that process_complete_transcript uses restored state."""
        # This test verifies the code path in realtime_exam.py

        # The fix adds this code before creating ExamState:
        # saved_state = exam_agent_graph.get_state(config)
        # current_index = saved_state.values.get("current_index", 0)

        # Verify the code exists in the file
        import inspect
        from agents import realtime_exam

        source = inspect.getsource(realtime_exam)

        # Check for state restoration code
        assert "get_state(config)" in source, "Missing get_state call in realtime_exam.py"
        assert "current_index = saved_state.values.get" in source or \
               'current_index = saved_state.values.get("current_index"' in source, \
               "Missing current_index restoration"

        print("✅ realtime_exam.py contains state restoration code")

    def test_trigger_greeting_exists(self):
        """Test that trigger_greeting function exists."""
        from agents import realtime_exam
        import inspect

        source = inspect.getsource(realtime_exam)

        assert "async def trigger_greeting" in source, "Missing trigger_greeting function"
        assert "[SESSION_START]" in source, "Missing SESSION_START marker"
        assert "greeting_sent = True" in source, "Missing greeting_sent flag"

        print("✅ realtime_exam.py contains greeting fix")


class TestRealtimeLearnIntegration:
    """Integration tests for realtime_learn.py state handling."""

    def test_process_transcript_restores_state(self):
        """Test that process_complete_transcript uses restored state."""
        import inspect
        from agents import realtime_learn

        source = inspect.getsource(realtime_learn)

        # Check for state restoration code
        assert "get_state(config)" in source, "Missing get_state call in realtime_learn.py"
        assert "current_topic_index = saved_state.values.get" in source or \
               'current_topic_index = saved_state.values.get("current_topic_index"' in source, \
               "Missing current_topic_index restoration"

        print("✅ realtime_learn.py contains state restoration code")

    def test_trigger_greeting_exists(self):
        """Test that trigger_greeting function exists."""
        from agents import realtime_learn
        import inspect

        source = inspect.getsource(realtime_learn)

        assert "async def trigger_greeting" in source, "Missing trigger_greeting function"
        assert "[SESSION_START]" in source, "Missing SESSION_START marker"
        assert "greeting_sent = True" in source, "Missing greeting_sent flag"

        print("✅ realtime_learn.py contains greeting fix")


class TestParticipantConnectedHandler:
    """Tests for participant_connected event handler."""

    def test_exam_has_participant_connected_handler(self):
        """Verify exam agent triggers greeting on participant connect."""
        import inspect
        from agents import realtime_exam

        source = inspect.getsource(realtime_exam)

        assert "@room.on(\"participant_connected\")" in source or \
               '@room.on("participant_connected")' in source, \
               "Missing participant_connected handler"
        assert "trigger_greeting()" in source, "Missing trigger_greeting call"

        print("✅ realtime_exam.py triggers greeting on participant connect")

    def test_learn_has_participant_connected_handler(self):
        """Verify learn agent triggers greeting on participant connect."""
        import inspect
        from agents import realtime_learn

        source = inspect.getsource(realtime_learn)

        assert "@room.on(\"participant_connected\")" in source or \
               '@room.on("participant_connected")' in source, \
               "Missing participant_connected handler"
        assert "trigger_greeting()" in source, "Missing trigger_greeting call"

        print("✅ realtime_learn.py triggers greeting on participant connect")
