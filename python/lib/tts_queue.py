"""
TTS Queue - Handles race conditions for multi-step voice responses.

Problem:
  - Graph emits message 1 → TTS starts speaking (3 seconds)
  - Graph emits message 2 → TTS still speaking message 1!
  - Without queue: messages could overlap or get lost

Solution:
  - TTS runs in its own task, consuming from a queue
  - Graph nodes just enqueue messages (non-blocking)
  - Messages are spoken in order, with proper timing

Features:
  - Sequential playback (no overlapping)
  - Optional minimum delay between messages
  - User interruption support (clear queue)
  - Intent classification for acknowledgments vs interruptions
  - Graceful shutdown
"""

import asyncio
from dataclasses import dataclass
from typing import Callable, Optional, Awaitable
from enum import Enum


# ============================================================
# INTERRUPTION INTENT CLASSIFICATION
# ============================================================

class InterruptionIntent(Enum):
    ACKNOWLEDGMENT = "acknowledgment"  # "okay", "sure" → keep queue
    CANCEL = "cancel"                  # "stop", "wait" → clear queue
    NEW_INPUT = "new_input"            # new question → clear queue


# Keyword patterns for fast classification (no LLM needed)
ACKNOWLEDGMENT_PATTERNS = {
    "okay", "ok", "alright", "sure", "go ahead", "yes", "yeah", "yep",
    "uh huh", "mm hmm", "mhm", "got it", "sounds good", "please",
    "go on", "continue", "that's fine", "fine", "cool", "great"
}

CANCEL_PATTERNS = {
    "stop", "wait", "hold on", "never mind", "nevermind", "cancel",
    "forget it", "nope", "dont", "actually no", "skip",
    "pause", "hang on"
}

# These require exact match (not substring match) to avoid false positives
CANCEL_EXACT_PATTERNS = {"no"}


def classify_interruption(transcript: str) -> InterruptionIntent:
    """
    Fast keyword-based classification of user interruption intent.
    No LLM call needed - runs in <1ms.

    Args:
        transcript: What the user said (from STT)

    Returns:
        InterruptionIntent indicating whether to keep or clear queue
    """
    text = transcript.lower().strip()

    # Remove punctuation for matching
    text_clean = ''.join(c for c in text if c.isalnum() or c.isspace())

    # Check for exact matches first (short responses)
    if text_clean in ACKNOWLEDGMENT_PATTERNS:
        return InterruptionIntent.ACKNOWLEDGMENT

    if text_clean in CANCEL_PATTERNS:
        return InterruptionIntent.CANCEL

    if text_clean in CANCEL_EXACT_PATTERNS:
        return InterruptionIntent.CANCEL

    # Check for pattern containment (phrases)
    for pattern in ACKNOWLEDGMENT_PATTERNS:
        if pattern in text_clean and len(text_clean) < 20:
            return InterruptionIntent.ACKNOWLEDGMENT

    # Only check cancel patterns that are safe for substring matching
    for pattern in CANCEL_PATTERNS:
        # Use word boundary check to avoid matching "no" in "another"
        words = text_clean.split()
        if pattern in words or (len(pattern.split()) > 1 and pattern in text_clean):
            return InterruptionIntent.CANCEL

    # Longer responses (>5 words) are likely new questions
    word_count = len(text_clean.split())
    if word_count > 5:
        return InterruptionIntent.NEW_INPUT

    # Default: treat as new input (safer to process than ignore)
    return InterruptionIntent.NEW_INPUT


# ============================================================
# PROSODY-ENHANCED CLASSIFICATION
# ============================================================

@dataclass
class TurnMetadata:
    """Metadata from Deepgram Flux about the user's turn."""
    duration_ms: float  # Time from StartOfTurn to EndOfTurn
    had_eager_eot: bool = False  # True if EagerEndOfTurn fired (user paused briefly)
    had_turn_resumed: bool = False  # True if TurnResumed fired (user continued)
    word_count: int = 0  # Number of words in transcript


def classify_with_prosody(
    transcript: str,
    metadata: TurnMetadata
) -> InterruptionIntent:
    """
    Enhanced classification combining text + acoustic/prosodic signals.

    Prosody signals from Deepgram Flux:
    - Turn duration: Short (~0.5s) = filler/acknowledgment, Long (2s+) = real input
    - EagerEndOfTurn: User paused briefly (might be thinking)
    - TurnResumed: User continued after pause (don't interrupt)

    Args:
        transcript: What the user said (from STT)
        metadata: Turn timing and event data from Deepgram Flux

    Returns:
        InterruptionIntent indicating whether to keep or clear queue
    """
    text_lower = transcript.lower().strip()
    text_clean = ''.join(c for c in text_lower if c.isalnum() or c.isspace())

    # ============================================================
    # PROSODY-BASED FAST PATH
    # ============================================================

    # Very short utterance (<800ms) + acknowledgment keywords = definitely acknowledgment
    # This catches "okay", "sure", "mhm" said quickly
    if metadata.duration_ms < 800:
        if text_clean in ACKNOWLEDGMENT_PATTERNS:
            return InterruptionIntent.ACKNOWLEDGMENT
        # Very short + cancel word = real cancel (said with urgency)
        words = text_clean.split()
        if any(w in CANCEL_PATTERNS or w in CANCEL_EXACT_PATTERNS for w in words):
            return InterruptionIntent.CANCEL

    # Short utterance (800ms-1500ms) - could be either
    # Use keyword matching with prosody as tiebreaker
    if metadata.duration_ms < 1500:
        # Check acknowledgment first (more common during TTS)
        if text_clean in ACKNOWLEDGMENT_PATTERNS:
            return InterruptionIntent.ACKNOWLEDGMENT
        # Cancel patterns
        words = text_clean.split()
        if any(w in CANCEL_PATTERNS or w in CANCEL_EXACT_PATTERNS for w in words):
            return InterruptionIntent.CANCEL

    # Medium utterance (1500ms-3000ms) - likely a short question or comment
    # If EagerEndOfTurn fired and no TurnResumed, user finished naturally
    if 1500 <= metadata.duration_ms < 3000:
        # Still check for acknowledgment patterns (said more slowly)
        if text_clean in ACKNOWLEDGMENT_PATTERNS and not metadata.had_turn_resumed:
            return InterruptionIntent.ACKNOWLEDGMENT

    # Longer utterance (3s+) = definitely new input, regardless of keywords
    if metadata.duration_ms >= 3000:
        return InterruptionIntent.NEW_INPUT

    # User continued after pause (TurnResumed) = they're formulating a thought
    # Treat as new input even if short
    if metadata.had_turn_resumed and metadata.word_count > 3:
        return InterruptionIntent.NEW_INPUT

    # ============================================================
    # FALL BACK TO KEYWORD-ONLY CLASSIFICATION
    # ============================================================
    return classify_interruption(transcript)


class TTSPriority(Enum):
    NORMAL = 1
    HIGH = 2      # Skip ahead in queue
    INTERRUPT = 3  # Clear queue and speak immediately


@dataclass
class TTSMessage:
    text: str
    priority: TTSPriority = TTSPriority.NORMAL
    min_delay_after: float = 0.3  # Min seconds of silence after this message


class TTSQueue:
    """
    Async queue for TTS messages with race condition handling.

    Usage:
        tts_queue = TTSQueue(speak_function)
        await tts_queue.start()

        # From graph nodes (non-blocking):
        await tts_queue.enqueue("Let me search...")
        await tts_queue.enqueue("Here's what I found...")

        # Wait for all messages to be spoken:
        await tts_queue.wait_until_empty()
    """

    def __init__(
        self,
        speak_fn: Callable[[str], Awaitable[float]],  # Returns duration spoken
        min_gap: float = 0.3,  # Minimum gap between messages
    ):
        self.speak_fn = speak_fn
        self.min_gap = min_gap
        self.queue: asyncio.Queue[TTSMessage | None] = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.is_speaking = False
        self.current_message: Optional[str] = None
        self._empty_event = asyncio.Event()
        self._empty_event.set()  # Start as empty

    async def start(self):
        """Start the TTS worker task."""
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self._worker())
            print("🔊 TTS Queue started")

    async def stop(self):
        """Stop the TTS worker gracefully."""
        if self.worker_task:
            await self.queue.put(None)  # Poison pill
            await self.worker_task
            self.worker_task = None
            print("🔇 TTS Queue stopped")

    async def enqueue(
        self,
        text: str,
        priority: TTSPriority = TTSPriority.NORMAL,
        min_delay_after: float = 0.3
    ):
        """
        Add message to TTS queue (non-blocking).

        This is safe to call from graph nodes - it returns immediately.
        The message will be spoken when it's its turn in the queue.
        """
        if not text.strip():
            return

        msg = TTSMessage(text=text, priority=priority, min_delay_after=min_delay_after)

        if priority == TTSPriority.INTERRUPT:
            # Clear existing queue and add this message
            await self._clear_queue()

        self._empty_event.clear()  # Queue is no longer empty
        await self.queue.put(msg)

        print(f"📥 Queued: '{text[:50]}...' (queue size: {self.queue.qsize()})")

    async def wait_until_empty(self, timeout: float = 30.0):
        """Wait until all queued messages have been spoken."""
        try:
            await asyncio.wait_for(self._empty_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            print(f"⚠️ TTS queue wait timed out after {timeout}s")

    async def clear_and_interrupt(self, interrupt_message: Optional[str] = None):
        """
        Clear queue and optionally speak an interrupt message.
        Use when user starts speaking (barge-in).
        """
        await self._clear_queue()

        if interrupt_message:
            await self.enqueue(interrupt_message, priority=TTSPriority.INTERRUPT)

    async def _clear_queue(self):
        """Clear all pending messages."""
        cleared = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                cleared += 1
            except asyncio.QueueEmpty:
                break

        if cleared > 0:
            print(f"🗑️ Cleared {cleared} queued messages")

    async def _worker(self):
        """Background task that processes TTS queue."""
        print("🎙️ TTS worker started")

        while True:
            try:
                # Get next message (blocks until available)
                msg = await self.queue.get()

                # Poison pill = shutdown
                if msg is None:
                    break

                # Mark as speaking
                self.is_speaking = True
                self.current_message = msg.text

                try:
                    # Actually speak (streams audio to LiveKit)
                    duration = await self.speak_fn(msg.text)

                    # IMPORTANT: speak_fn returns when STREAMING completes,
                    # but audio PLAYBACK takes longer. We must wait for playback
                    # so is_speaking stays True while student hears the audio.
                    if duration > 0:
                        await asyncio.sleep(duration)

                    # Then add gap between messages for natural pacing
                    gap = max(self.min_gap, msg.min_delay_after)
                    if gap > 0:
                        await asyncio.sleep(gap)

                except Exception as e:
                    print(f"❌ TTS error: {e}")

                finally:
                    self.is_speaking = False
                    self.current_message = None
                    self.queue.task_done()

                # Check if queue is now empty
                if self.queue.empty():
                    self._empty_event.set()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ TTS worker error: {e}")

        print("🎙️ TTS worker stopped")


# ============================================================
# INTEGRATION HELPER
# ============================================================

class StreamingTTSHandler:
    """
    Helper class for integrating TTS queue with LangGraph streaming.

    Usage:
        handler = StreamingTTSHandler(speak_function)
        await handler.start()

        async for event in graph.astream(state):
            await handler.process_graph_event(event, spoken_count)

        await handler.finish()
    """

    def __init__(self, speak_fn: Callable[[str], Awaitable[float]]):
        self.tts_queue = TTSQueue(speak_fn)
        self.spoken_count = 0

    async def start(self):
        await self.tts_queue.start()

    async def process_graph_event(self, event: dict, base_message_count: int = 1):
        """
        Process a graph streaming event and queue any new AI messages.

        Args:
            event: The event from graph.astream()
            base_message_count: Number of messages to skip (e.g., human message = 1)
        """
        from langchain_core.messages import AIMessage

        for node_name, state_update in event.items():
            if "messages" in state_update:
                messages = state_update["messages"]
                new_messages = messages[base_message_count + self.spoken_count:]

                for msg in new_messages:
                    if isinstance(msg, AIMessage) and msg.content:
                        print(f"🆕 New message from {node_name}")
                        await self.tts_queue.enqueue(msg.content)
                        self.spoken_count += 1

    async def finish(self):
        """Wait for all messages to be spoken, then cleanup."""
        await self.tts_queue.wait_until_empty()
        await self.tts_queue.stop()

    def reset(self):
        """Reset for next conversation turn."""
        self.spoken_count = 0


# ============================================================
# EXAMPLE USAGE
# ============================================================

async def example_usage():
    """Example showing how to use TTSQueue with graph streaming."""

    # Mock speak function
    async def mock_speak(text: str) -> float:
        duration = len(text.split()) * 0.1  # Rough estimate
        print(f"🔊 Speaking: {text[:50]}...")
        await asyncio.sleep(duration)
        print(f"   ✅ Done ({duration:.1f}s)")
        return duration

    # Create handler
    handler = StreamingTTSHandler(mock_speak)
    await handler.start()

    # Simulate rapid message emission (like fast web search)
    print("\n📤 Simulating rapid message emission...")

    await handler.tts_queue.enqueue("Let me search for that information...")
    await handler.tts_queue.enqueue("Here's what I found: quantum effects in photosynthesis...")
    await handler.tts_queue.enqueue("Does that help answer your question?")

    print("\n⏳ Messages queued, waiting for TTS to complete...")
    await handler.finish()

    print("\n✅ All messages spoken in order!")


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════╗
║  TTS Queue - Race Condition Handling                           ║
║                                                                ║
║  Watch how messages are queued instantly but spoken in order:  ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    asyncio.run(example_usage())
