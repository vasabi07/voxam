"""
Exam-specific realtime voice handler.
Uses exam_agent graph for exam/assessment sessions.
Includes voice minute tracking and credit monitoring.

Key features:
- Streaming response architecture with TTSQueue
- Two-step response pattern (emit_thinking → tools → response)
- Interruption handling with prosody classification
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from agents.realtime_base import (
    connect_to_room,
    publish_audio_track,
    create_stt_handler_with_prosody,
    stream_tts_sentences,
    send_data_message,
)
from agents.exam_agent import graph as exam_agent_graph, State as ExamState, preload_first_question, check_time_warnings
from lib.tts_queue import TTSQueue, classify_with_prosody, TurnMetadata, InterruptionIntent

# Grace period for reconnection (in seconds)
RECONNECT_GRACE_PERIOD = 300  # 5 minutes


def get_supabase_client():
    """Get Supabase client for database operations."""
    from supabase import create_client
    return create_client(
        os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )


async def update_connected_time(session_id: str, connected: bool, user_connected_at: Optional[datetime] = None):
    """
    Update session connected time in database.

    On connect: Set lastConnectedAt
    On disconnect: Add elapsed time to totalConnectedSeconds
    """
    try:
        supabase = get_supabase_client()

        if connected:
            # User connected - record the time
            supabase.table("ExamSession").update({
                "lastConnectedAt": datetime.now(timezone.utc).isoformat(),
                "lastDisconnectedAt": None,  # Clear disconnect time
            }).eq("id", session_id).execute()
            print(f"✅ Session {session_id}: User connected at {datetime.now(timezone.utc)}")
        else:
            # User disconnected - calculate elapsed time and add to total
            session = supabase.table("ExamSession").select(
                "totalConnectedSeconds, lastConnectedAt"
            ).eq("id", session_id).single().execute()

            if session.data and session.data.get("lastConnectedAt"):
                last_connected = datetime.fromisoformat(
                    session.data["lastConnectedAt"].replace('Z', '+00:00')
                )
                elapsed_seconds = int((datetime.now(timezone.utc) - last_connected).total_seconds())
                new_total = session.data.get("totalConnectedSeconds", 0) + elapsed_seconds

                supabase.table("ExamSession").update({
                    "totalConnectedSeconds": new_total,
                    "lastConnectedAt": None,  # Clear - user no longer connected
                    "lastDisconnectedAt": datetime.now(timezone.utc).isoformat(),
                }).eq("id", session_id).execute()

                print(f"✅ Session {session_id}: User disconnected. Added {elapsed_seconds}s, total: {new_total}s")

    except Exception as e:
        print(f"❌ Error updating connected time: {e}")


async def monitor_credit_limit(
    session_id: str,
    user_id: str,
    room,
    audio_source,
    region: str,
    shutdown_event: asyncio.Event
):
    """
    Background task to monitor user's remaining voice minutes.
    Warns at 2 minutes remaining, force-ends at 0.
    """
    from credits import check_voice_minutes, calculate_session_minutes

    warned = False

    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(60)  # Check every minute

            if shutdown_event.is_set():
                break

            # Get user's remaining minutes
            has_credits, remaining_minutes = check_voice_minutes(user_id)

            # Get current session time
            supabase = get_supabase_client()
            session = supabase.table("ExamSession").select(
                "totalConnectedSeconds, lastConnectedAt"
            ).eq("id", session_id).single().execute()

            if not session.data:
                continue

            total_seconds = session.data.get("totalConnectedSeconds", 0)

            # If still connected, add current connection time
            if session.data.get("lastConnectedAt"):
                last_dt = datetime.fromisoformat(
                    session.data["lastConnectedAt"].replace('Z', '+00:00')
                )
                total_seconds += int((datetime.now(timezone.utc) - last_dt).total_seconds())

            current_session_minutes = calculate_session_minutes(total_seconds)
            effective_remaining = remaining_minutes - current_session_minutes

            print(f"📊 Credit check: {remaining_minutes} mins available, {current_session_minutes} mins used this session, {effective_remaining} mins remaining")

            if effective_remaining <= 2 and not warned:
                # Warn user
                warning_msg = "Warning: You have approximately 2 minutes of voice time remaining. The session will end automatically after that."
                await stream_tts_sentences(warning_msg, audio_source, region)
                await send_data_message(room, "warning", warning_msg)
                warned = True
                print(f"⚠️ Credit warning sent to user {user_id}")

            elif effective_remaining <= 0:
                # Force end
                force_end_msg = "Your voice minutes have been exhausted. The exam will now end. Your progress has been saved."
                await stream_tts_sentences(force_end_msg, audio_source, region)
                await send_data_message(room, "force_end", force_end_msg)
                print(f"🛑 Force ending session for user {user_id} - credits exhausted")

                # Set shutdown event to stop the monitor
                shutdown_event.set()

                # Disconnect room after a short delay for TTS to complete
                await asyncio.sleep(3)
                await room.disconnect()
                break

        except Exception as e:
            print(f"❌ Error in credit monitor: {e}")


async def handle_reconnect(
    saved_state: dict,
    room,
    tts_queue,
    send_data_fn,
):
    """
    Handle student reconnection with context.
    Provides a welcome-back message with current position and time remaining.

    Args:
        saved_state: The restored state values from checkpoint
        room: LiveKit room for data channel messages
        tts_queue: TTS queue for speaking the message
        send_data_fn: Function to send data channel messages
    """
    current_q = saved_state.get("current_index", 0) + 1
    total_q = saved_state.get("total_questions", "?")

    # Calculate time remaining if available
    time_info = ""
    exam_start = saved_state.get("exam_start_time")
    duration = saved_state.get("duration_minutes")
    if exam_start and duration:
        import time
        elapsed = time.time() - exam_start
        remaining = (duration * 60) - elapsed
        if remaining > 0:
            mins = int(remaining // 60)
            time_info = f" You have about {mins} minutes remaining."

    reconnect_msg = f"Welcome back. We were on question {current_q} of {total_q}.{time_info} Ready to continue?"

    print(f"🔄 Reconnection message: {reconnect_msg}")

    # Send via data channel
    await send_data_fn(room, "instruction", reconnect_msg)

    # Speak via TTS
    await tts_queue.enqueue(reconnect_msg)
    await tts_queue.wait_until_empty()


async def start_exam_agent(
    room_name: str,
    token: str,
    qp_id: str,
    thread_id: str,
    region: str = "india",
    session_id: str = None,
    user_id: str = None,
):
    """
    Exam agent that joins a LiveKit room, listens to student audio,
    processes with LangGraph exam agent, and responds with TTS.

    Features:
    - Streaming response architecture with TTSQueue
    - Two-step response pattern (emit_thinking → tools → response)
    - Interruption handling with prosody classification

    Args:
        room_name: LiveKit room name
        token: LiveKit access token
        qp_id: Question paper ID
        thread_id: Thread ID for conversation persistence
        region: "india" or "global" for geo-based TTS voice selection
        session_id: ExamSession database ID for tracking
        user_id: User ID for credit tracking
    """
    # Connect to LiveKit room
    room = await connect_to_room(room_name, token)
    print(f"📝 QP ID: {qp_id}, Thread ID: {thread_id}")
    print(f"🎯 Region: {region.upper()}")
    print(f"📋 Session ID: {session_id}, User ID: {user_id}")

    # Publish audio track for TTS
    audio_source, audio_track = await publish_audio_track(room)

    # Create TTS queue for handling multi-step responses
    async def speak_with_duration(text: str) -> float:
        """Speak text and return estimated duration."""
        await stream_tts_sentences(text, audio_source, region)
        # Estimate duration: ~2.5 words per second for TTS
        word_count = len(text.split())
        return word_count / 2.5

    tts_queue = TTSQueue(speak_with_duration, min_gap=0.3)
    await tts_queue.start()
    print("🔊 TTS Queue started for streaming responses")

    # Shutdown event for graceful termination
    shutdown_event = asyncio.Event()

    # Track student connection state for time tracking
    student_connected = False
    reconnect_timer_task = None

    # Start credit monitoring if session_id and user_id provided
    if session_id and user_id:
        asyncio.create_task(
            monitor_credit_limit(session_id, user_id, room, audio_source, region, shutdown_event)
        )
        print(f"📊 Credit monitor started for session {session_id}")

    async def handle_reconnect_timeout():
        """Called when reconnection grace period expires."""
        nonlocal student_connected
        await asyncio.sleep(RECONNECT_GRACE_PERIOD)

        if not student_connected and session_id:
            print(f"⏰ Reconnect timeout ({RECONNECT_GRACE_PERIOD}s) - marking session as ABANDONED")
            try:
                # Mark session as abandoned
                supabase = get_supabase_client()
                supabase.table("ExamSession").update({
                    "status": "ABANDONED",
                    "endedAt": datetime.now(timezone.utc).isoformat(),
                }).eq("id", session_id).execute()

                # Deduct credits for actual usage
                from credits import deduct_voice_minutes, calculate_session_minutes
                session = supabase.table("ExamSession").select(
                    "totalConnectedSeconds"
                ).eq("id", session_id).single().execute()

                if session.data:
                    minutes = calculate_session_minutes(session.data.get("totalConnectedSeconds", 0))
                    if minutes > 0:
                        deduct_voice_minutes(user_id, minutes)
                        print(f"💳 Deducted {minutes} minutes for abandoned session")

                # Disconnect room
                shutdown_event.set()
                await room.disconnect()

            except Exception as e:
                print(f"❌ Error handling reconnect timeout: {e}")

    @room.on("participant_connected")
    def on_participant_connected(participant):
        """Handle student connecting to the room."""
        nonlocal student_connected, reconnect_timer_task, greeting_sent

        if participant.identity.startswith("exam-agent"):
            return  # Ignore agent

        print(f"👤 Participant connected: {participant.identity}")
        student_connected = True

        # Cancel reconnect timer if running
        if reconnect_timer_task and not reconnect_timer_task.done():
            reconnect_timer_task.cancel()
            print("✅ Reconnect timer cancelled - student reconnected")

        # Update connected time
        if session_id:
            asyncio.create_task(update_connected_time(session_id, connected=True))

        # Check if this is a reconnection (has saved state with exam_started=True)
        async def handle_connect():
            nonlocal greeting_sent
            try:
                config = {"configurable": {"thread_id": thread_id}}
                saved_state = exam_agent_graph.get_state(config)

                if saved_state and saved_state.values and saved_state.values.get("exam_started"):
                    # This is a reconnection - provide context
                    print("🔄 Detected reconnection - providing context")
                    await handle_reconnect(
                        saved_state.values,
                        room,
                        tts_queue,
                        send_data_message,
                    )
                    greeting_sent = True  # Mark as handled
                else:
                    # First connection - trigger greeting
                    await trigger_greeting()
            except Exception as e:
                print(f"⚠️ Error checking state for reconnection: {e}")
                # Fallback to greeting
                await trigger_greeting()

        asyncio.create_task(handle_connect())

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        """Handle student disconnecting from the room."""
        nonlocal student_connected, reconnect_timer_task

        if participant.identity.startswith("exam-agent"):
            return  # Ignore agent

        print(f"👤 Participant disconnected: {participant.identity}")
        student_connected = False

        # Update connected time (pause timer)
        if session_id:
            asyncio.create_task(update_connected_time(session_id, connected=False))

        # Start reconnect grace period timer
        print(f"⏳ Starting {RECONNECT_GRACE_PERIOD}s reconnect grace period...")
        reconnect_timer_task = asyncio.create_task(handle_reconnect_timeout())

    # Preload first question (done once)
    first_invocation = True
    cached_question = None
    cached_total = None
    greeting_sent = False  # Track if greeting has been sent

    async def trigger_greeting():
        """Trigger the greeting when student connects (before they speak)."""
        nonlocal first_invocation, cached_question, cached_total, greeting_sent

        if greeting_sent:
            return  # Already greeted

        try:
            print(f"\n{'='*60}")
            print(f"🎉 Triggering greeting for new session...")
            print(f"{'='*60}\n")

            # Preload questions
            if first_invocation:
                cached_question, cached_total = preload_first_question(qp_id)
                if cached_question:
                    print(f"📚 Preloaded first question ({cached_total} total)")
                else:
                    print(f"⚠️ Failed to preload questions for QP: {qp_id}")
                first_invocation = False

            # Create state with SESSION_START marker to trigger greeting
            import time as time_module
            exam_state = ExamState(
                messages=[HumanMessage(content="[SESSION_START]")],
                thread_id=thread_id,
                qp_id=qp_id,
                current_index=0,
                current_question=cached_question,
                total_questions=cached_total,
                exam_started=False,  # This triggers GREETING_PROMPT
                exam_start_time=time_module.time(),  # Initialize exam start time
                question_start_time=time_module.time(),  # First question starts now
            )

            # Configuration for checkpointer
            config = {"configurable": {"thread_id": thread_id}}

            # Use streaming to get greeting response
            ai_response = None
            async for event in exam_agent_graph.astream(exam_state, config=config):
                for node_name, state_update in event.items():
                    if "messages" in state_update:
                        for msg in state_update["messages"]:
                            if isinstance(msg, AIMessage) and msg.content:
                                ai_response = msg.content

            if ai_response:
                print(f"\n{'='*60}")
                print(f"👋 GREETING:")
                print(f"{ai_response}")
                print(f"{'='*60}\n")

                # Send greeting via data channel
                await send_data_message(room, "instruction", ai_response)

                # Stream TTS greeting (enqueue to TTSQueue)
                await tts_queue.enqueue(ai_response)
                await tts_queue.wait_until_empty()
                print("✅ Greeting complete")

            greeting_sent = True

        except Exception as e:
            print(f"❌ ERROR triggering greeting: {e}")
            import traceback
            traceback.print_exc()

    async def process_complete_transcript_with_prosody(full_transcript: str, metadata: TurnMetadata):
        """
        Process complete user utterance with the exam agent using streaming.
        Handles two-step responses (emit_thinking → processing → response).
        """
        nonlocal first_invocation, cached_question, cached_total, greeting_sent

        try:
            if not full_transcript.strip():
                print("⚠️ Empty transcript, skipping")
                return

            # Check for interruption during TTS playback
            if tts_queue.is_speaking:
                intent = classify_with_prosody(full_transcript, metadata)
                print(f"🎯 Interruption detected! Intent: {intent.value}")

                if intent == InterruptionIntent.ACKNOWLEDGMENT:
                    # "okay", "sure" → let TTS continue
                    print("✅ Acknowledgment - continuing TTS")
                    return
                elif intent == InterruptionIntent.CANCEL:
                    # "stop", "wait" → clear queue
                    print("🛑 Cancel - clearing TTS queue")
                    await tts_queue.clear_and_interrupt()
                    return
                # NEW_INPUT → clear queue and process
                print("🆕 New input - clearing queue and processing")
                await tts_queue.clear_and_interrupt()

            print(f"\n{'='*60}")
            print(f"🤖 Processing transcript with exam agent (streaming)...")
            print(f"📝 Student said: {full_transcript}")
            print(f"⏱️  Turn duration: {metadata.duration_ms:.0f}ms")
            print(f"{'='*60}\n")

            # Preload on first invocation (if not already done by greeting)
            if first_invocation:
                cached_question, cached_total = preload_first_question(qp_id)
                if cached_question:
                    print(f"📚 Preloaded first question ({cached_total} total)")
                else:
                    print(f"⚠️ Failed to preload questions for QP: {qp_id}")
                first_invocation = False

            # Configuration for checkpointer
            config = {"configurable": {"thread_id": thread_id}}

            # Retrieve current state from checkpoint to preserve current_index
            try:
                saved_state = exam_agent_graph.get_state(config)
                if saved_state and saved_state.values:
                    current_index = saved_state.values.get("current_index", 0)
                    current_question = saved_state.values.get("current_question", cached_question)
                    exam_started = saved_state.values.get("exam_started", greeting_sent)
                    print(f"📍 Restored state: current_index={current_index}, exam_started={exam_started}")
                else:
                    current_index = 0
                    current_question = cached_question
                    exam_started = greeting_sent
                    print(f"📍 No saved state, using defaults: current_index={current_index}")
            except Exception as e:
                print(f"⚠️ Could not restore state: {e}, using defaults")
                current_index = 0
                current_question = cached_question
                exam_started = greeting_sent

            # Create exam state with RESTORED values
            import time as time_module
            exam_state = ExamState(
                messages=[HumanMessage(content=full_transcript)],
                thread_id=thread_id,
                qp_id=qp_id,
                current_index=current_index,
                current_question=current_question,
                total_questions=cached_total,
                exam_started=exam_started,
                # Restore time tracking from saved state
                exam_start_time=saved_state.values.get("exam_start_time") if saved_state and saved_state.values else time_module.time(),
                question_start_time=saved_state.values.get("question_start_time") if saved_state and saved_state.values else time_module.time(),
                time_per_question=saved_state.values.get("time_per_question") if saved_state and saved_state.values else {},
                warned_5min=saved_state.values.get("warned_5min", False) if saved_state and saved_state.values else False,
                warned_2min=saved_state.values.get("warned_2min", False) if saved_state and saved_state.values else False,
                warned_1min=saved_state.values.get("warned_1min", False) if saved_state and saved_state.values else False,
            )

            # Track the final response
            final_response = None
            response_type = "follow_up"
            response_options = None

            # Stream agent responses as they're emitted
            async for event in exam_agent_graph.astream(exam_state, config=config):
                for node_name, state_update in event.items():
                    print(f"📥 Event from node: {node_name}")

                    # Check for messages in state updates
                    if "messages" in state_update:
                        for msg in state_update["messages"]:
                            # Handle emit_thinking: Speak immediately for two-step UX
                            if isinstance(msg, ToolMessage) and "[EMIT_THINKING]" in str(msg.content):
                                thinking_text = str(msg.content).replace("[EMIT_THINKING]", "").strip()
                                if thinking_text:
                                    print(f"💭 Speaking thinking: {thinking_text}")
                                    # Enqueue for immediate TTS (non-blocking)
                                    await tts_queue.enqueue(thinking_text)
                                continue

                            # Handle AI messages (final response)
                            if isinstance(msg, AIMessage) and msg.content:
                                final_response = msg.content
                                response_type = state_update.get("response_type", "follow_up")
                                response_options = state_update.get("response_options")

            if final_response:
                print(f"\n{'='*60}")
                print(f"✅ AGENT RESPONSE:")
                print(f"{final_response}")
                print(f"{'='*60}\n")

                print(f"📊 Response type: {response_type}")

                # Send data channel message for questions (UI display)
                if response_type == "question":
                    await send_data_message(room, "question", final_response, response_options)

                # Enqueue final response to TTS queue
                await tts_queue.enqueue(final_response)

                # Wait for all TTS to complete
                await tts_queue.wait_until_empty()
                print("✅ Agent response complete")

                # Check for time warnings after response completes
                try:
                    updated_state = exam_agent_graph.get_state(config)
                    if updated_state and updated_state.values:
                        warning_msg, warning_updates = check_time_warnings(updated_state.values)
                        if warning_msg:
                            print(f"⏰ Time warning: {warning_msg}")
                            # Send warning via data channel
                            await send_data_message(room, "warning", warning_msg)
                            # Speak the warning
                            await tts_queue.enqueue(warning_msg)
                            await tts_queue.wait_until_empty()
                except Exception as e:
                    print(f"⚠️ Error checking time warnings: {e}")
            else:
                print("⚠️ No final AI response from agent")

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

        # Start STT handler with prosody tracking for intelligent interruption handling
        asyncio.create_task(
            create_stt_handler_with_prosody(
                track=track,
                on_end_of_turn=process_complete_transcript_with_prosody,
            )
        )

    # Wait for room to close
    print("✅ Exam agent ready and listening...")
    try:
        await asyncio.Future()  # Run forever until disconnected
    finally:
        # Cleanup TTS queue on shutdown
        await tts_queue.stop()
        print("🔇 TTS Queue stopped")


async def main(
    room_name: str,
    token: str,
    qp_id: str,
    thread_id: str,
    region: str = "india",
    session_id: str = None,
    user_id: str = None,
):
    """
    Main entry point - called from API endpoint.
    In production, this is spawned as a background task from FastAPI.

    Example usage from api.py:
        asyncio.create_task(
            main(room_name, token, qp_id, thread_id, region, session_id, user_id)
        )
    """
    try:
        print(f"\n{'='*60}")
        print(f"🚀 Starting Exam Agent with Streaming + TTSQueue")
        print(f"Room: {room_name}")
        print(f"QP ID: {qp_id}")
        print(f"Thread ID: {thread_id}")
        print(f"Region: {region.upper()}")
        print(f"Session: {session_id}")
        print(f"User: {user_id}")
        print(f"{'='*60}\n")

        await start_exam_agent(
            room_name, token, qp_id, thread_id, region,
            session_id=session_id, user_id=user_id
        )

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("⚠️  This module is meant to be called from api.py")
    print("For testing, provide: room_name, token, qp_id, thread_id, [region]")
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
        print("Usage: python realtime_exam.py <room_name> <token> <qp_id> <thread_id> [region]")
