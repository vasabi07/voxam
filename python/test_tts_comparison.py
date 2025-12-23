"""
TTS Provider Comparison Test
=============================
Compares: OpenAI TTS-1, Kokoro (DeepInfra), Orpheus 3B (DeepInfra)
- Uses sentence-length texts (matching our sentence buffer approach)
- Saves audio files for quality comparison
- Measures TTFB latency
"""
import os
import time
import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")

# Sentence-length texts (matching our sentence buffer approach)
TEST_SENTENCES = {
    "greeting": "Welcome to your Chemistry examination, I'm Professor Venkat.",
    "question": "What is the chemical formula of water, and why is it important for life?",
    "feedback": "That's an excellent answer! You've correctly identified the key concepts.",
}

OUTPUT_DIR = "/Users/vasanth/voxam/python/tts_samples"


def test_openai_tts(text: str, label: str) -> tuple:
    """Test OpenAI TTS-1"""
    print(f"\n🔵 OpenAI TTS-1 ({label})")
    
    start = time.time()
    first_chunk_time = None
    audio_chunks = []
    
    try:
        with openai_client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="onyx",
            input=text,
            response_format="mp3",
        ) as response:
            for chunk in response.iter_bytes(chunk_size=1024):
                if first_chunk_time is None:
                    first_chunk_time = time.time() - start
                audio_chunks.append(chunk)
        
        total = time.time() - start
        audio_data = b"".join(audio_chunks)
        
        # Save file
        filepath = f"{OUTPUT_DIR}/openai_{label}.mp3"
        with open(filepath, "wb") as f:
            f.write(audio_data)
        
        print(f"   TTFB: {first_chunk_time:.3f}s | Total: {total:.3f}s | Saved: {filepath}")
        return first_chunk_time, total
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None, None


def test_kokoro_tts(text: str, label: str) -> tuple:
    """Test Kokoro-82M on DeepInfra"""
    print(f"\n🟢 Kokoro-82M ({label})")
    
    start = time.time()
    first_chunk_time = None
    audio_chunks = []
    
    try:
        with httpx.Client() as client:
            response = client.post(
                "https://api.deepinfra.com/v1/inference/hexgrad/Kokoro-82M",
                headers={
                    "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"text": text},
                timeout=60.0,
            )
            
            if response.status_code == 200:
                first_chunk_time = time.time() - start
                audio_data = response.content
                
                total = time.time() - start
                
                # Save file (raw PCM, convert to wav header)
                filepath = f"{OUTPUT_DIR}/kokoro_{label}.wav"
                # Add WAV header for 24kHz mono 16-bit
                import struct
                sample_rate = 24000
                num_channels = 1
                bits_per_sample = 16
                data_size = len(audio_data)
                wav_header = struct.pack(
                    '<4sI4s4sIHHIIHH4sI',
                    b'RIFF', 36 + data_size, b'WAVE', b'fmt ', 16,
                    1, num_channels, sample_rate,
                    sample_rate * num_channels * bits_per_sample // 8,
                    num_channels * bits_per_sample // 8,
                    bits_per_sample, b'data', data_size
                )
                with open(filepath, "wb") as f:
                    f.write(wav_header + audio_data)
                
                print(f"   TTFB: {first_chunk_time:.3f}s | Total: {total:.3f}s | Saved: {filepath}")
                return first_chunk_time, total
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text[:200]}")
                return None, None
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None, None


def test_orpheus_tts(text: str, label: str) -> tuple:
    """Test Orpheus 3B on DeepInfra"""
    print(f"\n🟣 Orpheus 3B ({label})")
    
    start = time.time()
    first_chunk_time = None
    
    try:
        with httpx.Client() as client:
            response = client.post(
                "https://api.deepinfra.com/v1/inference/canopylabs/orpheus-3b-0.1-ft",
                headers={
                    "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"input": text, "voice": "leo"},
                timeout=60.0,
            )
            
            if response.status_code == 200:
                first_chunk_time = time.time() - start
                audio_data = response.content
                
                total = time.time() - start
                
                # Save file
                filepath = f"{OUTPUT_DIR}/orpheus_{label}.wav"
                # Add WAV header for 24kHz mono 16-bit
                import struct
                sample_rate = 24000
                num_channels = 1
                bits_per_sample = 16
                data_size = len(audio_data)
                wav_header = struct.pack(
                    '<4sI4s4sIHHIIHH4sI',
                    b'RIFF', 36 + data_size, b'WAVE', b'fmt ', 16,
                    1, num_channels, sample_rate,
                    sample_rate * num_channels * bits_per_sample // 8,
                    num_channels * bits_per_sample // 8,
                    bits_per_sample, b'data', data_size
                )
                with open(filepath, "wb") as f:
                    f.write(wav_header + audio_data)
                
                print(f"   TTFB: {first_chunk_time:.3f}s | Total: {total:.3f}s | Saved: {filepath}")
                return first_chunk_time, total
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text[:200]}")
                return None, None
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None, None


def main():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("🎙️ TTS PROVIDER COMPARISON TEST")
    print("   (Sentence-length texts for sentence buffer approach)")
    print("=" * 60)
    
    results = {"openai": {}, "kokoro": {}, "orpheus": {}}
    
    for label, text in TEST_SENTENCES.items():
        print(f"\n{'='*50}")
        print(f"📝 Test: {label.upper()} ({len(text)} chars)")
        print(f"   \"{text}\"")
        print("=" * 50)
        
        # OpenAI
        ttfb, total = test_openai_tts(text, label)
        results["openai"][label] = {"ttfb": ttfb, "total": total}
        
        # Kokoro
        ttfb, total = test_kokoro_tts(text, label)
        results["kokoro"][label] = {"ttfb": ttfb, "total": total}
        
        # Orpheus
        ttfb, total = test_orpheus_tts(text, label)
        results["orpheus"][label] = {"ttfb": ttfb, "total": total}
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY - TTFB (Time to First Byte)")
    print("=" * 60)
    print(f"{'Text':<12} {'OpenAI':<12} {'Kokoro':<12} {'Orpheus':<12}")
    print("-" * 50)
    
    for label in TEST_SENTENCES.keys():
        openai_ttfb = f"{results['openai'][label]['ttfb']:.3f}s" if results['openai'][label]['ttfb'] else "N/A"
        kokoro_ttfb = f"{results['kokoro'][label]['ttfb']:.3f}s" if results['kokoro'][label]['ttfb'] else "N/A"
        orpheus_ttfb = f"{results['orpheus'][label]['ttfb']:.3f}s" if results['orpheus'][label]['ttfb'] else "N/A"
        print(f"{label:<12} {openai_ttfb:<12} {kokoro_ttfb:<12} {orpheus_ttfb:<12}")
    
    print(f"\n🎧 Audio files saved to: {OUTPUT_DIR}/")
    print("✅ Test complete!")


if __name__ == "__main__":
    main()
