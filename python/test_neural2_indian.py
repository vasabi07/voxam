"""
Google Cloud TTS - Neural2 Indian English Voice Test
=====================================================
Tests en-IN voices with different Professor-style sentences.
Saves audio files for quality comparison.
"""
import os
import time
from dotenv import load_dotenv
from google.cloud import texttospeech

load_dotenv()

# Initialize client
client = texttospeech.TextToSpeechClient()

OUTPUT_DIR = "/Users/vasanth/voxam/python/tts_samples/neural2_indian"

# Indian English Neural2 voices
VOICES = [
    ("en-IN-Neural2-A", "FEMALE"),
    ("en-IN-Neural2-B", "MALE"),
    ("en-IN-Neural2-C", "MALE"),
    ("en-IN-Neural2-D", "FEMALE"),
]

# Test sentences (Professor Venkat style)
TEST_SENTENCES = {
    "greeting": "Welcome to your Chemistry examination. I'm Professor Venkat, and I'll be guiding you through this test today.",
    "question": "Let's move on to question number two. Can you explain the process of photosynthesis in simple terms?",
    "feedback_positive": "Excellent answer! You've demonstrated a clear understanding of the core concepts. Keep up the good work!",
    "feedback_correction": "That's not quite right. Let me give you a hint. Think about what happens when light energy is absorbed by chlorophyll.",
    "encouragement": "Don't worry, take your time. This is a learning process, and it's okay to think through the problem step by step.",
}


def test_voice(voice_name: str, gender: str, text: str, label: str):
    """Test a specific voice configuration"""
    print(f"\n🎙️ Voice: {voice_name} ({gender}) - {label}")
    
    # Configure synthesis
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-IN",
        name=voice_name,
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
        pitch=0.0,
    )
    
    start = time.time()
    
    try:
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        
        latency = time.time() - start
        audio_data = response.audio_content
        
        # Save file
        safe_voice = voice_name.replace("-", "_")
        filepath = f"{OUTPUT_DIR}/{safe_voice}_{label}.mp3"
        with open(filepath, "wb") as f:
            f.write(audio_data)
        
        # Estimate duration (MP3 ~16kbps for speech)
        duration_estimate = len(audio_data) / 2000  # rough estimate
        
        print(f"   ⏱️  Latency: {latency:.3f}s | Size: {len(audio_data)/1024:.1f}KB | Saved: {filepath}")
        
        return latency
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def main():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("🇮🇳 NEURAL2 INDIAN ENGLISH VOICE TEST")
    print("=" * 60)
    
    results = {}
    
    # Test all voices with all sentences
    for voice_name, gender in VOICES:
        print(f"\n{'='*50}")
        print(f"📣 Testing Voice: {voice_name} ({gender})")
        print("=" * 50)
        
        voice_results = {}
        
        for label, text in TEST_SENTENCES.items():
            latency = test_voice(voice_name, gender, text, label)
            voice_results[label] = latency
        
        results[voice_name] = voice_results
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 LATENCY SUMMARY")
    print("=" * 60)
    print(f"{'Voice':<20} {'Avg Latency':<15}")
    print("-" * 40)
    
    for voice_name, voice_results in results.items():
        latencies = [v for v in voice_results.values() if v is not None]
        if latencies:
            avg = sum(latencies) / len(latencies)
            print(f"{voice_name:<20} {avg:.3f}s")
    
    print(f"\n🎧 Audio files saved to: {OUTPUT_DIR}/")
    print("\n💡 RECOMMENDED FOR PROFESSOR VENKAT:")
    print("   - en-IN-Neural2-B (Male) - Deep, authoritative")
    print("   - en-IN-Neural2-C (Male) - Clear, professional")
    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
