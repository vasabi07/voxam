# Technical Debt & Future Improvements

## High Priority

### 1. Chat Agent: Switch to Redis Checkpointer
**File:** `python/agents/chat_agent.py`
**Current:** `MemorySaver` (in-memory, lost on restart)
**Target:** `RedisSaver` (persistent across restarts)

**Why:**
- Chat history lost when server restarts
- No cross-session persistence for users
- Already using Redis for exam_agent, should be consistent

**When to do:**
- [ ] When users complain about lost chat history
- [ ] When scaling to multiple server instances
- [ ] When hitting 500+ active users

**How:**
```python
# Replace in create_chat_graph()
# From:
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)

# To:
from langgraph.checkpoint.redis import RedisSaver
REDIS_URI = "redis://localhost:6379"
with RedisSaver.from_conn_string(REDIS_URI) as checkpointer:
    checkpointer.setup()
graph = workflow.compile(checkpointer=checkpointer)
```

**Note:** CopilotKit's ag_ui_langgraph may have async compatibility issues with RedisSaver. Test thoroughly.

---

## Medium Priority

### 2. Document-Scoped Retrieval
**File:** `python/agents/chat_agent.py`, `python/retrieval.py`
**Current:** Retrieves from ALL documents in Neo4j
**Target:** Filter by user's active document (`doc_id`)

### 3. Model Cost Optimization
**File:** `python/agents/chat_agent.py`
**Current:** Using `gpt-4o-mini` for rewriter and generator
**Target:** Consider `gemini-2.0-flash` for cost savings (62% cheaper, 7x faster)

---

## Low Priority

### 4. RAG Evaluation Metrics
Add RAGAS evaluation for retrieval quality monitoring.

### 5. Reranking Layer
Add cross-encoder reranking after hybrid search for better precision.

---

*Last updated: November 29, 2025*
