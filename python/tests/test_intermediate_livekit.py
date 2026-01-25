"""
Test script for LangGraph intermediate messages with ACTUAL LiveKit TTS.

This creates a real LiveKit room and demonstrates:
1. Graph emits intermediate message → TTS speaks it
2. Graph continues (web search)
3. Graph emits final message → TTS speaks it

Prerequisites:
- LiveKit server running (local or cloud)
- Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in .env

Run with: python -m tests.test_intermediate_livekit
"""

import asyncio
import os
import time
import re
from typing import Literal, Optional, TypedDict
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

# LiveKit imports
from livekit import rtc, api
from google.cloud import texttospeech

load_dotenv()

# Config
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")


# ============================================================
# STATE DEFINITION
# ============================================================

class IntermediateTestState(TypedDict):
    """State for intermediate message testing."""
    messages: list
    user_query: str
    found_in_content: bool
    pending_search: bool
    search_query: Optional[str]
    search_results: Optional[str]


# ============================================================
# MOCK CONTENT
# ============================================================

TOPIC_CONTENT = """
Photosynthesis converts light energy into chemical energy in chloroplasts.
Light reactions occur in thylakoids, producing ATP and NADPH.
The Calvin cycle fixes CO2 into glucose using these products.
"""


# ============================================================
# GRAPH NODES
# ============================================================

def content_router(state: IntermediateTestState) -> dict:
    """Check if question can be answered from content."""
    query = state["user_query"].lower()

    # Simple keyword match for demo
    keywords = ["photosynthesis", "chlorophyll", "atp", "calvin", "glucose", "light"]
    found = any(kw in query for kw in keywords)

    print(f"🔍 Content check for '{state['user_query']}': found={found}")

    return {
        "found_in_content": found,
        "pending_search": not found,
        "search_query": state["user_query"] if not found else None
    }


def emit_intermediate_message(state: IntermediateTestState) -> dict:
    """Emit 'searching...' message - this gets spoken immediately!"""
    print(f"📢 Emitting intermediate message...")

    return {
        "messages": state["messages"] + [
            AIMessage(content="I don't see that in your notes. Let me search the web for you...")
        ]
    }


async def do_web_search(state: IntermediateTestState) -> dict:
    """Simulate web search with delay."""
    print(f"🌐 Searching web for: {state.get('search_query')}")

    # Simulate API latency
    await asyncio.sleep(2)

    mock_result = """Quantum effects in photosynthesis involve quantum coherence,
    where energy is transferred with near-perfect efficiency through multiple pathways simultaneously."""

    print(f"✅ Search complete!")

    return {
        "search_results": mock_result,
        "pending_search": False
    }


def respond_with_search(state: IntermediateTestState) -> dict:
    """Final response with search results."""
    results = state.get("search_results", "")

    return {
        "messages": state["messages"] + [
            AIMessage(content=f"Here's what I found: {results}")
        ]
    }


def respond_from_content(state: IntermediateTestState) -> dict:
    """Response from topic content."""
    return {
        "messages": state["messages"] + [
            AIMessage(content=f"Great question! {TOPIC_CONTENT}")
        ]
    }


def route_after_check(state: IntermediateTestState) -> str:
    return "respond_from_content" if state["found_in_content"] else "emit_intermediate"


# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph():
    workflow = StateGraph(IntermediateTestState)

    workflow.add_node("content_router", content_router)
    workflow.add_node("emit_intermediate", emit_intermediate_message)
    workflow.add_node("web_search", do_web_search)
    workflow.add_node("respond_with_search", respond_with_search)
    workflow.add_node("respond_from_content", respond_from_content)

    workflow.set_entry_point("content_router")

    workflow.add_conditional_edges("content_router", route_after_check)
    workflow.add_edge("emit_intermediate", "web_search")
    workflow.add_edge("web_search", "respond_with_search")
    workflow.add_edge("respond_with_search", END)
    workflow.add_edge("respond_from_content", END)

    return workflow.compile()


# ============================================================
# LIVEKIT TTS HANDLER
# ============================================================

class LiveKitTTSHandler:
    """Handles TTS output to LiveKit room."""

    def __init__(self, audio_source: rtc.AudioSource, region: str = "india"):
        self.audio_source = audio_source
        self.region = region
        self.tts_client = texttospeech.TextToSpeechClient()

    async def speak(self, text: str):
        """Convert text to speech and stream to LiveKit."""
        print(f"\n🔊 [TTS] Speaking: '{text[:60]}...'")
        start = time.time()

        try:
            # Generate TTS audio
            response = self.tts_client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=text),
                voice=texttospeech.VoiceSelectionParams(
                    name="en-IN-Neural2-B",
                    language_code="en-IN"
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                    sample_rate_hertz=48000
                )
            )

            audio_data = response.audio_content

            # Create and send audio frame
            frame = rtc.AudioFrame(
                data=audio_data,
                sample_rate=48000,
                num_channels=1,
                samples_per_channel=len(audio_data) // 2
            )

            await self.audio_source.capture_frame(frame)

            duration = len(audio_data) / (48000 * 2)
            print(f"   ✅ [TTS] Spoke {duration:.1f}s (generated in {time.time()-start:.2f}s)")

            # Wait for audio to play
            await asyncio.sleep(duration)

        except Exception as e:
            print(f"   ❌ [TTS] Error: {e}")

    async def speak_sentences(self, text: str):
        """Split text into sentences and speak each one."""
        sentences = re.findall(r'[^.!?]+[.!?]+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                await self.speak(sentence)

        # Handle remaining text without punctuation
        remaining = re.sub(r'[^.!?]+[.!?]+', '', text).strip()
        if remaining:
            await self.speak(remaining)


# ============================================================
# STREAMING PROCESSOR - THE KEY INTEGRATION
# ============================================================

async def process_with_streaming_tts(
    graph,
    user_query: str,
    tts_handler: LiveKitTTSHandler
):
    """
    Process query with graph streaming, speaking messages as they appear.

    This is the key function showing how to integrate:
    - LangGraph streaming (yields state after each node)
    - LiveKit TTS (speaks immediately when new message detected)
    """

    print(f"\n{'='*60}")
    print(f"🎓 Processing: '{user_query}'")
    print(f"{'='*60}")

    initial_state = IntermediateTestState(
        messages=[HumanMessage(content=user_query)],
        user_query=user_query,
        found_in_content=False,
        pending_search=False,
        search_query=None,
        search_results=None
    )

    # Track which messages we've already spoken
    spoken_count = 1  # Start at 1 (human message)

    # Stream graph execution
    async for event in graph.astream(initial_state):
        for node_name, state_update in event.items():
            print(f"\n--- Node: {node_name} ---")

            # Check for new AI messages
            if "messages" in state_update:
                messages = state_update["messages"]
                new_messages = messages[spoken_count:]

                for msg in new_messages:
                    if isinstance(msg, AIMessage) and msg.content:
                        print(f"🆕 New message from {node_name}!")

                        # SPEAK IMMEDIATELY!
                        await tts_handler.speak_sentences(msg.content)

                        spoken_count += 1

    print(f"\n✅ Processing complete! Messages spoken: {spoken_count - 1}")


# ============================================================
# MAIN TEST
# ============================================================

async def run_livekit_test():
    """Run the test with actual LiveKit connection."""

    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        print("❌ Missing LiveKit credentials. Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET")
        print("   Falling back to mock TTS...")
        await run_mock_test()
        return

    # Create room name
    room_name = f"intermediate-test-{int(time.time())}"

    # Generate token
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity("test-agent")
        .with_name("Test Agent")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )

    print(f"\n📡 Connecting to LiveKit room: {room_name}")
    print(f"   URL: {LIVEKIT_URL}")

    # Connect to room
    room = rtc.Room()
    await room.connect(LIVEKIT_URL, token)
    print(f"✅ Connected!")

    # Create audio source
    audio_source = rtc.AudioSource(48000, 1)
    audio_track = rtc.LocalAudioTrack.create_audio_track("agent_voice", audio_source)
    await room.local_participant.publish_track(audio_track)
    print(f"🔊 Published audio track")

    # Create TTS handler
    tts_handler = LiveKitTTSHandler(audio_source)

    # Build graph
    graph = build_graph()

    # Test 1: Question in content
    print("\n" + "="*80)
    print("TEST 1: Question IN content (direct response)")
    print("="*80)

    await process_with_streaming_tts(
        graph,
        "How does photosynthesis work?",
        tts_handler
    )

    await asyncio.sleep(1)

    # Test 2: Question NOT in content (triggers intermediate message)
    print("\n" + "="*80)
    print("TEST 2: Question NOT in content (intermediate message + search)")
    print("="*80)

    await process_with_streaming_tts(
        graph,
        "What about quantum effects in biology?",
        tts_handler
    )

    # Cleanup
    await room.disconnect()
    print("\n✅ Test complete! Disconnected from room.")


async def run_mock_test():
    """Run with mock TTS (no LiveKit)."""

    async def mock_speak(text: str):
        print(f"🔊 [MOCK TTS]: {text}")
        await asyncio.sleep(len(text.split()) * 0.1)

    graph = build_graph()

    initial_state = IntermediateTestState(
        messages=[HumanMessage(content="What about quantum biology?")],
        user_query="What about quantum biology?",
        found_in_content=False,
        pending_search=False,
        search_query=None,
        search_results=None
    )

    spoken_count = 1

    async for event in graph.astream(initial_state):
        for node_name, state_update in event.items():
            print(f"--- Node: {node_name} ---")

            if "messages" in state_update:
                for msg in state_update["messages"][spoken_count:]:
                    if isinstance(msg, AIMessage) and msg.content:
                        await mock_speak(msg.content)
                        spoken_count += 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  LangGraph + LiveKit Intermediate Messages Test                    ║
║                                                                    ║
║  This demonstrates REAL TTS output with intermediate messages:     ║
║                                                                    ║
║  Flow:                                                             ║
║  1. User asks question not in content                              ║
║  2. Graph emits "Let me search..." → TTS SPEAKS IMMEDIATELY        ║
║  3. Graph does web search (2s delay)                               ║
║  4. Graph emits "Here's what I found..." → TTS SPEAKS              ║
║                                                                    ║
║  The key is using graph.astream() to get state after each node!    ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(run_livekit_test())
