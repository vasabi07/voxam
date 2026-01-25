"""
Shared utilities for voice realtime agents.
Contains TTS/STT setup, LiveKit connection, and audio processing.
"""
import asyncio
import os
import time
import re
from typing import Optional, Callable, Awaitable, Any
from livekit import rtc
from dotenv import load_dotenv
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from google.cloud import texttospeech

# Load environment variables
load_dotenv(dotenv_path=".env", override=False)
load_dotenv(dotenv_path=".env.local", override=True)

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

if not LIVEKIT_URL:
    raise ValueError("Missing LIVEKIT_URL environment variable. Please check your .env.local file.")

if not DEEPGRAM_API_KEY:
    raise ValueError("Missing DEEPGRAM_API_KEY. Please check your .env.local file.")

# Initialize TTS clients
tts_client = texttospeech.TextToSpeechClient()
dg_tts_client = AsyncDeepgramClient(api_key=DEEPGRAM_API_KEY)


# ============================================================
# TTS UTILITIES
# ============================================================

async def generate_and_stream_tts(text: str, audio_source: rtc.AudioSource, region: str = "india") -> bool:
    """
    Generate TTS audio and stream to LiveKit.
    Uses Google Neural2 for India, Deepgram Aura for global users.

    Applies TTS preprocessing to convert:
    - Mathematical notation (², π, ∫) to spoken words
    - Abbreviations (e.g., Fig., Eq.) to full words
    - Citations removed
    - Pauses added for lists and punctuation

    Args:
        text: Text to convert to speech
        audio_source: LiveKit audio source to stream to
        region: "india" for Google Neural2, "global" for Deepgram Aura

    Returns:
        True if successful, False otherwise
    """
    from lib.voice_optimizer import optimize_for_tts

    try:
        start_time = time.time()

        # Preprocess text for natural speech
        text = optimize_for_tts(text)
        print(f"🎵 Generating TTS [{region.upper()}] for: '{text[:80]}...'")

        if region == "india":
            audio_data = await generate_tts_google(text)
        else:
            audio_data = await generate_tts_deepgram(text)

        if not audio_data:
            return False

        generation_time = time.time() - start_time

        # Create AudioFrame and stream to LiveKit
        frame = rtc.AudioFrame(
            data=audio_data,
            sample_rate=48000,
            num_channels=1,
            samples_per_channel=len(audio_data) // 2
        )

        await audio_source.capture_frame(frame)

        duration_seconds = len(audio_data) / (48000 * 2)
        print(f"✅ TTS generated: {duration_seconds:.2f}s (in {generation_time:.2f}s)")
        return True

    except Exception as e:
        print(f"❌ TTS generation error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def generate_tts_google(text: str) -> Optional[bytes]:
    """Generate TTS using Google Cloud Neural2 (Indian English voice)."""
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000,
        speaking_rate=1.0,
    )

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        name="en-IN-Neural2-B",  # Indian English male voice
        language_code="en-IN",
    )

    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    return response.audio_content


async def generate_tts_deepgram(text: str) -> Optional[bytes]:
    """Generate TTS using Deepgram Aura (Global English voice)."""
    options = {
        "model": "aura-orion-en",  # Orion is clear and professional
        "encoding": "linear16",
        "sample_rate": 48000,
    }

    response = await dg_tts_client.speak.v("1").stream(
        {"text": text},
        options
    )

    # Collect all audio chunks
    audio_chunks = []
    async for chunk in response.stream:
        if chunk:
            audio_chunks.append(chunk)
    return b"".join(audio_chunks)


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences for progressive TTS streaming."""
    sentence_pattern = re.compile(r'([^.!?]+[.!?]+)')
    sentences = sentence_pattern.findall(text)

    # Get remaining text without punctuation
    remaining = sentence_pattern.sub('', text).strip()
    if remaining:
        sentences.append(remaining)

    return [s.strip() for s in sentences if s.strip()]


async def stream_tts_sentences(
    text: str,
    audio_source: rtc.AudioSource,
    region: str = "india"
) -> None:
    """Stream TTS for each sentence progressively."""
    sentences = split_into_sentences(text)
    print(f"🎙️ Streaming TTS for {len(sentences)} sentences...")

    for sentence in sentences:
        await generate_and_stream_tts(sentence, audio_source, region)


# ============================================================
# LIVEKIT UTILITIES
# ============================================================

async def connect_to_room(room_name: str, token: str) -> rtc.Room:
    """Connect to a LiveKit room."""
    room = rtc.Room()

    def on_disconnected(reason: str):
        print(f"[Agent] Disconnected from room: {reason}")

    room.on("disconnected", on_disconnected)

    await room.connect(LIVEKIT_URL, token)
    print(f"🤖 Agent joined room: {room_name}")

    return room


async def publish_audio_track(room: rtc.Room) -> tuple[rtc.AudioSource, rtc.LocalAudioTrack]:
    """Create and publish audio source for TTS output."""
    audio_source = rtc.AudioSource(48000, 1)  # 48kHz, mono
    audio_track = rtc.LocalAudioTrack.create_audio_track("agent_voice", audio_source)
    await room.local_participant.publish_track(audio_track)
    print("🔊 Published agent audio track for TTS output")

    return audio_source, audio_track


# ============================================================
# DEEPGRAM STT UTILITIES
# ============================================================

async def create_stt_handler(
    track: rtc.Track,
    on_end_of_turn: Callable[[str], Awaitable[None]],
    on_start_of_turn: Optional[Callable[[], None]] = None,
    on_partial: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Create Deepgram Flux STT handler for a LiveKit audio track.

    Args:
        track: LiveKit audio track to process
        on_end_of_turn: Async callback when user finishes speaking (receives full transcript)
        on_start_of_turn: Optional callback when user starts speaking
        on_partial: Optional callback for partial transcripts
    """
    transcript_buffer = []

    try:
        # Initialize Deepgram Flux client
        dg_client = AsyncDeepgramClient(api_key=DEEPGRAM_API_KEY)

        async with dg_client.listen.v2.connect(
            model="flux-general-en",
            encoding="linear16",
            sample_rate="48000",
            eot_threshold="0.7",
            eot_timeout_ms="5000"
        ) as connection:

            def on_message(message) -> None:
                nonlocal transcript_buffer

                msg_type = getattr(message, "type", "Unknown")

                if msg_type == "Connected":
                    print(f"✅ Connected to Deepgram Flux v2")
                    return

                if msg_type == "TurnInfo":
                    event = getattr(message, "event", "Unknown")

                    if event == "Update":
                        if hasattr(message, 'transcript') and message.transcript:
                            transcript = message.transcript.strip()
                            if transcript and len(transcript) > 10 and on_partial:
                                on_partial(transcript)

                    elif event == "StartOfTurn":
                        print(f"🎤 StartOfTurn - user started speaking")
                        if on_start_of_turn:
                            on_start_of_turn()

                    elif event == "EagerEndOfTurn":
                        print(f"⚡ EagerEndOfTurn detected")
                        if hasattr(message, 'transcript') and message.transcript:
                            transcript_buffer.append(message.transcript.strip())

                    elif event == "TurnResumed":
                        print(f"🔄 TurnResumed - user continued speaking")

                    elif event == "EndOfTurn":
                        if hasattr(message, 'transcript') and message.transcript:
                            final_transcript = message.transcript.strip()
                            if final_transcript:
                                transcript_buffer.append(final_transcript)

                        if transcript_buffer:
                            print(f"🎤 EndOfTurn! Processing complete utterance...")
                            full_transcript = " ".join(transcript_buffer)
                            transcript_buffer = []

                            print(f"📝 Complete transcript: '{full_transcript}'")
                            asyncio.create_task(on_end_of_turn(full_transcript))

            def on_error(error) -> None:
                print(f"❌ Deepgram Flux error: {error}")

            # Register event handlers
            connection.on(EventType.OPEN, lambda _: print("Flux connection opened"))
            connection.on(EventType.MESSAGE, on_message)
            connection.on(EventType.CLOSE, lambda _: print("Flux connection closed"))
            connection.on(EventType.ERROR, on_error)

            # Start listening task
            listen_task = asyncio.create_task(connection.start_listening())
            print("✅ Deepgram Flux v2 connection started")

            # Create audio stream from LiveKit track
            from livekit import rtc as lk_rtc
            audio_stream = lk_rtc.AudioStream(track)
            frame_count = 0
            bytes_sent = 0

            print(f"📊 Track info: kind={track.kind}, sid={track.sid}")

            try:
                async for event in audio_stream:
                    frame = event.frame

                    if frame_count == 0:
                        print(f"🔍 First frame: rate={frame.sample_rate}Hz, ch={frame.num_channels}")

                    try:
                        # Convert to 48kHz mono PCM16 for Deepgram Flux
                        if frame.sample_rate != 48000 or frame.num_channels != 1:
                            resampled = frame.remix_and_resample(48000, 1)
                        else:
                            resampled = frame

                        pcm_bytes = resampled.data.tobytes()

                        if len(pcm_bytes) > 0:
                            await connection._send(pcm_bytes)
                            frame_count += 1
                            bytes_sent += len(pcm_bytes)

                            if frame_count == 1:
                                print(f"✅ First frame sent to Deepgram Flux!")

                            if frame_count % 500 == 0:
                                print(f"📡 Frame {frame_count}: {bytes_sent / 1024:.1f} KB sent")

                    except Exception as e:
                        print(f"❌ Error processing frame {frame_count}: {e}")
                        if frame_count == 0:
                            break

            except Exception as e:
                print(f"❌ Audio stream error: {e}")
                import traceback
                traceback.print_exc()

            finally:
                # Process remaining transcripts
                if transcript_buffer:
                    remaining = " ".join(transcript_buffer)
                    print(f"🔄 Remaining transcript: '{remaining}'")
                    if remaining:
                        await on_end_of_turn(remaining)

                if listen_task and not listen_task.done():
                    listen_task.cancel()

                print(f"📊 Total: {frame_count} frames, {bytes_sent / 1024:.1f} KB")

    except Exception as e:
        print(f"❌ Deepgram connection error: {e}")
        import traceback
        traceback.print_exc()


# Import TurnMetadata for prosody-enhanced STT handler
from lib.tts_queue import TurnMetadata


async def create_stt_handler_with_prosody(
    track: rtc.Track,
    on_end_of_turn: Callable[[str, TurnMetadata], Awaitable[None]],
    on_start_of_turn: Optional[Callable[[], None]] = None,
    on_partial: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Create Deepgram Flux STT handler WITH prosody/timing metadata.

    This version tracks:
    - Turn duration (time from StartOfTurn to EndOfTurn)
    - EagerEndOfTurn events (user paused briefly)
    - TurnResumed events (user continued after pause)

    Use this for intelligent interruption handling - distinguishing
    "okay" (acknowledgment) from "okay so..." (new input).

    Args:
        track: LiveKit audio track to process
        on_end_of_turn: Async callback with (transcript, TurnMetadata)
        on_start_of_turn: Optional callback when user starts speaking
        on_partial: Optional callback for partial transcripts
    """
    transcript_buffer = []

    # Prosody tracking state
    turn_start_time: Optional[float] = None
    had_eager_eot = False
    had_turn_resumed = False

    try:
        dg_client = AsyncDeepgramClient(api_key=DEEPGRAM_API_KEY)

        async with dg_client.listen.v2.connect(
            model="flux-general-en",
            encoding="linear16",
            sample_rate="48000",
            eot_threshold="0.7",
            eot_timeout_ms="5000"
        ) as connection:

            def on_message(message) -> None:
                nonlocal transcript_buffer, turn_start_time, had_eager_eot, had_turn_resumed

                msg_type = getattr(message, "type", "Unknown")

                if msg_type == "Connected":
                    print(f"✅ Connected to Deepgram Flux v2 (with prosody tracking)")
                    return

                if msg_type == "TurnInfo":
                    event = getattr(message, "event", "Unknown")

                    if event == "Update":
                        if hasattr(message, 'transcript') and message.transcript:
                            transcript = message.transcript.strip()
                            if transcript and len(transcript) > 10 and on_partial:
                                on_partial(transcript)

                    elif event == "StartOfTurn":
                        print(f"🎤 StartOfTurn - user started speaking")
                        turn_start_time = time.time()
                        had_eager_eot = False
                        had_turn_resumed = False
                        if on_start_of_turn:
                            on_start_of_turn()

                    elif event == "EagerEndOfTurn":
                        print(f"⚡ EagerEndOfTurn detected")
                        had_eager_eot = True
                        if hasattr(message, 'transcript') and message.transcript:
                            transcript_buffer.append(message.transcript.strip())

                    elif event == "TurnResumed":
                        print(f"🔄 TurnResumed - user continued speaking")
                        had_turn_resumed = True

                    elif event == "EndOfTurn":
                        if hasattr(message, 'transcript') and message.transcript:
                            final_transcript = message.transcript.strip()
                            if final_transcript:
                                transcript_buffer.append(final_transcript)

                        if transcript_buffer:
                            print(f"🎤 EndOfTurn! Processing with prosody data...")
                            full_transcript = " ".join(transcript_buffer)
                            transcript_buffer = []

                            # Calculate turn duration
                            duration_ms = 0.0
                            if turn_start_time:
                                duration_ms = (time.time() - turn_start_time) * 1000

                            # Create metadata
                            metadata = TurnMetadata(
                                duration_ms=duration_ms,
                                had_eager_eot=had_eager_eot,
                                had_turn_resumed=had_turn_resumed,
                                word_count=len(full_transcript.split())
                            )

                            print(f"📝 Transcript: '{full_transcript}' | Duration: {duration_ms:.0f}ms | EagerEOT: {had_eager_eot} | Resumed: {had_turn_resumed}")

                            # Reset for next turn
                            turn_start_time = None
                            had_eager_eot = False
                            had_turn_resumed = False

                            asyncio.create_task(on_end_of_turn(full_transcript, metadata))

            def on_error(error) -> None:
                print(f"❌ Deepgram Flux error: {error}")

            connection.on(EventType.OPEN, lambda _: print("Flux connection opened (prosody)"))
            connection.on(EventType.MESSAGE, on_message)
            connection.on(EventType.CLOSE, lambda _: print("Flux connection closed"))
            connection.on(EventType.ERROR, on_error)

            listen_task = asyncio.create_task(connection.start_listening())
            print("✅ Deepgram Flux v2 (with prosody) started")

            from livekit import rtc as lk_rtc
            audio_stream = lk_rtc.AudioStream(track)
            frame_count = 0
            bytes_sent = 0

            print(f"📊 Track info: kind={track.kind}, sid={track.sid}")

            try:
                async for event in audio_stream:
                    frame = event.frame

                    if frame_count == 0:
                        print(f"🔍 First frame: rate={frame.sample_rate}Hz, ch={frame.num_channels}")

                    try:
                        if frame.sample_rate != 48000 or frame.num_channels != 1:
                            resampled = frame.remix_and_resample(48000, 1)
                        else:
                            resampled = frame

                        pcm_bytes = resampled.data.tobytes()

                        if len(pcm_bytes) > 0:
                            await connection._send(pcm_bytes)
                            frame_count += 1
                            bytes_sent += len(pcm_bytes)

                            if frame_count == 1:
                                print(f"✅ First frame sent to Deepgram Flux!")

                            if frame_count % 500 == 0:
                                print(f"📡 Frame {frame_count}: {bytes_sent / 1024:.1f} KB sent")

                    except Exception as e:
                        print(f"❌ Error processing frame {frame_count}: {e}")
                        if frame_count == 0:
                            break

            except Exception as e:
                print(f"❌ Audio stream error: {e}")
                import traceback
                traceback.print_exc()

            finally:
                if transcript_buffer:
                    remaining = " ".join(transcript_buffer)
                    print(f"🔄 Remaining transcript: '{remaining}'")
                    if remaining and turn_start_time:
                        duration_ms = (time.time() - turn_start_time) * 1000
                        metadata = TurnMetadata(
                            duration_ms=duration_ms,
                            had_eager_eot=had_eager_eot,
                            had_turn_resumed=had_turn_resumed,
                            word_count=len(remaining.split())
                        )
                        await on_end_of_turn(remaining, metadata)

                if listen_task and not listen_task.done():
                    listen_task.cancel()

                print(f"📊 Total: {frame_count} frames, {bytes_sent / 1024:.1f} KB")

    except Exception as e:
        print(f"❌ Deepgram connection error: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# DATA CHANNEL UTILITIES
# ============================================================

async def send_data_message(
    room: rtc.Room,
    message_type: str,
    text: str,
    options: Optional[list[str]] = None
) -> None:
    """Send structured data message to frontend via LiveKit data channel."""
    import json

    data_payload = {
        "type": message_type,
        "text": text,
    }
    if options is not None:
        data_payload["options"] = options

    await room.local_participant.publish_data(
        json.dumps(data_payload).encode(),
        reliable=True
    )
    print(f"📤 Sent {message_type} data to frontend via data channel")
