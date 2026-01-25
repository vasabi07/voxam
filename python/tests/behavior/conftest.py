"""
Behavior test fixtures for exam agent quality evaluation.

These tests use LIVE LLM calls (real API costs).
"""
import pytest
import os
import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)


@pytest.fixture(scope="session")
def cerebras_llm():
    """Get the Cerebras LLM (gpt-oss-120b) for quality testing."""
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        pytest.skip("CEREBRAS_API_KEY not configured")

    return ChatOpenAI(
        model="gpt-oss-120b",
        api_key=api_key,
        base_url="https://api.cerebras.ai/v1",
        temperature=0
    )


@pytest.fixture(scope="session")
def exam_tools():
    """Get exam agent tools for binding."""
    from langchain_core.tools import tool

    @tool
    def advance_to_next_question(qp_id: str, current_index: int) -> dict:
        """Advance to the next question in the exam."""
        return {"done": False, "new_index": current_index + 1}

    @tool
    def search_conversation_history(query: str, thread_id: str) -> str:
        """Search conversation history for relevant exchanges."""
        return "No matching exchanges found."

    return [advance_to_next_question, search_conversation_history]


@pytest.fixture(scope="session")
def llm_with_tools(cerebras_llm, exam_tools):
    """LLM with exam tools bound."""
    return cerebras_llm.bind_tools(exam_tools)


@pytest.fixture
def sample_mcq_question():
    """Sample MCQ question for testing."""
    return {
        "text": "What is the primary function of mitochondria in a cell?",
        "question_type": "multiple_choice",
        "options": [
            "A) Store genetic information",
            "B) Produce ATP through cellular respiration",
            "C) Synthesize proteins",
            "D) Break down waste products"
        ],
        "context": "Mitochondria are membrane-bound organelles found in the cytoplasm of eukaryotic cells.",
        "correct_answer": "B",
        "key_points": [
            "ATP production",
            "Cellular respiration",
            "Powerhouse of the cell"
        ],
        "difficulty": "basic",
        "bloom_level": "remember"
    }


@pytest.fixture
def sample_long_answer_question():
    """Sample long answer question for testing."""
    return {
        "text": "Explain the process of photosynthesis and its importance to life on Earth.",
        "question_type": "long_answer",
        "options": [],
        "context": "Photosynthesis is a process used by plants and other organisms to convert light energy into chemical energy.",
        "correct_answer": "Photosynthesis converts CO2 and water into glucose and oxygen using sunlight.",
        "key_points": [
            "Light absorption by chlorophyll",
            "Carbon dioxide fixation",
            "Glucose production",
            "Oxygen release",
            "Foundation of food chains"
        ],
        "difficulty": "intermediate",
        "bloom_level": "understand"
    }


@pytest.fixture
def exam_mode_prompt():
    """EXAM mode system prompt."""
    return """You are a strict exam conductor conducting a formal examination via voice.

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
- WRONG: "That's a good start, but consider the chemical bonds..."
- CORRECT: "Answer recorded. Ready for the next question?"

- WRONG: "Let me explain this concept..."
- CORRECT: "This is an exam. I cannot provide explanations."

Exam: test-qp, Question {current_index} of {total_questions}.
Duration: 30 minutes."""


@pytest.fixture
def learn_mode_prompt():
    """LEARN mode system prompt."""
    return """You are an engaging learning tutor conducting a voice-based study session.

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

Question {current_index} of {total_questions}.
Remember: Deep understanding > number of questions covered."""


@pytest.fixture
def greeting_prompt():
    """Greeting prompt for first turn."""
    return """You just connected to a new exam/study session.

**YOUR FIRST TURN:**
- Welcome the student warmly but professionally
- State: This exam has {total_questions} questions, {duration_minutes} minutes
- Brief rules: "I'll read each question clearly. Say 'next' when ready to continue."
- Ask: "Ready to begin when you are!"

**DO NOT present the first question yet.** Wait for student confirmation."""


def build_question_context(question: dict, mode: str = "exam") -> str:
    """Build question context string for prompt injection."""
    q_type = question.get("question_type", "long_answer")
    options = question.get("options", [])

    context = f"""
[CURRENT QUESTION - DO NOT call advance_to_next_question unless moving to next]
Question: {question['text']}
Type: {q_type}
"""

    if q_type == "multiple_choice" and options:
        context += f"Options:\n" + "\n".join(f"  {opt}" for opt in options) + "\n"

    if mode == "learn":
        context += f"""
[USE TO HELP STUDENT - syllabus context]
{question.get('context', '')[:500]}

[REVEAL AFTER STUDENT ATTEMPTS]
Key Points: {', '.join(question.get('key_points', []))}
Correct Answer: {question.get('correct_answer', '')}
"""
    else:
        context += f"""
[INTERNAL REFERENCE - DO NOT reveal to student]
Syllabus context: {question.get('context', '')[:500]}
"""

    return context
