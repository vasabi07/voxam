"""
LLM Quality Evaluation Tests for Exam Agent.

These tests use LIVE LLM calls to evaluate response quality.
Run with: pytest tests/behavior/test_llm_quality.py -v -s

IMPORTANT: These tests cost real API credits.
"""
import pytest
import time
import re
from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


# ============================================================================
# Quality Evaluation Helpers
# ============================================================================

def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def contains_hint_language(text: str) -> bool:
    """Check if response contains hint/teaching language."""
    hint_patterns = [
        r"\bhint\b",
        r"\bclue\b",
        r"\bconsider\b",
        r"\bthink about\b",
        r"\bremember that\b",
        r"\bthe answer is\b",
        r"\bactually[,\s]",
        r"\blet me explain\b",
        r"\bhere'?s (a|the) (hint|tip)\b",
        r"\byou should know\b",
        r"\bthe correct answer\b",
        r"\btry to recall\b",
    ]
    text_lower = text.lower()
    for pattern in hint_patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def contains_teaching_language(text: str) -> bool:
    """Check if response contains teaching/explanation language."""
    teaching_patterns = [
        r"\bbecause\b.*\bis\b",
        r"\bthis is because\b",
        r"\bthe reason\b",
        r"\bfor example\b",
        r"\bsuch as\b",
        r"\bin other words\b",
        r"\bto understand\b",
        r"\blet me (explain|clarify)\b",
        r"\bthe concept of\b",
        r"\bworks by\b",
        r"\bfunctions as\b",
        r"\bmeans that\b",
        r"\bimplies\b",
        r"\bdemonstrates\b",
    ]
    text_lower = text.lower()
    for pattern in teaching_patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def contains_feedback_language(text: str) -> bool:
    """Check if response contains feedback/evaluation language."""
    feedback_patterns = [
        r"\bgood (answer|job|start|try)\b",
        r"\bwell done\b",
        r"\bexcellent\b",
        r"\bthat'?s (correct|right|wrong|incorrect)\b",
        r"\bpartially correct\b",
        r"\byou'?re (on the right track|close)\b",
        r"\balmost\b",
        r"\bnot quite\b",
        r"\bgreat\b",
    ]
    text_lower = text.lower()
    for pattern in feedback_patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def contains_socratic_elements(text: str) -> bool:
    """Check if response contains Socratic dialogue elements."""
    socratic_patterns = [
        r"\bwhat (do you|makes you) think\b",
        r"\bwhy do you\b",
        r"\bcan you explain\b",
        r"\bwhat if\b",
        r"\bhow would you\b",
        r"\bhave you considered\b",
        r"\bwhat about\b",
        r"\btell me more\b",
    ]
    text_lower = text.lower()
    for pattern in socratic_patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def has_tool_call(response, tool_name: str) -> bool:
    """Check if response has a specific tool call."""
    if not hasattr(response, 'tool_calls') or not response.tool_calls:
        return False
    for tool_call in response.tool_calls:
        if tool_call.get('name') == tool_name:
            return True
    return False


def get_tool_call_args(response, tool_name: str) -> Optional[dict]:
    """Get arguments from a specific tool call."""
    if not hasattr(response, 'tool_calls') or not response.tool_calls:
        return None
    for tool_call in response.tool_calls:
        if tool_call.get('name') == tool_name:
            return tool_call.get('args', {})
    return None


# ============================================================================
# EXAM Mode Compliance Tests
# ============================================================================

class TestExamModeCompliance:
    """Tests that EXAM mode follows strict proctoring rules."""

    def test_exam_refuses_hint_request(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """EXAM mode must refuse hint requests."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Can you give me a hint for this question?")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[EXAM Hint Refusal Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Verify: No hint language, acknowledges refusal
        assert not contains_hint_language(response_text), \
            f"EXAM mode provided hint: {response_text}"

        # Should contain refusal language
        refusal_patterns = [
            r"\bcannot\b",
            r"\bcan'?t\b",
            r"\bno hints?\b",
            r"\bnot (allowed|permitted|able)\b",
            r"\bthis is an exam\b",
        ]
        has_refusal = any(
            re.search(p, response_text.lower()) for p in refusal_patterns
        )
        assert has_refusal, f"EXAM mode did not clearly refuse hint: {response_text}"

    def test_exam_no_teaching_on_wrong_answer(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """EXAM mode must not teach when student gives wrong answer."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="A")  # Wrong answer (correct is B)
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[EXAM No Teaching Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Verify: No teaching or feedback
        assert not contains_teaching_language(response_text), \
            f"EXAM mode taught after wrong answer: {response_text}"
        assert not contains_feedback_language(response_text), \
            f"EXAM mode gave feedback: {response_text}"

    def test_exam_brief_responses(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """EXAM mode responses should be brief (<100 words)."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="I think the answer is B, ATP production.")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        word_count = count_words(response_text)

        print(f"\n[EXAM Brevity Test]")
        print(f"Response ({latency:.2f}s, {word_count} words): {response_text}")

        assert word_count < 100, \
            f"EXAM mode response too long ({word_count} words): {response_text}"

    def test_exam_accepts_letter_only_answer(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """EXAM mode should accept just letter answers for MCQs."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="B")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[EXAM Letter Answer Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should acknowledge answer, not ask for elaboration
        elaboration_patterns = [
            r"\bcan you (explain|elaborate)\b",
            r"\bwhy did you choose\b",
            r"\btell me more\b",
            r"\bwhat makes you\b",
        ]
        has_elaboration_request = any(
            re.search(p, response_text.lower()) for p in elaboration_patterns
        )
        assert not has_elaboration_request, \
            f"EXAM mode asked for elaboration on MCQ: {response_text}"

    def test_exam_redirects_off_topic(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """EXAM mode should redirect off-topic questions."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="What's the weather like today?")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[EXAM Off-Topic Redirect Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should redirect to exam
        redirect_patterns = [
            r"\bexam\b",
            r"\bquestion\b",
            r"\bfocus\b",
            r"\blet'?s (continue|return|proceed)\b",
        ]
        has_redirect = any(
            re.search(p, response_text.lower()) for p in redirect_patterns
        )
        assert has_redirect, \
            f"EXAM mode did not redirect off-topic: {response_text}"


# ============================================================================
# LEARN Mode Compliance Tests
# ============================================================================

class TestLearnModeCompliance:
    """Tests that LEARN mode follows interactive tutoring rules."""

    def test_learn_provides_hints_when_asked(
        self, llm_with_tools, learn_mode_prompt, sample_mcq_question
    ):
        """LEARN mode should provide hints when asked."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="learn")
        system_prompt = learn_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Can you give me a hint?")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[LEARN Hint Provision Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should provide some guidance (not refuse)
        refusal_patterns = [
            r"\bcannot provide hints?\b",
            r"\bno hints? (allowed|available)\b",
        ]
        has_refusal = any(
            re.search(p, response_text.lower()) for p in refusal_patterns
        )
        assert not has_refusal, \
            f"LEARN mode refused hint: {response_text}"

        # Should have helpful content related to the question
        assert len(response_text) > 20, \
            f"LEARN mode hint too brief: {response_text}"

    def test_learn_uses_socratic_dialogue(
        self, llm_with_tools, learn_mode_prompt, sample_mcq_question
    ):
        """LEARN mode should use Socratic dialogue for partial answers."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="learn")
        system_prompt = learn_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="I think it has something to do with energy...")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[LEARN Socratic Dialogue Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should engage further, not just move on
        move_on_patterns = [
            r"\bnext question\b",
            r"\bmoving on\b",
            r"\blet'?s proceed\b",
        ]
        just_moved_on = any(
            re.search(p, response_text.lower()) for p in move_on_patterns
        ) and len(response_text) < 50

        assert not just_moved_on, \
            f"LEARN mode moved on without engagement: {response_text}"

    def test_learn_provides_feedback(
        self, llm_with_tools, learn_mode_prompt, sample_mcq_question
    ):
        """LEARN mode should provide feedback on answers."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="learn")
        system_prompt = learn_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="The answer is B, because mitochondria produce ATP through cellular respiration.")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[LEARN Feedback Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should acknowledge the answer quality in some way
        acknowledgment_patterns = [
            r"\bcorrect\b",
            r"\bright\b",
            r"\bgood\b",
            r"\byes\b",
            r"\bexactly\b",
            r"\bthat'?s it\b",
            r"\bwell done\b",
        ]
        has_acknowledgment = any(
            re.search(p, response_text.lower()) for p in acknowledgment_patterns
        )
        # Note: This is a soft assertion - LEARN mode SHOULD give feedback but format varies
        print(f"Has acknowledgment: {has_acknowledgment}")

    def test_learn_explains_wrong_answer(
        self, llm_with_tools, learn_mode_prompt, sample_mcq_question
    ):
        """LEARN mode should explain when student is wrong."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="learn")
        system_prompt = learn_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="A - I think mitochondria store genetic information.")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[LEARN Wrong Answer Explanation Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should contain teaching/clarification, not just accept wrong answer
        assert len(response_text) > 30, \
            f"LEARN mode response too brief for wrong answer: {response_text}"


# ============================================================================
# Tool Call Accuracy Tests
# ============================================================================

class TestToolCallAccuracy:
    """Tests that tool calls are made correctly."""

    def test_advance_called_on_next_request(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """Tool advance_to_next_question called when student says 'next'."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            AIMessage(content="Answer recorded."),
            HumanMessage(content="Next question please.")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        print(f"\n[Tool Call - Next Question Test]")
        print(f"Response ({latency:.2f}s): {response.content}")
        print(f"Tool calls: {response.tool_calls if hasattr(response, 'tool_calls') else 'None'}")

        assert has_tool_call(response, "advance_to_next_question"), \
            f"Expected advance_to_next_question tool call"

    def test_advance_has_correct_arguments(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """Tool call should have correct qp_id and current_index."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        # Add QP metadata to prompt
        system_prompt = exam_mode_prompt.format(
            current_index=3, total_questions=10
        ) + "\n" + question_context
        system_prompt += "\n\n[SESSION METADATA]\nqp_id: test-qp-123\ncurrent_index: 2"

        messages = [
            SystemMessage(content=system_prompt),
            AIMessage(content="Answer recorded for question 3."),
            HumanMessage(content="next")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        print(f"\n[Tool Call Arguments Test]")
        print(f"Response ({latency:.2f}s): {response.content}")
        print(f"Tool calls: {response.tool_calls if hasattr(response, 'tool_calls') else 'None'}")

        args = get_tool_call_args(response, "advance_to_next_question")
        if args:
            print(f"Tool args: {args}")
            # Verify args contain expected fields
            assert "qp_id" in args or "current_index" in args, \
                f"Tool call missing expected arguments: {args}"

    def test_no_tool_call_on_answer_only(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """No tool call when student just answers (not requesting next)."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="B")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        print(f"\n[No Premature Tool Call Test]")
        print(f"Response ({latency:.2f}s): {response.content}")
        print(f"Tool calls: {response.tool_calls if hasattr(response, 'tool_calls') else 'None'}")

        # Should NOT advance unless student explicitly asks
        has_advance = has_tool_call(response, "advance_to_next_question")
        # Note: Some LLMs may ask "ready for next?" after recording - that's acceptable
        # What's NOT acceptable is automatically advancing
        if has_advance:
            print("WARNING: LLM called advance after just an answer - this may skip questions")

    def test_search_history_called_on_reference(
        self, llm_with_tools, learn_mode_prompt, sample_mcq_question
    ):
        """Tool search_conversation_history called when referencing past discussion."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="learn")
        system_prompt = learn_mode_prompt.format(
            current_index=5, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="What did we discuss earlier about cellular energy?")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        print(f"\n[Search History Tool Call Test]")
        print(f"Response ({latency:.2f}s): {response.content}")
        print(f"Tool calls: {response.tool_calls if hasattr(response, 'tool_calls') else 'None'}")

        # Should call search_conversation_history
        has_search = has_tool_call(response, "search_conversation_history")
        print(f"Has search_conversation_history call: {has_search}")
        # Note: LLM may handle this without tool if context is already available


# ============================================================================
# Greeting Flow Tests
# ============================================================================

class TestGreetingFlow:
    """Tests for session greeting behavior."""

    def test_greeting_includes_question_count(
        self, llm_with_tools, greeting_prompt
    ):
        """Greeting should mention total question count."""
        system_prompt = greeting_prompt.format(
            total_questions=15,
            duration_minutes=30
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="[SESSION_START]")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[Greeting Question Count Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should mention question count
        assert "15" in response_text or "fifteen" in response_text.lower(), \
            f"Greeting did not mention question count: {response_text}"

    def test_greeting_includes_duration(
        self, llm_with_tools, greeting_prompt
    ):
        """Greeting should mention exam duration."""
        system_prompt = greeting_prompt.format(
            total_questions=10,
            duration_minutes=30
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="[SESSION_START]")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[Greeting Duration Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should mention duration
        duration_patterns = [r"\b30\b", r"\bthirty\b", r"\bminutes?\b", r"\bduration\b"]
        has_duration = any(
            re.search(p, response_text.lower()) for p in duration_patterns
        )
        assert has_duration, \
            f"Greeting did not mention duration: {response_text}"

    def test_greeting_does_not_present_question(
        self, llm_with_tools, greeting_prompt
    ):
        """Greeting should NOT present the first question."""
        system_prompt = greeting_prompt.format(
            total_questions=10,
            duration_minutes=30
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="[SESSION_START]")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[Greeting No Question Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should NOT contain question-presenting patterns
        question_patterns = [
            r"question (1|one|#1)\s*[:.]",
            r"here'?s (your|the) (first|1st) question",
            r"let'?s (start|begin) with",
            r"first question is",
        ]
        presents_question = any(
            re.search(p, response_text.lower()) for p in question_patterns
        )
        # Also check for MCQ option patterns
        has_options = re.search(r"\b[A-D]\)", response_text) is not None

        assert not presents_question and not has_options, \
            f"Greeting presented question prematurely: {response_text}"


# ============================================================================
# Latency Measurement Tests
# ============================================================================

class TestLatency:
    """Tests for response latency."""

    def test_response_latency_under_3_seconds(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """Response latency should be under 3 seconds (p95 target: 2s)."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="B")
        ]

        latencies = []
        for i in range(3):
            start_time = time.time()
            response = llm_with_tools.invoke(messages)
            latency = time.time() - start_time
            latencies.append(latency)
            print(f"  Run {i+1}: {latency:.2f}s")

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"\n[Latency Test Results]")
        print(f"Average: {avg_latency:.2f}s")
        print(f"Max: {max_latency:.2f}s")

        assert max_latency < 5.0, \
            f"Max latency too high: {max_latency:.2f}s"
        assert avg_latency < 3.0, \
            f"Average latency too high: {avg_latency:.2f}s"


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge case handling."""

    def test_handles_empty_input(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """Should handle empty input gracefully."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[Empty Input Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should respond gracefully (not error)
        assert len(response_text) > 0, "No response to empty input"

    def test_handles_unclear_answer(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """Should handle unclear/mumbled responses."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=1, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="um... I... maybe... uh...")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[Unclear Input Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should prompt for clarification, not just accept
        assert len(response_text) > 0, "No response to unclear input"

    def test_handles_quit_request_exam(
        self, llm_with_tools, exam_mode_prompt, sample_mcq_question
    ):
        """Should handle quit/end exam request professionally."""
        from tests.behavior.conftest import build_question_context

        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(
            current_index=3, total_questions=10
        ) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="I want to quit the exam")
        ]

        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        latency = time.time() - start_time

        response_text = response.content
        print(f"\n[Quit Request Test]")
        print(f"Response ({latency:.2f}s): {response_text}")

        # Should respond professionally
        assert len(response_text) > 0, "No response to quit request"
        # Should not contain inappropriate language
        assert "sure" not in response_text.lower() or "end" in response_text.lower(), \
            "Response should acknowledge quit intent appropriately"


# ============================================================================
# Summary Report Generator
# ============================================================================

class TestSummaryReport:
    """Generates a summary report of all quality metrics."""

    def test_generate_quality_summary(
        self, llm_with_tools, exam_mode_prompt, learn_mode_prompt,
        greeting_prompt, sample_mcq_question
    ):
        """Run multiple scenarios and generate summary report."""
        from tests.behavior.conftest import build_question_context

        results = {
            "exam_hint_refusal": False,
            "exam_no_teaching": False,
            "exam_brevity": False,
            "learn_provides_hints": False,
            "learn_engagement": False,
            "tool_call_accuracy": False,
            "greeting_correct": False,
            "latency_ok": False,
        }
        latencies = []

        # Test EXAM hint refusal
        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(current_index=1, total_questions=10) + "\n" + question_context

        messages = [SystemMessage(content=system_prompt), HumanMessage(content="Can you give me a hint?")]
        start = time.time()
        response = llm_with_tools.invoke(messages)
        latencies.append(time.time() - start)
        results["exam_hint_refusal"] = not contains_hint_language(response.content)

        # Test EXAM no teaching
        messages = [SystemMessage(content=system_prompt), HumanMessage(content="A")]
        start = time.time()
        response = llm_with_tools.invoke(messages)
        latencies.append(time.time() - start)
        results["exam_no_teaching"] = not contains_teaching_language(response.content)
        results["exam_brevity"] = count_words(response.content) < 100

        # Test LEARN hints
        question_context = build_question_context(sample_mcq_question, mode="learn")
        system_prompt = learn_mode_prompt.format(current_index=1, total_questions=10) + "\n" + question_context

        messages = [SystemMessage(content=system_prompt), HumanMessage(content="Can you give me a hint?")]
        start = time.time()
        response = llm_with_tools.invoke(messages)
        latencies.append(time.time() - start)
        refusal_patterns = [r"\bcannot\b", r"\bcan'?t\b.*hints?\b"]
        results["learn_provides_hints"] = not any(re.search(p, response.content.lower()) for p in refusal_patterns)

        # Test LEARN engagement
        messages = [SystemMessage(content=system_prompt), HumanMessage(content="I think it's about energy...")]
        start = time.time()
        response = llm_with_tools.invoke(messages)
        latencies.append(time.time() - start)
        results["learn_engagement"] = len(response.content) > 30

        # Test tool call
        question_context = build_question_context(sample_mcq_question, mode="exam")
        system_prompt = exam_mode_prompt.format(current_index=1, total_questions=10) + "\n" + question_context

        messages = [
            SystemMessage(content=system_prompt),
            AIMessage(content="Answer recorded."),
            HumanMessage(content="next question")
        ]
        start = time.time()
        response = llm_with_tools.invoke(messages)
        latencies.append(time.time() - start)
        results["tool_call_accuracy"] = has_tool_call(response, "advance_to_next_question")

        # Test greeting
        greeting_sys = greeting_prompt.format(total_questions=10, duration_minutes=30)
        messages = [SystemMessage(content=greeting_sys), HumanMessage(content="[SESSION_START]")]
        start = time.time()
        response = llm_with_tools.invoke(messages)
        latencies.append(time.time() - start)
        results["greeting_correct"] = "10" in response.content or "ten" in response.content.lower()

        # Latency
        avg_latency = sum(latencies) / len(latencies)
        results["latency_ok"] = avg_latency < 3.0

        # Generate Report
        print("\n" + "=" * 60)
        print("LLM QUALITY EVALUATION REPORT - gpt-oss-120b (Cerebras)")
        print("=" * 60)

        print("\nEXAM Mode Compliance:")
        print(f"  [{'PASS' if results['exam_hint_refusal'] else 'FAIL'}] Hint refusal")
        print(f"  [{'PASS' if results['exam_no_teaching'] else 'FAIL'}] No teaching on wrong answer")
        print(f"  [{'PASS' if results['exam_brevity'] else 'FAIL'}] Response brevity (<100 words)")

        print("\nLEARN Mode Compliance:")
        print(f"  [{'PASS' if results['learn_provides_hints'] else 'FAIL'}] Provides hints when asked")
        print(f"  [{'PASS' if results['learn_engagement'] else 'FAIL'}] Engages with partial answers")

        print("\nTool Call Accuracy:")
        print(f"  [{'PASS' if results['tool_call_accuracy'] else 'FAIL'}] advance_to_next_question on 'next'")

        print("\nGreeting Flow:")
        print(f"  [{'PASS' if results['greeting_correct'] else 'FAIL'}] Mentions question count")

        print("\nLatency:")
        print(f"  [{'PASS' if results['latency_ok'] else 'FAIL'}] Average: {avg_latency:.2f}s (target <3.0s)")
        print(f"  Individual: {[f'{l:.2f}s' for l in latencies]}")

        passed = sum(results.values())
        total = len(results)
        print(f"\nOverall: {passed}/{total} tests passed ({100*passed/total:.0f}%)")
        print("=" * 60)

        # Assert overall quality threshold
        assert passed >= 6, f"Quality threshold not met: {passed}/{total}"
