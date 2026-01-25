"""
LLM-based behavioral test for the Learn Agent conversational flow.

Tests the agent's behavior WITHOUT requiring Redis/Neo4j/Supabase connections.
Uses mocked tool responses to simulate the full conversational flow.

Run: python -m agents.test_learn_agent_conversational
"""

import os
import json
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Mock data for testing
MOCK_DOCUMENTS = [
    {"id": "doc-001", "title": "Biology Chapter 5 - Photosynthesis"},
    {"id": "doc-002", "title": "Physics Unit 3 - Motion"},
    {"id": "doc-003", "title": "Chemistry Organic Reactions"},
]

MOCK_TOPICS = [
    "Introduction to Photosynthesis",
    "Light-Dependent Reactions",
    "Calvin Cycle",
    "Factors Affecting Photosynthesis",
    "Photosynthesis vs Cellular Respiration",
]

MOCK_TOPIC_CONTENT = {
    "name": "Light-Dependent Reactions",
    "content": """The light-dependent reactions occur in the thylakoid membrane of chloroplasts.
These reactions capture light energy and convert it to chemical energy in the form of ATP and NADPH.

Key steps:
1. Light absorption by chlorophyll pigments
2. Water splitting (photolysis) releasing oxygen
3. Electron transport chain
4. ATP synthesis via chemiosmosis
5. NADPH formation

The overall equation: 2H2O + 2NADP+ + 3ADP + 3Pi → O2 + 2NADPH + 3ATP""",
    "key_concepts": ["chlorophyll", "thylakoid", "ATP", "NADPH", "electron transport chain", "photolysis"],
    "pages": [45, 46, 47],
}


def create_test_llm():
    """Create LLM for testing."""
    return ChatOpenAI(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.3,
        max_tokens=500
    )


def test_greeting_phase():
    """Test: Agent should greet and offer to fetch documents."""
    print("\n" + "="*60)
    print("TEST 1: Greeting Phase")
    print("="*60)

    llm = create_test_llm()

    system_prompt = """You are a friendly learning tutor starting a voice study session.

**YOUR FIRST TURN:**
- Welcome the student warmly and conversationally
- Say: "Let me grab your documents real quick..."
- You MUST call fetch_user_documents(user_id) to get their docs

**TONE:** Casual, friendly, like a helpful study buddy.
Keep responses SHORT - this is a voice conversation.

You have the following tool available:
- fetch_user_documents(user_id: str): Fetches user's documents

Respond naturally, then indicate you want to call the tool."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Hey, I want to study")
    ]

    response = llm.invoke(messages)
    print(f"\nStudent: Hey, I want to study")
    print(f"\nAgent: {response.content}")

    # Check behavior
    content_lower = response.content.lower()

    checks = {
        "Greets student warmly": any(w in content_lower for w in ["hey", "hi", "hello", "welcome"]),
        "Mentions fetching documents": any(w in content_lower for w in ["document", "grab", "fetch", "get", "materials", "notes"]),
        "Conversational tone": len(response.content) < 300,  # Short for voice
    }

    print("\n--- Behavioral Checks ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    return all(checks.values())


def test_document_selection_phase():
    """Test: Agent should present documents and help user choose."""
    print("\n" + "="*60)
    print("TEST 2: Document Selection Phase")
    print("="*60)

    llm = create_test_llm()

    docs_list = ", ".join([f"'{d['title']}'" for d in MOCK_DOCUMENTS])

    system_prompt = f"""The student is choosing which document to study.

**AVAILABLE DOCUMENTS:**
{docs_list}

**YOUR TASK:**
- Present the documents conversationally
- Ask which one they want to study
- When they pick one, confirm their choice

**TONE:** Supportive, no rush. Keep it SHORT for voice."""

    # Simulate tool result already received
    tool_result = json.dumps({
        "found": True,
        "documents": MOCK_DOCUMENTS,
        "message": "Found 3 documents"
    })

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="I want to study"),
        AIMessage(content="Let me grab your documents..."),
        ToolMessage(content=tool_result, tool_call_id="test"),
    ]

    response = llm.invoke(messages)
    print(f"\n[Tool returned 3 documents]")
    print(f"\nAgent: {response.content}")

    # Check behavior
    content_lower = response.content.lower()

    checks = {
        "Mentions available documents": any(d["title"].lower()[:10] in content_lower for d in MOCK_DOCUMENTS) or "document" in content_lower,
        "Asks for choice": any(w in content_lower for w in ["which", "what", "choose", "pick", "want", "interested"]),
        "Conversational (not a list)": not content_lower.startswith("1.") and not content_lower.startswith("-"),
    }

    print("\n--- Behavioral Checks ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    return all(checks.values())


def test_topic_selection_phase():
    """Test: Agent should present topics and help user choose."""
    print("\n" + "="*60)
    print("TEST 3: Topic Selection Phase")
    print("="*60)

    llm = create_test_llm()

    topics_list = ", ".join(MOCK_TOPICS)

    system_prompt = f"""The student is choosing a topic from their document.

**DOCUMENT:** Biology Chapter 5 - Photosynthesis
**AVAILABLE TOPICS:** {topics_list}

**YOUR TASK:**
- Present the topics conversationally (not a boring numbered list)
- Ask: "Which one sounds interesting to you?"
- Be curious and encouraging

**TONE:** Curious, encouraging exploration. Keep it SHORT for voice."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Let's do Biology"),
        AIMessage(content="Great choice! Let me see what topics are in there..."),
        ToolMessage(content=json.dumps({"found": True, "topics": MOCK_TOPICS}), tool_call_id="test"),
    ]

    response = llm.invoke(messages)
    print(f"\n[Tool returned 5 topics]")
    print(f"\nAgent: {response.content}")

    # Check behavior
    content_lower = response.content.lower()

    checks = {
        "Mentions some topics": any(t.lower()[:8] in content_lower for t in MOCK_TOPICS) or "topic" in content_lower,
        "Asks for preference": any(w in content_lower for w in ["which", "interest", "want", "explore", "start", "dive"]),
        "Encouraging tone": any(w in content_lower for w in ["sounds", "interesting", "cool", "great", "awesome", "let's"]),
    }

    print("\n--- Behavioral Checks ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    return all(checks.values())


def test_teaching_phase_overview():
    """Test: Agent should offer overview vs dive-in choice after loading content."""
    print("\n" + "="*60)
    print("TEST 4: Teaching Phase - Overview Offer")
    print("="*60)

    llm = create_test_llm()

    topic = MOCK_TOPIC_CONTENT

    system_prompt = f"""You are tutoring the student on a specific topic via voice.

**TOPIC:** {topic['name']}
**CONTENT:** {topic['content'][:500]}
**KEY CONCEPTS:** {', '.join(topic['key_concepts'])}

**AFTER LOADING CONTENT, ASK:**
"Got it! Do you want me to give you a quick overview of {topic['name']}, or do you just want to dive in and ask questions?"

**REMEMBER:** This is VOICE - keep responses SHORT."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Let's do light dependent reactions"),
        AIMessage(content="Alright, let me grab those notes..."),
        ToolMessage(content=json.dumps({"found": True, "topic": topic}), tool_call_id="test"),
    ]

    response = llm.invoke(messages)
    print(f"\n[Tool loaded topic content]")
    print(f"\nAgent: {response.content}")

    # Check behavior
    content_lower = response.content.lower()

    checks = {
        "Confirms content loaded": any(w in content_lower for w in ["got it", "loaded", "ready", "found", "here"]),
        "Offers overview option": any(w in content_lower for w in ["overview", "summary", "quick", "explain", "walk through"]),
        "Offers questions option": any(w in content_lower for w in ["question", "dive", "ask", "start"]),
        "Short for voice": len(response.content) < 400,
    }

    print("\n--- Behavioral Checks ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    return all(checks.values())


def test_teaching_phase_explanation():
    """Test: Agent should give a clear explanation from content."""
    print("\n" + "="*60)
    print("TEST 5: Teaching Phase - Explanation")
    print("="*60)

    llm = create_test_llm()

    topic = MOCK_TOPIC_CONTENT

    system_prompt = f"""You are tutoring the student on a specific topic via voice.

**TOPIC:** {topic['name']}
**CONTENT:** {topic['content']}
**KEY CONCEPTS:** {', '.join(topic['key_concepts'])}

**TEACHING STYLE:**
- Answer from the content provided
- Keep explanations clear and voice-friendly
- Check understanding: "Does that make sense?"

**REMEMBER:** This is VOICE - keep responses SHORT (2-3 sentences max unless explaining)."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Give me a quick overview"),
    ]

    response = llm.invoke(messages)
    print(f"\nStudent: Give me a quick overview")
    print(f"\nAgent: {response.content}")

    # Check behavior
    content_lower = response.content.lower()

    checks = {
        "Explains the topic": any(w in content_lower for w in ["light", "energy", "chloroplast", "thylakoid", "atp", "electron"]),
        "Voice-appropriate length": 50 < len(response.content) < 800,
        "Checks understanding": any(w in content_lower for w in ["sense", "question", "clear", "follow", "understand"]),
    }

    print("\n--- Behavioral Checks ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    return all(checks.values())


def test_confusion_handling():
    """Test: Agent should handle confusion with patience."""
    print("\n" + "="*60)
    print("TEST 6: Edge Case - Confusion Handling")
    print("="*60)

    llm = create_test_llm()

    topic = MOCK_TOPIC_CONTENT

    system_prompt = f"""You are tutoring the student on a specific topic via voice.

**TOPIC:** {topic['name']}
**CONTENT:** {topic['content']}

**WHEN STUDENT IS CONFUSED:**
- Say "No problem, let me try a different approach..."
- Use simpler language or a new analogy
- Break into smaller pieces
- Check: "Is that clearer?"

DO NOT just repeat the same explanation verbatim."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="I don't understand the electron transport chain at all"),
    ]

    response = llm.invoke(messages)
    print(f"\nStudent: I don't understand the electron transport chain at all")
    print(f"\nAgent: {response.content}")

    # Check behavior
    content_lower = response.content.lower()

    checks = {
        "Acknowledges confusion": any(w in content_lower for w in ["no problem", "okay", "that's", "tricky", "let me", "try"]),
        "Uses simpler language or analogy": any(w in content_lower for w in ["think of", "like", "imagine", "basically", "simple", "chain"]),
        "Doesn't dismiss": "not important" not in content_lower and "too hard" not in content_lower,
    }

    print("\n--- Behavioral Checks ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    return all(checks.values())


def test_topic_switch():
    """Test: Agent should handle topic switch gracefully."""
    print("\n" + "="*60)
    print("TEST 7: Edge Case - Topic Switch Request")
    print("="*60)

    llm = create_test_llm()

    topic = MOCK_TOPIC_CONTENT

    system_prompt = f"""You are tutoring the student on a specific topic via voice.

**CURRENT TOPIC:** {topic['name']}

**SWITCHING TOPICS:**
When they say "let's do something else":
1. Give a brief summary (1 sentence)
2. Say "Sure! What else would you like to explore?"

Be supportive of exploration."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Can we switch to a different topic?"),
    ]

    response = llm.invoke(messages)
    print(f"\nStudent: Can we switch to a different topic?")
    print(f"\nAgent: {response.content}")

    # Check behavior
    content_lower = response.content.lower()

    checks = {
        "Agrees to switch": any(w in content_lower for w in ["sure", "of course", "absolutely", "yeah", "yes", "no problem"]),
        "Offers transition": any(w in content_lower for w in ["what", "which", "explore", "next", "else", "another"]),
        "Supportive tone": "no" not in content_lower[:20] or "sure" in content_lower,
    }

    print("\n--- Behavioral Checks ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    return all(checks.values())


def test_reconnection_message():
    """Test: Reconnection should provide context."""
    print("\n" + "="*60)
    print("TEST 8: Reconnection Handling")
    print("="*60)

    llm = create_test_llm()

    system_prompt = """You are resuming a tutoring session after the student disconnected.

**CONTEXT:**
- You were discussing "Light-Dependent Reactions"
- The student had just asked about the Calvin Cycle

**YOUR TASK:**
- Welcome them back warmly
- Remind them where you were
- Ask if they want to continue or switch

Keep it SHORT and voice-friendly."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="(Student reconnected)"),
    ]

    response = llm.invoke(messages)
    print(f"\n[Student reconnected to session]")
    print(f"\nAgent: {response.content}")

    # Check behavior
    content_lower = response.content.lower()

    checks = {
        "Welcomes back": any(w in content_lower for w in ["welcome back", "back", "hey again", "there you are"]),
        "Provides context": any(w in content_lower for w in ["were", "discussing", "talking", "left off", "light", "reaction"]),
        "Offers choice": any(w in content_lower for w in ["continue", "ready", "where", "want", "switch"]),
    }

    print("\n--- Behavioral Checks ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    return all(checks.values())


def run_all_tests():
    """Run all behavioral tests."""
    print("\n" + "="*60)
    print("🧪 LEARN AGENT BEHAVIORAL TESTS")
    print("="*60)
    print("Testing conversational flow and edge case handling...")

    results = {
        "Greeting Phase": test_greeting_phase(),
        "Document Selection": test_document_selection_phase(),
        "Topic Selection": test_topic_selection_phase(),
        "Teaching - Overview Offer": test_teaching_phase_overview(),
        "Teaching - Explanation": test_teaching_phase_explanation(),
        "Confusion Handling": test_confusion_handling(),
        "Topic Switch": test_topic_switch(),
        "Reconnection": test_reconnection_message(),
    }

    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All behavioral tests passed!")
    else:
        print(f"\n⚠️ {total - passed} test(s) need attention")

    return passed == total


if __name__ == "__main__":
    run_all_tests()
