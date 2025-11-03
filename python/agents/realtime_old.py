import asyncio
import os
import time
import re
from livekit import rtc
from dotenv import load_dotenv
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets import ListenV2SocketClientResponse
from google.cloud import texttospeech
from agents.exam_agent import graph as exam_agent_graph, State as ExamState
from langchain_core.messages import HumanMessage
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv(dotenv_path=".env.local", override=False)

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL")

# API keys for STT/TTS
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

if not LIVEKIT_URL:
    raise ValueError("Missing LIVEKIT_URL environment variable. Please check your .env.local file.")

if not DEEPGRAM_API_KEY:
    raise ValueError("Missing DEEPGRAM_API_KEY. Please check your .env.local file.")

# Initialize Google Cloud TTS client
tts_client = texttospeech.TextToSpeechClient()


async def generate_and_stream_tts(text: str, audio_source: rtc.AudioSource):
    """
    Generate TTS audio using Google Cloud TTS and stream to LiveKit
    LiveKit handles all audio format conversions automatically
    """
    try:
        start_time = time.time()
        print(f"🎵 Generating TTS for: '{text[:80]}...'")
        
        # Configure synthesis - use 48kHz to match LiveKit's default
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=48000,  # Match LiveKit's sample rate
            speaking_rate=1.0,
        )
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            name="en-US-Chirp3-HD-Achird",
            language_code="en-US",
        )
        
        # Synthesize speech
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        audio_data = response.audio_content
        generation_time = time.time() - start_time
        
        # Create a single AudioFrame with all the audio data
        # LiveKit handles chunking and streaming internally
        frame = rtc.AudioFrame(
            data=audio_data,
            sample_rate=48000,
            num_channels=1,
            samples_per_channel=len(audio_data) // 2  # 2 bytes per sample (int16)
        )
        
        # Capture the frame - LiveKit handles the rest
        await audio_source.capture_frame(frame)
        
        duration_seconds = len(audio_data) / (48000 * 2)
        print(f"✅ TTS generated: {duration_seconds:.2f}s (in {generation_time:.2f}s)")
        return True
        
    except Exception as e:
        print(f"❌ TTS generation error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def start_exam_agent(room_name: str, token: str, qp_id: str, thread_id: str, mode: str = "exam"):
    """
    Agent that joins a LiveKit room, listens to student audio via Deepgram STT,
    processes with LangGraph exam agent, and responds with Google TTS
    
    Args:
        room_name: LiveKit room name
        token: LiveKit access token
        qp_id: Question paper ID
        thread_id: Thread ID for conversation persistence
        mode: "exam" or "learn"
    """
    
    # Create and connect to room
    room = rtc.Room()
    
    def on_disconnected(reason: str):
        print(f"[Agent] Disconnected from room: {reason}")
    
    room.on("disconnected", on_disconnected)
    
    await room.connect(LIVEKIT_URL, token)
    print(f"🤖 Agent joined room: {room_name}")
    print(f"📝 QP ID: {qp_id}, Thread ID: {thread_id}")
    print(f"🎯 Mode: {mode.upper()}")
    
    # Create audio source and track for TTS output
    audio_source = rtc.AudioSource(48000, 1)  # 48kHz, mono
    audio_track = rtc.LocalAudioTrack.create_audio_track("agent_voice", audio_source)
    await room.local_participant.publish_track(audio_track)
    print("🔊 Published agent audio track for TTS output")
    
    # Deepgram connection state
    dg_connection = None
    transcript_buffer = []
    connection_active = False
    
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
            
            # Create exam state
            exam_state = ExamState(
                messages=[HumanMessage(content=full_transcript)],
                thread_id=thread_id,
                qp_id=qp_id,
                current_index=0,
                mode=mode
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
            
            # Split into sentences for progressive streaming
            sentence_pattern = re.compile(r'([^.!?]+[.!?]+)')
            sentences = sentence_pattern.findall(ai_response)
            
            # Stream TTS for each sentence
            print(f"🎙️ Streaming TTS for {len(sentences)} sentences...")
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    await generate_and_stream_tts(sentence, audio_source)
            
            # Handle remaining text without punctuation
            last_text = sentence_pattern.sub('', ai_response).strip()
            if last_text:
                await generate_and_stream_tts(last_text, audio_source)
            
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
        nonlocal dg_connection, transcript_buffer, connection_active
        
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return
        
        print(f"🎧 Received audio track from {participant.identity}")
        
        # Initialize Deepgram connection using async websocket
        dg_client = DeepgramClient(DEEPGRAM_API_KEY)
        dg_connection = dg_client.listen.asyncwebsocket.v("1")
        
        # Configure Deepgram for LiveKit audio (48kHz, mono, 16-bit PCM)
        options = LiveOptions(
            model="nova-2",  # Use nova-2 for better performance
            language="en-US",
            encoding="linear16",
            sample_rate=48000,
            channels=1,
            vad_events=True,
            endpointing=400,  # 400ms silence for utterance end
            interim_results=True,
            smart_format=True,
            filler_words=False,
        )
        
        # Get main event loop for scheduling coroutines
        main_loop = asyncio.get_running_loop()
        
        # Message handler for Deepgram responses
        def on_message(self, result, **kwargs):
            nonlocal transcript_buffer
            
            sentence = result.channel.alternatives[0].transcript
            
            if sentence.strip() and result.is_final:
                print(f"✅ Final: {sentence}")
                transcript_buffer.append(sentence.strip())
            elif sentence.strip() and not result.is_final:
                # Only log longer partial transcripts
                if len(sentence.strip()) > 10:
                    print(f"⏳ Partial: {sentence}")
            
            # Process complete utterance when speech_final is detected
            if hasattr(result, 'speech_final') and result.speech_final and transcript_buffer:
                print(f"🎤 Speech final! Processing {len(transcript_buffer)} segments...")
                full_transcript = " ".join(transcript_buffer)
                transcript_buffer = []
                
                # Schedule processing in main event loop
                async def process_answer():
                    try:
                        await process_complete_transcript(full_transcript)
                    except Exception as e:
                        print(f"❌ Error processing: {e}")
                        import traceback
                        traceback.print_exc()
                
                asyncio.run_coroutine_threadsafe(process_answer(), main_loop)
        
        def on_utterance_end(self, utterance_end, **kwargs):
            nonlocal transcript_buffer
            print(f"🎤 Utterance end! Buffer: {len(transcript_buffer)} items")
            
            if transcript_buffer:
                full_transcript = " ".join(transcript_buffer)
                transcript_buffer = []
                
                async def process_answer():
                    try:
                        await process_complete_transcript(full_transcript)
                    except Exception as e:
                        print(f"❌ Error: {e}")
                        import traceback
                        traceback.print_exc()
                
                asyncio.run_coroutine_threadsafe(process_answer(), main_loop)
        
        # Error handler
        def on_error(self, error, **kwargs):
            nonlocal connection_active
            print(f"❌ Deepgram error: {error}")
            connection_active = False
        
        # Register event handlers
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)
        
        # Start Deepgram connection
        if not await dg_connection.start(options):
            print("❌ Failed to start Deepgram")
            return
        
        print("✅ Deepgram connection started")
        connection_active = True
                
                # Create audio stream to receive frames from LiveKit
                from livekit import rtc as lk_rtc
                audio_stream = lk_rtc.AudioStream(track)
                frame_count = 0
                bytes_sent = 0
                
                print(f"📊 Track info: kind={track.kind}, sid={track.sid}")
                
                try:
                    async for event in audio_stream:
                        if not connection_active:
                            print("❌ Deepgram connection lost")
                            break
                        
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
                                # Send to Deepgram Flux using _send() method
                                await dg_connection._send(pcm_bytes)
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
                                connection_active = False
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
                    
                    # Cancel listening task
                    if listen_task and not listen_task.done():
                        listen_task.cancel()
                    
                    print(f"� Total frames processed: {frame_count}, Total bytes: {bytes_sent / 1024:.1f} KB")
        
        except Exception as e:
            print(f"❌ Deepgram connection error: {e}")
            import traceback
            traceback.print_exc()
    
    # Wait for room to close
    print("✅ Agent ready and listening...")
    await asyncio.Future()  # Run forever until disconnected


async def main(room_name: str, token: str, qp_id: str, thread_id: str, mode: str = "exam"):
    """
    Main entry point - called from API endpoint
    In production, this is spawned as a background task from FastAPI
    
    Example usage from api.py:
        asyncio.create_task(
            main(room_name, token, qp_id, thread_id, mode)
        )
    """
    try:
        print(f"\n{'='*60}")
        print(f"🚀 Starting Exam Agent")
        print(f"Room: {room_name}")
        print(f"QP ID: {qp_id}")
        print(f"Thread ID: {thread_id}")
        print(f"Mode: {mode.upper()}")
        print(f"{'='*60}\n")
        
        # Start the exam agent
        await start_exam_agent(room_name, token, qp_id, thread_id, mode)
        
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
        print("Usage: python realtime.py <room_name> <token> <qp_id> <thread_id> [mode]")
