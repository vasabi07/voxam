"""
Test: Multi-step exam responses with intermediate messages.

Example flow:
  Student: "I don't know"
  Agent: "Hmm, that's okay. Let me give you a simpler version..."  ← SPEAK
  [Rewrite question]
  Agent: "Here's an easier way to think about it: ..."  ← SPEAK

This adds realism to the exam agent by showing "thinking" before adapting.
"""

import asyncio
from typing import Literal, Optional, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
import os

load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")


# ============================================================
# STATE
# ============================================================

class ExamMultistepState(TypedDict):
    messages: list
    student_answer: str
    current_question: dict
    mode: str  # "exam" or "learn"

    # Multi-step state
    needs_simplification: bool
    simplified_question: Optional[str]
    thinking_message_emitted: bool


# ============================================================
# MOCK QUESTION
# ============================================================

MOCK_QUESTION = {
    "text": "Explain the process of oxidative phosphorylation and its role in ATP synthesis.",
    "type": "long_answer",
    "key_points": ["electron transport chain", "proton gradient", "ATP synthase"],
    "difficulty": "hard"
}


# ============================================================
# NODES
# ============================================================

def analyze_answer(state: ExamMultistepState) -> dict:
    """Check if student needs help (struggling/confused)."""
    answer = state["student_answer"].lower()
    mode = state.get("mode", "learn")

    # Detect struggling patterns
    struggling_patterns = [
        "i don't know",
        "i'm not sure",
        "can you explain",
        "i'm confused",
        "what?",
        "huh?",
        "no idea",
        "help",
        "too hard",
        "don't understand"
    ]

    needs_help = any(p in answer for p in struggling_patterns)

    # In EXAM mode, don't simplify (strict). In LEARN mode, adapt.
    needs_simplification = needs_help and mode == "learn"

    print(f"🔍 [analyze] Answer: '{answer}' | Needs help: {needs_help} | Mode: {mode}")

    return {
        "needs_simplification": needs_simplification,
        "thinking_message_emitted": False
    }


def emit_thinking_message(state: ExamMultistepState) -> dict:
    """
    Emit the "thinking" message - spoken BEFORE simplification.
    This makes the agent feel more natural/human.
    """
    print(f"💭 [thinking] Emitting thinking message...")

    thinking_responses = [
        "Hmm, that's okay. Let me think of a simpler way to ask this...",
        "No worries! Let me rephrase that for you...",
        "That's a tricky one. Let me break it down differently...",
    ]

    import random
    message = random.choice(thinking_responses)

    return {
        "messages": state["messages"] + [AIMessage(content=message)],
        "thinking_message_emitted": True
    }


def simplify_question(state: ExamMultistepState) -> dict:
    """
    Actually simplify the question (could use LLM in production).
    This runs AFTER the thinking message is spoken.
    """
    print(f"🔄 [simplify] Rewriting question...")

    # Simulate LLM thinking time
    import time
    time.sleep(1)  # In production, this would be actual LLM call

    # Simplified version
    simplified = """
    Let's break it down: In your cells, there's a process that makes energy (ATP).
    It happens in the mitochondria.
    Can you tell me what the mitochondria is often called, and why it needs oxygen?
    """

    return {
        "simplified_question": simplified.strip()
    }


def respond_with_simplified(state: ExamMultistepState) -> dict:
    """Final response with the simplified question."""
    simplified = state.get("simplified_question", "")

    print(f"💬 [respond] Delivering simplified question...")

    return {
        "messages": state["messages"] + [
            AIMessage(content=f"Here's an easier way to think about it: {simplified}")
        ]
    }


def respond_normally(state: ExamMultistepState) -> dict:
    """Normal response (answer was fine, no simplification needed)."""
    print(f"💬 [respond] Normal acknowledgment...")

    return {
        "messages": state["messages"] + [
            AIMessage(content="Got it! Let me note that down. Ready for the next question?")
        ]
    }


# ============================================================
# ROUTING
# ============================================================

def route_after_analysis(state: ExamMultistepState) -> str:
    if state.get("needs_simplification"):
        return "emit_thinking"
    return "respond_normally"


# ============================================================
# BUILD GRAPH
# ============================================================

def build_exam_multistep_graph():
    workflow = StateGraph(ExamMultistepState)

    workflow.add_node("analyze", analyze_answer)
    workflow.add_node("emit_thinking", emit_thinking_message)
    workflow.add_node("simplify", simplify_question)
    workflow.add_node("respond_simplified", respond_with_simplified)
    workflow.add_node("respond_normally", respond_normally)

    workflow.set_entry_point("analyze")

    workflow.add_conditional_edges("analyze", route_after_analysis, {
        "emit_thinking": "emit_thinking",
        "respond_normally": "respond_normally"
    })

    # Multi-step path: think → simplify → respond
    workflow.add_edge("emit_thinking", "simplify")
    workflow.add_edge("simplify", "respond_simplified")
    workflow.add_edge("respond_simplified", END)

    # Normal path
    workflow.add_edge("respond_normally", END)

    return workflow.compile()


# ============================================================
# STREAMING PROCESSOR
# ============================================================

async def mock_tts(text: str):
    """Simulate TTS."""
    print(f"\n🔊 [TTS]: {text}")
    await asyncio.sleep(len(text.split()) * 0.08)
    print(f"   ✅ [TTS DONE]\n")


async def process_student_answer(graph, answer: str, mode: str = "learn"):
    """Process with streaming to capture intermediate messages."""

    print(f"\n{'='*60}")
    print(f"🎓 Student answer: '{answer}'")
    print(f"   Mode: {mode}")
    print(f"{'='*60}")

    initial_state = ExamMultistepState(
        messages=[HumanMessage(content=answer)],
        student_answer=answer,
        current_question=MOCK_QUESTION,
        mode=mode,
        needs_simplification=False,
        simplified_question=None,
        thinking_message_emitted=False
    )

    spoken_count = 1

    async for event in graph.astream(initial_state):
        for node_name, state_update in event.items():
            print(f"--- Node: {node_name} ---")

            if "messages" in state_update:
                for msg in state_update["messages"][spoken_count:]:
                    if isinstance(msg, AIMessage) and msg.content:
                        print(f"🆕 Message from {node_name}!")
                        await mock_tts(msg.content)
                        spoken_count += 1

    print(f"✅ Complete! Messages: {spoken_count - 1}")


# ============================================================
# TESTS
# ============================================================

async def run_tests():
    graph = build_exam_multistep_graph()

    print("\n" + "="*80)
    print("TEST 1: Student answers normally (no adaptation needed)")
    print("="*80)

    await process_student_answer(
        graph,
        "The electron transport chain creates a proton gradient...",
        mode="learn"
    )

    print("\n" + "="*80)
    print("TEST 2: Student is confused - LEARN mode (should adapt)")
    print("="*80)

    await process_student_answer(
        graph,
        "I don't know, this is too hard",
        mode="learn"
    )

    print("\n" + "="*80)
    print("TEST 3: Student is confused - EXAM mode (should NOT adapt)")
    print("="*80)

    await process_student_answer(
        graph,
        "I don't know, this is too hard",
        mode="exam"
    )


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  Exam Agent Multi-Step Response Test                                ║
║                                                                     ║
║  Demonstrates adaptive responses with intermediate messages:        ║
║                                                                     ║
║  LEARN mode (student confused):                                     ║
║    → "Hmm, let me think of a simpler way..."  [TTS SPEAKS]         ║
║    → [Rewrite question - 1s delay]                                  ║
║    → "Here's an easier way: ..."  [TTS SPEAKS]                      ║
║                                                                     ║
║  EXAM mode (strict):                                                ║
║    → "Got it! Ready for next question?"  [No adaptation]            ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(run_tests())
