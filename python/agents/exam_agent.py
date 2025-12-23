from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
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

load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

class State(MessagesState):
    thread_id: str
    qp_id: str
    user_id: Optional[str] = None              # User taking the exam
    current_index: int = 0
    mode: Literal["exam", "learn"] = "exam"
    duration_minutes: int = None
    # Optimizations: cache current question to avoid tool calls
    current_question: Optional[dict] = None    # {text, options, context, etc.}
    total_questions: Optional[int] = None      # For completion check without Redis
    exam_started: bool = False                 # Has first question been asked?
    correction_task_id: Optional[str] = None   # Celery task ID for correction



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
def advance_to_next_question(qp_id: str, current_index: int) -> dict:
    """Advance to the next question in the exam. Call this when ready to move to the next question."""
    key = f"qp:{qp_id}:questions"
    try:
        next_index = current_index + 1
        questions = r.json().get(key)
        
        if not questions or not isinstance(questions, list):
            return {"done": True, "error": "Question paper not found"}
        
        if next_index >= len(questions):
            return {"done": True, "message": "All questions completed. Exam finished."}
        
        q = questions[next_index]
        return {
            "done": False,
            "new_index": next_index,
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
        return {"done": True, "error": f"Error: {str(e)}"}


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


tools = [advance_to_next_question]
# Using Cerebras GPT OSS 120B for superior reasoning and tutoring
llm = ChatOpenAI(
    model="gpt-oss-120b",
    api_key=CEREBRAS_API_KEY,
    base_url="https://api.cerebras.ai/v1",
    temperature=0
)
llm_with_tools = llm.bind_tools(tools)

# System prompts for different modes
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
- Call advance_to_next_question() ONLY when student is ready for next question
- Keep responses brief

**EXAMPLE INTERACTIONS:**
❌ WRONG: "That's a good start, but consider the chemical bonds..."
✅ CORRECT: "Answer recorded. Ready for the next question?"

❌ WRONG: "Let me explain this concept..."
✅ CORRECT: "This is an exam. I cannot provide explanations."

Exam: {qp_id}, Question {current_index_display} of {total_questions}.
Duration: {duration_minutes} minutes."""

LEARN_MODE_PROMPT = """You are an engaging learning tutor conducting a voice-based study session.

**LEARNING PHILOSOPHY:**
1. **ENCOURAGE DISCUSSION** - Engage in deep conversations
2. **PROVIDE GUIDANCE** - Offer hints, explanations, scaffolding
3. **GIVE FEEDBACK** - Comment on answers, highlight strengths
4. **TEACH ACTIVELY** - Explain concepts, provide examples

**YOUR RESPONSIBILITIES:**
- Present questions from the CURRENT QUESTION section below
- Use the syllabus context to guide the student
- Engage in Socratic dialogue - ask follow-up questions
- Explain answers using key_points (after student attempts!)
- Call advance_to_next_question() when ready to move on

**TEACHING STRATEGIES:**
- Ask probing questions: "What makes you think that?"
- Provide hints: "Consider the relationship between X and Y..."
- Use the context to enrich explanations
- Use key_points to assess answer completeness

Question {current_index_display} of {total_questions}.
Remember: Deep understanding > number of questions covered."""

GREETING_PROMPT = """You just connected to a new exam/study session. 

**YOUR FIRST TURN:**
- Welcome the student warmly but professionally
- State: This exam has {total_questions} questions, {duration_minutes} minutes
- Brief rules: "I'll read each question clearly. Say 'next' when ready to continue."
- Ask: "Ready to begin when you are!"

**DO NOT present the first question yet.** Wait for student confirmation."""


def build_question_context(state: State) -> str:
    """Build the question context string for prompt injection."""
    current_index_display = state["current_index"] + 1
    mode = state.get("mode", "exam")
    
    # Session just started - greet first
    if not state.get("exam_started"):
        return GREETING_PROMPT.format(
            total_questions=state.get("total_questions", "?"),
            duration_minutes=state.get("duration_minutes") or 15
        )
    
    # Question loaded - inject into prompt
    if state.get("current_question"):
        q = state["current_question"]
        
        if mode == "exam":
            # Exam mode: context is internal reference only
            return f"""
[CURRENT QUESTION - DO NOT call advance_to_next_question unless moving to next]
Question {current_index_display}: {q['text']}
Type: {q.get('question_type', 'long_answer')}
Options: {', '.join(q.get('options', [])) or 'N/A (long answer)'}

[INTERNAL REFERENCE - DO NOT reveal to student]
Syllabus context: {q.get('context', 'N/A')[:500]}...
"""
        else:
            # Learn mode: use context to help student
            return f"""
[CURRENT QUESTION - DO NOT call advance_to_next_question unless moving to next]
Question {current_index_display}: {q['text']}
Type: {q.get('question_type', 'long_answer')}
Options: {', '.join(q.get('options', [])) or 'N/A (long answer)'}
Difficulty: {q.get('difficulty', 'basic')} | Bloom: {q.get('bloom_level', 'remember')}

[USE TO HELP STUDENT - syllabus context]
{q.get('context', 'N/A')[:500]}

[REVEAL AFTER STUDENT ATTEMPTS]
Key Points: {q.get('key_points', [])}
Correct Answer: {q.get('correct_answer', 'N/A')}
"""
    
    return "[ERROR: No question loaded. This shouldn't happen.]"


def agent(state: State) -> State:
    """Reasoning step: LLM decides to answer or call a tool."""
    
    current_index_display = state["current_index"] + 1
    mode = state.get("mode", "exam")
    
    # Build the question context
    question_context = build_question_context(state)
    
    # Select base system prompt based on mode
    if mode == "exam":
        base_prompt = EXAM_MODE_PROMPT.format(
            qp_id=state["qp_id"],
            current_index_display=current_index_display,
            total_questions=state.get("total_questions", "?"),
            duration_minutes=state.get("duration_minutes") or 15
        )
    else:
        base_prompt = LEARN_MODE_PROMPT.format(
            current_index_display=current_index_display,
            total_questions=state.get("total_questions", "?")
        )
    
    # Combine base prompt + question context
    full_prompt = base_prompt + "\n\n" + question_context
    
    system_message = SystemMessage(content=full_prompt)
    messages = [system_message] + state["messages"]

    response = llm_with_tools.invoke(messages)
    state["messages"].append(response)
    
    # After greeting, mark exam as started
    if not state.get("exam_started") and len(state["messages"]) > 2:
        state["exam_started"] = True
    
    return state


# ToolNode (executes tool calls)
tool_node = ToolNode(tools)

def process_tool_response(state: State) -> State:
    """Process tool responses and update state accordingly."""
    messages = state["messages"]
    
    # Look for tool response in recent messages
    for msg in reversed(messages[-3:]):  # Check last few messages
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            try:
                import json
                # Try to parse if it looks like JSON
                if msg.content.startswith('{'):
                    response = json.loads(msg.content)
                    
                    if response.get("done"):
                        # Exam complete - trigger cleanup
                        state["current_question"] = None
                        print(f"🎯 Exam complete signal received")
                    elif response.get("question"):
                        # Update state with new question
                        state["current_index"] = response["new_index"]
                        state["current_question"] = response["question"]
                        print(f"📝 Advanced to question {response['new_index'] + 1}")
            except (json.JSONDecodeError, TypeError):
                pass
    
    return state

def cleanup_exam(state: State) -> State:
    """Trigger correction task instead of immediate cleanup."""
    from tasks.correction import trigger_correction
    
    qp_id = state["qp_id"]
    thread_id = state["thread_id"]
    user_id = state.get("user_id", "unknown")
    exam_id = f"exam_{qp_id}_{int(time.time())}"
    
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

# === Build the React-style graph ===
workflow = StateGraph(State)
workflow.add_node("agent", agent)
workflow.add_node("tools", tool_node)
workflow.add_node("process_response", process_tool_response)  # Process tool output
workflow.add_node("check_completion", lambda state: state)  # Pass-through node for routing
workflow.add_node("cleanup", cleanup_exam)

# Add conditional routing from agent
workflow.add_conditional_edges("agent", should_continue)

# Add conditional routing to check if exam is complete
workflow.add_conditional_edges("check_completion", check_if_exam_complete)

# After tools, process the response then go back to agent
workflow.add_edge("tools", "process_response")
workflow.add_edge("process_response", "agent")

# After cleanup, end
workflow.add_edge("cleanup", "__end__")

workflow.set_entry_point("agent")
graph = workflow.compile(checkpointer=checkpointer)

# === Example run ===
if __name__ == "__main__":
    import uuid
    import sys
    
    # Allow mode selection via command line argument
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ["exam", "learn"] else "exam"
    
    # Use a fixed thread ID to continue previous conversation
    fixed_thread_id = f"{mode}_session_1"
    
    print(f"\n{'='*60}")
    print(f"🎯 Running in {mode.upper()} mode")
    print(f"{'='*60}\n")
    
    # Pre-load first question (optimization - no tool call needed)
    qp_id = "qp1"
    first_question, total_questions = preload_first_question(qp_id)
    
    if not first_question:
        print("❌ Could not load question paper. Make sure QP is in Redis.")
        exit(1)
    
    print(f"📋 Loaded QP with {total_questions} questions")
    
    if mode == "exam":
        print("📋 EXAM MODE: Strict, formal, no discussions")
    else:
        print("📚 LEARN MODE: Interactive, supportive, full discussion")
    
    # Initialize state with pre-loaded question (agent-first greeting)
    state = State(
        messages=[SystemMessage(content="[SESSION_START]")],  # Trigger greeting
        thread_id=fixed_thread_id,
        qp_id=qp_id,
        current_index=0,
        mode=mode,
        current_question=first_question,  # Pre-loaded!
        total_questions=total_questions,
        exam_started=False,
        duration_minutes=15,
    )

    # Configuration with thread_id for checkpointer
    config = {"configurable": {"thread_id": fixed_thread_id}}
    
    print(f"Starting new {mode} session with thread ID: {fixed_thread_id}")
    
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