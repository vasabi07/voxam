#!/usr/bin/env python3
"""
Generate voiceover for VOXAM Instagram Ad using Gemini 2.5 Flash TTS.

Requirements:
    pip install google-genai

Usage:
    python generate-voiceover-gemini.py

Output:
    ../public/voiceover.mp3
"""

import os
import wave
import subprocess
from pathlib import Path

# Load env from python/.env
env_path = Path(__file__).parent.parent.parent.parent / "python" / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                key, value = line.strip().split("=", 1)
                value = value.strip('"').strip("'")
                os.environ.setdefault(key, value)

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Installing google-genai...")
    os.system("pip install google-genai")
    from google import genai
    from google.genai import types


# Voiceover script with director's notes for style control
# Using natural language prompts for pacing and tone
# Target duration: ~31 seconds (steady, confident)
VOICEOVER_PROMPT = """
You are a confident, warm presenter. Speak with enthusiasm at a steady, flowing pace.
This is a 31-second social media ad. Keep momentum while allowing brief pauses between sentences.

Read this script naturally with short pauses between sentences:

"Turn your notes into real exam practice.

Introducing VOXAM.

Upload any study material - PDFs, textbooks, or notes.

Ask to create an exam. VOXAM builds questions that test deep understanding.

Practice with your voice. An AI tutor listens, adapts, and guides you.

Get detailed feedback on every answer, and know exactly where to improve.

Try VOXAM free at voxam.in"
"""


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Write PCM data to a WAV file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def convert_wav_to_mp3(wav_path: Path, mp3_path: Path):
    """Convert WAV to MP3 using ffmpeg."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), "-b:a", "192k", str(mp3_path)],
            capture_output=True,
            check=True,
        )
        wav_path.unlink()  # Remove WAV after conversion
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ffmpeg not available, keeping WAV file")
        return False


def generate_voiceover():
    """Generate voiceover using Gemini 2.5 Flash TTS."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment")
        return

    client = genai.Client(api_key=api_key)

    # Available voices: Zephyr (Bright), Puck (Upbeat), Kore (Firm),
    # Sulafat (Warm), Achird (Friendly), Enceladus (Breathy), Algieba (Smooth)
    # Using Sulafat for warm, tutorish quality
    voice_name = "Sulafat"  # Warm voice

    print(f"Generating voiceover with Gemini 2.5 Flash TTS (voice: {voice_name})...")

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=VOICEOVER_PROMPT,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    )
                )
            ),
        ),
    )

    # Extract audio data
    data = response.candidates[0].content.parts[0].inline_data.data

    # Save paths
    output_dir = Path(__file__).parent.parent / "public"
    wav_path = output_dir / "voiceover.wav"
    mp3_path = output_dir / "voiceover.mp3"

    # Write WAV file
    wave_file(str(wav_path), data)
    print(f"WAV saved: {wav_path}")

    # Convert to MP3
    if convert_wav_to_mp3(wav_path, mp3_path):
        print(f"MP3 saved: {mp3_path}")
        print(f"File size: {mp3_path.stat().st_size / 1024:.1f} KB")
    else:
        print(f"WAV file kept at: {wav_path}")
        print(f"File size: {wav_path.stat().st_size / 1024:.1f} KB")

    # Check duration
    try:
        from mutagen.mp3 import MP3
        if mp3_path.exists():
            duration = MP3(str(mp3_path)).info.length
            print(f"Duration: {duration:.1f} seconds")
    except ImportError:
        pass


if __name__ == "__main__":
    generate_voiceover()
