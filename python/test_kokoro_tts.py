"""
Kokoro TTS Latency Test Script

Tests:
1. Time to first byte (TTFT)
2. Total generation time
3. Streaming vs non-streaming comparison
"""
import httpx
import time
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
KOKORO_ENDPOINT = "https://api.deepinfra.com/v1/inference/hexgrad/Kokoro-82M"

if not DEEPINFRA_API_KEY:
    raise ValueError("Missing DEEPINFRA_API_KEY in .env")

# Test sentences of varying lengths
TEST_TEXTS = {
    "short": "Welcome to your Chemistry exam.",
    "medium": "Welcome to your Chemistry examination. This test consists of 10 questions, and you have 15 minutes to complete it.",
    "long": "Welcome to your Chemistry examination. This test consists of 10 questions, and you have 15 minutes to complete it. I'll read each question clearly. Please say 'next' when you're ready to move on. Let's begin with Question 1: What is the chemical formula of water?",
}


async def test_non_streaming(text: str, label: str):
    """Test non-streaming TTS request"""
    print(f"\n📝 Testing NON-STREAMING ({label}): {len(text)} chars")
    
    start = time.time()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            KOKORO_ENDPOINT,
            headers={
                "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "voice": "af_heart",
                "output_format": "wav",
            },
            timeout=60.0,
        )
        response.raise_for_status()
        audio_data = response.content
    
    elapsed = time.time() - start
    audio_duration = len(audio_data) / (48000 * 2)  # Assuming 48kHz 16-bit mono
    
    print(f"   ⏱️  Total time: {elapsed:.3f}s")
    print(f"   🔊 Audio size: {len(audio_data)} bytes (~{audio_duration:.2f}s of audio)")
    print(f"   📊 Ratio: {elapsed/audio_duration:.2f}x realtime")
    
    return elapsed


async def test_streaming(text: str, label: str):
    """Test streaming TTS request"""
    print(f"\n📝 Testing STREAMING ({label}): {len(text)} chars")
    
    start = time.time()
    first_chunk_time = None
    total_bytes = 0
    chunks = 0
    
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            KOKORO_ENDPOINT,
            headers={
                "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "voice": "af_heart",
                "output_format": "wav",
                "stream": True,
            },
            timeout=60.0,
        ) as response:
            response.raise_for_status()
            
            async for chunk in response.aiter_bytes():
                if first_chunk_time is None:
                    first_chunk_time = time.time() - start
                    print(f"   🚀 TTFT (Time to First Token): {first_chunk_time:.3f}s")
                
                total_bytes += len(chunk)
                chunks += 1
    
    elapsed = time.time() - start
    audio_duration = total_bytes / (48000 * 2)
    
    print(f"   ⏱️  Total time: {elapsed:.3f}s")
    print(f"   🔊 Audio size: {total_bytes} bytes (~{audio_duration:.2f}s of audio)")
    print(f"   📦 Chunks received: {chunks}")
    print(f"   📊 Ratio: {elapsed/audio_duration:.2f}x realtime")
    
    return first_chunk_time, elapsed


async def main():
    print("=" * 60)
    print("🎤 KOKORO TTS LATENCY TEST")
    print("=" * 60)
    
    results = {}
    
    for label, text in TEST_TEXTS.items():
        print(f"\n{'='*40}")
        print(f"Testing: {label.upper()}")
        print(f"{'='*40}")
        
        # Non-streaming test
        try:
            non_stream_time = await test_non_streaming(text, label)
        except Exception as e:
            print(f"   ❌ Non-streaming failed: {e}")
            non_stream_time = None
        
        # Streaming test
        try:
            ttft, stream_time = await test_streaming(text, label)
        except Exception as e:
            print(f"   ❌ Streaming failed: {e}")
            ttft, stream_time = None, None
        
        results[label] = {
            "chars": len(text),
            "non_streaming": non_stream_time,
            "streaming_total": stream_time,
            "ttft": ttft,
        }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"{'Label':<10} {'Chars':<8} {'Non-Stream':<12} {'Stream':<12} {'TTFT':<10}")
    print("-" * 52)
    
    for label, data in results.items():
        ns = f"{data['non_streaming']:.3f}s" if data['non_streaming'] else "N/A"
        st = f"{data['streaming_total']:.3f}s" if data['streaming_total'] else "N/A"
        ttft = f"{data['ttft']:.3f}s" if data['ttft'] else "N/A"
        print(f"{label:<10} {data['chars']:<8} {ns:<12} {st:<12} {ttft:<10}")
    
    print("\n✅ Test complete!")
    
    # Check if TTFT is under target
    if results.get('long', {}).get('ttft'):
        ttft = results['long']['ttft']
        if ttft < 0.5:
            print(f"🎯 TTFT ({ttft:.3f}s) is UNDER 0.5s target! ✅")
        else:
            print(f"⚠️ TTFT ({ttft:.3f}s) is ABOVE 0.5s target")


if __name__ == "__main__":
    asyncio.run(main())
