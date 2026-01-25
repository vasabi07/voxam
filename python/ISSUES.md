# Known Issues & Tasks

## Open Issues

### 1. Exam Agent Skips Questions When Advancing
**Status:** Fixed
**Priority:** Medium
**Date:** 2025-01-12
**Fixed:** 2026-01-16

**Description:**
During exam sessions, the agent sometimes skipped questions when advancing. Agent jumped from Question 1 directly to Question 3, skipping Question 2.

**Root Cause (Actual):**
In `realtime_exam.py`, each invocation created a fresh `ExamState` with `current_index=0`. This **overwrote** the checkpointed `current_index`, causing the state to reset.

The LLM was NOT at fault - the quality evaluation confirmed the LLM correctly handles tool arguments.

**Fix:**
1. Before invoking the graph, retrieve the saved state using `graph.get_state(config)`
2. Use the restored `current_index`, `current_question`, and `exam_started` values
3. Only pass new message, let other state fields be restored from checkpoint

**Code Change:**
```python
# BEFORE (buggy):
exam_state = ExamState(
    messages=[HumanMessage(content=full_transcript)],
    current_index=0,  # Always 0 - overwrites checkpoint!
    ...
)

# AFTER (fixed):
saved_state = exam_agent_graph.get_state(config)
current_index = saved_state.values.get("current_index", 0)  # Restored!
exam_state = ExamState(
    messages=[HumanMessage(content=full_transcript)],
    current_index=current_index,  # Preserved from checkpoint
    ...
)
```

**Files Modified:**
- `python/agents/realtime_exam.py`

---

### 2. Learn Agent Prematurely Ends Topic/Session
**Status:** Fixed
**Priority:** Medium
**Date:** 2025-01-12
**Fixed:** 2026-01-16

**Description:**
During learn sessions, the agent sometimes skipped topics or prematurely ended sessions.

**Root Cause (Actual):**
Same as Issue #1 - in `realtime_learn.py`, each invocation created a fresh `LearnState` with `current_topic_index=0`. This **overwrote** the checkpointed state, causing topics to reset.

**Fix:**
Applied same fixes as exam agent:
1. Added `trigger_greeting()` function called on participant connect
2. Retrieve saved state using `graph.get_state(config)` before invoking
3. Use restored `current_topic_index`, `current_topic`, `session_started` values

**Files Modified:**
- `python/agents/realtime_learn.py`

---

## Quality Evaluation Results

### LLM Quality Assessment - gpt-oss-120b (Cerebras)
**Status:** Completed
**Date:** 2026-01-15

**Summary:** gpt-oss-120b performs excellently for exam proctoring with 100% pass rate on core quality metrics.

**Test Results:**

| Category | Test | Result | Notes |
|----------|------|--------|-------|
| **EXAM Mode Compliance** | | | |
| | Hint refusal | ✅ PASS | "I cannot provide hints. Please state your answer." |
| | No teaching on wrong answer | ✅ PASS | "Answer recorded. Ready for the next question?" |
| | Response brevity (<100 words) | ✅ PASS | Average 7-15 words |
| | Accept letter-only MCQ answers | ✅ PASS | Accepts "B" without elaboration request |
| | Redirect off-topic questions | ✅ PASS | Redirects to exam focus |
| **LEARN Mode Compliance** | | | |
| | Provides hints when asked | ✅ PASS | Scaffolded Socratic hints |
| | Socratic dialogue | ✅ PASS | Probing questions, guides discovery |
| | Explains wrong answers | ✅ PASS | Engages and teaches without giving away |
| **Tool Call Accuracy** | | | |
| | advance_to_next_question on "next" | ✅ PASS | Correct tool + args |
| | Correct qp_id and current_index | ✅ PASS | Arguments match prompt context |
| | No premature tool call | ✅ PASS | Doesn't auto-advance after answer |
| **Greeting Flow** | | | |
| | Mentions question count | ✅ PASS | "This exam consists of 15 questions" |
| | Mentions duration | ✅ PASS | "30 minutes to complete it" |
| | Doesn't present question prematurely | ✅ PASS | Waits for confirmation |
| **Latency** | | | |
| | Response time | ✅ PASS | Avg: 0.46-0.71s, Max: 2.35s |

**Sample Responses:**

1. **EXAM Hint Refusal:** "I cannot provide hints. Please state your answer."
2. **EXAM Answer Recording:** "Answer recorded. Ready for the next question?"
3. **LEARN Hint Provision:** "Think about what the cell needs to keep everything running—especially activities that require a lot of energy. Which organelle is often called the 'powerhouse' of the cell?"
4. **Greeting:** "Welcome! This exam consists of 15 questions and you have 30 minutes to complete it. I will read each question clearly, one at a time. When you're ready for the next question, just say 'next.' Are you ready to begin?"

**Conclusion:** gpt-oss-120b is **suitable for production** exam proctoring. The model:
- Follows strict EXAM mode rules (no hints, no teaching)
- Provides excellent interactive tutoring in LEARN mode
- Makes accurate tool calls with correct arguments
- Has outstanding latency (<1s average)

**Known Issue:** The question skipping bug (Issue #1) may be caused by prompt context handling, not LLM quality. The LLM correctly interprets tool arguments from prompt context in isolated tests.

---

## Completed

### Greeting Bug Fix - Exam Agent
**Status:** Completed
**Date:** 2026-01-16

**Problem:** Agent skipped greeting on first turn. User had to speak first before receiving greeting.

**Root Cause:** In `realtime_exam.py`, the greeting was only triggered when `process_complete_transcript` was called (after user speech), not when the user connected to the room.

**Fix:**
1. Added `trigger_greeting()` async function that runs the agent with `[SESSION_START]` message
2. Call `trigger_greeting()` from `on_participant_connected` event handler
3. Track `greeting_sent` flag to prevent duplicate greetings
4. Set `exam_started=greeting_sent` for subsequent user messages

**Flow (After Fix):**
1. User connects to room
2. `on_participant_connected` triggers `trigger_greeting()`
3. Agent greets user with welcome message
4. User speaks
5. Agent processes speech with `exam_started=True`

Files modified:
- `python/agents/realtime_exam.py`

---

### Context Management for Voice Agents
**Status:** Completed
**Date:** 2025-01-12

Added three-tier memory architecture to exam and learn agents:
- Running summary (semantic memory)
- Message windowing (last 4 messages to LLM)
- Search tool for conversation history lookup

Files modified:
- `python/agents/exam_agent.py`
- `python/agents/learn_agent.py`

---

### RAG Quality Evaluation - Chat Agent
**Status:** Completed
**Date:** 2026-01-16

**Objective:** Evaluate retrieval accuracy for hybrid RAG with RRF fusion.

**Test Document:** `doc_ec96ce1c` - Chapter 6: Control and Coordination (Biology, 7 content blocks)

**Issues Found & Fixed:**

1. **NULL doc_id on ContentBlocks** - The `persist_to_neo4j` function wasn't setting `doc_id` property on ContentBlock nodes, only using it in the `block_id` prefix. This caused:
   - Duplicate content from multiple uploads appearing in results
   - Orphaned blocks with embeddings but no text_content
   - Vector search returning high-scoring blocks (0.82) that contributed nothing to context

   **Fix:** Updated blocks with `SET cb.doc_id = 'doc_ec96ce1c'` to enable proper filtering.

2. **Ghost blocks with NULL text_content** - Some older ingestion created blocks with `_section_` naming format that had embeddings but no text_content stored. These "phantom" blocks scored high in vector search but returned empty content.

   **Fix:** Cleaned up database, re-ingested with proper pipeline.

**Quality Results (After Cleanup):**

| Metric | Result | Notes |
|--------|--------|-------|
| Vector search accuracy | ✅ PASS | Top result scores 0.76-0.82 for relevant queries |
| Keyword search accuracy | ✅ PASS | Top result scores 1.7+ for exact matches |
| RRF fusion | ✅ PASS | Correctly combines vector + keyword rankings |
| Context retrieval | ✅ PASS | 7/7 test queries returned relevant content |
| Edge case handling | ✅ PASS | Irrelevant queries filtered, special chars handled |

**Sample Diagnostics:**
```
Query: "What is a reflex action?"
  Vector #1: block::1 (score: 0.766) - "6.1.1 What happens in Reflex Actions?"
  Keyword #1: block::1 (score: 1.765) - Same block
  Final RRF: 0.0325 - Correct content retrieved
```

**Recommendations:**
1. Fix `persist_to_neo4j` to always set `doc_id` property on ContentBlock nodes
2. Add validation in ingestion pipeline to ensure text_content is not NULL before embedding
3. Consider adding a cleanup job to remove orphaned/ghost blocks

**Files Created:**
- `tests/behavior/test_rag_quality.py` - Comprehensive RAG quality test suite (19 tests)
