from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.checkpoint.redis import RedisSaver
from dotenv import load_dotenv
from typing import List, Literal, Optional
from redis import Redis
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
import time
import os
from pathlib import Path

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Rules directory for exam agent character/behavior
RULES_DIR = Path(__file__).parent / "rules"

# Context Management Thresholds
SUMMARIZATION_TRIGGER_THRESHOLD = 12  # Trigger when unsummarized messages exceed this
SUMMARIZATION_CHAR_THRESHOLD = 5000   # Or when unsummarized chars exceed this (~1250 tokens)
CONTEXT_MESSAGES_TO_LLM = 4           # Only pass last N messages to LLM (voice has short turns)

class State(MessagesState):
    thread_id: str
    qp_id: str
    user_id: Optional[str] = None              # User taking the exam
    current_index: int = 0
    duration_minutes: int = None
    # Optimizations: cache current question to avoid tool calls
    current_question: Optional[dict] = None    # {text, options, context, etc.}
    total_questions: Optional[int] = None      # For completion check without Redis
    exam_started: bool = False                 # Has first question been asked?
    correction_task_id: Optional[str] = None   # Celery task ID for correction

    # Response metadata for data channel (multimodal UI)
    response_type: Optional[Literal["question", "follow_up", "feedback", "instruction", "thinking"]] = None
    response_options: Optional[List[str]] = None  # MCQ options to display in UI
    # V1.5: Add response_image_url when image support is ready

    # Context Management Fields (running summary for long sessions)
    running_summary: Optional[str] = None          # Running summary of session progress
    summary_message_index: int = 0                 # Index up to which messages are summarized

    # Time Tracking Fields
    exam_start_time: Optional[float] = None       # Unix timestamp when exam started
    question_start_time: Optional[float] = None   # When current question was presented
    time_per_question: Optional[dict] = None      # {index: {actual_secs, expected_secs, status, ...}}

    # Time warnings (prevent repeat warnings)
    warned_5min: bool = False
    warned_2min: bool = False
    warned_1min: bool = False

    # Reconnection tracking
    is_reconnection: bool = False                 # True if resuming from checkpoint



#redis initialization
REDIS_URI = "redis://localhost:6379"
checkpointer = None
redis_client = None
try:
    with RedisSaver.from_conn_string(REDIS_URI) as _checkpointer:
        _checkpointer.setup()
        checkpointer = _checkpointer
except Exception as e:
    print(f"[ERROR] Could not connect to Redis at {REDIS_URI}: {e}")
    exit(1)



#tool nodes


# Redis client
r = Redis(host="localhost", port=6379, decode_responses=True)

@tool
def advance_to_next_question(qp_id: str, current_index: int, reason: str = "answered") -> dict:
    """
    Advance to the next question in the exam.
    Call this when ready to move to the next question.

    Args:
        qp_id: Question paper ID
        current_index: Current question index
        reason: Why moving on:
            - "answered" - Student provided an answer
            - "skipped" - Student explicitly skipped (said "skip", "I don't know", "next" without answering)
            - "partial" - Student gave incomplete answer and wants to move on
    """
    key = f"qp:{qp_id}:questions"
    try:
        next_index = current_index + 1
        questions = r.json().get(key)

        if not questions or not isinstance(questions, list):
            return {"done": True, "error": "Question paper not found", "previous_question_status": reason}

        if next_index >= len(questions):
            return {"done": True, "message": "All questions completed. Exam finished.", "previous_question_status": reason}

        q = questions[next_index]
        return {
            "done": False,
            "new_index": next_index,
            "previous_question_status": reason,  # For transcript + time_per_question
            "question": {
                "text": q.get('text', ''),
                "question_type": q.get('question_type', 'long_answer'),
                "options": q.get('options', []),
                "context": q.get('context', ''),
                "expected_time": q.get('expected_time', 5),
                "difficulty": q.get('difficulty', 'basic'),
                "bloom_level": q.get('bloom_level', 'remember'),
                "correct_answer": q.get('correct_answer', ''),
                "key_points": q.get('key_points', []),
            }
        }
    except Exception as e:
        return {"done": True, "error": f"Error: {str(e)}", "previous_question_status": reason}


@tool
def search_conversation_history(query: str, thread_id: str) -> str:
    """
    Search through earlier parts of this session's conversation.
    Use when the student references something discussed earlier like
    "what was that thing about...", "remember when I asked...", or
    "what did you say about question 2?".

    Args:
        query: What to search for (e.g., "photosynthesis explanation", "question 2 answer")
        thread_id: Current session's thread ID

    Returns:
        Relevant excerpts from earlier in the conversation
    """
    try:
        # Get checkpoint from Redis
        checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})
        if not checkpoint:
            return "No conversation history found."

        # Access messages from checkpoint
        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])
        if not messages:
            return "No messages in history."

        # Simple keyword search (fast, ~10ms)
        query_terms = query.lower().split()
        results = []

        for i, msg in enumerate(messages):
            content = getattr(msg, 'content', '') or ''
            if not content:
                continue
            content_lower = content.lower()

            # Score by term overlap
            score = sum(1 for term in query_terms if term in content_lower)
            if score > 0:
                role = "Student" if isinstance(msg, HumanMessage) else "Agent"
                # Include turn number and truncated content
                results.append((score, i, f"[Turn {i+1}] {role}: {content[:200]}..."))

        # Return top 3 matches sorted by relevance
        results.sort(reverse=True)
        top_results = [r[2] for r in results[:3]]

        if top_results:
            return "Found relevant exchanges:\n\n" + "\n\n".join(top_results)
        else:
            return "No matching exchanges found in conversation history."

    except Exception as e:
        return f"Search error: {str(e)}"




@tool
def get_rules(topics: List[str]) -> str:
    """
    Load exam conduct rules for handling specific situations.

    Use this when you encounter edge cases that need careful handling:
    - Student requests hints or help
    - Student goes off-topic
    - Student expresses frustration
    - Unclear audio or need to repeat
    - Question presentation guidelines

    Use this when you need guidance on handling edge cases.

    Args:
        topics: List of rule topics to load. Options:
                - "exam_conduct" - Rules for declined requests, tone, professionalism
                - "question_presentation" - How to read MCQs, long answers, formulas
                - "edge_cases" - Off-topic handling, unclear audio, frustration

    Returns:
        Relevant rules content to guide your response
    """
    available_rules = {
        "exam_conduct": "exam_conduct.md",
        "question_presentation": "question_presentation.md",
        "edge_cases": "edge_cases.md",
    }

    results = []
    for topic in topics:
        if topic in available_rules:
            rule_file = RULES_DIR / available_rules[topic]
            if rule_file.exists():
                content = rule_file.read_text()
                # Truncate to avoid context overflow (keep most relevant sections)
                if len(content) > 2000:
                    content = content[:2000] + "\n... [truncated]"
                results.append(f"=== {topic.upper()} RULES ===\n{content}")
            else:
                results.append(f"[{topic}] Rules file not found")
        else:
            results.append(f"[{topic}] Unknown topic. Available: {list(available_rules.keys())}")

    return "\n\n".join(results)


@tool
def emit_thinking(message: str) -> str:
    """
    Emit an immediate spoken response before processing.
    Call this FIRST when you need to use other tools.

    This lets the student know you're working on their request.
    Examples: "One moment...", "Let me check that...", "Sure, moving on..."

    Args:
        message: A brief acknowledgment to speak immediately (keep under 10 words)

    Returns:
        A marker that the streaming handler will process
    """
    return f"[EMIT_THINKING]{message}"


@tool
def get_time_remaining(exam_start_time: float, duration_minutes: int) -> str:
    """
    Calculate remaining exam time.
    Call when student asks "How much time do I have left?" or similar time queries.

    Args:
        exam_start_time: Unix timestamp when exam started (from state.exam_start_time)
        duration_minutes: Total exam duration in minutes (from state.duration_minutes)

    Returns:
        Human-readable time remaining, or TIME_EXPIRED if time is up
    """
    elapsed = time.time() - exam_start_time
    remaining = (duration_minutes * 60) - elapsed

    if remaining <= 0:
        return "TIME_EXPIRED"

    mins = int(remaining // 60)
    secs = int(remaining % 60)

    if mins > 0:
        return f"{mins} minutes and {secs} seconds remaining"
    else:
        return f"{secs} seconds remaining"


def preload_first_question(qp_id: str) -> tuple[dict, int]:
    """Pre-load the first question and total count. Call before starting exam."""
    key = f"qp:{qp_id}:questions"
    try:
        questions = r.json().get(key)
        if questions and isinstance(questions, list) and len(questions) > 0:
            q = questions[0]
            first_question = {
                "text": q.get('text', ''),
                "question_type": q.get('question_type', 'long_answer'),
                "options": q.get('options', []),
                "context": q.get('context', ''),
                "expected_time": q.get('expected_time', 5),
                "difficulty": q.get('difficulty', 'basic'),
                "bloom_level": q.get('bloom_level', 'remember'),
                "correct_answer": q.get('correct_answer', ''),
                "key_points": q.get('key_points', []),
            }
            return first_question, len(questions)
        return None, 0
    except Exception as e:
        print(f"Error preloading question: {e}")
        return None, 0


tools = [advance_to_next_question, search_conversation_history, get_rules, emit_thinking, get_time_remaining]
# Using Groq GPT OSS 120B for superior reasoning
llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    temperature=0
)
llm_with_tools = llm.bind_tools(tools)

# System prompt for exam mode (strict assessment)
EXAM_MODE_PROMPT = """You are a strict exam conductor conducting a formal examination via voice.

**STRICT RULES:**
1. **NO DISCUSSIONS** - Do not engage in explanations, hints, or teaching
2. **NO HELP** - Do not provide hints, clarifications, or guidance
3. **NO FEEDBACK** - Do not comment on answer quality (just acknowledge receipt)
4. **FORMAL TONE** - Professional, neutral, exam-hall atmosphere

**YOUR RESPONSIBILITIES:**
- Present questions clearly from the CURRENT QUESTION section below
- **MCQs:** Read question + ALL options (A, B, C, D) clearly
- **Long Answer:** Read the question, let student explain verbally
- Accept answers without evaluation
- Keep responses brief (1-2 sentences max)

**TOOL USAGE:**
- emit_thinking(): Call FIRST before other tools to acknowledge student (e.g., "One moment...", "Sure...")
- get_rules(["edge_cases"]): Call for edge cases (hints, off-topic, frustration) when you need guidance
- advance_to_next_question(qp_id, current_index, reason): Call when moving to next question
- get_time_remaining(exam_start_time, duration_minutes): Call when student asks about remaining time
- search_conversation_history(): Only if student asks about earlier parts of the exam

**WHEN MOVING TO NEXT QUESTION:**
- Student gave an answer → advance_to_next_question(reason="answered")
- Student says "skip", "I don't know", "next" without answering → advance_to_next_question(reason="skipped")
- Student gives partial answer and wants to move on → advance_to_next_question(reason="partial")

**SKIP ACKNOWLEDGMENT:**
When skipping, briefly acknowledge without negative framing:
- "Noted, moving to question 3..." (NOT "Skipping question 2")

**TIME QUERIES:**
When student asks "How much time left?", "How long do I have?":
- Call get_time_remaining() with exam_start_time and duration_minutes from context
- Report the time clearly: "You have about X minutes remaining."

**WORKFLOW - Follow this decision tree:**
1. **Simple answer acknowledgment** → Respond directly: "Answer recorded. Ready for the next question?" (NO tools needed)
2. **Student wants next question** → emit_thinking("Sure, moving on.") → advance_to_next_question() → read new question
3. **Student asks about time** → emit_thinking("Let me check...") → get_time_remaining() → report time
4. **Edge case (hints, off-topic, frustration)** → emit_thinking("One moment...") → get_rules(["edge_cases"]) → respond based on rules
5. **Asks about earlier conversation** → emit_thinking("Let me check...") → search_conversation_history() → respond

**IMPORTANT:** Most interactions are simple acknowledgments. Don't overthink - respond naturally without tools for routine answers.

**EDGE CASE RESPONSES (use these if you don't call get_rules):**

When student asks for hints/help:
→ "I understand this is challenging, but I cannot provide hints during the exam. Would you like me to repeat the question?"

When student goes off-topic:
→ "Let's stay focused on the exam. Ready for your answer, or would you like to move to the next question?"

When student expresses frustration:
→ "Take your time. You can attempt a partial answer or say 'next' to move on."

Exam: {qp_id}, Question {current_index_display} of {total_questions}.
Duration: {duration_minutes} minutes.
Exam start time: {exam_start_time}"""

GREETING_PROMPT = """You just connected to a new exam/study session.

**YOUR FIRST TURN:**
- Welcome the student warmly but professionally
- State: This exam has {total_questions} questions, {duration_minutes} minutes
- Brief rules: "I'll read each question clearly. Say 'next' when ready to continue."
- Ask: "Ready to begin when you are!"

**DO NOT present the first question yet.** Wait for student confirmation."""


# ============================================================
# CONTEXT MANAGEMENT - Running Summary Prompts
# ============================================================

EXAM_SUMMARY_PROMPT = """You are summarizing an exam session for context continuity. Focus on:
1. Questions asked (by number) and whether the student answered
2. Answer quality indicators (correct/partial/incorrect if apparent from responses)
3. Any clarifications the student requested (repeated questions, asked for clarity)
4. Current position in the exam

Keep it factual and structured. This is an assessment context.

EXISTING SUMMARY:
{existing_summary}

NEW CONVERSATION TO ADD:
{conversation}

UPDATED SUMMARY (extend the existing summary with new information):"""



# ============================================================
# CONTEXT MANAGEMENT - Summarization Functions
# ============================================================

def should_update_summary(state: State) -> bool:
    """
    Check if we need to update the running summary based on thresholds.
    Does NOT delete messages - just indicates if summary update needed.
    Only counts actual conversation messages (Human + AI with content), not tool messages.
    """
    messages = state.get("messages", [])
    summary_index = state.get("summary_message_index", 0)

    # Filter to only conversation messages (Human + AI with actual content)
    # Excludes: SystemMessage, ToolMessage, AIMessage with empty content (tool calls)
    unsummarized_msgs = [
        m for m in messages[summary_index:]
        if isinstance(m, (HumanMessage, AIMessage)) and m.content
    ]

    unsummarized_count = len(unsummarized_msgs)
    if unsummarized_count < SUMMARIZATION_TRIGGER_THRESHOLD:
        return False

    # Check char count of conversation messages only
    unsummarized_chars = sum(len(m.content) for m in unsummarized_msgs)

    if unsummarized_chars >= SUMMARIZATION_CHAR_THRESHOLD:
        print(f"📊 Summarization triggered: {unsummarized_chars} chars >= {SUMMARIZATION_CHAR_THRESHOLD}")
        return True

    if unsummarized_count >= SUMMARIZATION_TRIGGER_THRESHOLD:
        print(f"📊 Summarization triggered: {unsummarized_count} conversation messages >= {SUMMARIZATION_TRIGGER_THRESHOLD}")
        return True

    return False


def summarization_node(state: State) -> dict:
    """
    Update running summary with newly unsummarized messages.
    NEVER deletes messages - they stay for CorrectionReport at end.
    """
    messages = state.get("messages", [])
    existing_summary = state.get("running_summary", "")
    summary_index = state.get("summary_message_index", 0)

    # Summarize from last index to N before end (preserve recent for context window)
    end_index = max(0, len(messages) - CONTEXT_MESSAGES_TO_LLM)
    messages_to_summarize = messages[summary_index:end_index]

    if not messages_to_summarize:
        print("⏭️ No messages to summarize")
        return {}

    # Format conversation for summarization
    convo_lines = []
    for m in messages_to_summarize:
        if isinstance(m, HumanMessage):
            convo_lines.append(f"Student: {m.content}")
        elif isinstance(m, AIMessage) and m.content:
            # Truncate long responses to avoid context overflow
            convo_lines.append(f"Agent: {m.content[:300]}")

    convo_text = "\n".join(convo_lines)

    # Use Groq Llama 3.1 8B for fast, cheap summarization (9x faster than DeepInfra)
    summary_llm = ChatOpenAI(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0
    )

    prompt = EXAM_SUMMARY_PROMPT.format(
        existing_summary=existing_summary or "None yet - this is the first summary.",
        conversation=convo_text[-3000:]  # Limit input to avoid context overflow
    )

    try:
        response = summary_llm.invoke([SystemMessage(content=prompt)])
        new_summary = response.content.strip()
        if not new_summary:
            print("⚠️ Empty summary returned, keeping existing state")
            return {}
        print(f"✂️ Summarized {len(messages_to_summarize)} messages into {len(new_summary)} chars")
    except Exception as e:
        print(f"⚠️ Summarization failed: {e}")
        return {}

    return {
        "running_summary": new_summary,
        "summary_message_index": end_index,
    }


def check_time_warnings(state: State) -> tuple[Optional[str], dict]:
    """
    Check if we need to warn about remaining time.

    Args:
        state: Current exam state

    Returns:
        Tuple of (warning_message, state_updates)
        warning_message is None if no warning needed
    """
    if not state.get("exam_start_time"):
        return None, {}

    elapsed = time.time() - state["exam_start_time"]
    duration_secs = (state.get("duration_minutes") or 15) * 60
    remaining = duration_secs - elapsed

    state_updates = {}

    # Warn at 5 min, 2 min, 1 min
    if remaining <= 60 and not state.get("warned_1min"):
        state_updates["warned_1min"] = True
        return "One minute remaining in your exam.", state_updates
    elif remaining <= 120 and not state.get("warned_2min"):
        state_updates["warned_2min"] = True
        return "Two minutes remaining.", state_updates
    elif remaining <= 300 and not state.get("warned_5min"):
        state_updates["warned_5min"] = True
        return "Five minutes remaining.", state_updates

    return None, state_updates


def build_question_context(state: State) -> str:
    """Build the question context string for prompt injection."""
    current_index_display = state["current_index"] + 1

    # Session just started - greet first
    if not state.get("exam_started"):
        return GREETING_PROMPT.format(
            total_questions=state.get("total_questions", "?"),
            duration_minutes=state.get("duration_minutes") or 15
        )

    # Question loaded - inject into prompt
    if state.get("current_question"):
        q = state["current_question"]

        # Build image context if present
        image_context = ""
        if q.get("image_description"):
            image_context = f"\n[IMAGE CONTEXT - What the image shows]\n{q.get('image_description')}\n"

        # Exam mode: context is internal reference only
        return f"""
[CURRENT QUESTION - DO NOT call advance_to_next_question unless moving to next]
Question {current_index_display}: {q['text']}
Type: {q.get('question_type', 'long_answer')}
Options: {', '.join(q.get('options', [])) or 'N/A (long answer)'}
{image_context}
[INTERNAL REFERENCE - DO NOT reveal to student]
Syllabus context: {q.get('context', 'N/A')[:500]}...
"""

    return "[ERROR: No question loaded. This shouldn't happen.]"


def agent(state: State) -> State:
    """Reasoning step: LLM decides to answer or call a tool."""

    current_index_display = state["current_index"] + 1

    # Build the question context
    question_context = build_question_context(state)

    # Inject running summary for context continuity
    running_summary = state.get("running_summary", "")
    if running_summary:
        summary_section = f"""
[SESSION CONTEXT - Internal reference, do not read aloud]
{running_summary}
---
"""
    else:
        summary_section = ""

    # Build exam mode system prompt
    base_prompt = EXAM_MODE_PROMPT.format(
        qp_id=state["qp_id"],
        current_index_display=current_index_display,
        total_questions=state.get("total_questions", "?"),
        duration_minutes=state.get("duration_minutes") or 15,
        exam_start_time=state.get("exam_start_time") or time.time()
    )

    # Combine: base prompt + summary + question context
    full_prompt = base_prompt + "\n\n" + summary_section + question_context

    system_message = SystemMessage(content=full_prompt)

    # Message windowing - only pass last N messages to LLM
    # CRITICAL: Include ToolMessage so agent sees tool results (prevents infinite loops)
    recent_messages = []
    for m in state["messages"][-CONTEXT_MESSAGES_TO_LLM:]:
        if isinstance(m, HumanMessage):
            recent_messages.append(m)
        elif isinstance(m, AIMessage):
            # Include AIMessage even if content is empty (may have tool_calls)
            recent_messages.append(m)
        elif isinstance(m, ToolMessage):
            # Include tool results so agent knows tools already executed
            recent_messages.append(m)
    messages = [system_message] + recent_messages

    response = llm_with_tools.invoke(messages)
    state["messages"].append(response)

    # After greeting, mark exam as started
    if not state.get("exam_started") and len(state["messages"]) > 2:
        state["exam_started"] = True

    # Set response metadata for data channel
    current_question = state.get("current_question")
    human_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]

    if True:  # Always set response type
        if current_question:
            last_human = human_messages[-1].content if human_messages else ""

            if len(human_messages) == 1:
                state["response_type"] = "instruction"
                state["response_options"] = None
            elif any(p in last_human.lower() for p in ["next question", "next", "skip", "move on", "continue", "proceed", "next one", "go ahead"]) or state.get("exam_started") and current_question.get("text") in response.content:
                state["response_type"] = "question"
                state["response_options"] = current_question.get("options") or None
            else:
                is_feedback = any(word in response.content.lower() for word in ["correct", "incorrect", "good", "well done", "try again"])
                state["response_type"] = "feedback" if is_feedback else "follow_up"
                state["response_options"] = None
        else:
            state["response_type"] = "instruction"
            state["response_options"] = None

    return state


# SafeToolNode: catches tool exceptions and returns error ToolMessage
# instead of crashing the entire graph invocation (which causes student silence)
class SafeToolNode(ToolNode):
    async def ainvoke(self, state, config=None):
        try:
            return await super().ainvoke(state, config)
        except Exception as e:
            print(f"❌ Tool error: {e}")
            last_msg = state["messages"][-1]
            tool_call_id = last_msg.tool_calls[0]["id"] if hasattr(last_msg, "tool_calls") and last_msg.tool_calls else "error"
            return {"messages": [ToolMessage(
                content=f"[ERROR] Tool failed: {str(e)}. Please try again or skip.",
                tool_call_id=tool_call_id
            )]}

    def invoke(self, state, config=None):
        try:
            return super().invoke(state, config)
        except Exception as e:
            print(f"❌ Tool error: {e}")
            last_msg = state["messages"][-1]
            tool_call_id = last_msg.tool_calls[0]["id"] if hasattr(last_msg, "tool_calls") and last_msg.tool_calls else "error"
            return {"messages": [ToolMessage(
                content=f"[ERROR] Tool failed: {str(e)}. Please try again or skip.",
                tool_call_id=tool_call_id
            )]}

tool_node = SafeToolNode(tools)

def process_tool_response(state: State) -> State:
    """Process tool responses and update state accordingly.

    Handles:
    - emit_thinking: Just logs (streaming handler speaks it directly from ToolMessage)
    - advance_to_next_question: Updates current_index, current_question, and time tracking
    - Other tools: No special processing needed

    NOTE: We do NOT convert emit_thinking to AIMessage here because it breaks
    the message sequence (AIMessage→ToolMessage→AIMessage pattern expected by LLM).
    Instead, realtime_exam.py detects [EMIT_THINKING] in ToolMessage and speaks it.
    """
    messages = state["messages"]

    # Initialize time_per_question if not present
    if state.get("time_per_question") is None:
        state["time_per_question"] = {}

    # Look for tool response in recent messages
    for msg in reversed(messages[-3:]):  # Check last few messages
        # Handle emit_thinking: Just log, streaming handler will speak it
        if isinstance(msg, ToolMessage) and "[EMIT_THINKING]" in str(msg.content):
            thinking_text = str(msg.content).replace("[EMIT_THINKING]", "").strip()
            if thinking_text:
                print(f"💭 emit_thinking detected: {thinking_text}")
                # Don't convert to AIMessage - realtime_exam.py handles it
            continue

        # Handle advance_to_next_question JSON responses
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            try:
                import json
                # Try to parse if it looks like JSON
                if msg.content.startswith('{'):
                    response = json.loads(msg.content)

                    # Track time for the previous question when advancing
                    if response.get("new_index") is not None or response.get("done"):
                        prev_index = state.get("current_index", 0)
                        question_start = state.get("question_start_time")
                        current_q = state.get("current_question", {})

                        if question_start:
                            actual_time = time.time() - question_start
                            expected_time = (current_q.get("expected_time", 5)) * 60  # Convert to secs

                            # Calculate status for correction agent
                            ratio = actual_time / expected_time if expected_time > 0 else 1
                            if ratio < 0.3:
                                status = "rushed"        # Answered in <30% of expected time
                            elif ratio > 2.0:
                                status = "struggled"     # Took >2x expected time
                            else:
                                status = "normal"

                            # Record time data with completion status
                            state["time_per_question"][prev_index] = {
                                "actual_secs": round(actual_time, 1),
                                "expected_secs": expected_time,
                                "status": status,
                                "completion_status": response.get("previous_question_status", "answered"),
                                "difficulty": current_q.get("difficulty"),
                                "bloom_level": current_q.get("bloom_level"),
                            }
                            print(f"⏱️ Q{prev_index + 1} time: {actual_time:.1f}s (expected {expected_time}s) - {status}, {response.get('previous_question_status', 'answered')}")

                    if response.get("done"):
                        # Exam complete - trigger cleanup
                        state["current_question"] = None
                        print(f"🎯 Exam complete signal received")
                    elif response.get("question"):
                        # Update state with new question
                        state["current_index"] = response["new_index"]
                        state["current_question"] = response["question"]
                        # Reset question start time for new question
                        state["question_start_time"] = time.time()
                        print(f"📝 Advanced to question {response['new_index'] + 1}")
            except (json.JSONDecodeError, TypeError):
                pass

    return state

def cleanup_exam(state: State) -> State:
    """Update session status and trigger correction task."""
    from tasks.correction import trigger_correction

    qp_id = state["qp_id"]
    thread_id = state["thread_id"]
    user_id = state.get("user_id", "unknown")
    exam_id = f"exam_{qp_id}_{int(time.time())}"

    # Update ExamSession status so frontend knows exam is done
    try:
        from supabase import create_client
        from datetime import datetime, timezone
        supabase = create_client(
            os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
        supabase.table("ExamSession").update({
            "status": "COMPLETED",
            "endedAt": datetime.now(timezone.utc).isoformat(),
        }).eq("threadId", thread_id).execute()
        print(f"✅ ExamSession marked COMPLETED for thread {thread_id}")
    except Exception as e:
        print(f"⚠️ Failed to update session status: {e}")

    try:
        # Trigger async correction (Celery) - QP cleanup happens there
        task_id = trigger_correction(
            exam_id=exam_id,
            qp_id=qp_id,
            user_id=user_id,
            thread_id=thread_id
        )
        print(f"📝 Correction triggered: task_id={task_id}")
        
        # Store task_id in state for tracking (optional)
        state["correction_task_id"] = task_id
        
    except Exception as e:
        print(f"⚠️ Failed to trigger correction: {e}")
        # Fallback: delete QP anyway to avoid orphans
        r.delete(f"qp:{qp_id}:questions")
    
    return state

def should_continue(state: State) -> Literal["tools", "check_completion", "__end__"]:
    """Determine whether to continue to tools or check if exam is done."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, go to tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Otherwise, check if exam is complete
    return "check_completion"

def check_if_exam_complete(state: State) -> Literal["cleanup", "__end__"]:
    """Check if all questions have been answered using state (no Redis call)."""
    current_index = state.get("current_index", 0)
    total_questions = state.get("total_questions")
    
    # If we have total_questions in state, use it (no Redis call needed)
    if total_questions is not None:
        if current_index >= total_questions - 1 and state.get("current_question") is None:
            # current_question is None means tool returned done=True
            print(f"🎯 Exam complete: {current_index + 1}/{total_questions} questions answered")
            return "cleanup"
        return "__end__"
    
    # Fallback to Redis check (shouldn't happen with preload)
    qp_id = state["qp_id"]
    try:
        qp_key = f"qp:{qp_id}:questions"
        questions = r.json().get(qp_key)
        
        if questions and isinstance(questions, list):
            if current_index >= len(questions) - 1:
                print(f"🎯 Exam complete (fallback): {current_index + 1}/{len(questions)} questions")
                return "cleanup"
        
        return "__end__"
    except Exception as e:
        print(f"❌ Error checking completion: {e}")
        return "__end__"

# === Summarization routing ===
def route_summarization(state: State) -> str:
    """Decide if summarization needed before processing."""
    if should_update_summary(state):
        return "summarize"
    return "agent"


# === Build the React-style graph ===
workflow = StateGraph(State)
workflow.add_node("summarization", summarization_node)  # NEW: Summary node
workflow.add_node("agent", agent)
workflow.add_node("tools", tool_node)
workflow.add_node("process_response", process_tool_response)  # Process tool output
workflow.add_node("check_completion", lambda state: state)  # Pass-through node for routing
workflow.add_node("cleanup", cleanup_exam)

# Entry point: check if summarization needed first
workflow.add_conditional_edges(
    "__start__",
    route_summarization,
    {"summarize": "summarization", "agent": "agent"}
)
workflow.add_edge("summarization", "agent")

# Add conditional routing from agent
workflow.add_conditional_edges("agent", should_continue)

# Add conditional routing to check if exam is complete
workflow.add_conditional_edges("check_completion", check_if_exam_complete)

# After tools, process the response then go back to agent
workflow.add_edge("tools", "process_response")
workflow.add_edge("process_response", "agent")

# After cleanup, end
workflow.add_edge("cleanup", "__end__")

# Note: Entry point is handled by __start__ conditional edges above
graph = workflow.compile(checkpointer=checkpointer)

# === Example run ===
if __name__ == "__main__":
    import uuid
    import sys

    # Use a fixed thread ID to continue previous conversation
    fixed_thread_id = "exam_session_1"

    print(f"\n{'='*60}")
    print(f"🎯 Running EXAM MODE")
    print(f"{'='*60}\n")

    # Pre-load first question (optimization - no tool call needed)
    qp_id = "qp1"
    first_question, total_questions = preload_first_question(qp_id)

    if not first_question:
        print("❌ Could not load question paper. Make sure QP is in Redis.")
        exit(1)

    print(f"📋 Loaded QP with {total_questions} questions")
    print("📋 EXAM MODE: Strict, formal, no discussions")

    # Initialize state with pre-loaded question (agent-first greeting)
    state = State(
        messages=[SystemMessage(content="[SESSION_START]")],  # Trigger greeting
        thread_id=fixed_thread_id,
        qp_id=qp_id,
        current_index=0,
        current_question=first_question,  # Pre-loaded!
        total_questions=total_questions,
        exam_started=False,
        duration_minutes=15,
    )

    # Configuration with thread_id for checkpointer
    config = {"configurable": {"thread_id": fixed_thread_id}}

    print(f"Starting new exam session with thread ID: {fixed_thread_id}")

    # Start timing
    start_time = time.time()
    print(f"⏱️  Starting conversation at {time.strftime('%H:%M:%S', time.localtime(start_time))}")

    final_state = graph.invoke(state, config=config)

    # End timing
    end_time = time.time()
    latency = end_time - start_time
    print(f"⏱️  Conversation completed at {time.strftime('%H:%M:%S', time.localtime(end_time))}")
    print(f"📊 Total Response Time: {latency:.3f} seconds ({latency*1000:.1f}ms)")

    print("\n=== CLEAN CONVERSATION ===")
    for msg in final_state["messages"]:
        if isinstance(msg, HumanMessage):
            print(f"👤 STUDENT: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Only show the content, skip tool calls in the output
            if msg.content:  # Only show if there's actual content
                print(f"🤖 AGENT: {msg.content}")
    print("=== End Conversation ===\n")