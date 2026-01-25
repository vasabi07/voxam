"""
Live LLM behavior tests for chat agent context engineering.
Tests that the agent correctly uses clarifying question answers.

These tests make REAL LLM calls (API costs apply).
Run with: pytest tests/behavior/test_chat_agent_live.py -v -s
"""
import pytest
import os
import re
import sys
import time
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="session")
def chat_llm():
    """Get the Groq LLM (openai/gpt-oss-120b) for chat agent testing.

    Uses the same model as exam_agent and learn_agent for consistency.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY not configured")

    return ChatOpenAI(
        model="openai/gpt-oss-120b",
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.3
    )


@pytest.fixture(scope="session")
def chat_tools():
    """Get chat agent tools for binding."""
    from agents.chat_agent import all_agent_tools
    return all_agent_tools


@pytest.fixture(scope="session")
def llm_with_tools(chat_llm, chat_tools):
    """LLM with chat tools bound."""
    return chat_llm.bind_tools(chat_tools)


# ============================================================
# Helper Functions
# ============================================================

def has_tool_call(response, tool_name: str) -> bool:
    """Check if response has a specific tool call."""
    if not hasattr(response, 'tool_calls') or not response.tool_calls:
        return False
    return any(tc.get('name') == tool_name for tc in response.tool_calls)


def get_tool_calls(response) -> list[str]:
    """Get list of tool call names from response."""
    if not hasattr(response, 'tool_calls') or not response.tool_calls:
        return []
    return [tc.get('name') for tc in response.tool_calls]


def contains_re_ask_pattern(text: str) -> bool:
    """Check if response re-asks for clarification."""
    if not text:
        return False
    re_ask_patterns = [
        r"which (document|file|chapter|topic)\??",
        r"could you (specify|clarify|tell me)",
        r"please (specify|select|choose)",
        r"what .* would you like",
        r"can you (specify|clarify|tell)",
    ]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in re_ask_patterns)


# ============================================================
# Test: Clarification Usage
# ============================================================

class TestClarificationUsage:
    """Tests that agent uses clarification answers correctly."""

    def test_uses_document_selection(self, llm_with_tools):
        """After user selects document, agent should use it (not re-ask)."""
        from agents.chat_agent import AGENT_PROMPT, build_working_context

        # Simulate multi-turn conversation
        messages = [
            HumanMessage(content="what sections does this document have?"),
            AIMessage(content="I see you have several documents. Which one would you like me to list sections for?"),
            HumanMessage(content="physics-chapter-3"),
        ]

        working_context = build_working_context(messages)

        system_prompt = AGENT_PROMPT.format(
            user_documents_section="USER'S DOCUMENTS:\n- physics-chapter-3 (id: abc123-def456-ghi789)",
            active_document_section="ACTIVE DOCUMENT: None",
            summary_section="",
            working_context=working_context
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="what sections does this document have?"),
            AIMessage(content="I see you have several documents. Which one would you like me to list sections for?"),
            HumanMessage(content="physics-chapter-3"),
        ]

        response = llm_with_tools.invoke(llm_messages)

        # Should either call query_structure tool OR respond about sections
        # Should NOT re-ask "which document?"
        if response.content:
            assert not contains_re_ask_pattern(response.content), \
                f"Agent re-asked for document after user provided it: {response.content}"

        tool_calls = get_tool_calls(response)
        print(f"✓ Response: {response.content[:200] if response.content else 'No content'}")
        print(f"✓ Tool calls: {tool_calls}")

        # Ideally calls query_structure
        if has_tool_call(response, "query_structure"):
            print("✓ Agent correctly called query_structure tool")

    def test_uses_yes_for_web_search(self, llm_with_tools):
        """After user says 'yes' to web search, agent should search (not re-ask)."""
        from agents.chat_agent import AGENT_PROMPT, build_working_context

        messages = [
            HumanMessage(content="what is quantum entanglement"),
            AIMessage(content="I couldn't find information about quantum entanglement in your documents. Would you like me to search the web?"),
            HumanMessage(content="yes"),
        ]

        working_context = build_working_context(messages)

        system_prompt = AGENT_PROMPT.format(
            user_documents_section="USER'S DOCUMENTS:\n- biology-ch1 (id: bio-123)",
            active_document_section="ACTIVE DOCUMENT: None",
            summary_section="",
            working_context=working_context
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="what is quantum entanglement"),
            AIMessage(content="I couldn't find information about quantum entanglement in your documents. Would you like me to search the web?"),
            HumanMessage(content="yes"),
        ]

        response = llm_with_tools.invoke(llm_messages)

        # Should call web_search tool
        has_web_search = has_tool_call(response, "web_search")

        # Should NOT re-ask about web search
        if response.content:
            re_ask = re.search(r"would you like.*(search|web)", response.content.lower())
            assert not re_ask, f"Agent re-asked about web search: {response.content}"

        print(f"✓ Web search called: {has_web_search}")
        print(f"✓ Response: {response.content[:200] if response.content else 'No content'}")
        print(f"✓ Tool calls: {get_tool_calls(response)}")

    def test_uses_chapter_number(self, llm_with_tools):
        """After user provides chapter number, agent should use it."""
        from agents.chat_agent import AGENT_PROMPT, build_working_context

        messages = [
            HumanMessage(content="give me some practice questions"),
            AIMessage(content="Which chapter would you like questions from?"),
            HumanMessage(content="3"),
        ]

        working_context = build_working_context(messages)

        system_prompt = AGENT_PROMPT.format(
            user_documents_section="USER'S DOCUMENTS:\n- physics (chapters 1-5) (id: physics-doc-123)",
            active_document_section="ACTIVE DOCUMENT: physics (id: physics-doc-123)",
            summary_section="",
            working_context=working_context
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="give me some practice questions"),
            AIMessage(content="Which chapter would you like questions from?"),
            HumanMessage(content="3"),
        ]

        response = llm_with_tools.invoke(llm_messages)

        # Should call get_questions or provide questions
        # Should NOT re-ask "which chapter?"
        if response.content:
            assert not re.search(r"which chapter", response.content.lower()), \
                f"Agent re-asked for chapter: {response.content}"

        print(f"✓ Response: {response.content[:200] if response.content else 'No content'}")
        print(f"✓ Tool calls: {get_tool_calls(response)}")

        if has_tool_call(response, "get_questions"):
            print("✓ Agent correctly called get_questions tool")

    def test_uses_document_uuid(self, llm_with_tools):
        """After user provides a UUID, agent should use it (not re-ask)."""
        from agents.chat_agent import AGENT_PROMPT, build_working_context

        doc_uuid = "f380c2ad-ebe3-4775-bce2-2383c86fd3f3"

        messages = [
            HumanMessage(content="summarize this document"),
            AIMessage(content="You have 3 documents. Which one would you like me to summarize?\n- physics-ch1 (f380c2ad-ebe3-4775-bce2-2383c86fd3f3)\n- biology-ch1 (a1b2c3d4-e5f6-7890-abcd-ef1234567890)\n- chemistry-ch1 (11111111-2222-3333-4444-555555555555)"),
            HumanMessage(content=doc_uuid),
        ]

        working_context = build_working_context(messages)

        system_prompt = AGENT_PROMPT.format(
            user_documents_section=f"USER'S DOCUMENTS:\n- physics-ch1 (id: {doc_uuid})\n- biology-ch1 (id: a1b2c3d4-e5f6-7890-abcd-ef1234567890)",
            active_document_section="ACTIVE DOCUMENT: None",
            summary_section="",
            working_context=working_context
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="summarize this document"),
            AIMessage(content="You have 3 documents. Which one would you like me to summarize?\n- physics-ch1 (f380c2ad-ebe3-4775-bce2-2383c86fd3f3)\n- biology-ch1 (a1b2c3d4-e5f6-7890-abcd-ef1234567890)\n- chemistry-ch1 (11111111-2222-3333-4444-555555555555)"),
            HumanMessage(content=doc_uuid),
        ]

        response = llm_with_tools.invoke(llm_messages)

        # Should NOT re-ask "which document?"
        if response.content:
            assert not contains_re_ask_pattern(response.content), \
                f"Agent re-asked for document after user provided UUID: {response.content}"

        print(f"✓ Response: {response.content[:200] if response.content else 'No content'}")
        print(f"✓ Tool calls: {get_tool_calls(response)}")


# ============================================================
# Test: No False Context
# ============================================================

class TestNoFalseContext:
    """Tests that standalone queries don't get confused with clarifications."""

    def test_new_topic_not_treated_as_answer(self):
        """A substantial new query should be treated as new topic, not clarification answer."""
        from agents.chat_agent import build_working_context

        messages = [
            HumanMessage(content="hello"),
            AIMessage(content="Hi! How can I help you study today?"),
            HumanMessage(content="Explain the process of photosynthesis in detail"),
        ]

        working_context = build_working_context(messages)

        # working_context should be the full query (not wrapped)
        assert "[Answering:" not in working_context
        assert working_context == "Explain the process of photosynthesis in detail"

    def test_substantial_query_after_clarification_request(self):
        """Long query after AI's question should not be wrapped."""
        from agents.chat_agent import build_working_context

        messages = [
            HumanMessage(content="help me"),
            AIMessage(content="What would you like help with?"),
            HumanMessage(content="I need to understand the relationship between voltage and current in electrical circuits"),
        ]

        working_context = build_working_context(messages)

        # This is a substantial query (> 5 words), should not be wrapped
        assert "[Answering:" not in working_context
        assert "voltage" in working_context.lower()


# ============================================================
# Test: Working Context Building
# ============================================================

class TestWorkingContextBuilding:
    """Tests for the build_working_context function."""

    def test_uuid_response_gets_context(self):
        """UUID response should be wrapped with clarifying question context."""
        from agents.chat_agent import build_working_context

        messages = [
            HumanMessage(content="list sections"),
            AIMessage(content="Which document?"),
            HumanMessage(content="abc12345-def6-7890-abcd-ef1234567890"),
        ]

        context = build_working_context(messages)
        assert "[Answering:" in context
        assert "abc12345" in context

    def test_number_response_gets_context(self):
        """Number response should be wrapped with clarifying question context."""
        from agents.chat_agent import build_working_context

        messages = [
            HumanMessage(content="give me questions"),
            AIMessage(content="How many questions?"),
            HumanMessage(content="5"),
        ]

        context = build_working_context(messages)
        assert "[Answering:" in context
        assert "5" in context

    def test_yes_no_response_gets_context(self):
        """Yes/no response should be wrapped with clarifying question context."""
        from agents.chat_agent import build_working_context

        messages = [
            HumanMessage(content="search for this"),
            AIMessage(content="Do you want web search?"),
            HumanMessage(content="yes"),
        ]

        context = build_working_context(messages)
        assert "[Answering:" in context
        assert "yes" in context.lower()


# ============================================================
# Test: Latency and Quality
# ============================================================

class TestLatencyAndQuality:
    """Performance and quality metrics for context engineering."""

    def test_response_latency(self, llm_with_tools):
        """Measure response latency for clarification flows."""
        from agents.chat_agent import AGENT_PROMPT, build_working_context

        messages = [
            HumanMessage(content="list sections"),
            AIMessage(content="Which document?"),
            HumanMessage(content="physics"),
        ]

        working_context = build_working_context(messages)

        system_prompt = AGENT_PROMPT.format(
            user_documents_section="USER'S DOCUMENTS:\n- physics (id: physics-123)",
            active_document_section="ACTIVE DOCUMENT: None",
            summary_section="",
            working_context=working_context
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            *messages
        ]

        latencies = []
        for i in range(3):
            start = time.time()
            response = llm_with_tools.invoke(llm_messages)
            latency = time.time() - start
            latencies.append(latency)
            print(f"  Run {i+1}: {latency:.2f}s")

        avg_latency = sum(latencies) / len(latencies)
        print(f"\nAverage latency: {avg_latency:.2f}s")

        assert avg_latency < 10.0, f"Latency too high: {avg_latency:.2f}s"


# ============================================================
# Test: Agent Does Not Re-Ask After Getting Answer
# ============================================================

class TestNoReAskAfterAnswer:
    """Tests that agent doesn't re-ask after receiving a valid answer."""

    def test_no_reask_after_document_name(self, llm_with_tools):
        """Agent should not re-ask for document after user provides name."""
        from agents.chat_agent import AGENT_PROMPT, build_working_context

        messages = [
            HumanMessage(content="explain the first topic"),
            AIMessage(content="Which document should I look at? You have: physics-ch1, biology-ch1"),
            HumanMessage(content="physics-ch1"),
        ]

        working_context = build_working_context(messages)

        system_prompt = AGENT_PROMPT.format(
            user_documents_section="USER'S DOCUMENTS:\n- physics-ch1 (id: phys-123)\n- biology-ch1 (id: bio-456)",
            active_document_section="ACTIVE DOCUMENT: None",
            summary_section="",
            working_context=working_context
        )

        llm_messages = [
            SystemMessage(content=system_prompt),
            *messages
        ]

        response = llm_with_tools.invoke(llm_messages)

        # Should NOT contain a re-ask pattern
        if response.content:
            # Check for common re-ask patterns
            reask_patterns = [
                r"which document",
                r"could you specify",
                r"please select",
                r"which one would you",
            ]
            for pattern in reask_patterns:
                match = re.search(pattern, response.content.lower())
                assert not match, f"Agent re-asked with pattern '{pattern}': {response.content[:200]}"

        print(f"✓ Response does not re-ask: {response.content[:200] if response.content else 'No content'}")
        print(f"✓ Tool calls: {get_tool_calls(response)}")


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
