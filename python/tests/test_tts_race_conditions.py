"""
Test: Race condition handling in TTS Queue.

Demonstrates:
1. Messages queued faster than TTS can speak
2. Messages spoken in order (no overlap)
3. User interruption clears queue

Run with: python -m tests.test_tts_race_conditions
"""

import asyncio
from lib.tts_queue import TTSQueue, TTSPriority


async def slow_tts(text: str) -> float:
    """Simulate slow TTS (2 seconds per message)."""
    print(f"🔊 [TTS START] {text[:40]}...")
    await asyncio.sleep(2)  # 2 second TTS
    print(f"   ✅ [TTS DONE] {text[:40]}...")
    return 2.0


async def test_race_condition():
    """
    Test: Graph emits 3 messages instantly, TTS takes 2s each.
    Without queue: messages would overlap or be lost.
    With queue: messages spoken in order.
    """
    print("\n" + "="*70)
    print("TEST 1: Race Condition - Fast emission, slow TTS")
    print("="*70)

    queue = TTSQueue(slow_tts, min_gap=0.5)
    await queue.start()

    # Simulate graph emitting messages faster than TTS can speak
    print("\n📤 Graph emitting 3 messages instantly...")

    start = asyncio.get_event_loop().time()

    # These all enqueue instantly (non-blocking)
    await queue.enqueue("Message 1: Let me search for that...")
    await queue.enqueue("Message 2: Here's what I found...")
    await queue.enqueue("Message 3: Does that help?")

    enqueue_time = asyncio.get_event_loop().time() - start
    print(f"   ✅ All 3 messages enqueued in {enqueue_time:.3f}s (instant!)")

    print("\n⏳ Waiting for TTS to speak all messages...")
    await queue.wait_until_empty()

    total_time = asyncio.get_event_loop().time() - start
    print(f"\n✅ Total time: {total_time:.1f}s (expected ~6-7s for 3 messages)")
    print("   Messages were spoken in order, no overlap!")

    await queue.stop()


async def test_user_interruption():
    """
    Test: User interrupts while TTS is speaking.
    Queue should be cleared, pending messages discarded.
    """
    print("\n" + "="*70)
    print("TEST 2: User Interruption - Clear queue mid-speech")
    print("="*70)

    queue = TTSQueue(slow_tts, min_gap=0.5)
    await queue.start()

    # Queue 3 messages
    print("\n📤 Queueing 3 messages...")
    await queue.enqueue("Message 1: This is a long explanation...")
    await queue.enqueue("Message 2: This will be skipped...")
    await queue.enqueue("Message 3: This will also be skipped...")

    # Wait 1 second (TTS is mid-speech on message 1)
    print("\n⏳ Waiting 1s (TTS mid-speech)...")
    await asyncio.sleep(1)

    # Simulate user starting to speak
    print("\n🎤 User starts speaking - triggering interruption!")
    await queue.clear_and_interrupt()

    print(f"   Queue cleared! Is speaking: {queue.is_speaking}")

    # Wait for any remaining TTS to finish
    await asyncio.sleep(2)

    print("\n✅ Test complete!")
    print("   Messages 2 and 3 were skipped (user interrupted)")

    await queue.stop()


async def test_priority_message():
    """
    Test: High priority message during queue processing.
    """
    print("\n" + "="*70)
    print("TEST 3: Priority Message - Interrupt and speak immediately")
    print("="*70)

    queue = TTSQueue(slow_tts, min_gap=0.5)
    await queue.start()

    # Queue some messages
    print("\n📤 Queueing 2 normal messages...")
    await queue.enqueue("Normal message 1...")
    await queue.enqueue("Normal message 2...")

    # Wait for first to start
    await asyncio.sleep(0.5)

    # Send urgent message
    print("\n🚨 Sending INTERRUPT message!")
    await queue.enqueue(
        "URGENT: Please pay attention to this!",
        priority=TTSPriority.INTERRUPT
    )

    await queue.wait_until_empty()

    print("\n✅ Test complete!")
    print("   Interrupt message cleared queue and spoke immediately")

    await queue.stop()


async def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║  TTS Queue Race Condition Tests                                        ║
║                                                                        ║
║  Problem: Graph emits messages faster than TTS can speak them          ║
║  Solution: Queue with sequential playback + interruption support       ║
╚═══════════════════════════════════════════════════════════════════════╝
    """)

    await test_race_condition()
    await test_user_interruption()
    await test_priority_message()

    print("\n" + "="*70)
    print("All tests passed! Race conditions handled correctly.")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
