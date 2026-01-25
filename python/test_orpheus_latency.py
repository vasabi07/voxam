"""
Latency test for Orpheus TTS from Groq.
Measures time-to-first-byte (TTFB) and total generation time.
"""

import os
import time
import statistics
from dotenv import load_dotenv
import requests

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY not set in environment")
    exit(1)

# Test phrases of varying lengths (max 200 chars for Orpheus)
TEST_PHRASES = [
    "Hello, how are you today?",
    "The quick brown fox jumps over the lazy dog.",
    "Photosynthesis is the process by which plants convert light energy into chemical energy.",
    "[cheerful] This is amazing! I'm so happy to help you learn today.",
    "[sad] Unfortunately, that answer was not quite correct. Let's try again.",
]

# Orpheus voices
VOICES = ["autumn", "diana", "hannah", "austin", "daniel", "troy"]

def test_orpheus_streaming(voice="troy"):
    """Test Orpheus TTS with streaming to measure TTFB."""
    
    url = "https://api.groq.com/openai/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    results = []
    
    for phrase in TEST_PHRASES:
        print(f"\n📝 Testing: \"{phrase[:50]}{'...' if len(phrase) > 50 else ''}\"")
        print(f"   Length: {len(phrase)} chars | Voice: {voice}")
        
        payload = {
            "model": "canopylabs/orpheus-v1-english",
            "input": phrase,
            "voice": voice,
            "response_format": "wav",
        }
        
        # Measure streaming response
        start_time = time.perf_counter()
        first_chunk_time = None
        total_bytes = 0
        
        try:
            response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
            
            if response.status_code != 200:
                print(f"   ❌ Error: {response.status_code} - {response.text[:200]}")
                continue
            
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()
                    total_bytes += len(chunk)
            
            end_time = time.perf_counter()
            
            ttfb = (first_chunk_time - start_time) * 1000 if first_chunk_time else None
            total_time = (end_time - start_time) * 1000
            
            print(f"   ⏱️  TTFB: {ttfb:.0f}ms")
            print(f"   ⏱️  Total: {total_time:.0f}ms")
            print(f"   📦 Size: {total_bytes / 1024:.1f}KB")
            
            results.append({
                "phrase": phrase[:30],
                "phrase_len": len(phrase),
                "ttfb_ms": ttfb,
                "total_ms": total_time,
                "size_kb": total_bytes / 1024,
                "voice": voice,
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return results


def test_all_voices():
    """Test all available voices."""
    
    url = "https://api.groq.com/openai/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    test_phrase = "Hello, this is a test of the Orpheus text to speech system."
    
    print("\n" + "="*60)
    print("🎤 Testing All Orpheus Voices")
    print("="*60)
    
    voice_results = []
    
    for voice in VOICES:
        payload = {
            "model": "canopylabs/orpheus-v1-english",
            "input": test_phrase,
            "voice": voice,
            "response_format": "wav",
        }
        
        start_time = time.perf_counter()
        first_chunk_time = None
        total_bytes = 0
        
        try:
            response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ {voice}: {response.status_code} - {response.text[:100]}")
                continue
            
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()
                    total_bytes += len(chunk)
            
            end_time = time.perf_counter()
            ttfb = (first_chunk_time - start_time) * 1000 if first_chunk_time else None
            total = (end_time - start_time) * 1000
            
            print(f"✅ {voice:10} | TTFB: {ttfb:5.0f}ms | Total: {total:5.0f}ms | Size: {total_bytes/1024:.1f}KB")
            voice_results.append({"voice": voice, "ttfb": ttfb, "total": total})
            
        except Exception as e:
            print(f"❌ {voice}: {e}")
    
    return voice_results


def run_latency_benchmark(num_runs=3):
    """Run multiple iterations to get statistical measures."""
    print("\n" + "="*60)
    print("🚀 Orpheus TTS (Groq) Latency Benchmark")
    print(f"   Model: canopylabs/orpheus-v1-english")
    print("="*60)
    
    all_ttfb = []
    all_total = []
    
    for run in range(num_runs):
        print(f"\n{'='*20} Run {run + 1}/{num_runs} {'='*20}")
        results = test_orpheus_streaming(voice="troy")
        
        for r in results:
            if r.get("ttfb_ms"):
                all_ttfb.append(r["ttfb_ms"])
                all_total.append(r["total_ms"])
    
    if all_ttfb:
        print("\n" + "="*60)
        print("📊 Summary Statistics (across all runs)")
        print("="*60)
        print(f"\nTTFB (Time to First Byte):")
        print(f"   Min:    {min(all_ttfb):.0f}ms")
        print(f"   Max:    {max(all_ttfb):.0f}ms")
        print(f"   Mean:   {statistics.mean(all_ttfb):.0f}ms")
        print(f"   Median: {statistics.median(all_ttfb):.0f}ms")
        if len(all_ttfb) > 1:
            print(f"   StdDev: {statistics.stdev(all_ttfb):.0f}ms")
        
        print(f"\nTotal Generation Time:")
        print(f"   Min:    {min(all_total):.0f}ms")
        print(f"   Max:    {max(all_total):.0f}ms")
        print(f"   Mean:   {statistics.mean(all_total):.0f}ms")
        print(f"   Median: {statistics.median(all_total):.0f}ms")
        if len(all_total) > 1:
            print(f"   StdDev: {statistics.stdev(all_total):.0f}ms")
        
        # Calculate chars per second
        print(f"\n📈 Throughput estimate:")
        avg_chars = sum(len(p) for p in TEST_PHRASES) / len(TEST_PHRASES)
        avg_total = statistics.mean(all_total)
        print(f"   ~{avg_chars / (avg_total/1000):.0f} chars/second")
    else:
        print("\n⚠️  No successful runs")


if __name__ == "__main__":
    # First test all voices
    voice_results = test_all_voices()
    
    if voice_results:
        # Run full benchmark
        run_latency_benchmark(num_runs=3)
    else:
        print("\n⚠️  Could not connect to Orpheus TTS API")
