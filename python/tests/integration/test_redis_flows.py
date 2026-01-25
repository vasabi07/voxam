"""
Integration tests for Redis data flows.
Tests QP caching, task progress tracking, and LangGraph checkpointing.
"""
import pytest
import json
import uuid


class TestQuestionPaperCaching:
    """Tests for question paper caching in Redis."""

    def test_cache_qp_with_json(self, redis_client, cleanup_redis_keys):
        """Test caching a question paper using RedisJSON."""
        qp_id = f"test-qp-{uuid.uuid4().hex[:8]}"
        key = f"qp:{qp_id}:questions"
        cleanup_redis_keys(key)

        questions = [
            {
                "id": "q1",
                "question": "What is Python?",
                "type": "short_answer",
                "difficulty": "easy",
                "topic": "Basics"
            },
            {
                "id": "q2",
                "question": "Explain OOP concepts",
                "type": "long_answer",
                "difficulty": "medium",
                "topic": "OOP"
            }
        ]

        # Set using JSON
        redis_client.json().set(key, "$", questions)

        # Retrieve
        retrieved = redis_client.json().get(key)
        assert retrieved == questions
        assert len(retrieved) == 2
        assert retrieved[0]["question"] == "What is Python?"

    def test_qp_ttl_set_correctly(self, redis_client, cleanup_redis_keys):
        """Test that QP cache has appropriate TTL (4 hours for exam)."""
        qp_id = f"test-qp-{uuid.uuid4().hex[:8]}"
        key = f"qp:{qp_id}:questions"
        cleanup_redis_keys(key)

        redis_client.json().set(key, "$", [{"id": "q1", "question": "Test?"}])
        # Set 4 hour TTL (14400 seconds)
        redis_client.expire(key, 14400)

        ttl = redis_client.ttl(key)
        assert ttl > 0
        assert ttl <= 14400
        # Should be close to 4 hours
        assert ttl > 14000

    def test_retrieve_individual_question(self, redis_client, cleanup_redis_keys):
        """Test retrieving individual questions using JSONPath."""
        qp_id = f"test-qp-{uuid.uuid4().hex[:8]}"
        key = f"qp:{qp_id}:questions"
        cleanup_redis_keys(key)

        questions = [
            {"id": "q1", "question": "First question", "difficulty": "easy"},
            {"id": "q2", "question": "Second question", "difficulty": "medium"},
            {"id": "q3", "question": "Third question", "difficulty": "hard"}
        ]
        redis_client.json().set(key, "$", questions)

        # Get first question
        first = redis_client.json().get(key, "$[0]")
        assert first[0]["id"] == "q1"

        # Get by index
        second = redis_client.json().get(key, "$[1]")
        assert second[0]["difficulty"] == "medium"

    def test_qp_deletion_cleanup(self, redis_client):
        """Test that QP keys are properly deleted."""
        qp_id = f"test-qp-{uuid.uuid4().hex[:8]}"
        key = f"qp:{qp_id}:questions"

        redis_client.json().set(key, "$", [{"id": "q1"}])
        assert redis_client.exists(key) == 1

        redis_client.delete(key)
        assert redis_client.exists(key) == 0


class TestTaskProgressTracking:
    """Tests for task progress tracking using Redis hashes."""

    def test_set_task_progress(self, redis_client, cleanup_redis_keys):
        """Test setting task progress with hash."""
        task_id = f"test-task-{uuid.uuid4().hex[:8]}"
        key = f"task:{task_id}:progress"
        cleanup_redis_keys(key)

        redis_client.hset(key, mapping={
            "status": "processing",
            "progress": "25",
            "current_step": "extracting_text",
            "total_steps": "4"
        })

        result = redis_client.hgetall(key)
        assert result["status"] == "processing"
        assert result["progress"] == "25"
        assert result["current_step"] == "extracting_text"

    def test_task_progress_increment(self, redis_client, cleanup_redis_keys):
        """Test incrementing task progress."""
        task_id = f"test-task-{uuid.uuid4().hex[:8]}"
        key = f"task:{task_id}:progress"
        cleanup_redis_keys(key)

        redis_client.hset(key, mapping={
            "status": "processing",
            "progress": "0"
        })

        # Increment progress
        redis_client.hincrby(key, "progress", 25)
        result = redis_client.hget(key, "progress")
        assert result == "25"

        redis_client.hincrby(key, "progress", 25)
        result = redis_client.hget(key, "progress")
        assert result == "50"

    def test_task_status_transitions(self, redis_client, cleanup_redis_keys):
        """Test task status transitions (pending -> processing -> complete/failed)."""
        task_id = f"test-task-{uuid.uuid4().hex[:8]}"
        key = f"task:{task_id}:progress"
        cleanup_redis_keys(key)

        # Initial state
        redis_client.hset(key, mapping={"status": "pending", "progress": "0"})
        assert redis_client.hget(key, "status") == "pending"

        # Processing
        redis_client.hset(key, "status", "processing")
        assert redis_client.hget(key, "status") == "processing"

        # Complete
        redis_client.hset(key, mapping={"status": "complete", "progress": "100"})
        assert redis_client.hget(key, "status") == "complete"
        assert redis_client.hget(key, "progress") == "100"

    def test_task_with_error_details(self, redis_client, cleanup_redis_keys):
        """Test storing error details on task failure."""
        task_id = f"test-task-{uuid.uuid4().hex[:8]}"
        key = f"task:{task_id}:progress"
        cleanup_redis_keys(key)

        redis_client.hset(key, mapping={
            "status": "failed",
            "progress": "50",
            "error": "OCR extraction failed: Invalid PDF",
            "error_step": "extracting_text"
        })

        result = redis_client.hgetall(key)
        assert result["status"] == "failed"
        assert "OCR extraction failed" in result["error"]


class TestLangGraphCheckpointing:
    """Tests for LangGraph Redis checkpointing."""

    def test_checkpointer_can_setup(self, redis_checkpointer):
        """Test that LangGraph checkpointer can be set up."""
        # The fixture already calls setup(), so if we get here, it worked
        assert redis_checkpointer is not None

    def test_checkpointer_put_and_get(self, redis_checkpointer):
        """Test saving and retrieving checkpoint data."""
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata

        thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}

        # Create a simple checkpoint
        checkpoint = Checkpoint(
            v=1,
            id=f"checkpoint-{uuid.uuid4().hex[:8]}",
            ts="2024-01-01T00:00:00Z",
            channel_values={"messages": []},
            channel_versions={},
            versions_seen={},
            pending_sends=[],
        )
        metadata = CheckpointMetadata()

        # Put checkpoint
        result_config = redis_checkpointer.put(config, checkpoint, metadata, {})
        assert result_config is not None

        # Get checkpoint - need to recreate config since put() modifies it
        get_config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        retrieved = redis_checkpointer.get(get_config)
        assert retrieved is not None
        # Checkpoint IDs should match - retrieved is a CheckpointTuple
        assert retrieved["id"] == checkpoint["id"]

    def test_conversation_state_persistence(self, redis_checkpointer):
        """Test that conversation messages persist across checkpoints."""
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata

        thread_id = f"test-convo-{uuid.uuid4().hex[:8]}"

        # First checkpoint with initial message
        config1 = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        checkpoint1 = Checkpoint(
            v=1,
            id=f"cp1-{uuid.uuid4().hex[:8]}",
            ts="2024-01-01T00:00:01Z",
            channel_values={
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"}
                ]
            },
            channel_versions={},
            versions_seen={},
            pending_sends=[],
        )
        redis_checkpointer.put(config1, checkpoint1, CheckpointMetadata(), {})

        # Second checkpoint with more messages
        config2 = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        checkpoint2 = Checkpoint(
            v=1,
            id=f"cp2-{uuid.uuid4().hex[:8]}",
            ts="2024-01-01T00:00:02Z",
            channel_values={
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                    {"role": "user", "content": "What is Python?"},
                    {"role": "assistant", "content": "Python is a programming language."}
                ]
            },
            channel_versions={},
            versions_seen={},
            pending_sends=[],
        )
        redis_checkpointer.put(config2, checkpoint2, CheckpointMetadata(), {})

        # Retrieve latest
        get_config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        retrieved = redis_checkpointer.get(get_config)
        messages = retrieved["channel_values"]["messages"]
        assert len(messages) == 4
        assert messages[2]["content"] == "What is Python?"


class TestExamSessionCaching:
    """Tests for exam session data caching patterns."""

    def test_exam_session_state_cache(self, redis_client, cleanup_redis_keys):
        """Test caching exam session state."""
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        key = f"exam:{session_id}:state"
        cleanup_redis_keys(key)

        session_state = {
            "current_question": 0,
            "total_questions": 10,
            "answers": {},
            "start_time": "2024-01-01T10:00:00Z",
            "time_limit_seconds": 1800
        }

        redis_client.json().set(key, "$", session_state)

        retrieved = redis_client.json().get(key)
        assert retrieved["total_questions"] == 10
        assert retrieved["time_limit_seconds"] == 1800

    def test_exam_answer_recording(self, redis_client, cleanup_redis_keys):
        """Test recording answers during exam."""
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        key = f"exam:{session_id}:state"
        cleanup_redis_keys(key)

        initial_state = {
            "current_question": 0,
            "answers": {}
        }
        redis_client.json().set(key, "$", initial_state)

        # Record answer using JSONPath
        redis_client.json().set(key, "$.answers.q1", {
            "response": "Python is a programming language",
            "timestamp": "2024-01-01T10:05:00Z"
        })

        # Move to next question
        redis_client.json().set(key, "$.current_question", 1)

        # Record another answer
        redis_client.json().set(key, "$.answers.q2", {
            "response": "OOP includes encapsulation, inheritance, polymorphism",
            "timestamp": "2024-01-01T10:10:00Z"
        })

        retrieved = redis_client.json().get(key)
        assert retrieved["current_question"] == 1
        assert "q1" in retrieved["answers"]
        assert "q2" in retrieved["answers"]
        assert "Python" in retrieved["answers"]["q1"]["response"]


class TestLearnPlanCaching:
    """Tests for learn plan caching patterns."""

    def test_learn_plan_storage(self, redis_client, cleanup_redis_keys):
        """Test storing learn plan in Redis."""
        lp_id = f"test-lp-{uuid.uuid4().hex[:8]}"
        key = f"lp:{lp_id}:plan"
        cleanup_redis_keys(key)

        learn_plan = {
            "id": lp_id,
            "topic": "Python Basics",
            "sections": [
                {"id": "s1", "title": "Variables", "content_blocks": ["cb1", "cb2"]},
                {"id": "s2", "title": "Data Types", "content_blocks": ["cb3", "cb4"]}
            ],
            "estimated_duration_minutes": 30
        }

        redis_client.json().set(key, "$", learn_plan)

        retrieved = redis_client.json().get(key)
        assert retrieved["topic"] == "Python Basics"
        assert len(retrieved["sections"]) == 2

    def test_learn_session_progress(self, redis_client, cleanup_redis_keys):
        """Test tracking learn session progress."""
        session_id = f"test-learn-{uuid.uuid4().hex[:8]}"
        key = f"learn:{session_id}:progress"
        cleanup_redis_keys(key)

        redis_client.hset(key, mapping={
            "current_section": "0",
            "total_sections": "5",
            "completed_sections": "0",
            "status": "in_progress"
        })

        # Complete a section
        redis_client.hincrby(key, "current_section", 1)
        redis_client.hincrby(key, "completed_sections", 1)

        result = redis_client.hgetall(key)
        assert result["current_section"] == "1"
        assert result["completed_sections"] == "1"
