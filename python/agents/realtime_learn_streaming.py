"""
Learn agent with STREAMING support for intermediate messages.
Now supports zero-setup conversational discovery flow.

Key Features:
- Supports both legacy LP-based flow AND new conversational flow
- Uses graph.astream() for streaming intermediate messages
- Uses TTS Queue to handle race conditions
- Data channel integration for sending document/topic lists to UI
- Reconnection handling with context preservation

Usage:
  # New conversational flow (no lp_id)
  await start_learn_agent_streaming(room_name, token, None, thread_id, region, user_id)

  # Legacy LP flow
  await start_learn_agent_streaming(room_name, token, lp_id, thread_id, region, user_id)
"""

import asyncio
import re
import json
from concurrent.futures import ThreadPoolExecutor
from langchain_core.messages import HumanMessage, AIMessage

from agents.realtime_base import (
    connect_to_room,
    publish_audio_track,
    create_stt_handler_with_prosody,
    stream_tts_sentences,
    send_data_message,
)
from agents.learn_agent import (
    workflow as learn_agent_workflow,
    LearnState,
    preload_first_topic,
)
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from lib.tts_queue import TTSQueue, classify_with_prosody, TurnMetadata, InterruptionIntent

# Redis URI for async checkpointer
REDIS_URI = "redis://localhost:6379"


def derive_cognitive_level(topics: list[dict]) -> str:
    """
    Derive cognitive level from topic content complexity.
    Used to ground web search results to appropriate level.

    Returns: "elementary", "middle_school", "high_school", or "undergraduate"
    """
    if not topics:
        return "high_school"  # Default

    # Sample content from first few topics
    sample_content = " ".join([
        t.get("content", "")[:500] for t in topics[:3]
    ])

    if not sample_content:
        return "high_school"

    words = sample_content.split()
    if not words:
        return "high_school"

    # Heuristics for complexity:
    avg_word_length = sum(len(w) for w in words) / len(words)
    complex_count = sum(1 for w in words if len(w) > 10)
    complex_ratio = complex_count / len(words)

    technical_terms = ["coefficient", "derivative", "theorem", "synthesis",
                       "mitochondria", "equation", "hypothesis", "algorithm",
                       "methodology", "infrastructure", "paradigm"]
    technical_count = sum(1 for term in technical_terms if term in sample_content.lower())

    score = 0
    if avg_word_length > 6:
        score += 1
    if avg_word_length > 7:
        score += 1
    if complex_ratio > 0.08:
        score += 1
    if complex_ratio > 0.15:
        score += 1
    if technical_count >= 2:
        score += 1
    if technical_count >= 4:
        score += 1

    if score >= 4:
        level = "undergraduate"
    elif score >= 2:
        level = "high_school"
    elif score >= 1:
        level = "middle_school"
    else:
        level = "elementary"

    print(f"Derived cognitive level: {level} (score: {score})")
    return level


async def handle_reconnect(saved_state: dict, room, tts_queue):
    """
    Provide context when student reconnects mid-session.
    Sends appropriate message based on the phase they were in.
    """
    phase = saved_state.get("phase", "greeting")

    if phase == "teaching":
        topic = saved_state.get("selected_topic") or \
                (saved_state.get("current_topic_content") or {}).get("name") or \
                (saved_state.get("current_topic") or {}).get("name") or \
                "our discussion"
        msg = f"Welcome back! We were discussing {topic}. Ready to continue, or want to switch topics?"

    elif phase == "selecting_topic":
        doc = saved_state.get("selected_doc_title") or "your document"
        msg = f"Welcome back! We were picking a topic from {doc}. Which one interests you?"

    elif phase == "selecting_doc":
        msg = "Welcome back! We were picking which document to study. Which one would you like?"

    else:
        msg = "Welcome back! Let me grab your documents again..."

    # Send to both TTS and data channel
    await tts_queue.enqueue(msg)
    await send_data_message(room, "reconnect", {"message": msg, "phase": phase})

    print(f"[Reconnection] Phase: {phase}, Message: {msg[:50]}...")


async def send_ui_update_from_tool_result(tool_result: dict, room):
    """
    Send UI updates via data channel based on tool results.
    This allows the frontend to show document/topic selection UI.
    """
    try:
        # Document list from fetch_user_documents
        if "documents" in tool_result and tool_result.get("found"):
            await send_data_message(room, "document_list", {
                "documents": tool_result["documents"],
                "prompt": "Which document would you like to study?"
            })
            print(f"[Data Channel] Sent document_list ({len(tool_result['documents'])} docs)")

        # Topic list from fetch_document_topics
        elif "topics" in tool_result and "documents" not in tool_result and tool_result.get("found"):
            await send_data_message(room, "topic_list", {
                "topics": tool_result["topics"],
                "prompt": "Which topic interests you?"
            })
            print(f"[Data Channel] Sent topic_list ({len(tool_result['topics'])} topics)")

        # Topic content loaded from fetch_topic_content
        elif "topic" in tool_result and isinstance(tool_result.get("topic"), dict):
            topic_data = tool_result["topic"]
            await send_data_message(room, "topic_loaded", {
                "topic_name": topic_data.get("name", ""),
                "key_concepts": topic_data.get("key_concepts", []),
                "pages": topic_data.get("pages", [])
            })
            print(f"[Data Channel] Sent topic_loaded: {topic_data.get('name')}")

    except Exception as e:
        print(f"[Data Channel] Error sending UI update: {e}")


async def start_learn_agent_streaming(
    room_name: str,
    token: str,
    lp_id: str = None,
    thread_id: str = None,
    region: str = "india",
    user_id: str = None
):
    """
    Learn agent with STREAMING intermediate message support.

    Supports two flows:
    1. New conversational flow (lp_id=None): Agent discovers docs/topics via conversation
    2. Legacy LP flow (lp_id provided): Uses pre-loaded Learn Pack from Redis

    Uses TTSQueue to handle race conditions when graph emits messages
    faster than TTS can speak them.
    """
    # Connect to LiveKit room
    room = await connect_to_room(room_name, token)
    print(f"Learn Session Started")
    print(f"  Thread ID: {thread_id}")
    print(f"  LP ID: {lp_id or 'None (conversational flow)'}")
    print(f"  User ID: {user_id}")
    print(f"  Region: {region.upper()}")
    print(f"  Mode: {'Legacy LP' if lp_id else 'Conversational Discovery'}")

    # Publish audio track for TTS
    audio_source, audio_track = await publish_audio_track(room)

    # Create TTS speak function that returns duration
    async def speak_with_duration(text: str) -> float:
        """Wrapper that speaks and estimates duration."""
        await stream_tts_sentences(text, audio_source, region)
        word_count = len(text.split())
        return word_count / 2.5  # Rough estimate in seconds

    # Create and start TTS queue
    tts_queue = TTSQueue(speak_with_duration, min_gap=0.3)
    await tts_queue.start()

    # Create async checkpointer using context manager pattern
    async with AsyncRedisSaver.from_conn_string(REDIS_URI) as async_checkpointer:
        await async_checkpointer.asetup()
        learn_agent_graph = learn_agent_workflow.compile(checkpointer=async_checkpointer)
        print("Async graph compiled with AsyncRedisSaver")

        # State initialization
        first_invocation = True
        cached_topic = None
        cached_total = None
        all_topics = []
        cached_cognitive_level = "high_school"
        is_conversational_flow = lp_id is None

        async def process_with_streaming(full_transcript: str, metadata: TurnMetadata):
            """
            Process with streaming to capture and speak intermediate messages.

            Key features:
            1. Uses prosody data for smarter intent classification
            2. Uses astream() to get messages as graph executes
            3. Enqueues messages to TTSQueue (non-blocking)
            4. Sends UI updates via data channel for doc/topic lists
            5. Waits for all TTS to complete at the end
            """
            nonlocal first_invocation, cached_topic, cached_total, all_topics, cached_cognitive_level

            try:
                if not full_transcript.strip():
                    print("Empty transcript, skipping")
                    return

                # ============================================================
                # INTERRUPTION HANDLING
                # ============================================================
                tts_active = tts_queue.is_speaking or not tts_queue.queue.empty()

                if tts_active:
                    intent = classify_with_prosody(full_transcript, metadata)
                    print(f"Intent: {intent.value} for '{full_transcript[:30]}...' (duration: {metadata.duration_ms:.0f}ms)")

                    if intent == InterruptionIntent.ACKNOWLEDGMENT:
                        print("Acknowledgment detected - letting TTS continue")
                        return

                    elif intent == InterruptionIntent.CANCEL:
                        print("Cancel detected - clearing queue")
                        await tts_queue.clear_and_interrupt()
                        return

                    print("New input detected - clearing queue and processing")
                    await tts_queue.clear_and_interrupt()

                print(f"\n{'='*60}")
                print(f"[STREAMING] Processing: {full_transcript}")
                print(f"{'='*60}\n")

                # ============================================================
                # BUILD INITIAL STATE
                # ============================================================
                if is_conversational_flow:
                    # New conversational flow - no LP preload
                    if first_invocation:
                        print("Conversational flow - no LP preload needed")
                        first_invocation = False

                    learn_state = LearnState(
                        messages=[HumanMessage(content=full_transcript)],
                        thread_id=thread_id,
                        user_id=user_id,
                        phase="greeting",  # Will be updated from checkpoint if reconnecting
                        session_started=False,
                        cognitive_level=cached_cognitive_level,
                    )
                else:
                    # Legacy LP flow
                    if first_invocation:
                        cached_topic, cached_total, all_topics = preload_first_topic(lp_id)
                        if cached_topic:
                            print(f"Preloaded LP: {cached_topic.get('name')} ({cached_total} topics)")
                            cached_cognitive_level = derive_cognitive_level(all_topics)
                        first_invocation = False

                    learn_state = LearnState(
                        messages=[HumanMessage(content=full_transcript)],
                        thread_id=thread_id,
                        user_id=user_id,
                        lp_id=lp_id,
                        current_topic_index=0,
                        current_topic=cached_topic,
                        total_topics=cached_total,
                        topics=all_topics,
                        session_started=False if cached_topic else True,
                        cognitive_level=cached_cognitive_level,
                    )

                config = {"configurable": {"thread_id": thread_id}}

                # Track messages we've already queued
                queued_message_count = 1  # Start at 1 (human message)

                # ============================================================
                # STREAM THE GRAPH AND PROCESS MESSAGES
                # ============================================================
                async for event in learn_agent_graph.astream(learn_state, config=config):
                    for node_name, state_update in event.items():
                        print(f"\n--- Node: {node_name} ---")

                        # Check for tool results and send UI updates
                        if "messages" in state_update:
                            messages = state_update["messages"]
                            new_messages = messages[queued_message_count:]

                            for msg in new_messages:
                                # Check if it's a tool message with JSON content
                                if hasattr(msg, 'content') and isinstance(msg.content, str):
                                    try:
                                        if msg.content.startswith('{'):
                                            tool_result = json.loads(msg.content)
                                            await send_ui_update_from_tool_result(tool_result, room)
                                    except json.JSONDecodeError:
                                        pass

                                # Queue AI messages for TTS
                                if isinstance(msg, AIMessage) and msg.content:
                                    print(f"New message from {node_name}!")

                                    response_type = state_update.get("response_type", "teaching")

                                    # Send topic change to data channel
                                    if response_type == "next_topic":
                                        await send_data_message(
                                            room,
                                            "topic_change",
                                            msg.content,
                                            None
                                        )

                                    # Enqueue for TTS
                                    await tts_queue.enqueue(msg.content)
                                    queued_message_count += 1

                # Wait for all queued messages to be spoken
                print(f"\nGraph complete, waiting for TTS queue to finish...")
                await tts_queue.wait_until_empty()
                print(f"Streaming complete! Messages spoken: {queued_message_count - 1}")

            except Exception as e:
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()

        # ============================================================
        # PARTICIPANT CONNECTION HANDLERS
        # ============================================================
        @room.on("participant_connected")
        def on_participant_connected(participant):
            """Handle new participant connection - check for reconnection."""
            async def handle_connect():
                config = {"configurable": {"thread_id": thread_id}}

                try:
                    # Check if there's existing state (reconnection)
                    checkpoint_tuple = await async_checkpointer.aget_tuple(config)

                    if checkpoint_tuple and checkpoint_tuple.checkpoint:
                        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
                        if channel_values.get("session_started"):
                            # This is a reconnection
                            print(f"Participant {participant.identity} reconnected to existing session")
                            await handle_reconnect(channel_values, room, tts_queue)
                            return

                    # First connection - trigger greeting
                    if is_conversational_flow:
                        print(f"Participant {participant.identity} connected - starting conversational flow")
                        # The greeting will happen when they first speak
                        # Or we could auto-trigger here
                    else:
                        print(f"Participant {participant.identity} connected - LP flow")

                except Exception as e:
                    print(f"Error checking session state: {e}")

            asyncio.create_task(handle_connect())

        # Handle user interruption (barge-in)
        def on_user_start_speaking():
            """
            Called when user starts speaking.
            We wait for the full transcript and classify intent in process_with_streaming().
            """
            if tts_queue.is_speaking:
                print("User started speaking (waiting for intent classification...)")

        # Subscribe to user audio
        @room.on("track_subscribed")
        def on_track_subscribed(track, publication, participant):
            from livekit import rtc
            if track.kind != rtc.TrackKind.KIND_AUDIO:
                return

            print(f"Received audio from {participant.identity}")

            asyncio.create_task(
                create_stt_handler_with_prosody(
                    track=track,
                    on_end_of_turn=process_with_streaming,
                    on_start_of_turn=on_user_start_speaking,
                )
            )

        print("Learn agent (streaming) ready!")
        await asyncio.Future()  # Keep running


async def main(
    room_name: str,
    token: str,
    lp_id: str = None,
    thread_id: str = None,
    region: str = "india",
    user_id: str = None
):
    """Entry point for streaming learn agent."""
    try:
        print(f"\n{'='*60}")
        print(f"Starting STREAMING Learn Agent")
        print(f"Room: {room_name}")
        print(f"LP ID: {lp_id or 'None (conversational)'}")
        print(f"User ID: {user_id}")
        print(f"{'='*60}\n")

        await start_learn_agent_streaming(
            room_name, token, lp_id, thread_id, region, user_id
        )

    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 5:
        # Args: room_name, token, lp_id (or "none"), thread_id, [region], [user_id]
        lp_id_arg = sys.argv[3]
        lp_id = None if lp_id_arg.lower() in ("none", "null", "") else lp_id_arg

        asyncio.run(main(
            sys.argv[1],
            sys.argv[2],
            lp_id,
            sys.argv[4],
            sys.argv[5] if len(sys.argv) > 5 else "india",
            sys.argv[6] if len(sys.argv) > 6 else None
        ))
    else:
        print("Usage: python realtime_learn_streaming.py <room_name> <token> <lp_id|none> <thread_id> [region] [user_id]")
