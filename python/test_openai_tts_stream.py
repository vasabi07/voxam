"""
OpenAI TTS-1 Streaming Latency Test
====================================
Tests Time to First Byte (TTFB) and total generation time
for OpenAI's tts-1 model with streaming.
"""
import os
import time
import asyncio
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Test texts of varying lengths
TEST_TEXTS = {
    "short": "Welcome to your Chemistry exam.",
    "medium": "Welcome to your Chemistry examination. This test consists of 10 questions, and you have 15 minutes to complete it. Are you ready to begin?",
    "long": "Welcome to your Chemistry examination. This test consists of 10 questions, and you have 15 minutes to complete it. I'll read each question clearly. Please say 'next' when you're ready to move on. Let's begin with Question 1: What is the chemical formula of water? Take your time to think about this.",
    "professor": "That's an excellent observation! You've correctly identified the relationship between atoms and molecules. The key insight here is that water molecules consist of two hydrogen atoms bonded to one oxygen atom. Well done!",
}

VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


def test_streaming(text: str, label: str, voice: str = "onyx"):
    """Test streaming TTS request"""
    print(f"\n📝 Testing STREAMING ({label}): {len(text)} chars, voice: {voice}")
    
    start = time.time()
    first_chunk_time = None
    total_bytes = 0
    chunks = 0
    
    try:
        # Streaming response
        with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="pcm",  # Raw PCM for lowest latency
        ) as response:
            for chunk in response.iter_bytes(chunk_size=1024):
                if first_chunk_time is None:
                    first_chunk_time = time.time() - start
                    print(f"   🚀 TTFB (Time to First Byte): {first_chunk_time:.3f}s")
                
                total_bytes += len(chunk)
                chunks += 1
        
        elapsed = time.time() - start
        
        # PCM at 24kHz, 16-bit mono = 48000 bytes/sec
        duration_seconds = total_bytes / 48000
        
        print(f"   ⏱️  Total time: {elapsed:.3f}s")
        print(f"   🔊 Audio duration: ~{duration_seconds:.2f}s")
        print(f"   📦 Chunks received: {chunks}")
        print(f"   📊 Speed ratio: {duration_seconds/elapsed:.2f}x realtime")
        
        return first_chunk_time, elapsed
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None, None


def main():
    print("=" * 60)
    print("🎙️ OPENAI TTS-1 STREAMING LATENCY TEST")
    print("=" * 60)
    
    results = {}
    
    # Test with default voice (onyx - good for professor)
    for label, text in TEST_TEXTS.items():
        print(f"\n{'='*40}")
        print(f"Testing: {label.upper()}")
        print(f"{'='*40}")
        
        ttft, total = test_streaming(text, label, voice="onyx")
        results[label] = {"ttft": ttft, "total": total, "chars": len(text)}
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY (voice: onyx)")
    print("=" * 60)
    print(f"{'Label':<12} {'Chars':<8} {'TTFB':<12} {'Total':<12}")
    print("-" * 50)
    
    for label, data in results.items():
        ttft_str = f"{data['ttft']:.3f}s" if data['ttft'] else "N/A"
        total_str = f"{data['total']:.3f}s" if data['total'] else "N/A"
        print(f"{label:<12} {data['chars']:<8} {ttft_str:<12} {total_str:<12}")
    
    # Quick voice comparison on short text
    print("\n" + "=" * 60)
    print("🎭 VOICE COMPARISON (short text)")
    print("=" * 60)
    
    for voice in VOICES:
        ttft, _ = test_streaming(TEST_TEXTS["short"], "short", voice=voice)
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
