"""
Integration tests for chat agent context engineering.
Tests multi-turn conversation flows with clarifying questions.

These tests verify that the agent correctly handles:
1. Short responses to clarifying questions (UUIDs, numbers, yes/no)
2. Context preservation across multi-turn flows
3. Message filtering for LLM context

Run with: pytest tests/behavior/test_context_engineering.py -v
"""
import pytest
import os
import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agents.chat_agent import build_working_context, ChatState, AGENT_PROMPT


# ============================================================
# Test: Clarifying Question Flows
# ============================================================

class TestClarifyingQuestionFlows:
    """Test realistic conversation flows with clarifying questions."""

    @pytest.mark.parametrize("flow", [
        {
            "name": "document_selection_for_sections",
            "messages": [
                ("human", "what sections does this document have?"),
                ("ai", "I see you have 4 documents. Which one would you like me to list sections for?"),
                ("human", "f380c2ad-ebe3-4775-bce2-2383c86fd3f3"),
            ],
            "expected_context_contains": ["Answering", "Which one", "f380c2ad"],
        },
        {
            "name": "chapter_selection_for_questions",
            "messages": [
                ("human", "give me some practice questions"),
                ("ai", "Which chapter would you like questions from?"),
                ("human", "chapter 3"),
            ],
            "expected_context_contains": ["Answering", "chapter", "chapter 3"],
        },
        {
            "name": "yes_confirmation_for_web_search",
            "messages": [
                ("human", "I need info about quantum mechanics"),
                ("ai", "I couldn't find relevant content in your documents. Would you like me to search the web?"),
                ("human", "yes"),
            ],
            "expected_context_contains": ["Answering", "search the web", "yes"],
        },
        {
            "name": "document_name_selection",
            "messages": [
                ("human", "explain the first topic"),
                ("ai", "Which document should I look at? You have: physics-ch1, physics-ch2, biology-ch1"),
                ("human", "physics-ch1"),
            ],
            "expected_context_contains": ["Answering", "Which document", "physics-ch1"],
        },
        {
            "name": "number_selection",
            "messages": [
                ("human", "I need questions from my doc"),
                ("ai", "How many questions would you like?"),
                ("human", "10"),
            ],
            "expected_context_contains": ["Answering", "How many", "10"],
        },
        {
            "name": "no_rejection",
            "messages": [
                ("human", "search for this topic"),
                ("ai", "Do you want me to use web search for this?"),
                ("human", "no"),
            ],
            "expected_context_contains": ["Answering", "web search", "no"],
        },
        {
            "name": "ok_confirmation",
            "messages": [
                ("human", "generate a quiz"),
                ("ai", "I'll create a quiz from Chapter 2. Is that okay?"),
                ("human", "ok"),
            ],
            "expected_context_contains": ["Answering", "Is that okay", "ok"],
        },
    ])
    def test_clarifying_question_flow(self, flow):
        """Test that clarifying question answers are properly contextualized."""
        messages = []
        for msg_type, content in flow["messages"]:
            if msg_type == "human":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))

        result = build_working_context(messages)

        for expected in flow["expected_context_contains"]:
            assert expected.lower() in result.lower(), \
                f"Expected '{expected}' in context for flow '{flow['name']}', got: {result}"


# ============================================================
# Test: Conversation Continuity
# ============================================================

class TestConversationContinuity:
    """Test that context is maintained across multiple turns."""

    def test_multi_turn_context_preserved(self):
        """Verify working context captures multi-turn intent."""
        # Simulate a conversation where user refines their request
        messages = [
            HumanMessage(content="I want to study"),
            AIMessage(content="Great! What subject would you like to study?"),
            HumanMessage(content="physics"),
            AIMessage(content="Which physics topic? I have chapters on electricity, magnetism, and optics."),
            HumanMessage(content="electricity"),
        ]

        context = build_working_context(messages)

        # The context should capture the clarifying question about topics
        assert "[Answering:" in context
        assert "electricity" in context.lower()

    def test_standalone_query_no_false_context(self):
        """Ensure standalone queries don't get false clarification context."""
        messages = [
            HumanMessage(content="hello"),
            AIMessage(content="Hi! How can I help you today?"),
            HumanMessage(content="explain the concept of electric current in detail"),
        ]

        context = build_working_context(messages)

        # This is a full query (> 5 words), should NOT have [Answering:] prefix
        assert "[Answering:" not in context
        assert context == "explain the concept of electric current in detail"

    def test_long_conversation_uses_recent_question(self):
        """In a long conversation, use the most recent AI question."""
        messages = [
            HumanMessage(content="help me"),
            AIMessage(content="What would you like help with?"),
            HumanMessage(content="studying"),
            AIMessage(content="I'd be happy to help you study. What subject?"),
            HumanMessage(content="physics"),
            AIMessage(content="Physics is great! Which specific topic interests you?"),
            HumanMessage(content="optics"),
        ]

        context = build_working_context(messages)

        # Should reference the most recent question about specific topic
        assert "[Answering:" in context
        assert "topic" in context.lower() or "interests" in context.lower()
        assert "optics" in context.lower()


# ============================================================
# Test: Agent Context Engineering Verification
# ============================================================

class TestAgentContextEngineering:
    """End-to-end tests for agent with context engineering."""

    def test_agent_uses_working_context_in_prompt(self):
        """Verify AGENT_PROMPT has working_context placeholder."""
        assert "{working_context}" in AGENT_PROMPT
        assert "WORKING CONTEXT" in AGENT_PROMPT

    def test_agent_prompt_no_current_query(self):
        """Verify old current_query pattern is removed."""
        # Old implementation had {current_query} - should be gone
        assert "{current_query}" not in AGENT_PROMPT

    def test_agent_prompt_has_clarification_rule(self):
        """Verify prompt includes rule about using clarification answers."""
        assert "clarifying question" in AGENT_PROMPT.lower()
        # Should instruct agent to use the answer to complete the task
        assert "use" in AGENT_PROMPT.lower() or "complete" in AGENT_PROMPT.lower()

    def test_chat_state_has_working_context_field(self):
        """Verify ChatState has working_context field."""
        state = ChatState(messages=[])
        # Should be able to access working_context field
        assert state.get("working_context") is None  # Default is None

        # Should be able to set it
        state_with_context = ChatState(
            messages=[],
            working_context="User wants sections for document X"
        )
        assert state_with_context.get("working_context") == "User wants sections for document X"


# ============================================================
# Test: Edge Cases in Multi-Turn Flows
# ============================================================

class TestMultiTurnEdgeCases:
    """Edge cases in multi-turn conversation handling."""

    def test_tool_call_between_questions_ignored(self):
        """ToolMessage between AI question and user response shouldn't interfere."""
        messages = [
            HumanMessage(content="what chapters do I have?"),
            AIMessage(content="", tool_calls=[{"name": "query_structure", "id": "1", "args": {}}]),
            ToolMessage(content="Found 5 chapters...", tool_call_id="1"),
            AIMessage(content="You have 5 chapters. Which one would you like to explore?"),
            HumanMessage(content="2"),
        ]

        context = build_working_context(messages)

        # Should find the AI question (with ?) and include context
        assert "[Answering:" in context
        assert "Which one" in context

    def test_multiple_questions_in_one_ai_message(self):
        """AI message with multiple questions should still be detected."""
        messages = [
            HumanMessage(content="help me study"),
            AIMessage(content="Sure! What subject? And would you prefer quiz or reading?"),
            HumanMessage(content="physics"),
        ]

        context = build_working_context(messages)

        # Should detect the question and provide context
        assert "[Answering:" in context
        assert "physics" in context.lower()

    def test_ai_message_ends_with_question_mark_in_example(self):
        """AI message with question mark in an example shouldn't trigger."""
        messages = [
            HumanMessage(content="how do I ask questions"),
            AIMessage(content="You can ask things like 'What is photosynthesis?'. I'm ready when you are."),
            HumanMessage(content="ok"),
        ]

        context = build_working_context(messages)

        # The question mark is inside quotes, but the AI IS asking a question implicitly
        # Current implementation will detect any '?' in the message
        # This test documents current behavior - may want to improve later
        assert context in ["ok", "[Answering: You can ask things like 'What is photosynthesis?'. I'm ready when you are.] User response: ok"]

    def test_user_asks_ai_question(self):
        """User's question shouldn't be confused with AI's clarifying question."""
        messages = [
            HumanMessage(content="What is Ohm's law?"),
            AIMessage(content="Ohm's law states that V = IR. Do you want more details?"),
            HumanMessage(content="yes please"),
        ]

        context = build_working_context(messages)

        # "yes please" is 2 words, and AI asked a question
        assert "[Answering:" in context
        assert "more details" in context.lower() or "Do you want" in context

    def test_substantial_response_after_question_not_wrapped(self):
        """Long user response after AI question should not be wrapped."""
        messages = [
            HumanMessage(content="search my docs"),
            AIMessage(content="What would you like me to search for?"),
            HumanMessage(content="I need information about the chemical reactions in photosynthesis"),
        ]

        context = build_working_context(messages)

        # Response is > 5 words, so should be returned as-is
        assert "[Answering:" not in context
        assert context == "I need information about the chemical reactions in photosynthesis"


# ============================================================
# Test: Message Filtering for Context
# ============================================================

class TestContextMessageFiltering:
    """Test message filtering applied before LLM context."""

    def test_filter_realistic_conversation(self):
        """Test filtering on a realistic multi-tool conversation."""
        messages = [
            HumanMessage(content="what documents do I have?"),
            AIMessage(content="", tool_calls=[{"name": "list_documents", "id": "1", "args": {}}]),
            ToolMessage(content="[Doc1, Doc2, Doc3]", tool_call_id="1"),
            AIMessage(content="You have 3 documents: Physics Ch1, Physics Ch2, Biology Ch1."),
            HumanMessage(content="summarize physics ch1"),
            AIMessage(content="", tool_calls=[{"name": "search_documents", "id": "2", "args": {"query": "physics ch1 summary"}}]),
            ToolMessage(content="Physics Chapter 1 covers...", tool_call_id="2"),
            AIMessage(content="Physics Chapter 1 covers mechanics, including Newton's laws and kinematics."),
            HumanMessage(content="tell me about newton's first law"),
        ]

        # Filter as agent_node does
        filtered = []
        for m in messages:
            if isinstance(m, HumanMessage):
                filtered.append(m)
            elif isinstance(m, AIMessage) and m.content:
                filtered.append(m)

        # Should have 3 Human + 2 AI (with content only)
        assert len(filtered) == 5
        human_count = sum(1 for m in filtered if isinstance(m, HumanMessage))
        ai_count = sum(1 for m in filtered if isinstance(m, AIMessage))
        assert human_count == 3
        assert ai_count == 2

        # No ToolMessages
        assert all(not isinstance(m, ToolMessage) for m in filtered)

        # Verify the AI messages have content
        ai_messages = [m for m in filtered if isinstance(m, AIMessage)]
        assert all(m.content for m in ai_messages)

    def test_filter_preserves_order(self):
        """Filtered messages should maintain chronological order."""
        messages = [
            HumanMessage(content="first"),
            AIMessage(content="response to first"),
            HumanMessage(content="second"),
            AIMessage(content=""),  # Empty, should be filtered
            ToolMessage(content="tool result", tool_call_id="x"),
            AIMessage(content="response to second"),
            HumanMessage(content="third"),
        ]

        filtered = []
        for m in messages:
            if isinstance(m, HumanMessage):
                filtered.append(m)
            elif isinstance(m, AIMessage) and m.content:
                filtered.append(m)

        # Verify order
        assert len(filtered) == 5
        assert filtered[0].content == "first"
        assert filtered[1].content == "response to first"
        assert filtered[2].content == "second"
        assert filtered[3].content == "response to second"
        assert filtered[4].content == "third"


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
