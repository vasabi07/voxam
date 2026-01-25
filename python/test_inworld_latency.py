#!/usr/bin/env python3
"""
Inworld AI TTS Latency Test Script
Tests streaming TTS latency to compare with current Google/Sarvam.

Usage:
    export INWORLD_API_KEY=your_key
    python test_inworld_latency.py
"""

import os
import time
import asyncio
import httpx
import base64
from dotenv import load_dotenv

load_dotenv()

# Inworld supports multiple auth methods:
# 1. Basic auth (Base64 key from dashboard)
# 2. JWT Key + Secret (for generating tokens)
INWORLD_API_KEY = os.getenv("INWORLD_API_KEY")  # The Base64 key
INWORLD_JWT_KEY = os.getenv("INWORLD_JWT_KEY")  # Optional: JWT Key
INWORLD_JWT_SECRET = os.getenv("INWORLD_JWT_SECRET")  # Optional: JWT Secret

if not INWORLD_API_KEY:
    print("❌ Set INWORLD_API_KEY in .env (the Base64 key from dashboard)")
    exit(1)

def get_auth_header():
    """Try different auth formats."""
    # The Base64 key should be used directly
    return f"Basic {INWORLD_API_KEY}"


async def test_tts_streaming():
    """Test Inworld TTS streaming latency (time to first byte)"""
    print("\n" + "="*60)
    print("Testing Inworld AI TTS Latency (Streaming)")
    print("="*60)
    
    text = "Good Morning! Welcome to your physics exam. I am Venkat and I will be your examiner for today."
    
    # The Basic key from Inworld is already base64 encoded
    # Use it directly in the Authorization header
    auth_string = INWORLD_API_KEY
    
    async with httpx.AsyncClient() as client:
        times_ttfb = []  # Time to first byte
        times_total = []  # Total completion
        
        # Debug: show auth format
        auth_header = get_auth_header()
        print(f"Auth header (first 30 chars): {auth_header[:30]}...")
        
        for i in range(3):
            start = time.time()
            first_byte_time = None
            total_bytes = 0
            
            try:
                async with client.stream(
                    "POST",
                    "https://api.inworld.ai/tts/v1/voice:stream",
                    headers={
                        "Authorization": f"Basic {auth_string}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "voice_id": "Dennis",
                        "audio_config": {
                            "audio_encoding": "MP3",
                            "speaking_rate": 1
                        },
                        "temperature": 1.1,
                        "model_id": "inworld-tts-1-max"
                    },
                    timeout=30
                ) as response:
                    if response.status_code != 200:
                        print(f"  Run {i+1}: ❌ {response.status_code}")
                        content = await response.aread()
                        print(f"    Error: {content[:200]}")
                        continue
                    
                    async for chunk in response.aiter_bytes():
                        if first_byte_time is None:
                            first_byte_time = (time.time() - start) * 1000
                        total_bytes += len(chunk)
                
                total_time = (time.time() - start) * 1000
                
                if first_byte_time:
                    times_ttfb.append(first_byte_time)
                    times_total.append(total_time)
                    print(f"  Run {i+1}: TTFB={first_byte_time:.0f}ms, Total={total_time:.0f}ms, Size={total_bytes/1024:.1f}KB ✅")
            
            except Exception as e:
                print(f"  Run {i+1}: ❌ Error: {e}")
        
        if times_ttfb:
            avg_ttfb = sum(times_ttfb) / len(times_ttfb)
            avg_total = sum(times_total) / len(times_total)
            print(f"\n📊 Avg TTFB: {avg_ttfb:.0f}ms")
            print(f"📊 Avg Total: {avg_total:.0f}ms")
            return avg_ttfb, avg_total
    
    return None, None


async def main():
    print("="*60)
    print("INWORLD AI TTS LATENCY TEST")
    print("="*60)
    
    ttfb, total = await test_tts_streaming()
    
    print("\n" + "="*60)
    print("COMPARISON")
    print("="*60)
    print("  Current stack:")
    print("    Google TTS (India): ~300-500ms TTFB")
    print("    Sarvam TTS: ~800ms")
    if ttfb:
        print(f"\n  Inworld TTS: {ttfb:.0f}ms TTFB")
        if ttfb < 300:
            print("    🚀 Faster than Google!")
        elif ttfb < 500:
            print("    ✅ Comparable to Google")
        else:
            print("    ⚠️ Slower than Google")


if __name__ == "__main__":
    asyncio.run(main())
