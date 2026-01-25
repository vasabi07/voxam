"""
Test that the LLM correctly calls the discovery tools.
"""

import os
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# Define mock tools
@tool
def fetch_user_documents(user_id: str) -> dict:
    """Fetch all documents uploaded by this user."""
    return {"found": True, "documents": [{"id": "doc-1", "title": "Test Doc"}]}


@tool
def fetch_document_topics(doc_id: str) -> dict:
    """Fetch available topics for a document."""
    return {"found": True, "topics": ["Topic 1", "Topic 2"]}


@tool
def fetch_topic_content(doc_id: str, topic_name: str) -> dict:
    """Fetch full content for a specific topic."""
    return {"found": True, "topic": {"name": topic_name, "content": "..."}}


tools = [fetch_user_documents, fetch_document_topics, fetch_topic_content]


def test_greeting_calls_fetch_documents():
    """Test: Agent should call fetch_user_documents on greeting."""
    print("\n" + "="*60)
    print("TEST: Greeting calls fetch_user_documents")
    print("="*60)

    llm = ChatOpenAI(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0,
    )
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = """You are a learning tutor. When the session starts:
1. Greet the student warmly
2. IMMEDIATELY call fetch_user_documents(user_id="user-123") to get their documents

You MUST call the tool. Do not just describe what you would do."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Hi, I want to study"),
    ]

    response = llm_with_tools.invoke(messages)

    print(f"\nAgent response: {response.content[:100]}...")

    tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
    print(f"\nTool calls: {tool_calls}")

    passed = any(tc.get("name") == "fetch_user_documents" for tc in tool_calls)
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}: Agent {'called' if passed else 'did not call'} fetch_user_documents")

    return passed


def test_doc_selection_calls_fetch_topics():
    """Test: Agent should call fetch_document_topics when user picks a doc."""
    print("\n" + "="*60)
    print("TEST: Document selection calls fetch_document_topics")
    print("="*60)

    llm = ChatOpenAI(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0,
    )
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = """You are helping the student choose a document.

AVAILABLE DOCUMENTS:
- Biology (doc_id: "bio-123")
- Physics (doc_id: "phys-456")

When the user picks a document, IMMEDIATELY call fetch_document_topics(doc_id=...) with the correct doc_id.

You MUST call the tool."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Let's do Biology"),
    ]

    response = llm_with_tools.invoke(messages)

    print(f"\nAgent response: {response.content[:100]}...")

    tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
    print(f"\nTool calls: {tool_calls}")

    passed = any(tc.get("name") == "fetch_document_topics" for tc in tool_calls)
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}: Agent {'called' if passed else 'did not call'} fetch_document_topics")

    return passed


def test_topic_selection_calls_fetch_content():
    """Test: Agent should call fetch_topic_content when user picks a topic."""
    print("\n" + "="*60)
    print("TEST: Topic selection calls fetch_topic_content")
    print("="*60)

    llm = ChatOpenAI(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0,
    )
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = """You are helping the student choose a topic.

DOCUMENT: Biology (doc_id: "bio-123")
AVAILABLE TOPICS:
- Photosynthesis
- Cell Division
- Genetics

When the user picks a topic, IMMEDIATELY call fetch_topic_content(doc_id="bio-123", topic_name=...) with the topic they chose.

You MUST call the tool."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="I want to learn about Photosynthesis"),
    ]

    response = llm_with_tools.invoke(messages)

    print(f"\nAgent response: {response.content[:100]}...")

    tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
    print(f"\nTool calls: {tool_calls}")

    passed = any(tc.get("name") == "fetch_topic_content" for tc in tool_calls)
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}: Agent {'called' if passed else 'did not call'} fetch_topic_content")

    return passed


def run_all():
    """Run all tool-calling tests."""
    print("\n" + "="*60)
    print("🔧 TOOL CALLING TESTS")
    print("="*60)

    results = {
        "Greeting → fetch_user_documents": test_greeting_calls_fetch_documents(),
        "Doc selection → fetch_document_topics": test_doc_selection_calls_fetch_topics(),
        "Topic selection → fetch_topic_content": test_topic_selection_calls_fetch_content(),
    }

    print("\n" + "="*60)
    print("📊 TOOL CALLING TEST SUMMARY")
    print("="*60)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    run_all()
