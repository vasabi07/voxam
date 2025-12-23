"""
Neural2 Voice Test - en-IN-Neural2-B vs en-US-Neural2-J
========================================================
Creates audio samples for different teacher scenarios.
"""

import os
import time
import struct
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()
print("✅ Client initialized")

# Voices to test
VOICES = {
    "india_male": "en-IN-Neural2-B",
    "us_male": "en-US-Neural2-J",
}

# Teacher scenarios
TEACHER_PROMPTS = {
    "01_greeting": """Welcome to your Physics examination. I'm Professor Venkat, and I'll be your examiner today. Take a deep breath... we're going to start with some fundamental concepts.""",
    
    "02_first_question": """Alright, let's begin. Here's your first question. Newton's second law of motion states that force equals mass times acceleration. If I apply a force of 20 Newtons to a 4 kilogram object, what would be the resulting acceleration?""",
    
    "03_encouragement": """That's an excellent answer! You've correctly calculated that the acceleration is 5 meters per second squared. Very well done. Your understanding of the basics is solid.""",
    
    "04_wrong_answer": """Hmm, that's not quite right. Let me give you a hint. Remember, acceleration equals force divided by mass. So if you have 20 Newtons of force and 4 kilograms of mass, what do you get when you divide?""",
    
    "05_explanation": """Let me explain this concept more clearly. Kinetic energy is the energy an object possesses due to its motion. The formula is one-half times mass times velocity squared. So if you double the velocity, the kinetic energy increases by a factor of four, not two. Does that make sense?""",
    
    "06_thinking": """Hmm, let me think about that for a moment... Interesting question. The relationship between potential and kinetic energy is fundamental to understanding conservation of energy.""",
    
    "07_next_question": """Good. Now let's move on to the next question. This one is about thermodynamics. According to the first law of thermodynamics, what happens to the total energy in an isolated system?""",
    
    "08_final": """We've reached the end of our examination. You performed very well today. Your score will be available in the correction report. Thank you for your effort, and keep up the good work!""",
}


def save_wav(audio_data: bytes, filename: str):
    """Save raw PCM data as WAV file."""
    sample_rate = 24000
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(audio_data), b"WAVE", b"fmt ", 16, 1,
        1, sample_rate, sample_rate * 2, 2, 16, b"data", len(audio_data)
    )
    Path(filename).write_bytes(header + audio_data)


def generate_voice_samples(voice_name: str, voice_id: str):
    """Generate all samples for a voice."""
    print(f"\n🎤 Generating samples for: {voice_name} ({voice_id})")
    print("-" * 60)
    
    lang = "en-IN" if "IN" in voice_id else "en-US"
    
    for prompt_key, prompt_text in TEACHER_PROMPTS.items():
        try:
            start = time.time()
            
            response = client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=prompt_text),
                voice=texttospeech.VoiceSelectionParams(name=voice_id, language_code=lang),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                    sample_rate_hertz=24000,
                    speaking_rate=1.0,
                )
            )
            
            ttfb = time.time() - start
            audio = response.audio_content
            duration = len(audio) / (24000 * 2)
            
            filename = f"{voice_name}_{prompt_key}.wav"
            save_wav(audio, filename)
            
            print(f"   ✅ {prompt_key}: {duration:.1f}s audio (TTFB: {ttfb:.2f}s) → {filename}")
            
        except Exception as e:
            print(f"   ❌ {prompt_key}: {e}")
        
        time.sleep(0.2)


if __name__ == "__main__":
    print("=" * 60)
    print("🎙️ Neural2 Teacher Voice Samples")
    print("=" * 60)
    
    # Generate for India Male
    generate_voice_samples("india_male", "en-IN-Neural2-B")
    
    # Generate for US Male
    generate_voice_samples("us_male", "en-US-Neural2-J")
    
    print("\n" + "=" * 60)
    print("✅ Complete! Listen to the .wav files to compare voices.")
    print("=" * 60)
