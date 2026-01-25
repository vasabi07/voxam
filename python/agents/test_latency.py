"""
Latency test for exam agent - measures response times for different scenarios.
Also checks if emit_thinking intermediate responses are being generated.

Run with: python agents/test_latency.py
"""
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY not set")
    sys.exit(1)

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from agents.exam_agent import graph, State, preload_first_question
from redis import Redis

# Test Redis connection
r = Redis(host="localhost", port=6379, decode_responses=True)
try:
    r.ping()
    print("✅ Redis connected")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    sys.exit(1)

# Set up test question paper
TEST_QP_ID = "test_qp_latency"
TEST_QUESTIONS = [
    {
        "text": "What is photosynthesis?",
        "question_type": "long_answer",
        "options": [],
        "context": "Chapter 3 - Plant Biology",
        "expected_time": 5,
        "difficulty": "basic",
        "bloom_level": "understand",
        "correct_answer": "Process by which plants convert sunlight to energy",
        "key_points": ["sunlight", "chlorophyll", "glucose", "oxygen"],
    },
    {
        "text": "Which organelle is responsible for photosynthesis?",
        "question_type": "mcq",
        "options": ["A. Mitochondria", "B. Chloroplast", "C. Nucleus", "D. Ribosome"],
        "context": "Chapter 3 - Plant Biology",
        "expected_time": 2,
        "difficulty": "basic",
        "bloom_level": "remember",
        "correct_answer": "B",
        "key_points": ["chloroplast contains chlorophyll"],
    },
]

r.json().set(f"qp:{TEST_QP_ID}:questions", "$", TEST_QUESTIONS)
print(f"✅ Test QP stored: {TEST_QP_ID}\n")

# Test scenarios with expected behavior
SCENARIOS = [
    {
        "name": "simple_answer",
        "input": "I think photosynthesis is when plants use sunlight to make food",
        "description": "Simple answer - should be fast, NO tools",
    },
    {
        "name": "next_question",
        "input": "next",
        "description": "Move to next - needs advance_to_next_question tool",
    },
    {
        "name": "hint_request",
        "input": "Can you give me a hint?",
        "description": "Edge case - may use emit_thinking + get_rules",
    },
    {
        "name": "off_topic",
        "input": "What's your favorite color?",
        "description": "Off topic - may use emit_thinking + get_rules",
    },
]


def run_scenario(scenario: dict, thread_id: str) -> dict:
    """Run scenario and measure latency."""
    print(f"\n{'='*70}")
    print(f"🧪 {scenario['name'].upper()}: {scenario['description']}")
    print(f"📝 Input: \"{scenario['input']}\"")
    print(f"{'='*70}")

    first_question, total = preload_first_question(TEST_QP_ID)

    state = State(
        messages=[HumanMessage(content=scenario["input"])],
        thread_id=thread_id,
        qp_id=TEST_QP_ID,
        current_index=0,
        current_question=first_question,
        total_questions=total,
        exam_started=True,
    )

    config = {"configurable": {"thread_id": thread_id}}

    # Measure latency
    start = time.time()
    result = graph.invoke(state, config=config)
    latency = time.time() - start

    # Analyze messages
    tool_calls = []
    ai_messages = []
    tool_messages = []
    thinking_messages = []

    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(tc.get("name", "unknown"))
            if msg.content:
                ai_messages.append(msg.content[:100])
                # Check if this is a thinking message (short, acknowledgment-like)
                if len(msg.content) < 30 and any(w in msg.content.lower() for w in ["moment", "check", "sure", "let me"]):
                    thinking_messages.append(msg.content)
        elif isinstance(msg, ToolMessage):
            tool_messages.append(f"{msg.content[:50]}...")

    # Results
    print(f"\n⏱️  LATENCY: {latency*1000:.0f}ms ({latency:.2f}s)")
    print(f"\n📊 MESSAGE BREAKDOWN:")
    print(f"   Tool calls: {len(tool_calls)} → {tool_calls[:5]}{'...' if len(tool_calls) > 5 else ''}")
    print(f"   AI messages: {len(ai_messages)}")
    print(f"   Tool messages: {len(tool_messages)}")
    print(f"   Thinking messages (intermediate): {len(thinking_messages)}")

    if thinking_messages:
        print(f"\n💭 INTERMEDIATE RESPONSES (emit_thinking → AIMessage):")
        for t in thinking_messages[:3]:
            print(f"   → \"{t}\"")

    # Final response
    final_response = ai_messages[-1] if ai_messages else "None"
    print(f"\n🤖 FINAL RESPONSE: \"{final_response}...\"")

    return {
        "name": scenario["name"],
        "latency_ms": latency * 1000,
        "tool_calls": len(tool_calls),
        "thinking_count": len(thinking_messages),
        "final_response": final_response,
    }


def main():
    print("\n" + "="*70)
    print("📊 EXAM AGENT LATENCY TEST")
    print("="*70)

    results = []
    for i, scenario in enumerate(SCENARIOS):
        thread_id = f"latency_test_{i}_{int(time.time())}"
        try:
            result = run_scenario(scenario, thread_id)
            results.append(result)
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({"name": scenario["name"], "latency_ms": -1, "error": str(e)})

    # Summary table
    print("\n" + "="*70)
    print("📊 LATENCY SUMMARY")
    print("="*70)
    print(f"{'Scenario':<20} {'Latency':<12} {'Tools':<8} {'Thinking':<10}")
    print("-"*50)
    for res in results:
        latency = f"{res['latency_ms']:.0f}ms" if res.get('latency_ms', -1) > 0 else "ERROR"
        tools = res.get('tool_calls', 0)
        thinking = res.get('thinking_count', 0)
        print(f"{res['name']:<20} {latency:<12} {tools:<8} {thinking:<10}")

    # Cleanup
    redis_client = Redis(host="localhost", port=6379, decode_responses=True)
    redis_client.delete(f"qp:{TEST_QP_ID}:questions")
    print(f"\n🧹 Cleaned up test QP")


if __name__ == "__main__":
    main()
