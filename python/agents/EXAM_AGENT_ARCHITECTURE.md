# VOXAM Exam Agent - Architecture Breakdown

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXAM SESSION LIFECYCLE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Frontend (Next.js)                                                     │
│       │                                                                 │
│       ▼  POST /start-exam-session                                       │
│  ┌─────────┐                                                            │
│  │ api.py  │──► Creates LiveKit room + tokens                           │
│  └────┬────┘   Spawns realtime_exam.py as background task               │
│       │                                                                 │
│       ▼                                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    realtime_exam.py                              │   │
│  │  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐   │   │
│  │  │ Deepgram    │───►│ exam_agent   │───►│ TTS Queue +        │   │   │
│  │  │ STT (Flux)  │    │ (LangGraph)  │    │ Orpheus/Google TTS │   │   │
│  │  └─────────────┘    └──────────────┘    └────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. `api.py` - Session Orchestrator

**Entry point:** `POST /start-exam-session`

```python
class ExamSessionRequest:
    qp_id: str           # Question paper ID
    thread_id: str       # LangGraph conversation thread
    session_id: str      # Database tracking ID
    mode: str = "exam"   # "exam" or "learn"
    region: str = "orpheus"  # TTS provider
```

**Flow:**
1. Validates user credits (voice minutes)
2. Fetches QP from Postgres → caches to Redis
3. Creates unique LiveKit room
4. Spawns `realtime_exam.main()` as background task
5. Returns `room_name` + `token` to frontend

---

### 2. `realtime_exam.py` - Voice Handler (LiveKit Integration)

**Purpose:** Bridges voice I/O with the LangGraph agent

#### Key Components:

| Component | Responsibility |
|-----------|---------------|
| `connect_to_room()` | Joins LiveKit room as "exam-agent" |
| `publish_audio_track()` | Creates 48kHz mono audio source for TTS |
| `create_stt_handler_with_prosody()` | Deepgram Flux STT with turn timing |
| `TTSQueue` | Handles multi-step response sequencing |
| `monitor_credit_limit()` | Background task checking voice minutes |

#### Event Flow:

```
┌─────────────────────────────────────────────────────────────────┐
│                        VOICE LOOP                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Student speaks                                                 │
│       │                                                         │
│       ▼                                                         │
│  Deepgram Flux STT (streaming)                                  │
│       │                                                         │
│       │  Events: StartOfTurn → Update → EagerEndOfTurn →        │
│       │          TurnResumed → EndOfTurn                        │
│       │                                                         │
│       ▼  on_end_of_turn callback                                │
│  TurnMetadata { duration_ms, had_eager_eot, had_turn_resumed }  │
│       │                                                         │
│       ▼                                                         │
│  process_complete_transcript_with_prosody()                     │
│       │                                                         │
│       ├──► Is TTS speaking? → classify_with_prosody()           │
│       │         │                                               │
│       │         ├─ ACKNOWLEDGMENT ("okay") → ignore, continue   │
│       │         ├─ CANCEL ("stop") → clear queue                │
│       │         └─ NEW_INPUT → clear queue + process            │
│       │                                                         │
│       ▼                                                         │
│  exam_agent_graph.astream(state, config)                        │
│       │                                                         │
│       │  Streaming events:                                      │
│       │    - ToolMessage with [EMIT_THINKING] → speak NOW       │
│       │    - AIMessage with content → final response            │
│       │                                                         │
│       ▼                                                         │
│  tts_queue.enqueue(response) → TTS → LiveKit → Student hears    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Reconnection Handling:

```python
# When student reconnects:
1. Cancel reconnect timer (5-min grace period)
2. Restore state from Redis checkpoint
3. Speak: "Welcome back. We were on question X of Y. Ready to continue?"
```

---

### 3. `exam_agent.py` - LangGraph State Machine

**The brain of the exam conductor.**

#### State Schema:

```python
class State(MessagesState):
    thread_id: str
    qp_id: str
    current_index: int = 0
    current_question: Optional[dict]    # Cached question
    total_questions: Optional[int]
    exam_started: bool = False

    # Response metadata for UI
    response_type: Literal["question", "follow_up", "feedback", "instruction"]
    response_options: Optional[List[str]]  # MCQ options

    # Context management (long sessions)
    running_summary: Optional[str]
    summary_message_index: int = 0

    # Time tracking
    exam_start_time: Optional[float]
    question_start_time: Optional[float]
    time_per_question: Optional[dict]  # {index: {actual_secs, status, ...}}
    warned_5min, warned_2min, warned_1min: bool
```

#### Graph Structure:

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │  route_summarization()       │
            │  (Check if summary needed)   │
            └──────────────┬───────────────┘
                    ┌──────┴──────┐
                    │             │
                    ▼             ▼
          ┌──────────────┐  ┌───────────────────┐
          │ summarize    │  │                   │
          │ (Llama 8B)   │  │                   │
          └──────┬───────┘  │                   │
                 │          │                   │
                 └──────────►       agent       │◄────────┐
                            │   (GPT-OSS-120B)  │         │
                            └─────────┬─────────┘         │
                                      │                   │
                           should_continue()              │
                          ┌───────────┴───────────┐       │
                          │                       │       │
                          ▼                       ▼       │
                    ┌───────────┐        ┌──────────────┐ │
                    │   tools   │        │check_complete│ │
                    │(ToolNode) │        └──────┬───────┘ │
                    └─────┬─────┘               │         │
                          │                     │         │
                          ▼                     ▼         │
                  ┌───────────────┐       ┌──────────┐    │
                  │process_resp   │       │ cleanup  │    │
                  │(update state) │       │(trigger  │    │
                  └───────┬───────┘       │correction)    │
                          │               └────┬─────┘    │
                          │                    │          │
                          └────────────────────┼──────────┘
                                               ▼
                                            END
```

#### Tools Available:

| Tool | Purpose | When Used |
|------|---------|-----------|
| `emit_thinking(msg)` | Speak immediately (acknowledgment) | Before other tools |
| `advance_to_next_question(qp_id, idx, reason)` | Move to next question | Student says "next", finishes answer |
| `get_rules(topics)` | Load conduct rules from `.md` files | Edge cases (hints, off-topic) |
| `get_time_remaining(start, duration)` | Calculate remaining time | "How much time left?" |
| `search_conversation_history(query, thread_id)` | Find earlier exchanges | "What did you say about Q2?" |

#### System Prompts:

**GREETING_PROMPT** (exam_started=False):
```
- Welcome student
- State: X questions, Y minutes
- Brief rules: "Say 'next' to continue"
- Wait for confirmation
```

**EXAM_MODE_PROMPT** (exam_started=True):
```
STRICT RULES:
- NO discussions, hints, or teaching
- NO feedback on answer quality
- FORMAL, neutral tone

WORKFLOW:
1. Simple answer → "Answer recorded. Ready for next?"
2. "Next" → emit_thinking() → advance_to_next_question() → read question
3. Time query → get_time_remaining()
4. Edge case → get_rules(["edge_cases"])
```

---

### 4. `lib/tts_queue.py` - Response Sequencing

**Problem solved:** Graph emits multiple messages rapidly, but TTS takes seconds.

```
Without queue:    Message 1 ──────────▶ TTS (3s)
                  Message 2 ──────────▶ TTS (overlaps!) ❌

With queue:       Message 1 ──► Queue ──► TTS (3s) ──► done
                  Message 2 ──► Queue ─────────────────► TTS (2s) ✅
```

#### Interruption Classification:

```python
classify_with_prosody(transcript, metadata) → InterruptionIntent
```

| Duration | Keywords | Intent |
|----------|----------|--------|
| <800ms | "okay", "sure" | ACKNOWLEDGMENT (ignore) |
| <800ms | "stop", "wait" | CANCEL (clear queue) |
| <1500ms | Check patterns | Keyword-based |
| >3000ms | Any | NEW_INPUT (process) |

---

### 5. Context Management (Long Sessions)

**Thresholds:**
- Trigger summarization: 12+ unsummarized messages OR 5000+ chars
- Pass to LLM: Only last 4 messages (voice has short turns)

**Running Summary Example:**
```
Q1: Asked about photosynthesis, student answered correctly
Q2: Asked about cellular respiration, student requested repeat, then answered
Q3: Currently on this question (mitochondria function)
```

---

### 6. Time Tracking

```python
time_per_question[index] = {
    "actual_secs": 45.2,
    "expected_secs": 300,  # 5 min
    "status": "rushed" | "normal" | "struggled",
    "completion_status": "answered" | "skipped" | "partial",
    "difficulty": "basic" | "intermediate" | "advanced",
}
```

**Warnings:** 5 min, 2 min, 1 min remaining

---

### 7. Data Flow Summary

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           DATA STORES                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Redis                                                                   │
│  ├── qp:{qp_id}:questions  → Cached question paper (4hr TTL)            │
│  └── LangGraph checkpointer → Conversation state (thread_id)            │
│                                                                          │
│  Postgres (Supabase)                                                     │
│  ├── ExamSession  → status, totalConnectedSeconds, lastConnectedAt      │
│  ├── QuestionPaper → questions JSON, status                             │
│  └── CorrectionReport → score, grade, feedback (after exam)             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Key Behaviors

### 1. Two-Step Response Pattern
```
Student: "What's the next question?"
Agent: emit_thinking("Sure, moving on...") → [SPEAKS IMMEDIATELY]
       advance_to_next_question() → [TOOL EXECUTES]
       "Question 3: Explain the process of..." → [FINAL RESPONSE]
```

### 2. Greeting Flow
```
[SESSION_START] marker → GREETING_PROMPT →
"Welcome! This exam has 10 questions..."
→ Wait for "I'm ready" → EXAM_MODE_PROMPT + first question
```

### 3. Credit Monitoring
- Checks every 60 seconds
- Warns at 2 minutes remaining
- Force-ends at 0 minutes
- Deducts actual connected time (tracks disconnects)

### 4. Reconnection
- 5-minute grace period
- Restores state from checkpoint
- Provides context: "We were on question X..."

---

## `thread_id` vs `session_id`

| | `thread_id` | `session_id` |
|---|-------------|--------------|
| **Purpose** | LangGraph conversation persistence | Database record tracking |
| **Stored in** | Redis (LangGraph checkpointer) | Postgres (`ExamSession` table) |
| **Contains** | Conversation messages, agent state | Credits used, timestamps, status |
| **Pattern** | `{user_id}:{doc_id}` | UUID from Prisma |
| **Used for** | Resuming conversation after reconnect | Billing, analytics, correction reports |

**Could be simplified:** Use `session_id` as `thread_id` to reduce complexity.

---

## Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `realtime_exam.py` | 679 | Voice I/O, LiveKit, credit tracking |
| `exam_agent.py` | 908 | LangGraph state machine, prompts, tools |
| `lib/tts_queue.py` | 446 | Response sequencing, interruption handling |
| `realtime_base.py` | 569 | Shared TTS/STT utilities, Orpheus integration |
| `agents/rules/*.md` | - | Behavior rules for edge cases |

---

## Potential Improvements

1. **Simplify IDs** - Use `session_id` as `thread_id`
2. **Streaming TTS** - Stream audio chunks as LLM generates (lower TTFB)
3. **Better interruption** - Use LLM for ambiguous cases
4. **Image questions** - Support image display via data channel
5. **Adaptive pacing** - Adjust based on student's time_per_question patterns
