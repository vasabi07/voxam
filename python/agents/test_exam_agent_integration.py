"""
Integration test for exam agent with actual LLM calls.
Requires Redis to be running.

Run with: python agents/test_exam_agent_integration.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Verify environment
if not os.getenv("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY not set")
    sys.exit(1)

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agents.exam_agent import (
    graph, State, preload_first_question,
    EXAM_MODE_PROMPT, GREETING_PROMPT, RULES_DIR
)
from redis import Redis
import json

# Test Redis connection
r = Redis(host="localhost", port=6379, decode_responses=True)
try:
    r.ping()
    print("✅ Redis connected")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    sys.exit(1)

# Set up test question paper in Redis
TEST_QP_ID = "test_qp_integration"
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

# Store test QP in Redis
r.json().set(f"qp:{TEST_QP_ID}:questions", "$", TEST_QUESTIONS)
print(f"✅ Test QP stored in Redis: {TEST_QP_ID}")

# Test scenarios
SCENARIOS = [
    {
        "name": "hint_request",
        "input": "Can you give me a hint please?",
        "expect_tool_calls": ["emit_thinking", "get_rules"],
        "expect_not_in_response": ["hint is", "consider the", "think about"],
        "expect_in_response": ["cannot", "unable", "exam"],
    },
    {
        "name": "off_topic",
        "input": "What's the weather like today?",
        "expect_tool_calls": ["emit_thinking", "get_rules"],
        "expect_in_response": ["exam", "question", "assessment", "focus"],
    },
    {
        "name": "answer_acknowledgment",
        "input": "I think photosynthesis is the process where plants use sunlight to make food",
        "expect_not_in_response": ["correct", "wrong", "good answer", "well done"],
        "expect_in_response": ["recorded", "noted", "answer", "next"],
    },
    {
        "name": "frustration",
        "input": "This is too hard, I don't know anything",
        "expect_tool_calls": ["emit_thinking", "get_rules"],
        "expect_in_response": ["skip", "next", "move on", "okay"],
    },
]


def run_scenario(scenario: dict, thread_id: str) -> dict:
    """Run a single test scenario and return results."""
    print(f"\n{'='*60}")
    print(f"🧪 SCENARIO: {scenario['name']}")
    print(f"📝 Input: {scenario['input']}")
    print(f"{'='*60}")

    # Preload question
    first_question, total = preload_first_question(TEST_QP_ID)

    # Create state
    state = State(
        messages=[HumanMessage(content=scenario["input"])],
        thread_id=thread_id,
        qp_id=TEST_QP_ID,
        current_index=0,
        current_question=first_question,
        total_questions=total,
        exam_started=True,  # Skip greeting
    )

    config = {"configurable": {"thread_id": thread_id}}

    # Run the graph
    result = graph.invoke(state, config=config)

    # Extract tool calls and response
    tool_calls = []
    ai_response = ""

    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(tc.get("name", "unknown"))
            if msg.content:
                ai_response = msg.content

    print(f"\n🔧 Tool calls: {tool_calls}")
    print(f"🤖 Response: {ai_response[:200]}...")

    # Check expectations
    results = {
        "name": scenario["name"],
        "tool_calls": tool_calls,
        "response": ai_response,
        "passed": True,
        "failures": [],
    }

    # Check expected tool calls
    if "expect_tool_calls" in scenario:
        for expected_tool in scenario["expect_tool_calls"]:
            if expected_tool not in tool_calls:
                results["passed"] = False
                results["failures"].append(f"Missing tool call: {expected_tool}")

    # Check expected phrases in response
    if "expect_in_response" in scenario:
        response_lower = ai_response.lower()
        found_any = any(phrase.lower() in response_lower for phrase in scenario["expect_in_response"])
        if not found_any:
            results["passed"] = False
            results["failures"].append(f"Response missing expected phrases: {scenario['expect_in_response']}")

    # Check phrases that should NOT be in response
    if "expect_not_in_response" in scenario:
        response_lower = ai_response.lower()
        for phrase in scenario["expect_not_in_response"]:
            if phrase.lower() in response_lower:
                results["passed"] = False
                results["failures"].append(f"Response contains forbidden phrase: '{phrase}'")

    return results


def main():
    print("\n" + "="*60)
    print("🚀 EXAM AGENT INTEGRATION TEST")
    print("="*60)

    all_results = []

    for i, scenario in enumerate(SCENARIOS):
        thread_id = f"test_integration_{i}"
        try:
            result = run_scenario(scenario, thread_id)
            all_results.append(result)
        except Exception as e:
            print(f"❌ ERROR in scenario {scenario['name']}: {e}")
            import traceback
            traceback.print_exc()
            all_results.append({
                "name": scenario["name"],
                "passed": False,
                "failures": [str(e)],
            })

    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)

    passed = sum(1 for r in all_results if r["passed"])
    failed = len(all_results) - passed

    for result in all_results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status} - {result['name']}")
        if result.get("failures"):
            for failure in result["failures"]:
                print(f"       └─ {failure}")

    print(f"\n{'='*60}")
    print(f"Total: {passed}/{len(all_results)} passed")
    print(f"{'='*60}")

    # Cleanup
    r.delete(f"qp:{TEST_QP_ID}:questions")
    print(f"\n🧹 Cleaned up test QP from Redis")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
