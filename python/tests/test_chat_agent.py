"""
Tests for the Unified Agentic Chat Agent.
Covers context engineering, message filtering, intent detection, and error handling.

Run with: pytest tests/test_chat_agent.py -v
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from agents.chat_agent import (
    ChatState,
    get_user_context_from_config,
    build_working_context,
    AGENT_PROMPT,
)


# ============================================================
# Test: build_working_context() - Intent Detection
# ============================================================

class TestBuildWorkingContext:
    """Tests for build_working_context() intent detection."""

    def test_substantial_query_returned_as_is(self):
        """Queries with > 5 words should be returned unchanged."""
        messages = [
            HumanMessage(content="What are the main topics covered in chapter 3?")
        ]
        result = build_working_context(messages)
        assert result == "What are the main topics covered in chapter 3?"

    def test_uuid_after_clarifying_question(self):
        """UUID response after AI asks 'which document?' should include context."""
        messages = [
            HumanMessage(content="what sections does this doc have?"),
            AIMessage(content="Which document would you like me to list sections for?"),
            HumanMessage(content="f380c2ad-ebe3-4775-bce2-2383c86fd3f3")
        ]
        result = build_working_context(messages)
        assert "[Answering:" in result
        assert "Which document" in result
        assert "f380c2ad-ebe3-4775-bce2-2383c86fd3f3" in result

    def test_number_after_clarifying_question(self):
        """Number response after AI asks 'which chapter?' should include context."""
        messages = [
            HumanMessage(content="give me practice questions"),
            AIMessage(content="Which chapter would you like questions from?"),
            HumanMessage(content="3")
        ]
        result = build_working_context(messages)
        assert "[Answering:" in result
        assert "Which chapter" in result

    def test_yes_no_after_clarifying_question(self):
        """Yes/No responses should include the question context."""
        for response in ["yes", "no", "ok", "sure", "yeah"]:
            messages = [
                HumanMessage(content="search the web for this"),
                AIMessage(content="Would you like me to search the web for more information?"),
                HumanMessage(content=response)
            ]
            result = build_working_context(messages)
            assert "[Answering:" in result, f"Failed for response: {response}"

    def test_short_phrase_after_question(self):
        """Short phrases (<=3 words) after questions should include context."""
        messages = [
            HumanMessage(content="list sections"),
            AIMessage(content="Which document?"),
            HumanMessage(content="physics chapter 3")
        ]
        result = build_working_context(messages)
        assert "[Answering:" in result

    def test_no_question_mark_returns_raw(self):
        """If AI didn't ask a question, return the message as-is."""
        messages = [
            HumanMessage(content="hello"),
            AIMessage(content="Hi! How can I help you today."),  # No question mark
            HumanMessage(content="ok")
        ]
        result = build_working_context(messages)
        assert result == "ok"  # No context added

    def test_empty_messages(self):
        """Empty message list should return empty string."""
        result = build_working_context([])
        assert result == ""

    def test_truncates_long_ai_question(self):
        """AI questions longer than 200 chars should be truncated."""
        long_question = "Which of the following documents would you like? " * 10  # > 200 chars
        messages = [
            HumanMessage(content="list sections"),
            AIMessage(content=long_question),
            HumanMessage(content="1")
        ]
        result = build_working_context(messages)
        assert "..." in result
        assert len(result) < len(long_question) + 100

    def test_medium_query_returned_as_is(self):
        """Queries with exactly 5 words should be returned unchanged."""
        messages = [
            HumanMessage(content="explain the concept of mitosis")  # 5 words
        ]
        result = build_working_context(messages)
        assert result == "explain the concept of mitosis"

    def test_single_word_new_topic_no_question(self):
        """Single word query without prior AI question returns as-is."""
        messages = [
            HumanMessage(content="hello"),
            AIMessage(content="Hi there! I'm ready to help you study."),  # Statement, no question
            HumanMessage(content="photosynthesis")  # New topic
        ]
        result = build_working_context(messages)
        assert result == "photosynthesis"  # No context added (no question mark in AI response)

    def test_multiple_questions_uses_most_recent(self):
        """When AI asked multiple questions, uses the most recent one."""
        messages = [
            HumanMessage(content="help me study"),
            AIMessage(content="What subject would you like to study?"),
            HumanMessage(content="physics"),
            AIMessage(content="Which physics topic? I have chapters on electricity, magnetism, and optics."),
            HumanMessage(content="electricity")
        ]
        result = build_working_context(messages)
        assert "[Answering:" in result
        assert "Which physics topic" in result
        assert "electricity" in result

    def test_uuid_pattern_detection(self):
        """UUID pattern should be recognized as short response."""
        messages = [
            HumanMessage(content="summarize this document"),
            AIMessage(content="Which document would you like summarized?"),
            HumanMessage(content="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        ]
        result = build_working_context(messages)
        assert "[Answering:" in result

    def test_yep_and_nope_variants(self):
        """Test 'yep' and 'nope' variants of yes/no."""
        for response in ["yep", "nope"]:
            messages = [
                HumanMessage(content="search for more info"),
                AIMessage(content="Should I search the web?"),
                HumanMessage(content=response)
            ]
            result = build_working_context(messages)
            assert "[Answering:" in result, f"Failed for response: {response}"


# ============================================================
# Test: ToolMessage Filtering
# ============================================================

class TestMessageFiltering:
    """Tests for message filtering in agent_node context preparation."""

    def test_tool_messages_excluded_from_context(self):
        """ToolMessage should not be passed to LLM."""
        messages = [
            HumanMessage(content="what docs do I have?"),
            AIMessage(content="", tool_calls=[{"name": "list_user_documents", "id": "1", "args": {}}]),
            ToolMessage(content="Found 4 documents: ...", tool_call_id="1"),
            AIMessage(content="You have 4 documents: physics ch1, physics ch2..."),
            HumanMessage(content="what sections in physics ch1?"),
        ]

        # Filter like agent_node does
        recent_messages = []
        for m in messages:
            if isinstance(m, HumanMessage):
                recent_messages.append(m)
            elif isinstance(m, AIMessage) and m.content:
                recent_messages.append(m)
            # ToolMessage excluded

        assert len(recent_messages) == 3  # 2 Human + 1 AI with content
        assert all(not isinstance(m, ToolMessage) for m in recent_messages)

    def test_empty_ai_messages_excluded(self):
        """AIMessage with empty content (tool call placeholders) excluded."""
        messages = [
            HumanMessage(content="search for current electricity"),
            AIMessage(content=""),  # Tool call placeholder, no text
            AIMessage(content="Based on your documents, current electricity is..."),
        ]

        recent_messages = []
        for m in messages:
            if isinstance(m, HumanMessage):
                recent_messages.append(m)
            elif isinstance(m, AIMessage) and m.content:
                recent_messages.append(m)

        assert len(recent_messages) == 2  # Human + AI with content

    def test_mixed_message_types_filtered_correctly(self):
        """Test filtering with a realistic multi-turn conversation."""
        messages = [
            HumanMessage(content="What are the key concepts?"),
            AIMessage(content="", tool_calls=[{"name": "search_documents", "id": "1", "args": {"query": "key concepts"}}]),
            ToolMessage(content="Content block 1: ...", tool_call_id="1"),
            AIMessage(content="The key concepts include: 1. Ohm's Law, 2. Kirchhoff's Laws..."),
            HumanMessage(content="Tell me more about the first one"),
            AIMessage(content="", tool_calls=[{"name": "search_documents", "id": "2", "args": {"query": "Ohm's Law"}}]),
            ToolMessage(content="Content block about Ohm's Law...", tool_call_id="2"),
            AIMessage(content="Ohm's Law states that V = IR..."),
        ]

        recent_messages = []
        for m in messages:
            if isinstance(m, HumanMessage):
                recent_messages.append(m)
            elif isinstance(m, AIMessage) and m.content:
                recent_messages.append(m)

        # Should have: 2 Human messages + 2 AI messages with actual content
        assert len(recent_messages) == 4
        assert all(isinstance(m, (HumanMessage, AIMessage)) for m in recent_messages)
        assert all(not isinstance(m, ToolMessage) for m in recent_messages)


# ============================================================
# Test: User Context Extraction
# ============================================================

class TestUserContextExtraction:
    """Tests for get_user_context_from_config()."""

    def test_extract_user_id_only(self):
        """Extract user_id from 'chat-{user_id}' format with UUID."""
        # UUID format: 36 chars (8-4-4-4-12)
        config = {"configurable": {"thread_id": "chat-a1b2c3d4-e5f6-7890-abcd-ef1234567890"}}
        user_id, doc_id = get_user_context_from_config(config)

        assert user_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert doc_id is None

    def test_extract_user_and_doc_id(self):
        """Extract both from 'chat-{user_id}-{doc_id}' format."""
        config = {"configurable": {"thread_id": "chat-a1b2c3d4-e5f6-7890-abcd-ef1234567890-doc123"}}
        user_id, doc_id = get_user_context_from_config(config)

        assert user_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert doc_id == "doc123"

    def test_invalid_thread_id_format(self):
        """Non-chat thread_id should return None for both."""
        config = {"configurable": {"thread_id": "exam-user123"}}
        user_id, doc_id = get_user_context_from_config(config)

        assert user_id is None
        assert doc_id is None

    def test_empty_config(self):
        """Empty config should return None for both."""
        user_id, doc_id = get_user_context_from_config({})
        assert user_id is None
        assert doc_id is None

    def test_none_config(self):
        """None config should return None for both."""
        user_id, doc_id = get_user_context_from_config(None)
        assert user_id is None
        assert doc_id is None

    def test_missing_configurable(self):
        """Config without 'configurable' key should handle gracefully."""
        config = {"other_key": "value"}
        user_id, doc_id = get_user_context_from_config(config)

        assert user_id is None
        assert doc_id is None

    def test_short_thread_id_no_uuid(self):
        """Thread ID shorter than UUID length should not extract."""
        config = {"configurable": {"thread_id": "chat-short"}}
        user_id, doc_id = get_user_context_from_config(config)

        # "short" is less than 36 chars (UUID length), so no extraction
        assert user_id is None


# ============================================================
# Test: ChatState Initialization
# ============================================================

class TestChatState:
    """Tests for ChatState initialization and defaults."""

    def test_default_values(self):
        """State should have correct default values."""
        state = ChatState(messages=[])

        assert state.get("doc_id") is None
        assert state.get("user_id") is None
        assert state.get("credit_check_passed") is None
        assert state.get("conversation_summary") is None
        assert state.get("summary_message_index") is None
        assert state.get("working_context") is None

    def test_message_preservation(self):
        """Messages should be preserved in state."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]
        state = ChatState(messages=messages)

        assert len(state["messages"]) == 2
        assert state["messages"][0].content == "Hello"
        assert state["messages"][1].content == "Hi there!"


# ============================================================
# Test: Agent Prompt Structure
# ============================================================

class TestAgentPrompt:
    """Tests for AGENT_PROMPT structure and placeholders."""

    def test_prompt_has_working_context_placeholder(self):
        """AGENT_PROMPT should have working_context placeholder."""
        assert "{working_context}" in AGENT_PROMPT
        assert "WORKING CONTEXT" in AGENT_PROMPT

    def test_prompt_has_document_sections(self):
        """AGENT_PROMPT should have document-related placeholders."""
        assert "{user_documents_section}" in AGENT_PROMPT
        assert "{active_document_section}" in AGENT_PROMPT

    def test_prompt_has_summary_section(self):
        """AGENT_PROMPT should have summary section placeholder."""
        assert "{summary_section}" in AGENT_PROMPT

    def test_prompt_has_clarification_guidance(self):
        """AGENT_PROMPT should include guidance on using clarification answers."""
        assert "clarifying question" in AGENT_PROMPT.lower()

    def test_prompt_formatting(self):
        """AGENT_PROMPT should format correctly with all placeholders."""
        formatted = AGENT_PROMPT.format(
            user_documents_section="USER'S DOCUMENTS:\n- physics-ch1\n- physics-ch2",
            active_document_section="ACTIVE DOCUMENT: physics-ch1",
            summary_section="Previous discussion covered Ohm's Law.",
            working_context="User wants to understand current electricity"
        )

        assert "physics-ch1" in formatted
        assert "Ohm's Law" in formatted
        assert "current electricity" in formatted
        assert "{working_context}" not in formatted  # Placeholder replaced


# ============================================================
# Test: Tool Definitions
# ============================================================

class TestToolDefinitions:
    """Tests for tool function signatures and behavior."""

    def test_request_qp_form_with_doc_id(self):
        """QP form tool should work with doc_id."""
        from agents.chat_agent import request_qp_form

        result = request_qp_form.invoke({"doc_id": "doc123"})
        assert "doc123" in result

    def test_request_qp_form_without_doc_id(self):
        """QP form tool should work without doc_id."""
        from agents.chat_agent import request_qp_form

        result = request_qp_form.invoke({})
        assert "user will select" in result

    def test_request_upload_ui(self):
        """Upload UI tool should return expected message."""
        from agents.chat_agent import request_upload_ui

        result = request_upload_ui.invoke({})
        assert "Upload UI" in result

    def test_request_learn_form_with_doc_id(self):
        """Learn form tool should work with doc_id."""
        from agents.chat_agent import request_learn_form

        result = request_learn_form.invoke({"doc_id": "doc456"})
        assert "doc456" in result

    def test_show_sources_with_sources(self):
        """Show sources tool should work with source list."""
        from agents.chat_agent import show_sources

        sources = [
            {"page": 5, "title": "Chapter 2", "excerpt": "key concept..."},
            {"page": 10, "title": "Chapter 3", "excerpt": "another concept..."}
        ]
        result = show_sources.invoke({"sources": sources})
        assert "2 source citations" in result

    def test_show_sources_empty(self):
        """Show sources tool should handle empty list."""
        from agents.chat_agent import show_sources

        result = show_sources.invoke({"sources": []})
        assert "No sources" in result

    def test_web_search_tool(self):
        """Web search tool should handle query."""
        from agents.chat_agent import web_search

        result = web_search.invoke({"query": "mitochondria function"})
        assert "mitochondria function" in result.lower() or "web search" in result.lower()


# ============================================================
# Test: Workflow Construction
# ============================================================

class TestWorkflowConstruction:
    """Tests for workflow graph construction."""

    def test_create_chat_workflow_returns_graph(self):
        """create_chat_workflow should return a StateGraph."""
        from agents.chat_agent import create_chat_workflow

        workflow = create_chat_workflow()

        # Should be a StateGraph
        from langgraph.graph import StateGraph
        assert isinstance(workflow, StateGraph)

    def test_chat_graph_compilation(self):
        """create_chat_graph should return compiled graph."""
        from agents.chat_agent import create_chat_graph

        graph = create_chat_graph()

        # Compiled graph should have invoke method
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")


# ============================================================
# Test: Router Pattern Matching (Fast-path)
# ============================================================

class TestRouterPatterns:
    """Tests for pattern matching used in routing logic."""

    def test_greeting_patterns(self):
        """Simple greetings should be recognizable."""
        greetings = ["hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye"]
        greeting_patterns = ["hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye"]

        for greeting in greetings:
            query = greeting.strip().lower()
            matched = any(
                query == p or query.startswith(p + " ") or query.startswith(p + "!")
                for p in greeting_patterns
            )
            assert matched, f"'{greeting}' should match greeting pattern"

    def test_tool_patterns(self):
        """Tool-related queries should be recognizable."""
        tool_queries = [
            "create exam for chapter 1",
            "generate quiz on biology",
            "upload my notes",
            "i want to create a test",
        ]

        tool_patterns = [
            "create exam", "create quiz", "create test",
            "generate exam", "generate quiz", "generate test",
            "upload", "i want to create",
        ]

        for query in tool_queries:
            query_lower = query.lower()
            matched = any(pattern in query_lower for pattern in tool_patterns)
            assert matched, f"'{query}' should match a tool pattern"


# ============================================================
# Test: Edge Cases
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_long_query_handling(self):
        """Very long queries should be handled gracefully."""
        long_query = "What is " + "very " * 100 + "important?"
        messages = [HumanMessage(content=long_query)]

        # Should not crash
        result = build_working_context(messages)
        assert result == long_query  # Long query (> 5 words) returned as-is

    def test_unicode_query_handling(self):
        """Unicode characters in queries should work."""
        unicode_query = "What is the meaning of \u4e2d\u6587 (Chinese)?"
        messages = [HumanMessage(content=unicode_query)]

        result = build_working_context(messages)
        assert "\u4e2d\u6587" in result

    def test_special_characters_in_query(self):
        """Special characters should not break context building."""
        special_queries = [
            "What is DNA's structure?",
            "Explain the equation E=mc^2",
            "What about 50% efficiency?",
            "How does H2O form?",
        ]

        for query in special_queries:
            messages = [HumanMessage(content=query)]
            result = build_working_context(messages)
            assert result == query  # All > 5 words or contain enough context

    def test_empty_string_query(self):
        """Empty string query should be handled."""
        messages = [HumanMessage(content="")]
        result = build_working_context(messages)
        assert result == ""

    def test_whitespace_only_query(self):
        """Whitespace-only query should be handled."""
        messages = [HumanMessage(content="   ")]
        result = build_working_context(messages)
        assert result == ""

    def test_only_ai_messages(self):
        """Message list with only AI messages should return empty."""
        messages = [
            AIMessage(content="Hello! How can I help?"),
            AIMessage(content="I'm here to assist you."),
        ]
        result = build_working_context(messages)
        assert result == ""


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
