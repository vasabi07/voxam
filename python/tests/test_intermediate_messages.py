"""
Test script for LangGraph intermediate messages with LiveKit TTS.

This demonstrates how to:
1. Emit intermediate messages ("Let me search...")
2. Speak them immediately via TTS
3. Continue graph execution
4. Speak final response

Run with: python -m tests.test_intermediate_messages
"""

import asyncio
import os
import time
from typing import Literal, Optional, TypedDict
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")


# ============================================================
# STATE DEFINITION
# ============================================================

class TestState(TypedDict):
    """State for testing intermediate messages."""
    messages: list
    user_query: str

    # Content check result
    found_in_content: bool

    # Intermediate message flags
    pending_search: bool
    search_query: Optional[str]
    search_results: Optional[str]

    # For tracking which messages are new (for TTS)
    last_spoken_index: int


# ============================================================
# MOCK CONTENT (simulating topic content)
# ============================================================

MOCK_TOPIC_CONTENT = """
Photosynthesis is the process by which plants convert light energy into chemical energy.
It occurs in chloroplasts using chlorophyll.
The light reactions happen in thylakoids, producing ATP and NADPH.
The Calvin cycle uses these to fix CO2 into glucose.
Key concepts: chlorophyll, light reactions, Calvin cycle, ATP, glucose.
"""


# ============================================================
# STRUCTURED OUTPUT FOR CONTENT CHECK
# ============================================================

class ContentCheckResult(BaseModel):
    """Check if answer is in the provided content."""
    found_in_content: bool = Field(
        description="True if the question can be answered from the content"
    )
    confidence: float = Field(ge=0, le=1)
    reason: str


# LLM for content checking (fast, structured output)
router_llm = ChatOpenAI(
    model="nvidia/Nemotron-3-Nano-30B-A3B",
    api_key=DEEPINFRA_API_KEY,
    base_url="https://api.deepinfra.com/v1/openai",
    temperature=0
)


# ============================================================
# GRAPH NODES
# ============================================================

async def content_router_node(state: TestState) -> dict:
    """
    Check if the user's question can be answered from content.
    Fast check using smaller model.
    """
    query = state["user_query"]

    print(f"\n🔍 [content_router] Checking if '{query}' is in content...")

    # Simple keyword check for demo (in production, use LLM)
    query_lower = query.lower()
    content_lower = MOCK_TOPIC_CONTENT.lower()

    # Keywords that indicate the question is about our topic content
    content_keywords = ["photosynthesis", "chlorophyll", "atp", "calvin", "glucose", "light reactions", "thylakoid"]

    # Check if query contains any content keywords
    found = any(kw in query_lower for kw in content_keywords)

    # "quantum" is NOT in our content - should trigger web search
    if "quantum" in query_lower:
        found = False

    print(f"   Found in content: {found}")

    return {
        "found_in_content": found,
        "pending_search": not found,
        "search_query": query if not found else None
    }


def emit_searching_message_node(state: TestState) -> dict:
    """
    Emit intermediate message telling user we're searching.
    This message should be spoken IMMEDIATELY by TTS.
    """
    print(f"\n📢 [emit_searching] Emitting intermediate message...")

    searching_message = AIMessage(
        content="Hmm, I don't see that in your notes. Let me quickly search for some information on that..."
    )

    return {
        "messages": state["messages"] + [searching_message]
    }


async def web_search_node(state: TestState) -> dict:
    """
    Simulate web search (with artificial delay).
    In production, this would call Tavily/Perplexity.
    """
    query = state.get("search_query", "")

    print(f"\n🌐 [web_search] Searching for: '{query}'...")

    # Simulate search latency
    await asyncio.sleep(2)  # 2 second delay to simulate API call

    # Mock search results
    mock_results = f"""
    Based on web search for '{query}':
    Quantum effects in photosynthesis refer to the phenomenon where plants use quantum coherence
    to achieve near-perfect energy transfer efficiency. Recent studies suggest that quantum
    superposition helps chlorophyll molecules explore multiple energy pathways simultaneously.
    """

    print(f"   Search complete!")

    return {
        "search_results": mock_results.strip(),
        "pending_search": False
    }


def respond_with_search_results_node(state: TestState) -> dict:
    """
    Generate final response with grounded search results.
    """
    results = state.get("search_results", "No results found.")

    print(f"\n💬 [respond_with_search] Generating final response...")

    response = AIMessage(
        content=f"Here's what I found: {results[:200]}... Does that help answer your question?"
    )

    return {
        "messages": state["messages"] + [response]
    }


def respond_from_content_node(state: TestState) -> dict:
    """
    Generate response using topic content (no search needed).
    """
    query = state["user_query"]

    print(f"\n💬 [respond_from_content] Answering from content...")

    response = AIMessage(
        content=f"Great question about {query}! Based on your notes: {MOCK_TOPIC_CONTENT[:200]}..."
    )

    return {
        "messages": state["messages"] + [response]
    }


# ============================================================
# ROUTING FUNCTIONS
# ============================================================

def route_after_content_check(state: TestState) -> str:
    """Route based on whether content was found."""
    if state.get("found_in_content"):
        return "respond_from_content"
    else:
        return "emit_searching"


# ============================================================
# BUILD GRAPH
# ============================================================

def build_test_graph():
    """Build the test graph with intermediate message support."""

    workflow = StateGraph(TestState)

    # Add nodes
    workflow.add_node("content_router", content_router_node)
    workflow.add_node("emit_searching", emit_searching_message_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("respond_with_search", respond_with_search_results_node)
    workflow.add_node("respond_from_content", respond_from_content_node)

    # Entry point
    workflow.set_entry_point("content_router")

    # Routing after content check
    workflow.add_conditional_edges(
        "content_router",
        route_after_content_check,
        {
            "respond_from_content": "respond_from_content",
            "emit_searching": "emit_searching"
        }
    )

    # Web search flow: emit_searching → web_search → respond_with_search → END
    workflow.add_edge("emit_searching", "web_search")
    workflow.add_edge("web_search", "respond_with_search")
    workflow.add_edge("respond_with_search", END)

    # Direct response flow: respond_from_content → END
    workflow.add_edge("respond_from_content", END)

    return workflow.compile()


# ============================================================
# TTS SIMULATION (replace with actual TTS in production)
# ============================================================

async def mock_tts_speak(text: str):
    """Simulate TTS speaking (prints with delay)."""
    print(f"\n🔊 [TTS SPEAKING]: {text}")
    # Simulate TTS duration (roughly 100ms per word)
    word_count = len(text.split())
    await asyncio.sleep(word_count * 0.1)
    print(f"   ✅ [TTS DONE]")


# ============================================================
# STREAMING HANDLER - THE KEY PART!
# ============================================================

async def process_with_intermediate_messages(graph, user_query: str):
    """
    Process user query with streaming to capture intermediate messages.

    This is the key function that demonstrates how to:
    1. Stream graph execution
    2. Detect new AI messages at each step
    3. Speak them immediately
    """

    print(f"\n{'='*60}")
    print(f"🎓 Processing query: '{user_query}'")
    print(f"{'='*60}")

    # Initial state
    initial_state = TestState(
        messages=[HumanMessage(content=user_query)],
        user_query=user_query,
        found_in_content=False,
        pending_search=False,
        search_query=None,
        search_results=None,
        last_spoken_index=0  # Track which messages we've already spoken
    )

    # Track messages we've already spoken
    spoken_message_count = 1  # Start at 1 (the human message)

    # Stream the graph execution
    print(f"\n📊 Starting graph stream...")

    async for event in graph.astream(initial_state):
        # event is a dict with node_name: state_update
        for node_name, state_update in event.items():
            print(f"\n--- Node completed: {node_name} ---")

            # Check if this node added new messages
            if "messages" in state_update:
                current_messages = state_update["messages"]

                # Find new messages (ones we haven't spoken yet)
                new_messages = current_messages[spoken_message_count:]

                for msg in new_messages:
                    if isinstance(msg, AIMessage) and msg.content:
                        print(f"\n🆕 New AI message detected!")

                        # SPEAK IMMEDIATELY - don't wait for graph to finish!
                        await mock_tts_speak(msg.content)

                        spoken_message_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Graph execution complete!")
    print(f"   Total messages spoken: {spoken_message_count - 1}")
    print(f"{'='*60}")


# ============================================================
# ALTERNATIVE: Using stream_mode="updates" for finer control
# ============================================================

async def process_with_updates_mode(graph, user_query: str):
    """
    Alternative approach using stream_mode="updates".
    This gives you more granular control over state changes.
    """

    print(f"\n{'='*60}")
    print(f"🎓 [UPDATES MODE] Processing: '{user_query}'")
    print(f"{'='*60}")

    initial_state = TestState(
        messages=[HumanMessage(content=user_query)],
        user_query=user_query,
        found_in_content=False,
        pending_search=False,
        search_query=None,
        search_results=None,
        last_spoken_index=0
    )

    spoken_messages = set()  # Track message IDs we've spoken

    # Stream with updates mode - same format as default
    async for event in graph.astream(initial_state, stream_mode="updates"):
        for node_name, state_update in event.items():
            print(f"\n--- Update from: {node_name} ---")

            # Check for new messages
            if "messages" in state_update:
                for msg in state_update["messages"]:
                    if isinstance(msg, AIMessage) and msg.content:
                        # Use content hash as ID (in production, use proper message IDs)
                        msg_id = hash(msg.content)

                        if msg_id not in spoken_messages:
                            print(f"\n🆕 New AI message from {node_name}!")
                            await mock_tts_speak(msg.content)
                            spoken_messages.add(msg_id)

    print(f"\n✅ [UPDATES MODE] Complete!")


# ============================================================
# TEST CASES
# ============================================================

async def run_tests():
    """Run test cases to demonstrate intermediate messages."""

    graph = build_test_graph()

    print("\n" + "="*80)
    print("TEST 1: Question that IS in content (no web search)")
    print("="*80)

    await process_with_intermediate_messages(
        graph,
        "What is photosynthesis and how does chlorophyll work?"
    )

    print("\n" + "="*80)
    print("TEST 2: Question NOT in content (triggers web search)")
    print("="*80)

    await process_with_intermediate_messages(
        graph,
        "What about quantum effects in photosynthesis?"
    )

    print("\n" + "="*80)
    print("TEST 3: Same as TEST 2 but using updates mode")
    print("="*80)

    await process_with_updates_mode(
        graph,
        "How does quantum coherence help plants?"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════╗
║  LangGraph Intermediate Messages Test                          ║
║                                                                ║
║  This test demonstrates:                                       ║
║  1. Emitting intermediate messages mid-graph                  ║
║  2. Speaking them immediately (TTS simulation)                 ║
║  3. Continuing graph execution                                 ║
║  4. Speaking final response                                    ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(run_tests())
