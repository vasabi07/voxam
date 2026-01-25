import asyncio
import os
import time
import re
from livekit import rtc
from dotenv import load_dotenv
from deepgram import DeepgramClient, AsyncDeepgramClient
from deepgram.core.events import EventType  # SDK v5 correct import
from google.cloud import texttospeech
from agents.exam_agent import graph as exam_agent_graph, State as ExamState, preload_first_question
from langchain_core.messages import HumanMessage
from concurrent.futures import ThreadPoolExecutor

# Load environment variables (load .env first, then .env.local can override)
load_dotenv(dotenv_path=".env", override=False)
load_dotenv(dotenv_path=".env.local", override=True)

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL")

# API keys for STT/TTS
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

if not LIVEKIT_URL:
    raise ValueError("Missing LIVEKIT_URL environment variable. Please check your .env.local file.")

if not DEEPGRAM_API_KEY:
    raise ValueError("Missing DEEPGRAM_API_KEY. Please check your .env.local file.")

# Initialize Google Cloud TTS client (for India region)
tts_client = texttospeech.TextToSpeechClient()

# Initialize Deepgram client (for global/TTS) - SDK v5 requires keyword arg
dg_tts_client = AsyncDeepgramClient(api_key=DEEPGRAM_API_KEY)


async def generate_and_stream_tts(text: str, audio_source: rtc.AudioSource, region: str = "india"):
    """
    Generate TTS audio and stream to LiveKit.
    Uses Google Neural2 for India, Deepgram Aura for global users.
    
    Args:
        text: Text to convert to speech
        audio_source: LiveKit audio source to stream to
        region: "india" for Google Neural2, "global" for Deepgram Aura
    """
    try:
        start_time = time.time()
        print(f"🎵 Generating TTS [{region.upper()}] for: '{text[:80]}...'")
        
        if region == "india":
            # Google Cloud TTS - Indian English voice
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
            audio_data = response.audio_content
            sample_rate = 48000
            
        else:
            # Deepgram Aura - Global English voice (faster, cheaper for intl)
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
            audio_data = b"".join(audio_chunks)
            sample_rate = 48000
        
        generation_time = time.time() - start_time
        
        # Create AudioFrame and stream to LiveKit
        frame = rtc.AudioFrame(
            data=audio_data,
            sample_rate=sample_rate,
            num_channels=1,
            samples_per_channel=len(audio_data) // 2
        )
        
        await audio_source.capture_frame(frame)
        
        duration_seconds = len(audio_data) / (sample_rate * 2)
        print(f"✅ TTS generated: {duration_seconds:.2f}s (in {generation_time:.2f}s)")
        return True
        
    except Exception as e:
        print(f"❌ TTS generation error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def start_exam_agent(room_name: str, token: str, qp_id: str, thread_id: str, mode: str = "exam", region: str = "india"):
    """
    Agent that joins a LiveKit room, listens to student audio via Deepgram Flux STT,
    processes with LangGraph exam agent, and responds with TTS
    
    Args:
        room_name: LiveKit room name
        token: LiveKit access token
        qp_id: Question paper ID
        thread_id: Thread ID for conversation persistence
        mode: "exam" or "learn"
        region: "india" or "global" for geo-based TTS voice selection
    """
    
    # Create and connect to room
    room = rtc.Room()
    
    def on_disconnected(reason: str):
        print(f"[Agent] Disconnected from room: {reason}")
    
    room.on("disconnected", on_disconnected)
    
    await room.connect(LIVEKIT_URL, token)
    print(f"🤖 Agent joined room: {room_name}")
    print(f"📝 QP ID: {qp_id}, Thread ID: {thread_id}")
    print(f"🎯 Mode: {mode.upper()}, Region: {region.upper()}")
    
    # Create audio source and track for TTS output
    audio_source = rtc.AudioSource(48000, 1)  # 48kHz, mono
    audio_track = rtc.LocalAudioTrack.create_audio_track("agent_voice", audio_source)
    await room.local_participant.publish_track(audio_track)
    print("🔊 Published agent audio track for TTS output")
    
    # Transcript buffer for accumulating final results
    transcript_buffer = []
    
    # Track if this is the first invocation (for preloading questions)
    first_invocation = True
    cached_question = None
    cached_total = None
    async def process_complete_transcript(full_transcript: str):
        """Process complete user utterance with the exam agent and generate TTS response"""
        try:
            if not full_transcript.strip():
                print("⚠️ Empty transcript, skipping")
                return
            
            print(f"\n{'='*60}")
            print(f"🤖 Processing transcript with exam agent...")
            print(f"📝 Student said: {full_transcript}")
            print(f"{'='*60}\n")
            
            # Create exam state - first time preload questions, otherwise just new message
            nonlocal first_invocation, cached_question, cached_total
            
            if first_invocation:
                # Preload first question from Redis
                cached_question, cached_total = preload_first_question(qp_id)
                if cached_question:
                    print(f"📚 Preloaded first question ({cached_total} total)")
                else:
                    print(f"⚠️ Failed to preload questions for QP: {qp_id}")
                first_invocation = False
            
            exam_state = ExamState(
                messages=[HumanMessage(content=full_transcript)],
                thread_id=thread_id,
                qp_id=qp_id,
                current_index=0,
                mode=mode,
                current_question=cached_question,
                total_questions=cached_total,
                exam_started=False if cached_question else True,  # Will greet first, then show questions
            )
            
            # Configuration for checkpointer
            config = {"configurable": {"thread_id": thread_id}}
            
            # Run agent in thread pool (sync invoke)
            def run_agent():
                return exam_agent_graph.invoke(exam_state, config=config)
            
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
            print(f"✅ AGENT RESPONSE:")
            print(f"{ai_response}")
            print(f"{'='*60}\n")
            
            # === Extract response metadata for data channel ===
            response_type = result.get("response_type", "follow_up")
            response_options = result.get("response_options")
            
            print(f"📊 Response type: {response_type}")
            
            # Send data channel message for questions (UI display)
            if response_type == "question":
                import json
                data_payload = {
                    "type": "question",
                    "text": ai_response,
                    "options": response_options  # None for long_answer, list for MCQ
                }
                await room.local_participant.publish_data(
                    json.dumps(data_payload).encode(),
                    reliable=True
                )
                print(f"📤 Sent question data to frontend via data channel")
            
            # Split into sentences for progressive streaming
            sentence_pattern = re.compile(r'([^.!?]+[.!?]+)')
            sentences = sentence_pattern.findall(ai_response)
            
            # Stream TTS for each sentence (image description is in LLM context, not TTS)
            print(f"🎙️ Streaming TTS for {len(sentences)} sentences...")
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    await generate_and_stream_tts(sentence, audio_source, region)
            
            # Handle remaining text without punctuation
            last_text = sentence_pattern.sub('', ai_response).strip()
            if last_text:
                await generate_and_stream_tts(last_text, audio_source, region)
            
            print("✅ Agent response complete")
            
        except Exception as e:
            print(f"❌ ERROR processing transcript: {e}")
            import traceback
            traceback.print_exc()
    
    # Subscribe to user audio tracks
    @room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant
    ):
        # Create async task to handle the track
        asyncio.create_task(handle_track_subscribed(track, publication, participant))
    
    async def handle_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant
    ):
        nonlocal transcript_buffer
        
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return
        
        print(f"🎧 Received audio track from {participant.identity}")
        
        try:
            # Initialize Deepgram Flux client - SDK v5 requires keyword arg
            dg_client = AsyncDeepgramClient(api_key=DEEPGRAM_API_KEY)
            
            # Connect to Deepgram Flux v2 with async context manager
            # Using flux-general-en model with 48kHz linear16 audio
            async with dg_client.listen.v2.connect(
                model="flux-general-en",
                encoding="linear16",
                sample_rate="48000",
                eot_threshold="0.7",  # Default: 0.7 for reliable turn detection
                # eager_eot_threshold="0.5",  # Uncomment for early LLM response optimization
                eot_timeout_ms="5000"  # 5s max silence before forcing end-of-turn
            ) as connection:
                
                # Message handler for Deepgram Flux responses
                def on_message(message) -> None:  # SDK v5 uses dynamic types
                    nonlocal transcript_buffer
                    
                    # Check message type
                    msg_type = getattr(message, "type", "Unknown")
                    
                    if msg_type == "Connected":
                        print(f"✅ Connected to Deepgram Flux v2")
                        return
                    
                    # Flux sends TurnInfo messages with event field
                    if msg_type == "TurnInfo":
                        event = getattr(message, "event", "Unknown")
                        
                        # Handle transcription results in Update events
                        if event == "Update":
                            if hasattr(message, 'transcript') and message.transcript:
                                transcript = message.transcript.strip()
                                
                                if transcript and len(transcript) > 10:
                                    # Only log longer partial transcripts
                                    print(f"⏳ Partial: {transcript}")
                        
                        # Handle StartOfTurn - user started speaking
                        elif event == "StartOfTurn":
                            print(f"🎤 StartOfTurn - user started speaking")
                            # Could interrupt agent if it's speaking
                        
                        # Handle EagerEndOfTurn - medium confidence user finished
                        elif event == "EagerEndOfTurn":
                            print(f"⚡ EagerEndOfTurn detected - user likely finished speaking")
                            # Could start preparing LLM response speculatively
                            if hasattr(message, 'transcript') and message.transcript:
                                transcript_buffer.append(message.transcript.strip())
                        
                        # Handle TurnResumed - user kept talking after EagerEndOfTurn
                        elif event == "TurnResumed":
                            print(f"🔄 TurnResumed - user continued speaking")
                            # Should cancel any speculative LLM response
                        
                        # Handle EndOfTurn - high confidence user finished (THIS IS THE KEY EVENT!)
                        elif event == "EndOfTurn":
                            # Get the final transcript from this message
                            if hasattr(message, 'transcript') and message.transcript:
                                final_transcript = message.transcript.strip()
                                if final_transcript:
                                    transcript_buffer.append(final_transcript)
                            
                            if transcript_buffer:
                                print(f"🎤 EndOfTurn! Processing complete utterance...")
                                full_transcript = " ".join(transcript_buffer)
                                transcript_buffer = []
                                
                                print(f"📝 Complete transcript: '{full_transcript}'")
                                
                                # Process the complete utterance
                                asyncio.create_task(process_complete_transcript(full_transcript))
                
                def on_error(error) -> None:
                    print(f"❌ Deepgram Flux error: {error}")
                
                # Register event handlers
                connection.on(EventType.OPEN, lambda _: print("Flux connection opened"))
                connection.on(EventType.MESSAGE, on_message)
                connection.on(EventType.CLOSE, lambda _: print("Flux connection closed"))
                connection.on(EventType.ERROR, on_error)
                
                # Start listening task in background
                listen_task = asyncio.create_task(connection.start_listening())
                
                print("✅ Deepgram Flux v2 connection started")
                
                # Create audio stream to receive frames from LiveKit
                from livekit import rtc as lk_rtc
                audio_stream = lk_rtc.AudioStream(track)
                frame_count = 0
                bytes_sent = 0
                
                print(f"📊 Track info: kind={track.kind}, sid={track.sid}")
                
                try:
                    async for event in audio_stream:
                        frame = event.frame
                        
                        # Debug first frame
                        if frame_count == 0:
                            print(f"🔍 First frame received!")
                            print(f"   - Sample rate: {frame.sample_rate} Hz")
                            print(f"   - Channels: {frame.num_channels}")
                            print(f"   - Samples per channel: {frame.samples_per_channel}")
                        
                        try:
                            # Convert to 48kHz mono PCM16 for Deepgram Flux
                            if frame.sample_rate != 48000 or frame.num_channels != 1:
                                resampled = frame.remix_and_resample(48000, 1)
                            else:
                                resampled = frame
                            
                            # Convert frame to bytes
                            pcm_bytes = resampled.data.tobytes()
                            
                            if len(pcm_bytes) > 0:
                                # Send to Deepgram Flux
                                # Flux recommends ~80ms chunks for optimal performance
                                await connection._send(pcm_bytes)
                                frame_count += 1
                                bytes_sent += len(pcm_bytes)
                                
                                if frame_count == 1:
                                    print(f"✅ First frame sent to Deepgram Flux! Size: {len(pcm_bytes)} bytes")
                                
                                if frame_count % 500 == 0:
                                    print(f"📡 Frame {frame_count}: {bytes_sent / 1024:.1f} KB sent")
                            else:
                                if frame_count < 5:
                                    print(f"⚠️ Empty frame {frame_count}")
                                    
                        except Exception as e:
                            print(f"❌ Error processing frame {frame_count}: {e}")
                            import traceback
                            traceback.print_exc()
                            if frame_count == 0:  # If first frame fails, bail out
                                break
                
                except Exception as e:
                    print(f"❌ Audio stream error: {e}")
                    import traceback
                    traceback.print_exc()
                
                finally:
                    # Show remaining transcripts
                    if transcript_buffer:
                        remaining = " ".join(transcript_buffer)
                        print(f"🔄 Remaining transcript: '{remaining}'")
                        # Process any remaining transcript
                        if remaining:
                            await process_complete_transcript(remaining)
                    
                    # Cancel listening task
                    if listen_task and not listen_task.done():
                        listen_task.cancel()
                    
                    print(f"📊 Total frames processed: {frame_count}, Total bytes: {bytes_sent / 1024:.1f} KB")
        
        except Exception as e:
            print(f"❌ Deepgram connection error: {e}")
            import traceback
            traceback.print_exc()
    
    # Wait for room to close
    print("✅ Agent ready and listening...")
    await asyncio.Future()  # Run forever until disconnected


async def main(room_name: str, token: str, qp_id: str, thread_id: str, mode: str = "exam", region: str = "india"):
    """
    Main entry point - called from API endpoint
    In production, this is spawned as a background task from FastAPI
    
    Example usage from api.py:
        asyncio.create_task(
            main(room_name, token, qp_id, thread_id, mode, region)
        )
    """
    try:
        print(f"\n{'='*60}")
        print(f"🚀 Starting Exam Agent with Deepgram Flux v2")
        print(f"Room: {room_name}")
        print(f"QP ID: {qp_id}")
        print(f"Thread ID: {thread_id}")
        print(f"Mode: {mode.upper()}")
        print(f"Region: {region.upper()}")
        print(f"{'='*60}\n")
        
        # Start the exam agent
        await start_exam_agent(room_name, token, qp_id, thread_id, mode, region)
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # For local testing only
    print("⚠️  This module is meant to be called from api.py")
    print("For testing, provide: room_name, token, qp_id, thread_id, mode")
    import sys
    if len(sys.argv) >= 5:
        asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "exam"))
    else:
        print("Usage: python realtime_flux.py <room_name> <token> <qp_id> <thread_id> [mode]")
