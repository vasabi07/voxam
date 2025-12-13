# Python Concurrency: Async, Threads, Processes & vCPUs

A practical guide using Voxam as a real-world example.

---

## Part 1: The Problem - Why Do We Need Concurrency?

Your Voxam server needs to handle **multiple students doing voice exams at the same time**. Without concurrency:

```
Student A speaks → Server processes → 3 seconds
Student B speaks → WAITS for A → then 3 seconds
Student C speaks → WAITS for A,B → then 3 seconds
```

**Total: 9 seconds for 3 students.** Unacceptable.

With concurrency, all 3 should happen in ~3 seconds.

---

## Part 2: Understanding the CPU

### What is a vCPU?

A **virtual CPU** is a slice of a physical processor core that your virtual machine (CCX23) can use.

```
Physical Server (Hetzner data center)
┌─────────────────────────────────────────────────────┐
│  Physical CPU: 32 cores                              │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ... ┌─────┐        │
│  │Core1│ │Core2│ │Core3│ │Core4│     │Core32│       │
│  └─────┘ └─────┘ └─────┘ └─────┘     └─────┘        │
└─────────────────────────────────────────────────────┘
        │
        ▼ Hetzner allocates to YOU
┌─────────────────────────┐
│  CCX23 (Your VM)        │
│  vCPUs: 4               │
│  ┌─────┐ ┌─────┐        │
│  │vCPU1│ │vCPU2│        │
│  │vCPU3│ │vCPU4│        │
│  └─────┘ └─────┘        │
└─────────────────────────┘
```

**4 vCPUs = You can run 4 things truly in parallel.**

---

## Part 3: Types of Work

Before choosing a concurrency model, understand your workload:

### I/O-Bound Work (Most of Voxam)

Work that **waits for external systems**:

```python
# Waiting for network response - CPU is IDLE during this
response = await http_client.get("https://api.deepgram.com/...")  # 200ms wait
result = await redis.get("session:123")  # 2ms wait
```

**CPU usage: ~0%** during the wait. The program is just waiting.

### CPU-Bound Work (Some of Voxam)

Work that **requires actual computation**:

```python
# CPU is BUSY doing math
audio_bytes = encode_pcm_to_wav(raw_audio)  # CPU crunching numbers
embeddings = compute_similarity(vector1, vector2)  # Math operations
```

**CPU usage: 100%** during computation.

### Voxam's Workload Mix

| Operation | Type | Time | CPU Usage |
|-----------|------|------|-----------|
| Deepgram STT | I/O | 50-200ms | ~0% |
| Cerebras LLM | I/O | 100-500ms | ~0% |
| Google TTS | I/O | 200-500ms | ~0% |
| LiveKit audio | I/O | continuous | ~0% |
| Audio encoding | CPU | 10-50ms | 100% |
| JSON parsing | CPU | 1-5ms | 100% |

**Voxam is 95% I/O-bound.** This matters for choosing concurrency model.

---

## Part 4: Concurrency Models

### Option 1: Asyncio (What Voxam Uses)

**Concept:** One thread handles many tasks by switching between them during I/O waits.

```
Single Thread, Single Process
┌─────────────────────────────────────────────────────┐
│                    Event Loop                        │
│  ┌─────────────────────────────────────────────────┐ │
│  │ Task A: await deepgram() ──┐                    │ │
│  │ Task B: await livekit()  ──┼── All waiting      │ │
│  │ Task C: await cerebras() ──┘   for I/O          │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**How it works:**

```python
# file:///Users/vasanth/voxam/python/agents/realtime.py

async def handle_student_audio(audio_stream):
    async for event in audio_stream:
        # While waiting for next audio frame, other tasks run
        await process_audio(event.frame)

async def process_multiple_students():
    # All 3 run "concurrently" on ONE thread
    await asyncio.gather(
        handle_student_audio(student_a),
        handle_student_audio(student_b),
        handle_student_audio(student_c),
    )
```

**Pros:**
- Very efficient for I/O (thousands of connections on 1 thread)
- Low memory (no thread/process overhead)
- No race conditions (single thread)

**Cons:**
- CPU-bound work BLOCKS everything
- Only uses 1 CPU core

---

### Option 2: Threading

**Concept:** Multiple threads in one process, share memory.

```
Single Process, Multiple Threads
┌─────────────────────────────────────────────────────┐
│  Process (shares memory)                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│  │Thread 1 │ │Thread 2 │ │Thread 3 │ │Thread 4 │    │
│  │Student A│ │Student B│ │Student C│ │Student D│    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
└─────────────────────────────────────────────────────┘
```

**Python's Problem: The GIL**

```
Global Interpreter Lock (GIL)
┌─────────────────────────────────────────────────────┐
│  Only ONE thread can execute Python code at a time! │
│                                                      │
│  Thread 1: RUNNING   →  Thread 1: waiting           │
│  Thread 2: blocked      Thread 2: RUNNING           │
│  Thread 3: blocked      Thread 3: blocked           │
└─────────────────────────────────────────────────────┘
```

Even with 4 threads, only 1 runs Python at a time.

**When threads help:**
- I/O operations (GIL is released during I/O)
- Calling C libraries (GIL is released)

**Voxam uses ThreadPoolExecutor for this:**

```python
# file:///Users/vasanth/voxam/python/agents/realtime.py
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

# TTS is a blocking C library call - runs in thread, releases GIL
def blocking_tts():
    return tts_client.synthesize_speech(...)

# Run blocking call without blocking the event loop
result = await asyncio.get_event_loop().run_in_executor(
    executor, 
    blocking_tts
)
```

---

### Option 3: Multiprocessing (Uvicorn Workers)

**Concept:** Separate Python processes, each with own memory and GIL.

```
Multiple Processes (TRUE parallelism)
┌─────────────────┐ ┌─────────────────┐
│  Process 1      │ │  Process 2      │
│  (own GIL)      │ │  (own GIL)      │
│  ┌───────────┐  │ │  ┌───────────┐  │
│  │Event Loop │  │ │  │Event Loop │  │
│  │Student A  │  │ │  │Student B  │  │
│  └───────────┘  │ │  └───────────┘  │
└─────────────────┘ └─────────────────┘
        │                   │
        ▼                   ▼
     vCPU 1              vCPU 2
```

**Uvicorn workers = multiprocessing:**

```bash
# Starts 4 separate Python processes
uvicorn api:app --workers 4
```

Each worker:
- Has its own memory space
- Has its own GIL
- Can run on a different CPU core
- Handles different requests

**This is TRUE parallelism** - 4 TTS calls happen on 4 CPUs simultaneously.

---

## Part 5: Putting It Together - Voxam Architecture

### Current Setup (1 worker)

```
┌─────────────────────────────────────────────────────┐
│  Uvicorn (1 worker)                                  │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Python Process                                 │ │
│  │  ┌─────────────────────────────────────────┐   │ │
│  │  │         asyncio Event Loop              │   │ │
│  │  │  ┌─────────────────────────────────┐    │   │ │
│  │  │  │ Student A: exam session        │    │   │ │
│  │  │  │ Student B: exam session        │    │   │ │
│  │  │  │ Student C: exam session        │    │   │ │
│  │  │  └─────────────────────────────────┘    │   │ │
│  │  └─────────────────────────────────────────┘   │ │
│  │                                                 │ │
│  │  ┌─────────────────────────────────────────┐   │ │
│  │  │      ThreadPoolExecutor                 │   │ │
│  │  │  (for blocking TTS calls)               │   │ │
│  │  └─────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Uses 1 vCPU** for Python, other vCPUs for Redis/Neo4j.

### Scaled Setup (4 workers)

```
┌─────────────────────────────────────────────────────┐
│  Uvicorn (4 workers)                                 │
│  ┌───────────┐ ┌───────────┐                        │
│  │ Worker 1  │ │ Worker 2  │                        │
│  │ Student A │ │ Student C │  ← Parallel on         │
│  │ Student B │ │ Student D │    different CPUs      │
│  └───────────┘ └───────────┘                        │
│  ┌───────────┐ ┌───────────┐                        │
│  │ Worker 3  │ │ Worker 4  │                        │
│  │ Student E │ │ Student G │                        │
│  │ Student F │ │ Student H │                        │
│  └───────────┘ └───────────┘                        │
└─────────────────────────────────────────────────────┘
```

**Uses 4 vCPUs** for Python, true parallelism for TTS.

---

## Part 6: Decision Framework

### When to Use What

| Workload | Best Approach | Why |
|----------|---------------|-----|
| Many I/O tasks | asyncio | Low overhead, high concurrency |
| Blocking library | ThreadPoolExecutor | Release GIL during call |
| CPU-heavy tasks | multiprocessing (workers) | True parallelism |
| Need to scale | Add workers | Each worker = more capacity |

### Practical Rules

1. **Start with asyncio + ThreadPoolExecutor** (current Voxam)
2. **Add workers when:** CPU > 70% sustained
3. **Use 2 workers** for sweet spot on 4 vCPU
4. **Use 4 workers** only if CPU is the bottleneck, not memory

---

## Part 7: Real Voxam Example Trace

What happens when Student A speaks:

```
Time 0ms:   LiveKit sends audio frame
            → asyncio receives (no CPU, just I/O)
            
Time 1ms:   Forward to Deepgram WebSocket
            → asyncio sends (no CPU, just I/O)
            → Event loop handles Student B while waiting
            
Time 200ms: Deepgram returns transcript
            → asyncio receives (no CPU)
            
Time 201ms: Call Cerebras LLM
            → asyncio sends HTTP request (no CPU)
            → Event loop handles Student C while waiting
            
Time 500ms: LLM returns response
            → asyncio receives (no CPU)
            
Time 501ms: Call Google TTS (BLOCKING!)
            → ThreadPoolExecutor runs in separate thread
            → GIL released, event loop continues
            → Students B,C handled during this
            
Time 800ms: TTS audio ready
            → Send to LiveKit (no CPU)
            
Total CPU time: ~10ms
Total wall time: 800ms
```

**asyncio efficiently handled 3 students with just 10ms of actual CPU work.**

---

## Summary Cheat Sheet

| Concept | What It Is | When to Use |
|---------|------------|-------------|
| **vCPU** | Virtual CPU core | More vCPUs = more parallel capacity |
| **asyncio** | Concurrent I/O on 1 thread | Default for I/O-heavy apps |
| **GIL** | Python's lock | Limits threading for CPU work |
| **ThreadPoolExecutor** | Run blocking code in threads | For blocking libraries |
| **Workers** | Separate Python processes | Scale CPU-bound work |
| **I/O-bound** | Waiting for network/disk | Use asyncio |
| **CPU-bound** | Math/encoding | Use workers/processes |
