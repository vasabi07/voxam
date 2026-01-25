"""
Learn-specific realtime voice handler.
Uses learn_agent graph for tutoring/study sessions.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from langchain_core.messages import HumanMessage

from agents.realtime_base import (
    connect_to_room,
    publish_audio_track,
    create_stt_handler,
    stream_tts_sentences,
    send_data_message,
)
from agents.learn_agent import graph as learn_agent_graph, LearnState, preload_first_topic


async def start_learn_agent(
    room_name: str,
    token: str,
    lp_id: str,
    thread_id: str,
    region: str = "india"
):
    """
    Learn agent that joins a LiveKit room, listens to student audio,
    processes with LangGraph learn agent, and responds with TTS.

    Args:
        room_name: LiveKit room name
        token: LiveKit access token
        lp_id: Learn Pack ID
        thread_id: Thread ID for conversation persistence
        region: "india" or "global" for geo-based TTS voice selection
    """
    # Connect to LiveKit room
    room = await connect_to_room(room_name, token)
    print(f"📚 LP ID: {lp_id}, Thread ID: {thread_id}")
    print(f"🌍 Region: {region.upper()}")

    # Publish audio track for TTS
    audio_source, audio_track = await publish_audio_track(room)

    # Preload first topic (done once)
    first_invocation = True
    cached_topic = None
    cached_total = None
    all_topics = []
    greeting_sent = False  # Track if greeting has been sent

    async def trigger_greeting():
        """Trigger the greeting when student connects (before they speak)."""
        nonlocal first_invocation, cached_topic, cached_total, all_topics, greeting_sent

        if greeting_sent:
            return  # Already greeted

        try:
            print(f"\n{'='*60}")
            print(f"🎉 Triggering greeting for new learn session...")
            print(f"{'='*60}\n")

            # Preload topics
            if first_invocation:
                cached_topic, cached_total, all_topics = preload_first_topic(lp_id)
                if cached_topic:
                    print(f"📚 Preloaded first topic: {cached_topic.get('name')} ({cached_total} total)")
                else:
                    print(f"⚠️ Failed to preload topics for LP: {lp_id}")
                first_invocation = False

            # Create state with SESSION_START marker to trigger greeting
            learn_state = LearnState(
                messages=[HumanMessage(content="[SESSION_START]")],
                thread_id=thread_id,
                lp_id=lp_id,
                current_topic_index=0,
                current_topic=cached_topic,
                total_topics=cached_total,
                topics=all_topics,
                session_started=False,  # This triggers GREETING_PROMPT
            )

            # Configuration for checkpointer
            config = {"configurable": {"thread_id": thread_id}}

            # Run agent in thread pool (sync invoke)
            def run_agent():
                return learn_agent_graph.invoke(learn_state, config=config)

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, run_agent)

            # Extract AI response (greeting)
            ai_response = None
            for msg in reversed(result["messages"]):
                if hasattr(msg, '__class__') and msg.__class__.__name__ == "AIMessage":
                    if msg.content:
                        ai_response = msg.content
                        break

            if ai_response:
                print(f"\n{'='*60}")
                print(f"👋 GREETING:")
                print(f"{ai_response}")
                print(f"{'='*60}\n")

                # Send greeting via data channel
                await send_data_message(room, "instruction", ai_response)

                # Stream TTS greeting
                await stream_tts_sentences(ai_response, audio_source, region)
                print("✅ Greeting complete")

            greeting_sent = True

        except Exception as e:
            print(f"❌ ERROR triggering greeting: {e}")
            import traceback
            traceback.print_exc()

    @room.on("participant_connected")
    def on_participant_connected(participant):
        """Handle student connecting to the room."""
        if participant.identity.startswith("learn-agent"):
            return  # Ignore agent

        print(f"👤 Participant connected: {participant.identity}")

        # Trigger greeting when student first connects
        asyncio.create_task(trigger_greeting())

    async def process_complete_transcript(full_transcript: str):
        """Process complete user utterance with the learn agent."""
        nonlocal first_invocation, cached_topic, cached_total, all_topics, greeting_sent

        try:
            if not full_transcript.strip():
                print("⚠️ Empty transcript, skipping")
                return

            print(f"\n{'='*60}")
            print(f"🎓 Processing transcript with learn agent...")
            print(f"📝 Student said: {full_transcript}")
            print(f"{'='*60}\n")

            # Preload on first invocation (if not already done by greeting)
            if first_invocation:
                cached_topic, cached_total, all_topics = preload_first_topic(lp_id)
                if cached_topic:
                    print(f"📚 Preloaded first topic: {cached_topic.get('name')} ({cached_total} total)")
                else:
                    print(f"⚠️ Failed to preload topics for LP: {lp_id}")
                first_invocation = False

            # Configuration for checkpointer
            config = {"configurable": {"thread_id": thread_id}}

            # IMPORTANT: Retrieve current state from checkpoint to preserve current_topic_index
            # Without this, we overwrite the checkpointed current_topic_index with 0!
            try:
                saved_state = learn_agent_graph.get_state(config)
                if saved_state and saved_state.values:
                    current_topic_index = saved_state.values.get("current_topic_index", 0)
                    current_topic = saved_state.values.get("current_topic", cached_topic)
                    session_started = saved_state.values.get("session_started", greeting_sent)
                    print(f"📍 Restored state: current_topic_index={current_topic_index}, session_started={session_started}")
                else:
                    current_topic_index = 0
                    current_topic = cached_topic
                    session_started = greeting_sent
                    print(f"📍 No saved state, using defaults: current_topic_index={current_topic_index}")
            except Exception as e:
                print(f"⚠️ Could not restore state: {e}, using defaults")
                current_topic_index = 0
                current_topic = cached_topic
                session_started = greeting_sent

            # Create learn state with RESTORED values (not defaults!)
            learn_state = LearnState(
                messages=[HumanMessage(content=full_transcript)],
                thread_id=thread_id,
                lp_id=lp_id,
                current_topic_index=current_topic_index,  # Restored from checkpoint!
                current_topic=current_topic,  # Restored from checkpoint!
                total_topics=cached_total,
                topics=all_topics,
                session_started=session_started,  # Restored from checkpoint!
            )

            # Run agent in thread pool (sync invoke)
            def run_agent():
                return learn_agent_graph.invoke(learn_state, config=config)

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, run_agent)

            # Extract AI response
            ai_response = None
            for msg in reversed(result["messages"]):
                if hasattr(msg, '__class__') and msg.__class__.__name__ == "AIMessage":
                    if msg.content:
                        ai_response = msg.content
                        break

            if not ai_response:
                print("⚠️ No AI response from agent")
                return

            print(f"\n{'='*60}")
            print(f"✅ TUTOR RESPONSE:")
            print(f"{ai_response}")
            print(f"{'='*60}\n")

            # Extract response metadata for data channel
            response_type = result.get("response_type", "teaching")
            print(f"📊 Response type: {response_type}")

            # Send data channel message for topic info (UI display)
            if response_type == "next_topic":
                current_topic = result.get("current_topic", {})
                await send_data_message(
                    room,
                    "topic_change",
                    ai_response,
                    None  # No options for topics
                )

            # Stream TTS response
            await stream_tts_sentences(ai_response, audio_source, region)
            print("✅ Tutor response complete")

        except Exception as e:
            print(f"❌ ERROR processing transcript: {e}")
            import traceback
            traceback.print_exc()

    # Subscribe to user audio tracks
    @room.on("track_subscribed")
    def on_track_subscribed(
        track,
        publication,
        participant
    ):
        from livekit import rtc
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return

        print(f"🎧 Received audio track from {participant.identity}")

        # Start STT handler
        asyncio.create_task(
            create_stt_handler(
                track=track,
                on_end_of_turn=process_complete_transcript,
            )
        )

    # Wait for room to close
    print("✅ Learn agent ready and listening...")
    await asyncio.Future()  # Run forever until disconnected


async def main(
    room_name: str,
    token: str,
    lp_id: str,
    thread_id: str,
    region: str = "india"
):
    """
    Main entry point - called from API endpoint.
    In production, this is spawned as a background task from FastAPI.

    Example usage from api.py:
        asyncio.create_task(
            main(room_name, token, lp_id, thread_id, region)
        )
    """
    try:
        print(f"\n{'='*60}")
        print(f"🎓 Starting Learn Agent with Deepgram Flux v2")
        print(f"Room: {room_name}")
        print(f"LP ID: {lp_id}")
        print(f"Thread ID: {thread_id}")
        print(f"Region: {region.upper()}")
        print(f"{'='*60}\n")

        await start_learn_agent(room_name, token, lp_id, thread_id, region)

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("⚠️  This module is meant to be called from api.py")
    print("For testing, provide: room_name, token, lp_id, thread_id")
    import sys
    if len(sys.argv) >= 5:
        asyncio.run(main(
            sys.argv[1],
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
            sys.argv[5] if len(sys.argv) > 5 else "india"
        ))
    else:
        print("Usage: python realtime_learn.py <room_name> <token> <lp_id> <thread_id> [region]")
