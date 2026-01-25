#!/usr/bin/env python3
"""
Sarvam AI Latency Test Script
Tests STT and TTS latency to compare with current Deepgram/Google setup.

Usage:
    export SARVAM_API_KEY=your_key
    python test_sarvam_latency.py
"""

import os
import time
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
BASE_URL = "https://api.sarvam.ai"

if not SARVAM_API_KEY:
    print("❌ Set SARVAM_API_KEY in .env first")
    exit(1)


async def test_tts_latency():
    """Test Text-to-Speech latency"""
    print("\n" + "="*50)
    print("Testing Sarvam TTS Latency")
    print("="*50)
    
    text = "Welcome to the exam. This is question number one. Please listen carefully."
    
    async with httpx.AsyncClient() as client:
        times = []
        for i in range(3):
            start = time.time()
            
            response = await client.post(
                f"{BASE_URL}/text-to-speech",
                headers={
                    "api-subscription-key": SARVAM_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "inputs": [text],
                    "target_language_code": "en-IN",
                    "speaker": "anushka",  # Valid: anushka, abhilash, vidya, arya, etc.
                    "model": "bulbul:v2"
                },
                timeout=30
            )
            
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            if response.status_code == 200:
                print(f"  Run {i+1}: {elapsed:.0f}ms ✅")
            else:
                print(f"  Run {i+1}: {elapsed:.0f}ms ❌ {response.status_code}")
                print(f"    {response.text[:200]}")
        
        avg = sum(times) / len(times)
        print(f"\n📊 Avg TTS latency: {avg:.0f}ms")
        return avg


async def test_stt_latency():
    """Test Speech-to-Text latency (non-streaming)"""
    print("\n" + "="*50)
    print("Testing Sarvam STT Latency")
    print("="*50)
    
    # Create a simple test audio file (or use existing)
    test_audio_path = "test_audio.wav"
    
    if not os.path.exists(test_audio_path):
        print(f"⚠️  Create {test_audio_path} first (5-10 second audio clip)")
        print("   Or record: ffmpeg -f avfoundation -i ':0' -t 5 test_audio.wav")
        return None
    
    async with httpx.AsyncClient() as client:
        times = []
        for i in range(3):
            start = time.time()
            
            with open(test_audio_path, "rb") as f:
                response = await client.post(
                    f"{BASE_URL}/speech-to-text",
                    headers={
                        "api-subscription-key": SARVAM_API_KEY,
                    },
                    files={"file": f},
                    data={
                        "language_code": "en-IN",
                        "model": "saarika:v2"
                    },
                    timeout=30
                )
            
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            if response.status_code == 200:
                result = response.json()
                print(f"  Run {i+1}: {elapsed:.0f}ms ✅")
                print(f"    Transcript: {result.get('transcript', 'N/A')[:50]}...")
            else:
                print(f"  Run {i+1}: {elapsed:.0f}ms ❌ {response.status_code}")
        
        avg = sum(times) / len(times)
        print(f"\n📊 Avg STT latency: {avg:.0f}ms")
        return avg


async def main():
    print("="*60)
    print("SARVAM AI LATENCY TEST")
    print("="*60)
    
    tts_latency = await test_tts_latency()
    stt_latency = await test_stt_latency()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  TTS: {tts_latency:.0f}ms average" if tts_latency else "  TTS: Not tested")
    print(f"  STT: {stt_latency:.0f}ms average" if stt_latency else "  STT: Not tested")
    
    print("\n📊 Comparison with current stack:")
    print("  Google TTS (India): ~300-500ms")
    print("  Deepgram STT: ~100-200ms (streaming)")


if __name__ == "__main__":
    asyncio.run(main())
