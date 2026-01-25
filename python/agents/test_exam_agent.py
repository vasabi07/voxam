#!/usr/bin/env python3
"""
Interactive Test Script for Exam Agent
Run directly to test agent responses without LiveKit/Deepgram overhead.

Usage:
    python agents/test_exam_agent.py                    # Default: exam mode, use test QP
    python agents/test_exam_agent.py learn              # Learn mode
    python agents/test_exam_agent.py exam --qp <qp_id>  # Specific question paper
    
Interactive Commands:
    Type any message to send to the agent
    /quit or /exit - End session
    /state - Show current state
    /reset - Start fresh session
"""

import sys
import os
import time
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.exam_agent import graph, State, preload_first_question
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


def print_banner(mode: str, qp_id: str, total_questions: int):
    """Print startup banner."""
    print("\n" + "="*70)
    print("  🎯 VOXAM EXAM AGENT TEST CONSOLE")
    print("="*70)
    print(f"  Mode: {mode.upper()}")
    print(f"  QP ID: {qp_id}")
    print(f"  Questions: {total_questions}")
    print("-"*70)
    print("  Commands: /quit, /state, /reset, /help")
    print("="*70 + "\n")


def print_help():
    """Print help message."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║  AVAILABLE COMMANDS                                              ║
╠══════════════════════════════════════════════════════════════════╣
║  /quit, /exit  - End the test session                           ║
║  /state        - Show current agent state                        ║
║  /reset        - Start a fresh session (new thread_id)           ║
║  /help         - Show this help message                          ║
║                                                                  ║
║  TEST SCENARIOS TO TRY:                                          ║
║  ─────────────────────────────────────────────────────────────── ║
║  • "I'm ready"           - Normal flow, should start questions   ║
║  • "What's your name?"   - Off-topic, should redirect            ║
║  • "Skip" / "Next"       - Skip current question                 ║
║  • "I don't understand"  - Clarification request                 ║
║  • "End the exam"        - Early termination request             ║
║  • "Hmm... I think..."   - Partial/uncertain answer              ║
║  • "HELLO" (shouting)    - Handle case variations                ║
║  • ""                    - Empty input                           ║
╚══════════════════════════════════════════════════════════════════╝
""")


def show_state(state: State):
    """Display current state in a readable format."""
    print("\n" + "-"*50)
    print("📊 CURRENT STATE:")
    print(f"  • thread_id: {state.get('thread_id', 'N/A')}")
    print(f"  • qp_id: {state.get('qp_id', 'N/A')}")
    print(f"  • mode: {state.get('mode', 'N/A')}")
    print(f"  • current_index: {state.get('current_index', 0)}")
    print(f"  • total_questions: {state.get('total_questions', 0)}")
    print(f"  • exam_started: {state.get('exam_started', False)}")
    print(f"  • response_type: {state.get('response_type', 'N/A')}")
    
    current_q = state.get('current_question')
    if current_q:
        print(f"  • current_question: {current_q.get('text', 'N/A')[:60]}...")
    else:
        print(f"  • current_question: None")
    
    print(f"  • message_count: {len(state.get('messages', []))}")
    print("-"*50 + "\n")


def run_interactive_session(mode: str = "exam", qp_id: Optional[str] = None):
    """Run an interactive test session with the exam agent."""
    
    # Default QP ID if not provided - look for any available
    if not qp_id:
        from redis import Redis
        r = Redis(host="localhost", port=6379, decode_responses=True)
        keys = list(r.scan_iter("qp:*:questions"))
        if keys:
            # Extract QP ID from first key: "qp:<id>:questions"
            qp_id = keys[0].split(":")[1]
            print(f"📋 Found QP in Redis: {qp_id}")
        else:
            print("❌ No question papers found in Redis. Create one first.")
            return
    
    # Preload first question
    first_question, total_questions = preload_first_question(qp_id)
    
    if not first_question:
        print(f"❌ Could not load question paper: {qp_id}")
        return
    
    # Generate unique thread ID
    thread_id = f"test_{mode}_{int(time.time())}"
    
    print_banner(mode, qp_id, total_questions)
    
    # Initialize state
    current_state = State(
        messages=[],
        thread_id=thread_id,
        qp_id=qp_id,
        current_index=0,
        mode=mode,
        current_question=first_question,
        total_questions=total_questions,
        exam_started=False,
        duration_minutes=15,
    )
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # First invocation - trigger greeting
    print("🤖 Agent is connecting...")
    print("-"*50)
    
    # Send initial trigger to get greeting
    greeting_state = State(
        messages=[HumanMessage(content="[SESSION_START]")],
        thread_id=thread_id,
        qp_id=qp_id,
        current_index=0,
        mode=mode,
        current_question=first_question,
        total_questions=total_questions,
        exam_started=False,
        duration_minutes=15,
    )
    
    start_time = time.time()
    result = graph.invoke(greeting_state, config=config)
    latency = (time.time() - start_time) * 1000
    
    # Extract and display AI response
    for msg in result["messages"]:
        if isinstance(msg, AIMessage) and msg.content:
            print(f"\n🤖 AGENT: {msg.content}")
            print(f"   [latency: {latency:.0f}ms]")
    
    current_state = result
    
    # Interactive loop
    while True:
        try:
            user_input = input("\n👤 YOU: ").strip()
            
            # Handle commands
            if user_input.lower() in ["/quit", "/exit"]:
                print("\n👋 Ending session. Goodbye!")
                break
            
            if user_input.lower() == "/state":
                show_state(current_state)
                continue
            
            if user_input.lower() == "/help":
                print_help()
                continue
            
            if user_input.lower() == "/reset":
                thread_id = f"test_{mode}_{int(time.time())}"
                config = {"configurable": {"thread_id": thread_id}}
                first_question, total_questions = preload_first_question(qp_id)
                current_state = State(
                    messages=[],
                    thread_id=thread_id,
                    qp_id=qp_id,
                    current_index=0,
                    mode=mode,
                    current_question=first_question,
                    total_questions=total_questions,
                    exam_started=False,
                    duration_minutes=15,
                )
                print("🔄 Session reset. New thread ID:", thread_id)
                continue
            
            if not user_input:
                print("   (empty input - type something or /help)")
                continue
            
            # Invoke agent with user message
            new_state = State(
                messages=[HumanMessage(content=user_input)],
                thread_id=thread_id,
                qp_id=qp_id,
                current_index=current_state.get("current_index", 0),
                mode=mode,
                current_question=current_state.get("current_question"),
                total_questions=total_questions,
                exam_started=True,  # After greeting, exam has started
            )
            
            start_time = time.time()
            result = graph.invoke(new_state, config=config)
            latency = (time.time() - start_time) * 1000
            
            # Extract and display AI response
            for msg in result["messages"]:
                if isinstance(msg, AIMessage) and msg.content:
                    print(f"\n🤖 AGENT: {msg.content}")
                    
            print(f"   [latency: {latency:.0f}ms | q{result.get('current_index', 0)+1}/{total_questions}]")
            
            current_state = result
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Parse arguments
    mode = "exam"
    qp_id = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ["exam", "learn"]:
            mode = args[i]
        elif args[i] == "--qp" and i + 1 < len(args):
            qp_id = args[i + 1]
            i += 1
        i += 1
    
    run_interactive_session(mode=mode, qp_id=qp_id)
