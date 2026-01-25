#!/usr/bin/env python3
"""
Generate voice samples using Deepgram Aura-2 TTS for marketing voiceover selection.

Usage:
    cd marketing
    python generate_voice_samples.py
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from deepgram import AsyncDeepgramClient

# Load environment from python/.env
env_path = Path(__file__).parent.parent / "python" / ".env"
load_dotenv(env_path)

# Sample text for voice comparison
SAMPLE_TEXT = """Turn your notes into exam practice. Just ask VOXAM to create voice-powered exams.
Speak naturally, get instant feedback. Try VOXAM free at voxam.in."""

# Full voiceover script for Instagram ad (30 seconds, paced with pauses)
# Each line has a pause after it for visual sync
# Pacing: longer pauses between sections for breathing room
VOICEOVER_SCRIPT = """Turn your notes... into exam practice.

Introducing VOXAM.

Upload any PDF, textbook, or notes.

Just ask VOXAM to create an exam — it's that simple.

Answer out loud. The AI understands you.

Get instant feedback. Know exactly where to improve.

Try VOXAM free at voxam.in"""

# Voices to test with their characteristics
VOICES = {
    "thalia": "aura-2-thalia-en",    # Clear, Confident, Energetic, Enthusiastic
    "atlas": "aura-2-atlas-en",       # Enthusiastic, Confident, Approachable
    "asteria": "aura-2-asteria-en",   # Clear, Confident, Knowledgeable
    "orpheus": "aura-2-orpheus-en",   # Professional, Clear, Trustworthy
    "zeus": "aura-2-zeus-en",         # Deep, Trustworthy, Smooth
}

OUTPUT_DIR = Path(__file__).parent / "voice_samples"


async def generate_voice_sample(client: AsyncDeepgramClient, voice_name: str, model: str, text: str = SAMPLE_TEXT, output_name: str = None) -> None:
    """Generate a single voice sample and save as MP3."""
    output_name = output_name or voice_name
    output_path = OUTPUT_DIR / f"{output_name}.mp3"

    print(f"Generating {output_name} ({model})...")

    # Collect all audio chunks
    audio_chunks = []
    async for chunk in client.speak.v1.audio.generate(
        text=text,
        model=model,
        encoding="mp3",
    ):
        if chunk:
            audio_chunks.append(chunk)

    audio_data = b"".join(audio_chunks)

    # Save to file
    with open(output_path, "wb") as f:
        f.write(audio_data)

    print(f"  Saved to {output_path} ({len(audio_data)} bytes)")


async def main():
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("Error: DEEPGRAM_API_KEY not found in python/.env")
        return

    print(f"Using API key: {api_key[:8]}...")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = AsyncDeepgramClient(api_key=api_key)

    # Generate the main voiceover using Thalia voice
    print("=== Generating Instagram Ad Voiceover ===")
    print(f"Script preview: {VOICEOVER_SCRIPT[:60]}...")
    print()
    await generate_voice_sample(
        client,
        voice_name="thalia",
        model=VOICES["thalia"],
        text=VOICEOVER_SCRIPT,
        output_name="voiceover_thalia"
    )

    print()
    print("=== Generating Voice Comparison Samples ===")
    print(f"Sample text: {SAMPLE_TEXT[:50]}...")
    print()

    # Generate all voice samples for comparison
    for voice_name, model in VOICES.items():
        await generate_voice_sample(client, voice_name, model)

    print()
    print("Done! Files generated:")
    print("  - voiceover_thalia.mp3 (main Instagram ad voiceover)")
    print("  - {voice}.mp3 files (voice comparison samples)")


if __name__ == "__main__":
    asyncio.run(main())
