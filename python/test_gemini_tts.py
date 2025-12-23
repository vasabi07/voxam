"""
Gemini 2.5 Flash TTS Streaming Test (Official SDK Approach)
============================================================
Uses the official Google genai SDK pattern for TTS.
"""

import os
import time
import struct
import mimetypes
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ GOOGLE_API_KEY or GEMINI_API_KEY not found in .env")
    exit(1)


def parse_audio_mime_type(mime_type: str) -> dict:
    """Parse bits per sample and rate from audio MIME type."""
    bits_per_sample = 16
    rate = 24000
    
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
    
    return {"bits_per_sample": bits_per_sample, "rate": rate}


def test_tts_ttfb(text: str, voice: str = "Puck"):
    """
    Test TTFB using sync streaming API.
    """
    print(f"\n🎤 Testing TTS with voice '{voice}'")
    print(f"   Text: \"{text[:60]}...\"" if len(text) > 60 else f"   Text: \"{text}\"")
    print(f"   Length: {len(text)} chars")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        ),
    ]
    
    config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice
                )
            )
        ),
    )
    
    start_time = time.time()
    first_chunk_time = None
    chunk_count = 0
    total_bytes = 0
    
    try:
        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash-preview-tts",
            contents=contents,
            config=config,
        ):
            if first_chunk_time is None:
                first_chunk_time = time.time()
                ttfb = first_chunk_time - start_time
                print(f"   ⚡ TTFB: {ttfb:.3f}s")
            
            if (chunk.candidates is None or 
                chunk.candidates[0].content is None or
                chunk.candidates[0].content.parts is None):
                continue
            
            part = chunk.candidates[0].content.parts[0]
            if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                chunk_count += 1
                total_bytes += len(part.inline_data.data)
        
        total_time = time.time() - start_time
        
        # Estimate audio duration (24kHz, 16-bit = 2 bytes/sample)
        audio_duration = total_bytes / (24000 * 2)
        
        print(f"   📊 Total time: {total_time:.3f}s")
        print(f"   📊 Chunks: {chunk_count}")
        print(f"   📊 Audio bytes: {total_bytes:,}")
        print(f"   📊 Est. audio duration: {audio_duration:.2f}s")
        
        return ttfb
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_tts_save_audio(text: str, voice: str = "Puck", filename: str = "output"):
    """
    Generate TTS and save to WAV file.
    """
    print(f"\n🎤 Generating audio to file...")
    print(f"   Text: \"{text[:60]}...\"" if len(text) > 60 else f"   Text: \"{text}\"")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        ),
    ]
    
    config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice
                )
            )
        ),
    )
    
    # Collect all audio chunks
    all_audio_data = bytearray()
    sample_rate = 24000
    bits_per_sample = 16
    
    start_time = time.time()
    
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-flash-preview-tts",
        contents=contents,
        config=config,
    ):
        if (chunk.candidates is None or 
            chunk.candidates[0].content is None or
            chunk.candidates[0].content.parts is None):
            continue
        
        part = chunk.candidates[0].content.parts[0]
        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
            inline_data = part.inline_data
            all_audio_data.extend(inline_data.data)
            
            # Get sample rate from mime type
            if inline_data.mime_type:
                params = parse_audio_mime_type(inline_data.mime_type)
                sample_rate = params["rate"]
                bits_per_sample = params["bits_per_sample"]
    
    total_time = time.time() - start_time
    
    if all_audio_data:
        # Create WAV header
        num_channels = 1
        bytes_per_sample = bits_per_sample // 8
        byte_rate = sample_rate * num_channels * bytes_per_sample
        block_align = num_channels * bytes_per_sample
        data_size = len(all_audio_data)
        
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,
            1,  # PCM
            num_channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
            b"data",
            data_size
        )
        
        wav_filename = f"{filename}.wav"
        with open(wav_filename, "wb") as f:
            f.write(header + bytes(all_audio_data))
        
        audio_duration = data_size / (sample_rate * bytes_per_sample)
        print(f"   ✅ Saved to: {wav_filename}")
        print(f"   📊 Duration: {audio_duration:.2f}s")
        print(f"   📊 Generated in: {total_time:.2f}s")
        
        return wav_filename
    else:
        print("   ❌ No audio data received")
        return None


# Test sentences
TEST_SENTENCES = [
    "Welcome to your Physics examination.",
    "Here's my question for you... If I double the voltage, what happens to the current?",
    "Newton's second law states that the force acting on an object equals the mass times acceleration.",
]

VOICES = ["Puck", "Kore", "Charon", "Fenrir", "Aoede"]


if __name__ == "__main__":
    print("=" * 60)
    print("🎙️ Gemini 2.5 Flash TTS Test (Official SDK)")
    print("=" * 60)
    
    # Test 1: TTFB for different text lengths
    print("\n📝 Test 1: TTFB by Text Length")
    print("-" * 40)
    for sentence in TEST_SENTENCES:
        test_tts_ttfb(sentence)
        time.sleep(0.5)
    
    # Test 2: TTFB for different voices
    print("\n📝 Test 2: TTFB by Voice")
    print("-" * 40)
    test_text = "Welcome to your Physics examination."
    for voice in VOICES[:3]:  # Test first 3 voices
        test_tts_ttfb(test_text, voice)
        time.sleep(0.5)
    
    # Test 3: Save audio file
    print("\n📝 Test 3: Save Audio File")
    print("-" * 40)
    test_tts_save_audio(
        "Welcome to your Physics examination. I'm Professor Venkat, and I'll be your examiner today.",
        voice="Puck",
        filename="gemini_tts_test"
    )
    
    print("\n✅ All tests complete!")
