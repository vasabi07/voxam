"""
Orpheus 3B TTS Latency Test Script (DeepInfra)
==============================================

Tests:
1. Time to first byte (TTFT)
2. Total generation time
3. Streaming comparison vs Kokoro
"""
import httpx
import time
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
# Orpheus endpoint
ORPHEUS_ENDPOINT = "https://api.deepinfra.com/v1/inference/canopylabs/orpheus-3b-0.1-ft"

if not DEEPINFRA_API_KEY:
    raise ValueError("Missing DEEPINFRA_API_KEY in .env")

# Same test sentences for direct comparison
TEST_TEXTS = {
    "short": "Welcome to your Chemistry exam.",
    "medium": "Welcome to your Chemistry examination. This test consists of 10 questions, and you have 15 minutes to complete it.",
    "long": "Welcome to your Chemistry examination. This test consists of 10 questions, and you have 15 minutes to complete it. I'll read each question clearly. Please say 'next' when you're ready to move on. Let's begin with Question 1: What is the chemical formula of water?",
}


async def test_streaming(text: str, label: str):
    """Test streaming TTS request for Orpheus"""
    print(f"\n📝 Testing ORPHEUS STREAMING ({label}): {len(text)} chars")
    
    start = time.time()
    first_chunk_time = None
    total_bytes = 0
    chunks = 0
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST",
                ORPHEUS_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": text,
                    # Supported: 'tara', 'leah', 'jess', 'leo', 'dan', 'mia', 'zac'
                    "voice": "leo", 
                    "stream": True,
                },
                timeout=60.0,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    print(f"   ❌ Error: {response.status_code} - {body.decode()}")
                    return None, None

                async for chunk in response.aiter_bytes():
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - start
                        print(f"   🚀 TTFT (Time to First Token): {first_chunk_time:.3f}s")
                    
                    total_bytes += len(chunk)
                    chunks += 1
        except Exception as e:
            print(f"   ❌ Network error: {e}")
            return None, None
    
    elapsed = time.time() - start
    # Duration calculation depends on sample rate, usually 24kHz or 48kHz for Orpheus.
    # We'll just report bytes/sec or total time for now.
    
    print(f"   ⏱️  Total time: {elapsed:.3f}s")
    print(f"   🔊 Total bytes: {total_bytes:,}")
    print(f"   📦 Chunks received: {chunks}")
    
    return first_chunk_time, elapsed


async def main():
    print("=" * 60)
    print("🎙️ ORPHEUS 3B TTS LATENCY TEST")
    print("=" * 60)
    
    results = {}
    
    for label, text in TEST_TEXTS.items():
        print(f"\n{'='*40}")
        print(f"Testing: {label.upper()}")
        print(f"{'='*40}")
        
        ttft, total = await test_streaming(text, label)
        
        results[label] = {
            "chars": len(text),
            "ttft": ttft,
            "total": total
        }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"{'Label':<10} {'Chars':<8} {'TTFT':<12} {'Total Time':<12}")
    print("-" * 45)
    
    for label, data in results.items():
        ttft_str = f"{data['ttft']:.3f}s" if data['ttft'] else "N/A"
        total_str = f"{data['total']:.3f}s" if data['total'] else "N/A"
        print(f"{label:<10} {data['chars']:<8} {ttft_str:<12} {total_str:<12}")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
