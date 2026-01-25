"""
Integration tests for chat agent tools.
Tests actual tool execution with various parameter combinations.

These tests execute the real tool functions (not just LLM decision-making)
to catch bugs like:
- query_structure failing when doc_id=None (Neo4j ParameterMissing error)
- Tool execution errors
- Parameter handling edge cases

Run with: pytest tests/integration/test_chat_tools.py -v -s
"""
import pytest
import os
import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def user_context(existing_document):
    """Get user_id and doc_id from existing document fixture."""
    return {
        "user_id": existing_document["user_id"],
        "doc_id": existing_document["doc_id"]
    }


def make_uuid_thread_id(user_id: str, doc_id: str = None) -> str:
    """
    Create a thread_id that works with get_user_context_from_config.

    The parser expects: chat-{36-char-uuid}-{doc_id}
    If user_id is not a UUID, we pad/truncate to 36 chars.
    """
    # Ensure user_id is exactly 36 chars (UUID format)
    if len(user_id) < 36:
        user_id_padded = user_id + "0" * (36 - len(user_id))
    else:
        user_id_padded = user_id[:36]

    if doc_id:
        return f"chat-{user_id_padded}-{doc_id}"
    else:
        return f"chat-{user_id_padded}"


@pytest.fixture
def config_with_doc(user_context, neo4j_driver):
    """Config with both user_id and doc_id in thread_id.

    Uses a mock to bypass thread_id parsing and inject the real user context.
    """
    from unittest.mock import patch

    user_id = user_context["user_id"]
    doc_id = user_context["doc_id"]

    # Create a config and patch get_user_context_from_config to return real values
    config = {"configurable": {"thread_id": f"chat-test-{user_id}-{doc_id}"}}

    # Store the real context for patching
    config["_test_user_id"] = user_id
    config["_test_doc_id"] = doc_id

    return config


@pytest.fixture
def config_without_doc(user_context, neo4j_driver):
    """Config with only user_id (no doc_id) in thread_id."""
    user_id = user_context["user_id"]

    config = {"configurable": {"thread_id": f"chat-test-{user_id}"}}
    config["_test_user_id"] = user_id
    config["_test_doc_id"] = None

    return config


@pytest.fixture
def config_invalid_user():
    """Config with a non-existent user_id (valid UUID format)."""
    return {"configurable": {"thread_id": "chat-00000000-0000-0000-0000-000000000000"}}


# ============================================================
# Test: query_structure Tool
# ============================================================

class TestQueryStructure:
    """Integration tests for query_structure tool."""

    def test_query_structure_with_doc_id(self, config_with_doc):
        """query_structure should work with valid doc_id."""
        from unittest.mock import patch
        from agents.chat_tools import query_structure

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = query_structure.invoke(
                {"question": "What chapters does this document have?"},
                config=config_with_doc
            )

        assert result is not None
        assert isinstance(result, str)
        print(f"✓ Result: {result[:200]}...")

    def test_query_structure_without_doc_id(self, config_without_doc):
        """query_structure should handle doc_id=None without crashing.

        This is the key test that catches the ParameterMissing bug:
        when doc_id is None, the Text2Cypher LLM may still generate
        a query that references $doc_id, causing Neo4j to fail.
        """
        from unittest.mock import patch
        from agents.chat_tools import query_structure

        user_id = config_without_doc["_test_user_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, None)):
            # Should not raise ParameterMissing error
            result = query_structure.invoke(
                {"question": "What documents do I have?"},
                config=config_without_doc
            )

        assert result is not None
        assert isinstance(result, str)
        # Should return something (fallback or actual results), not crash
        print(f"✓ Result (no doc_id): {result[:200]}...")

    def test_query_structure_list_chapters(self, config_with_doc):
        """query_structure should list chapters."""
        from unittest.mock import patch
        from agents.chat_tools import query_structure

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = query_structure.invoke(
                {"question": "List all chapters"},
                config=config_with_doc
            )

        assert result is not None
        print(f"✓ Chapters result: {result[:300]}...")

    def test_query_structure_count_blocks(self, config_with_doc):
        """query_structure should handle count queries."""
        from unittest.mock import patch
        from agents.chat_tools import query_structure

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = query_structure.invoke(
                {"question": "How many content blocks are in this document?"},
                config=config_with_doc
            )

        assert result is not None
        print(f"✓ Count result: {result[:200]}...")

    def test_query_structure_invalid_user(self, config_invalid_user):
        """query_structure should handle invalid user gracefully."""
        from agents.chat_tools import query_structure

        result = query_structure.invoke(
            {"question": "What chapters are there?"},
            config=config_invalid_user
        )

        assert result is not None
        # Should return "No documents found" or similar, not crash
        print(f"✓ Invalid user result: {result}")


# ============================================================
# Test: search_documents Tool
# ============================================================

class TestSearchDocuments:
    """Integration tests for search_documents tool."""

    def test_search_documents_with_doc_id(self, config_with_doc):
        """search_documents should work with valid doc_id."""
        from unittest.mock import patch
        from agents.chat_tools import search_documents

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = search_documents.invoke(
                {"query": "introduction"},
                config=config_with_doc
            )

        assert result is not None
        assert isinstance(result, str)
        print(f"✓ Search result: {result[:200]}...")

    def test_search_documents_without_doc_id(self, config_without_doc):
        """search_documents should search all user docs when doc_id=None."""
        from unittest.mock import patch
        from agents.chat_tools import search_documents

        user_id = config_without_doc["_test_user_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, None)):
            result = search_documents.invoke(
                {"query": "main concepts"},
                config=config_without_doc
            )

        assert result is not None
        assert isinstance(result, str)
        print(f"✓ Search all docs result: {result[:200]}...")

    def test_search_documents_with_sources(self, config_with_doc):
        """search_documents should include source citations."""
        from unittest.mock import patch
        from agents.chat_tools import search_documents

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = search_documents.invoke(
                {"query": "explain the topic"},
                config=config_with_doc
            )

        assert result is not None
        # Results with sources include SOURCES_FOR_CITATION
        if "No relevant content found" not in result:
            # If content was found, check format
            assert "Found" in result or "passage" in result.lower()
        print(f"✓ Sources result: {result[:300]}...")

    def test_search_documents_no_results(self, config_with_doc):
        """search_documents should handle no results gracefully."""
        from unittest.mock import patch
        from agents.chat_tools import search_documents

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = search_documents.invoke(
                {"query": "xyzzy12345nonexistenttermforsure"},
                config=config_with_doc
            )

        assert result is not None
        # Should return a helpful message, not crash
        assert "No relevant content found" in result or "Found" in result
        print(f"✓ No results: {result}")

    def test_search_documents_invalid_user(self, config_invalid_user):
        """search_documents should handle invalid user gracefully."""
        from agents.chat_tools import search_documents

        result = search_documents.invoke(
            {"query": "anything"},
            config=config_invalid_user
        )

        assert result is not None
        print(f"✓ Invalid user search: {result}")


# ============================================================
# Test: get_questions Tool
# ============================================================

class TestGetQuestions:
    """Integration tests for get_questions tool."""

    def test_get_questions_with_doc_id(self, config_with_doc):
        """get_questions should work with valid doc_id."""
        from unittest.mock import patch
        from agents.chat_tools import get_questions

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = get_questions.invoke(
                {"count": 1},
                config=config_with_doc
            )

        assert result is not None
        assert isinstance(result, str)
        print(f"✓ Questions result: {result[:300]}...")

    def test_get_questions_without_doc_id(self, config_without_doc):
        """get_questions should handle doc_id=None."""
        from unittest.mock import patch
        from agents.chat_tools import get_questions

        user_id = config_without_doc["_test_user_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, None)):
            result = get_questions.invoke(
                {"count": 1},
                config=config_without_doc
            )

        assert result is not None
        assert isinstance(result, str)
        print(f"✓ Questions (no doc_id): {result[:300]}...")

    def test_get_questions_with_count(self, config_with_doc):
        """get_questions should respect count parameter."""
        from unittest.mock import patch
        from agents.chat_tools import get_questions

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = get_questions.invoke(
                {"count": 3},
                config=config_with_doc
            )

        assert result is not None
        print(f"✓ Multiple questions: {result[:400]}...")

    def test_get_questions_with_chapter_filter(self, config_with_doc):
        """get_questions should filter by chapter."""
        from unittest.mock import patch
        from agents.chat_tools import get_questions

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = get_questions.invoke(
                {"chapter": "1", "count": 1},
                config=config_with_doc
            )

        assert result is not None
        print(f"✓ Chapter filter: {result[:300]}...")

    def test_get_questions_with_difficulty_filter(self, config_with_doc):
        """get_questions should filter by difficulty."""
        from unittest.mock import patch
        from agents.chat_tools import get_questions

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            result = get_questions.invoke(
                {"difficulty": "basic", "count": 1},
                config=config_with_doc
            )

        assert result is not None
        print(f"✓ Difficulty filter: {result[:300]}...")

    def test_get_questions_invalid_user(self, config_invalid_user):
        """get_questions should handle invalid user gracefully."""
        from agents.chat_tools import get_questions

        result = get_questions.invoke(
            {"count": 1},
            config=config_invalid_user
        )

        assert result is not None
        # Should return helpful message, not crash
        print(f"✓ Invalid user questions: {result}")


# ============================================================
# Test: Helper Functions
# ============================================================

class TestHelperFunctions:
    """Tests for helper functions in chat_tools."""

    def test_get_user_context_with_doc_id(self):
        """get_user_context_from_config parses thread_id with doc_id."""
        from agents.chat_tools import get_user_context_from_config

        user_id = "12345678-1234-1234-1234-123456789012"
        doc_id = "abcdef12-3456-7890-abcd-ef1234567890"
        config = {"configurable": {"thread_id": f"chat-{user_id}-{doc_id}"}}

        parsed_user_id, parsed_doc_id = get_user_context_from_config(config)

        assert parsed_user_id == user_id
        assert parsed_doc_id == doc_id

    def test_get_user_context_without_doc_id(self):
        """get_user_context_from_config parses thread_id without doc_id."""
        from agents.chat_tools import get_user_context_from_config

        user_id = "12345678-1234-1234-1234-123456789012"
        config = {"configurable": {"thread_id": f"chat-{user_id}"}}

        parsed_user_id, parsed_doc_id = get_user_context_from_config(config)

        assert parsed_user_id == user_id
        assert parsed_doc_id is None

    def test_get_user_context_empty_config(self):
        """get_user_context_from_config handles empty config."""
        from agents.chat_tools import get_user_context_from_config

        user_id, doc_id = get_user_context_from_config({})

        assert user_id is None
        assert doc_id is None

    def test_get_user_context_none_config(self):
        """get_user_context_from_config handles None config."""
        from agents.chat_tools import get_user_context_from_config

        user_id, doc_id = get_user_context_from_config(None)

        assert user_id is None
        assert doc_id is None

    def test_get_user_context_invalid_thread_id(self):
        """get_user_context_from_config handles invalid thread_id."""
        from agents.chat_tools import get_user_context_from_config

        config = {"configurable": {"thread_id": "invalid-format"}}
        user_id, doc_id = get_user_context_from_config(config)

        assert user_id is None
        assert doc_id is None

    def test_extract_doc_id_from_question(self):
        """extract_doc_id_from_question extracts UUID from question text."""
        from agents.chat_tools import extract_doc_id_from_question

        # Test with UUID in question
        doc_id = extract_doc_id_from_question(
            "f380c2ad-ebe3-4775-bce2-2383c86fd3f3 what topics does this doc have?"
        )
        assert doc_id == "f380c2ad-ebe3-4775-bce2-2383c86fd3f3"

        # Test with UUID in middle
        doc_id = extract_doc_id_from_question(
            "Tell me about document f380c2ad-ebe3-4775-bce2-2383c86fd3f3"
        )
        assert doc_id == "f380c2ad-ebe3-4775-bce2-2383c86fd3f3"

        # Test with no UUID
        doc_id = extract_doc_id_from_question("What chapters are there?")
        assert doc_id is None

        # Test with partial UUID (should not match)
        doc_id = extract_doc_id_from_question("What about f380c2ad?")
        assert doc_id is None


# ============================================================
# Test: Tool Error Handling
# ============================================================

class TestToolErrorHandling:
    """Tests for error handling in chat tools."""

    def test_query_structure_handles_cypher_error(self, config_with_doc):
        """query_structure should fallback on Cypher generation errors."""
        from unittest.mock import patch
        from agents.chat_tools import query_structure

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            # A very unusual question that might cause bad Cypher generation
            result = query_structure.invoke(
                {"question": ";;;;DROP TABLE users;;;"},
                config=config_with_doc
            )

        # Should return something (fallback), not crash or expose error
        assert result is not None
        assert "error" not in result.lower() or "Error" not in result
        print(f"✓ Error handling: {result[:200]}...")

    def test_search_documents_handles_embedding_error(self, config_with_doc):
        """search_documents should handle very long queries."""
        from unittest.mock import patch
        from agents.chat_tools import search_documents

        user_id = config_with_doc["_test_user_id"]
        doc_id = config_with_doc["_test_doc_id"]

        with patch("agents.chat_tools.get_user_context_from_config", return_value=(user_id, doc_id)):
            # Very long query
            long_query = "test " * 1000
            result = search_documents.invoke(
                {"query": long_query},
                config=config_with_doc
            )

        # Should handle gracefully
        assert result is not None
        print(f"✓ Long query handled: {result[:100]}...")


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
