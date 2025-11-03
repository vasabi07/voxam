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

load_dotenv()

class State(MessagesState):
    thread_id: str
    qp_id: str
    current_index: int = 0
    mode: Literal["exam", "learn"] = "exam"




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
def get_current_question(qp_id: str, index: int) -> str:
    """Return the current question text based on qp_id and index."""
    key = f"qp:{qp_id}:questions"
    try:
        # Try to get the entire questions array first
        questions = r.json().get(key)
        if questions and isinstance(questions, list) and index < len(questions):
            return questions[index].get('text', 'No question text found.')
        return "No question found."
    except Exception as e:
        return f"Error retrieving question: {str(e)}"

@tool
def get_current_context(qp_id: str, index: int) -> str:
    """Return the current question's context text."""
    key = f"qp:{qp_id}:questions"
    try:
        # Try to get the entire questions array first
        questions = r.json().get(key)
        if questions and isinstance(questions, list) and index < len(questions):
            return questions[index].get('context', 'No context found.')
        return "No context found."
    except Exception as e:
        return f"Error retrieving context: {str(e)}"

@tool
def get_next_question(qp_id: str, index: int) -> str:
    """Return the next question after index."""
    key = f"qp:{qp_id}:questions"
    try:
        next_index = index + 1
        questions = r.json().get(key)
        if questions and isinstance(questions, list) and next_index < len(questions):
            return questions[next_index].get('text', 'No question text found.')
        return "No more questions."
    except Exception as e:
        return f"Error retrieving next question: {str(e)}"


tools = [get_current_question, get_current_context, get_next_question]
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
llm_with_tools = llm.bind_tools(tools)

# System prompts for different modes
EXAM_MODE_PROMPT = """You are a strict exam conductor conducting a formal examination. Your role is to:

**STRICT RULES:**
1. **NO DISCUSSIONS** - Do not engage in explanations, hints, or teaching during the exam
2. **NO HELP** - Do not provide hints, clarifications, or guidance on how to answer
3. **NO FEEDBACK** - Do not comment on answer quality or correctness (just acknowledge receipt)
4. **FORMAL TONE** - Maintain a professional, neutral, exam-hall atmosphere

**YOUR RESPONSIBILITIES:**
- Present questions clearly using get_current_question()
- Provide context ONLY if explicitly requested using get_current_context()
- Accept answers without evaluation or discussion
- Move to next question using get_next_question() when student is ready
- Keep responses brief and procedural

**EXAMPLE INTERACTIONS:**
❌ WRONG: "That's a good start, but you might want to consider the chemical bonds..."
✅ CORRECT: "Answer recorded. Ready for the next question?"

❌ WRONG: "Let me explain this concept to help you understand..."
✅ CORRECT: "This is an exam. I cannot provide explanations during the test."

❌ WRONG: "You're on the right track! The answer involves..."
✅ CORRECT: "Thank you. Moving to the next question."

✅ CORRECT (when ending): "All questions completed. Your responses have been recorded. Good luck!"

Current QP: {qp_id}, Current question index: {current_index}.
Remember: This is a formal exam. No teaching, no hints, no discussions."""

LEARN_MODE_PROMPT = """You are an engaging and supportive learning tutor. Your role is to:

**LEARNING PHILOSOPHY:**
1. **ENCOURAGE DISCUSSION** - Engage in deep conversations about the topic
2. **PROVIDE GUIDANCE** - Offer hints, explanations, and scaffolding
3. **GIVE FEEDBACK** - Comment on answers, highlight strengths, suggest improvements
4. **TEACH ACTIVELY** - Explain concepts, provide examples, break down complex ideas

**YOUR RESPONSIBILITIES:**
- Present questions using get_current_question() as learning prompts
- Provide context using get_current_context() to enrich understanding
- Engage in Socratic dialogue - ask follow-up questions
- Explain why answers are correct or incorrect
- Provide additional examples and analogies
- Encourage critical thinking and deeper exploration
- Celebrate progress and provide constructive feedback

**TEACHING STRATEGIES:**
- Ask probing questions: "What makes you think that?"
- Provide hints: "Consider the relationship between X and Y..."
- Offer explanations: "The reason this works is because..."
- Break down concepts: "Let's tackle this step by step..."
- Connect to prior knowledge: "Remember when we discussed...?"
- Provide encouragement: "Great thinking! Now let's explore..."

**EXAMPLE INTERACTIONS:**
✅ "Excellent start! The chemical bond part is correct. Now, can you think about what happens to the electrons during this process?"
✅ "I see your reasoning, but let's explore this together. What do you know about oxidation reactions?"
✅ "That's a common misconception. Let me explain why: when magnesium burns..."
✅ "Perfect! You've got it. The key insight here is... Now, want to try a related concept?"

Current QP: {qp_id}, Current question index: {current_index}.
Remember: This is a learning session. Encourage, guide, and teach!"""

def agent(state: State) -> State:
    """Reasoning step: LLM decides to answer or call a tool."""
    
    # Select system prompt based on mode
    if state.get("mode", "exam") == "exam":
        system_prompt = EXAM_MODE_PROMPT.format(
            qp_id=state["qp_id"],
            current_index=state["current_index"]
        )
    else:  # learn mode
        system_prompt = LEARN_MODE_PROMPT.format(
            qp_id=state["qp_id"],
            current_index=state["current_index"]
        )
    
    system_message = SystemMessage(content=system_prompt)
    messages = [system_message] + state["messages"]

    response = llm_with_tools.invoke(messages)  # returns an AIMessage
    state["messages"].append(response)
    return state


# ToolNode (executes tool calls)
tool_node = ToolNode(tools)

def cleanup_exam(state: State) -> State:
    """Delete QP from Redis when exam is complete."""
    qp_id = state["qp_id"]
    qp_key = f"qp:{qp_id}:questions"
    
    try:
        deleted = r.delete(qp_key)
        if deleted:
            print(f"✅ Exam complete. Deleted QP from Redis: {qp_key}")
        else:
            print(f"⚠️ QP already removed or not found: {qp_key}")
    except Exception as e:
        print(f"❌ Error cleaning up: {e}")
    
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
    """Check if all questions have been answered."""
    qp_id = state["qp_id"]
    current_index = state["current_index"]
    
    try:
        # Get total number of questions
        qp_key = f"qp:{qp_id}:questions"
        questions = r.json().get(qp_key)
        
        if questions and isinstance(questions, list):
            total_questions = len(questions)
            # If current_index is the last question (0-indexed)
            if current_index >= total_questions - 1:
                print(f"🎯 Exam complete: {current_index + 1}/{total_questions} questions answered")
                return "cleanup"
        
        # Not complete yet, continue conversation
        return "__end__"
    except Exception as e:
        print(f"❌ Error checking completion: {e}")
        return "__end__"

# === Build the React-style graph ===
workflow = StateGraph(State)
workflow.add_node("agent", agent)
workflow.add_node("tools", tool_node)
workflow.add_node("check_completion", lambda state: state)  # Pass-through node for routing
workflow.add_node("cleanup", cleanup_exam)

# Add conditional routing from agent
workflow.add_conditional_edges("agent", should_continue)

# Add conditional routing to check if exam is complete
workflow.add_conditional_edges("check_completion", check_if_exam_complete)

# After tools, always go back to agent
workflow.add_edge("tools", "agent")

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
    
    if mode == "exam":
        print("📋 EXAM MODE: Strict, formal, no discussions")
        example_message = "Can you help me understand this question better?"
    else:
        print("📚 LEARN MODE: Interactive, supportive, full discussion")
        example_message = "I'm not sure about this answer. Can you explain?"
    
    # Example state (pretend qp_id=qp1 already loaded into Redis)
    state = State(
        messages=[HumanMessage(content=example_message)],
        thread_id=fixed_thread_id,
        qp_id="qp1",
        current_index=0,
        mode=mode,
    )

    # Configuration with thread_id for checkpointer
    config = {"configurable": {"thread_id": fixed_thread_id}}
    
    print(f"Continuing {mode} session with thread ID: {fixed_thread_id}")
    
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