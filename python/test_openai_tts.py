"""
OpenAI gpt-4o-mini-tts Voice Test
=================================
Uses the latest gpt-4o-mini-tts-2025-12-15 model.
Creates audio samples for different teacher scenarios.

Pricing: $12/1M audio tokens (~$0.015/min)
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
print("✅ OpenAI client initialized")

# Model to use
MODEL = "gpt-4o-mini-tts-2025-12-15"

# Voices available for gpt-4o-mini-tts
VOICES = ["alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"]

# Voice instruction for Indian professor
PROFESSOR_INSTRUCTION = """You are Professor Venkat, a warm but rigorous Indian academic examiner.
Speak with a calm, measured pace. Use a warm, encouraging tone with clear articulation.
Add natural pauses for emphasis. Your accent should reflect Indian English pronunciation."""

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


def generate_voice_samples(voice: str, use_instructions: bool = True):
    """Generate all samples for a voice."""
    suffix = "with_inst" if use_instructions else "no_inst"
    print(f"\n🎤 Generating samples: {voice} ({suffix})")
    print("-" * 60)
    
    for prompt_key, prompt_text in TEACHER_PROMPTS.items():
        try:
            start = time.time()
            
            kwargs = {
                "model": MODEL,
                "voice": voice,
                "input": prompt_text,
                "response_format": "mp3",
            }
            
            if use_instructions:
                kwargs["instructions"] = PROFESSOR_INSTRUCTION
            
            response = client.audio.speech.create(**kwargs)
            
            ttfb = time.time() - start
            audio = response.content
            
            filename = f"openai_{voice}_{suffix}_{prompt_key}.mp3"
            Path(filename).write_bytes(audio)
            
            print(f"   ✅ {prompt_key}: {len(audio)/1024:.1f}KB (TTFB: {ttfb:.2f}s) → {filename}")
            
        except Exception as e:
            print(f"   ❌ {prompt_key}: {e}")
        
        time.sleep(0.3)


def test_all_voices_greeting():
    """Test all voices with just the greeting to compare."""
    print("\n🎤 Testing all voices with greeting")
    print("-" * 60)
    
    greeting = TEACHER_PROMPTS["01_greeting"]
    
    for voice in VOICES:
        try:
            start = time.time()
            
            response = client.audio.speech.create(
                model=MODEL,
                voice=voice,
                input=greeting,
                instructions=PROFESSOR_INSTRUCTION,
                response_format="mp3",
            )
            
            ttfb = time.time() - start
            audio = response.content
            
            filename = f"openai_{voice}_greeting.mp3"
            Path(filename).write_bytes(audio)
            
            print(f"   ✅ {voice:10}: {len(audio)/1024:.1f}KB (TTFB: {ttfb:.2f}s)")
            
        except Exception as e:
            print(f"   ❌ {voice:10}: {e}")
        
        time.sleep(0.3)


if __name__ == "__main__":
    print("=" * 60)
    print(f"🎙️ OpenAI TTS Test - {MODEL}")
    print("=" * 60)
    
    # Test 1: All voices with greeting (to pick the best one)
    test_all_voices_greeting()
    
    # Test 2: Full samples with "coral" voice (good for warm professor)
    generate_voice_samples("coral", use_instructions=True)
    
    # Test 3: Full samples with "onyx" voice (deep male)
    generate_voice_samples("onyx", use_instructions=True)
    
    print("\n" + "=" * 60)
    print("✅ Complete! Listen to the .mp3 files to compare voices.")
    print("=" * 60)
    print(f"\nFiles created:")
    print("   - openai_*_greeting.mp3 (all 9 voices)")
    print("   - openai_coral_with_inst_*.mp3 (full scenarios)")
    print("   - openai_onyx_with_inst_*.mp3 (full scenarios)")
