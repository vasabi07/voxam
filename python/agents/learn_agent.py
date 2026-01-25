"""
Learn Mode Agent for Voxam.
Fully conversational, zero-setup learning experience.

Key Design:
- NO pre-session setup required - agent discovers everything conversationally
- Student-driven: "What do you want to learn today?"
- Phases: greeting -> selecting_doc -> selecting_topic -> teaching

Flow:
1. Student joins call
2. Agent greets and fetches docs: "Let me grab your documents..."
3. Student picks doc (or agent shows options in UI)
4. Agent fetches topics: "What topic interests you?"
5. Student picks topic
6. Agent fetches content: "Let me grab the notes... Done!"
7. Student-driven learning with retriever support
"""

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.checkpoint.redis import RedisSaver
from dotenv import load_dotenv
from typing import List, Literal, Optional
from redis import Redis
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from pathlib import Path
import os
import json

# Import summary models and prompt
from agents.learn_session_summary import (
    LearnSessionSummary,
    TopicCoverage,
    SUMMARY_PROMPT
)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Context Management Thresholds
SUMMARIZATION_TRIGGER_THRESHOLD = 12
SUMMARIZATION_CHAR_THRESHOLD = 5000
CONTEXT_MESSAGES_TO_LLM = 4

# Rules directory
RULES_DIR = Path(__file__).parent / "rules"


class LearnState(MessagesState):
    """State for learn mode sessions with conversational discovery."""
    thread_id: str
    user_id: str  # Required for document fetch

    # Session phases
    phase: Literal["greeting", "selecting_doc", "selecting_topic", "teaching"] = "greeting"

    # Document selection
    available_documents: List[dict] = []  # [{id, title}]
    selected_doc_id: Optional[str] = None
    selected_doc_title: Optional[str] = None

    # Topic selection
    available_topics: List[str] = []  # Topic names
    selected_topic: Optional[str] = None
    current_topic_content: Optional[dict] = None  # {name, content, key_concepts, pages}

    # Legacy fields for backwards compatibility
    lp_id: Optional[str] = None
    current_topic_index: int = 0
    topics: List[dict] = []
    total_topics: int = 0
    current_topic: Optional[dict] = None

    # Session state
    session_started: bool = False

    # Web search
    web_search_offered: bool = False
    web_search_results: Optional[str] = None

    # Response metadata
    response_type: Optional[Literal[
        "greeting", "document_list", "topic_list", "topic_loaded",
        "teaching", "clarification", "next_topic", "summary",
        "searching", "web_search_result"
    ]] = None

    # Context Management
    running_summary: Optional[str] = None
    summary_message_index: int = 0

    # Content routing
    content_check_done: bool = False
    found_in_content: bool = True
    pending_web_search: bool = False
    search_query: Optional[str] = None
    search_results: Optional[str] = None

    # Cognitive grounding
    cognitive_level: Optional[str] = None

    # Reconnection
    is_reconnection: bool = False


# Redis initialization
REDIS_URI = "redis://localhost:6379"
checkpointer = None
try:
    with RedisSaver.from_conn_string(REDIS_URI) as _checkpointer:
        _checkpointer.setup()
        checkpointer = _checkpointer
except Exception as e:
    print(f"[ERROR] Could not connect to Redis at {REDIS_URI}: {e}")
    exit(1)

r = Redis(host="localhost", port=6379, decode_responses=True)


# ============================================================
# NEW TOOLS FOR CONVERSATIONAL DISCOVERY
# ============================================================

@tool
def fetch_user_documents(user_id: str) -> dict:
    """
    Fetch all READY documents uploaded by this user from Supabase.
    Call at session start: "Let me grab your documents..."

    The returned document IDs work in both Supabase AND Neo4j queries
    (Supabase Document.id = Neo4j Document.documentId).

    Returns:
        dict with 'found' (bool), 'documents' (list), and 'message' (str)
    """
    from supabase import create_client

    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return {
            "found": False,
            "documents": [],
            "message": "Server configuration error - cannot fetch documents."
        }

    try:
        supabase = create_client(supabase_url, supabase_key)
        result = supabase.table("Document").select(
            "id, title, status"
        ).eq("userId", user_id).eq("status", "READY").is_("archivedAt", "null").execute()

        documents = result.data or []

        if documents:
            return {
                "found": True,
                "documents": [
                    {"id": d["id"], "title": d["title"]}
                    for d in documents
                ],
                "message": f"Found {len(documents)} documents"
            }
        else:
            return {
                "found": False,
                "documents": [],
                "message": "No documents found. Upload something first!"
            }

    except Exception as e:
        print(f"[ERROR] fetch_user_documents: {e}")
        return {
            "found": False,
            "documents": [],
            "message": f"Error fetching documents: {str(e)}"
        }


@tool
def fetch_document_topics(doc_id: str) -> dict:
    """
    Fetch available topics (parent_headers) for a document from Neo4j.
    Call after user picks a document: "What topic interests you?"

    Returns:
        dict with 'found' (bool), 'topics' (list of strings), and 'message' (str)
    """
    from neo4j import GraphDatabase

    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_uri or not neo4j_user or not neo4j_password:
        return {
            "found": False,
            "topics": [],
            "message": "Neo4j configuration error."
        }

    query = """
    MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
    WHERE cb.parent_header IS NOT NULL AND cb.parent_header <> ''
    RETURN DISTINCT cb.parent_header AS topic
    ORDER BY topic
    """

    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        with driver.session() as session:
            result = session.run(query, doc_id=doc_id)
            topics = [r["topic"] for r in result]
        driver.close()

        if topics:
            return {
                "found": True,
                "topics": topics,
                "message": f"Found {len(topics)} topics"
            }
        else:
            return {
                "found": False,
                "topics": [],
                "message": "No topics found in this document."
            }

    except Exception as e:
        print(f"[ERROR] fetch_document_topics: {e}")
        return {
            "found": False,
            "topics": [],
            "message": f"Error fetching topics: {str(e)}"
        }


@tool
def fetch_topic_content(doc_id: str, topic_name: str) -> dict:
    """
    Fetch full content for a specific topic from Neo4j.
    Call after user picks a topic: "Let me grab the notes..."

    Returns:
        dict with 'found' (bool), 'topic' (dict with name, content, key_concepts, pages)
    """
    from neo4j import GraphDatabase

    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_uri or not neo4j_user or not neo4j_password:
        return {"found": False, "message": "Neo4j configuration error."}

    query = """
    MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
    WHERE cb.parent_header = $topic_name
    RETURN cb.text_content AS content, cb.page_start AS page, cb.block_id AS block_id
    ORDER BY cb.page_start
    """

    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        with driver.session() as session:
            result = session.run(query, doc_id=doc_id, topic_name=topic_name)
            blocks = list(result)
        driver.close()

        if not blocks:
            return {"found": False, "message": f"No content found for '{topic_name}'"}

        # Combine content
        full_content = "\n\n".join([b["content"] for b in blocks if b["content"]])
        pages = list(set([b["page"] for b in blocks if b["page"]]))

        # Extract key concepts using fast LLM
        key_concepts = extract_key_concepts(full_content)

        return {
            "found": True,
            "topic": {
                "name": topic_name,
                "content": full_content,
                "key_concepts": key_concepts,
                "pages": sorted(pages),
            }
        }

    except Exception as e:
        print(f"[ERROR] fetch_topic_content: {e}")
        return {"found": False, "message": f"Error fetching content: {str(e)}"}


def extract_key_concepts(content: str, max_concepts: int = 7) -> List[str]:
    """Extract key concepts from content using fast LLM."""
    try:
        concept_llm = ChatOpenAI(
            model="llama-3.1-8b-instant",
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            temperature=0,
            max_tokens=200
        )

        prompt = f"""Extract 3-7 key concepts from this educational text.
Return ONLY a comma-separated list of concept names, nothing else.

Text:
{content[:2000]}

Key concepts:"""

        response = concept_llm.invoke([SystemMessage(content=prompt)])
        concepts = [c.strip() for c in response.content.split(",") if c.strip()]
        return concepts[:max_concepts]

    except Exception as e:
        print(f"[WARN] Key concept extraction failed: {e}")
        return []


@tool
def search_document_content(query: str, doc_id: str, user_id: str) -> str:
    """
    Search the full document for relevant content using hybrid search.
    Use when student asks about something not in current topic.

    Args:
        query: What to search for
        doc_id: Document ID
        user_id: User ID for access control

    Returns:
        Relevant passages with page references
    """
    from retrieval import retrieve_context_with_sources

    try:
        context, sources = retrieve_context_with_sources(
            query_text=query,
            user_id=user_id,
            doc_id=doc_id,
            k=3,
            max_chars=2000
        )

        if not context:
            return f"I couldn't find anything about '{query}' in your document."

        pages = [s.get("page") for s in sources if s.get("page")]
        page_info = f" (pages {', '.join(map(str, pages))})" if pages else ""

        return f"Found in your notes{page_info}:\n\n{context}"

    except Exception as e:
        print(f"[ERROR] search_document_content: {e}")
        return f"Error searching document: {str(e)}"


@tool
def search_web_for_concept(query: str) -> dict:
    """
    Search the web when a concept is not covered in the course materials.
    Call this when the student asks about something not in the current content.
    """
    from tavily import TavilyClient

    tavily_key = os.getenv("TAVILY_API_KEY")

    if not tavily_key:
        return {
            "found": False,
            "message": "Web search is not configured. Let's focus on what's in your course materials for now.",
            "query": query
        }

    try:
        client = TavilyClient(api_key=tavily_key)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=3
        )

        results = []
        for r in response.get("results", []):
            title = r.get("title", "")
            content = r.get("content", "")[:250]
            results.append(f"- {title}: {content}")

        if results:
            return {
                "found": True,
                "message": "\n".join(results),
                "query": query
            }
        else:
            return {
                "found": False,
                "message": "No relevant results found for that query.",
                "query": query
            }

    except Exception as e:
        print(f"[ERROR] Web search: {e}")
        return {
            "found": False,
            "message": "I had trouble searching. Let me answer based on what I know.",
            "query": query
        }


@tool
def search_conversation_history(query: str, thread_id: str) -> str:
    """
    Search through earlier parts of this session's conversation.
    Use when the student references something discussed earlier like
    "what was that thing about...", "remember when you explained...", etc.

    Args:
        query: What to search for
        thread_id: Current session's thread ID

    Returns:
        Relevant excerpts from earlier in the conversation
    """
    try:
        checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})
        if not checkpoint:
            return "No conversation history found."

        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])
        if not messages:
            return "No messages in history."

        query_terms = query.lower().split()
        results = []

        for i, msg in enumerate(messages):
            content = getattr(msg, 'content', '') or ''
            if not content:
                continue
            content_lower = content.lower()

            score = sum(1 for term in query_terms if term in content_lower)
            if score > 0:
                role = "Student" if isinstance(msg, HumanMessage) else "Tutor"
                results.append((score, i, f"[Turn {i+1}] {role}: {content[:200]}..."))

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
    Load tutoring rules for handling specific situations.

    Args:
        topics: List of rule topics. Options:
            - "teaching_style" - How to explain, use analogies, check understanding
            - "learn_edge_cases" - Off-topic, frustration, confusion handling
            - "edge_cases" - Shared edge cases (unclear audio, etc.)
    """
    available_rules = {
        "teaching_style": "teaching_style.md",
        "learn_edge_cases": "learn_edge_cases.md",
        "edge_cases": "edge_cases.md",
    }

    results = []
    for topic in topics:
        topic_lower = topic.lower().strip()
        if topic_lower in available_rules:
            rule_file = RULES_DIR / available_rules[topic_lower]
            if rule_file.exists():
                content = rule_file.read_text()
                results.append(f"=== {topic.upper()} ===\n{content[:2000]}")

    return "\n\n".join(results) if results else f"No rules found. Available: {', '.join(available_rules.keys())}"


@tool
def advance_to_next_topic(doc_id: str, current_topic: str, available_topics: List[str]) -> dict:
    """
    Move to the next topic in the document.
    Call this when the student is ready to move on.

    Args:
        doc_id: Document ID
        current_topic: Current topic name
        available_topics: List of available topics

    Returns:
        dict with next topic info or 'done' if all covered
    """
    try:
        if current_topic in available_topics:
            current_idx = available_topics.index(current_topic)
            next_idx = current_idx + 1

            if next_idx >= len(available_topics):
                return {"done": True, "message": "All topics covered. Great learning session!"}

            next_topic_name = available_topics[next_idx]

            # Fetch the next topic content
            content_result = fetch_topic_content.invoke({
                "doc_id": doc_id,
                "topic_name": next_topic_name
            })

            if content_result.get("found"):
                return {
                    "done": False,
                    "new_index": next_idx,
                    "topic": content_result["topic"]
                }
            else:
                return {"done": True, "error": "Could not load next topic."}
        else:
            return {"done": True, "error": "Current topic not found in available topics."}

    except Exception as e:
        return {"done": True, "error": f"Error: {str(e)}"}


# Legacy tool for backwards compatibility with LP-based sessions
def preload_first_topic(lp_id: str) -> tuple[dict, int, list]:
    """Pre-load the first topic and all topics list from Redis LP."""
    key = f"lp:{lp_id}:topics"
    try:
        lp_data = r.json().get(key)
        if lp_data and lp_data.get("topics"):
            topics = lp_data["topics"]
            if len(topics) > 0:
                first_topic = {
                    "name": topics[0].get("name", ""),
                    "content": topics[0].get("content", ""),
                    "key_concepts": topics[0].get("key_concepts", []),
                    "pages": topics[0].get("pages", []),
                    "chunk_ids": topics[0].get("chunk_ids", []),
                }
                return first_topic, len(topics), topics
        return None, 0, []
    except Exception as e:
        print(f"Error preloading topic: {e}")
        return None, 0, []


# All tools available to the agent
tools = [
    # Discovery tools
    fetch_user_documents,
    fetch_document_topics,
    fetch_topic_content,
    # Teaching tools
    search_document_content,
    search_web_for_concept,
    search_conversation_history,
    advance_to_next_topic,
    get_rules,
]

# Main LLM
llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    temperature=0.3
)
llm_with_tools = llm.bind_tools(tools)


# ============================================================
# PROMPTS FOR CONVERSATIONAL FLOW
# ============================================================

GREETING_PROMPT = """You are a friendly learning tutor starting a voice study session.

**YOUR FIRST TURN:**
- Welcome the student warmly and conversationally
- Say: "Let me grab your documents real quick..."
- Call fetch_user_documents(user_id) to get their docs

**AFTER GETTING DOCS:**
- If docs found: "I see you have [titles]. Which one do you want to study today?"
- If no docs: "Hmm, looks like you haven't uploaded any documents yet. Upload something and come back!"

**TONE:** Casual, friendly, like a helpful study buddy. Use natural speech patterns.
Keep responses SHORT - this is a voice conversation."""


DOC_SELECTION_PROMPT = """The student is choosing which document to study.

**AVAILABLE DOCUMENTS:**
{documents_list}

**YOUR TASK:**
- If they name a document -> confirm and call fetch_document_topics(doc_id)
- If unclear -> ask for clarification
- Say: "Great choice! Let me see what topics are in there..."

**TONE:** Supportive, no rush.
Keep responses SHORT - this is a voice conversation."""


TOPIC_SELECTION_PROMPT = """The student is choosing a topic from their document.

**DOCUMENT:** {doc_title}
**AVAILABLE TOPICS:** {topics_list}

**YOUR TASK:**
- List the topics conversationally (not a boring list)
- Ask: "Which one sounds interesting to you?"
- When they pick -> say "Alright, let me grab those notes..." -> call fetch_topic_content(doc_id, topic_name)

**TONE:** Curious, encouraging exploration.
Keep responses SHORT - this is a voice conversation."""


TEACHING_PROMPT = """You are tutoring the student on a specific topic via voice.

**TOPIC:** {topic_name}
**CONTENT:** {content}
**KEY CONCEPTS:** {key_concepts}

**AFTER LOADING CONTENT, ASK:**
"Got it! Do you want me to give you a quick overview of {topic_name}, or do you just want to dive in and ask questions?"

**TEACHING STYLE:**
- If overview -> summarize key points in 30 seconds max
- If questions -> let them drive, answer from content
- Check understanding regularly: "Does that make sense?"
- If they ask something not in content -> use search_document_content()
- If not in document at all -> offer web search

**SWITCHING TOPICS:**
- If they say "let's do something else" -> brief summary -> call fetch_document_topics() again
- "Sure! What else would you like to explore?"

**TOOLS AVAILABLE:**
- search_document_content(query, doc_id, user_id): Search elsewhere in the document
- search_web_for_concept(query): Web search for things not in document
- search_conversation_history(query, thread_id): "What did we discuss earlier?"
- get_rules(["teaching_style"]): If unsure how to explain something
- advance_to_next_topic(): When they want the next topic

**REMEMBER:**
- This is VOICE - keep responses SHORT (2-3 sentences max unless explaining)
- Pause after key points
- Be conversational, not lecture-y
- Encourage questions"""


# ============================================================
# CONTEXT MANAGEMENT
# ============================================================

LEARN_RUNNING_SUMMARY_PROMPT = """You are summarizing a tutoring/study session for context continuity. Focus on:
1. Topics and concepts discussed so far
2. Student questions and any confusion points identified
3. Key explanations or examples given
4. Understanding level the student has demonstrated

Keep it pedagogically useful for continuing effective tutoring.

EXISTING SUMMARY:
{existing_summary}

NEW CONVERSATION TO ADD:
{conversation}

UPDATED SUMMARY (extend the existing summary with new information):"""


def should_update_summary(state: LearnState) -> bool:
    """Check if we need to update the running summary."""
    messages = state.get("messages", [])
    summary_index = state.get("summary_message_index", 0)

    unsummarized_msgs = [
        m for m in messages[summary_index:]
        if isinstance(m, (HumanMessage, AIMessage)) and m.content
    ]

    unsummarized_count = len(unsummarized_msgs)
    if unsummarized_count < SUMMARIZATION_TRIGGER_THRESHOLD:
        return False

    unsummarized_chars = sum(len(m.content) for m in unsummarized_msgs)

    if unsummarized_chars >= SUMMARIZATION_CHAR_THRESHOLD:
        print(f"Summarization triggered: {unsummarized_chars} chars")
        return True

    if unsummarized_count >= SUMMARIZATION_TRIGGER_THRESHOLD:
        print(f"Summarization triggered: {unsummarized_count} messages")
        return True

    return False


def summarization_node(state: LearnState) -> dict:
    """Update running summary with newly unsummarized messages."""
    messages = state.get("messages", [])
    existing_summary = state.get("running_summary", "")
    summary_index = state.get("summary_message_index", 0)

    end_index = max(0, len(messages) - CONTEXT_MESSAGES_TO_LLM)
    messages_to_summarize = messages[summary_index:end_index]

    if not messages_to_summarize:
        return {}

    convo_lines = []
    for m in messages_to_summarize:
        if isinstance(m, HumanMessage):
            convo_lines.append(f"Student: {m.content}")
        elif isinstance(m, AIMessage) and m.content:
            convo_lines.append(f"Tutor: {m.content[:300]}")

    convo_text = "\n".join(convo_lines)

    summary_llm = ChatOpenAI(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0
    )

    prompt = LEARN_RUNNING_SUMMARY_PROMPT.format(
        existing_summary=existing_summary or "None yet - this is the first summary.",
        conversation=convo_text[-3000:]
    )

    try:
        response = summary_llm.invoke([SystemMessage(content=prompt)])
        new_summary = response.content.strip()
        if not new_summary:
            return {}
        print(f"Summarized {len(messages_to_summarize)} messages")
    except Exception as e:
        print(f"Summarization failed: {e}")
        return {}

    return {
        "running_summary": new_summary,
        "summary_message_index": end_index,
    }


def build_system_prompt(state: LearnState) -> str:
    """Build the appropriate system prompt based on current phase."""
    phase = state.get("phase", "greeting")
    running_summary = state.get("running_summary", "")

    summary_section = ""
    if running_summary:
        summary_section = f"""
[SESSION CONTEXT - Internal reference, do not read aloud]
{running_summary}
---
"""

    if phase == "greeting":
        return GREETING_PROMPT + "\n\n" + summary_section

    elif phase == "selecting_doc":
        docs = state.get("available_documents", [])
        docs_list = ", ".join([f"'{d['title']}'" for d in docs]) if docs else "none found"
        return DOC_SELECTION_PROMPT.format(documents_list=docs_list) + "\n\n" + summary_section

    elif phase == "selecting_topic":
        topics = state.get("available_topics", [])
        topics_list = ", ".join(topics[:10]) if topics else "none found"
        doc_title = state.get("selected_doc_title", "your document")
        return TOPIC_SELECTION_PROMPT.format(
            doc_title=doc_title,
            topics_list=topics_list
        ) + "\n\n" + summary_section

    elif phase == "teaching":
        topic_content = state.get("current_topic_content") or state.get("current_topic") or {}
        topic_name = topic_content.get("name", state.get("selected_topic", "the topic"))
        content = topic_content.get("content", "No content available")[:2000]
        key_concepts = ", ".join(topic_content.get("key_concepts", []))

        return TEACHING_PROMPT.format(
            topic_name=topic_name,
            content=content,
            key_concepts=key_concepts or "Not extracted"
        ) + "\n\n" + summary_section

    return GREETING_PROMPT + "\n\n" + summary_section


# ============================================================
# GRAPH NODES
# ============================================================

def agent(state: LearnState) -> LearnState:
    """Reasoning step: LLM decides to respond or call a tool."""
    system_prompt = build_system_prompt(state)
    system_message = SystemMessage(content=system_prompt)

    # Message windowing
    conversation_messages = [
        m for m in state["messages"]
        if isinstance(m, (HumanMessage, AIMessage)) and m.content
    ]
    recent_messages = conversation_messages[-CONTEXT_MESSAGES_TO_LLM:]
    messages = [system_message] + recent_messages

    response = llm_with_tools.invoke(messages)
    state["messages"].append(response)

    # Mark session as started after first response
    if not state.get("session_started") and len(state["messages"]) > 2:
        state["session_started"] = True

    # Update response type
    phase = state.get("phase", "greeting")
    if phase == "greeting":
        state["response_type"] = "greeting"
    elif phase == "selecting_doc":
        state["response_type"] = "document_list"
    elif phase == "selecting_topic":
        state["response_type"] = "topic_list"
    elif phase == "teaching":
        state["response_type"] = "teaching"

    return state


tool_node = ToolNode(tools)


def process_tool_response(state: LearnState) -> LearnState:
    """Process tool responses and update state/phase accordingly."""
    messages = state["messages"]

    for msg in reversed(messages[-3:]):
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            try:
                if msg.content.startswith('{'):
                    response = json.loads(msg.content)

                    # Handle fetch_user_documents response
                    if "documents" in response:
                        state["available_documents"] = response.get("documents", [])
                        if response.get("found"):
                            state["phase"] = "selecting_doc"
                            state["response_type"] = "document_list"
                        print(f"Documents fetched: {len(state['available_documents'])}")

                    # Handle fetch_document_topics response
                    elif "topics" in response and "documents" not in response:
                        state["available_topics"] = response.get("topics", [])
                        if response.get("found"):
                            state["phase"] = "selecting_topic"
                            state["response_type"] = "topic_list"
                        print(f"Topics fetched: {len(state['available_topics'])}")

                    # Handle fetch_topic_content response
                    elif "topic" in response and isinstance(response.get("topic"), dict):
                        topic_data = response["topic"]
                        state["current_topic_content"] = topic_data
                        state["current_topic"] = topic_data  # For backwards compat
                        state["selected_topic"] = topic_data.get("name")
                        state["phase"] = "teaching"
                        state["response_type"] = "topic_loaded"
                        print(f"Topic loaded: {topic_data.get('name')}")

                    # Handle advance_to_next_topic response
                    elif response.get("done"):
                        state["current_topic"] = None
                        state["current_topic_content"] = None
                        print("Learn session complete signal received")
                    elif response.get("topic"):
                        state["current_topic_index"] = response.get("new_index", 0)
                        state["current_topic"] = response["topic"]
                        state["current_topic_content"] = response["topic"]
                        state["selected_topic"] = response["topic"].get("name")
                        print(f"Advanced to topic: {response['topic'].get('name')}")

            except (json.JSONDecodeError, TypeError):
                pass

    return state


# ============================================================
# CONTENT ROUTING (for web search flow)
# ============================================================

def content_router_node(state: LearnState) -> dict:
    """Check if the latest student question can be answered from topic content."""
    messages = state.get("messages", [])
    current_topic = state.get("current_topic_content") or state.get("current_topic")

    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not human_messages:
        return {"found_in_content": True, "pending_web_search": False, "content_check_done": True}

    query = human_messages[-1].content.lower().strip()

    # Skip for simple responses
    simple_patterns = ["yes", "no", "ok", "okay", "next", "continue", "thanks", "thank you", "got it", "sure", "yep", "nope"]
    if query in simple_patterns or len(query) < 8:
        return {"found_in_content": True, "pending_web_search": False, "content_check_done": True}

    # Skip for navigation
    if any(phrase in query for phrase in ["next topic", "move on", "let's continue", "what's next", "switch"]):
        return {"found_in_content": True, "pending_web_search": False, "content_check_done": True}

    # If no topic loaded, skip
    if not current_topic:
        return {"found_in_content": True, "pending_web_search": False, "content_check_done": True}

    topic_content = current_topic.get("content", "").lower()
    key_concepts = [c.lower() for c in current_topic.get("key_concepts", [])]

    stop_words = {"what", "is", "the", "a", "an", "how", "does", "do", "can", "you", "explain", "tell", "me", "about", "why", "where", "when", "which", "would", "could", "should"}
    query_words = [w for w in query.split() if w not in stop_words and len(w) > 2]

    matches = 0
    for word in query_words:
        if word in topic_content:
            matches += 1
        for concept in key_concepts:
            if word in concept or concept in query:
                matches += 2

    found = matches >= 2
    print(f"[content_router] Query: '{query[:50]}...' | Matches: {matches} | Found: {found}")

    return {
        "found_in_content": found,
        "pending_web_search": not found,
        "search_query": query if not found else None,
        "content_check_done": True
    }


def emit_searching_message_node(state: LearnState) -> dict:
    """Emit intermediate message before web search."""
    topic_name = (state.get("current_topic_content") or state.get("current_topic") or {}).get("name", "the topic")
    query = state.get("search_query", "that")

    searching_message = AIMessage(
        content=f"Hmm, I don't see that covered in your notes on {topic_name}. Let me quickly search for some information..."
    )

    return {
        "messages": state["messages"] + [searching_message],
        "response_type": "searching"
    }


def web_search_node(state: LearnState) -> dict:
    """Perform actual web search."""
    from tavily import TavilyClient

    query = state.get("search_query", "")
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not tavily_key:
        return {
            "search_results": "I couldn't search the web right now. Let me try to help based on what I know.",
            "pending_web_search": False
        }

    try:
        client = TavilyClient(api_key=tavily_key)
        response = client.search(query=query, search_depth="basic", max_results=3)

        results = []
        for r in response.get("results", []):
            title = r.get("title", "")
            content = r.get("content", "")[:250]
            results.append(f"- {title}: {content}")

        return {
            "search_results": "\n".join(results) if results else "No relevant results found.",
            "pending_web_search": False
        }

    except Exception as e:
        print(f"Web search error: {e}")
        return {
            "search_results": "I had trouble searching. Let me answer based on general knowledge.",
            "pending_web_search": False
        }


def ground_and_respond_node(state: LearnState) -> dict:
    """Generate response using web search results."""
    search_results = state.get("search_results", "")
    cognitive_level = state.get("cognitive_level", "high_school")
    topic_content = (state.get("current_topic_content") or state.get("current_topic") or {}).get("content", "")[:500]
    original_query = state.get("search_query", "the question")

    grounding_llm = ChatOpenAI(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.3
    )

    grounding_prompt = f"""You are helping a {cognitive_level} level student understand a topic.

Their question: {original_query}

Course content context:
{topic_content}

Web search results:
{search_results}

YOUR TASK:
1. Extract the most relevant information
2. Simplify to match {cognitive_level} level
3. Connect to concepts they're learning if possible
4. Keep it concise (2-4 sentences) - this will be spoken aloud

Response:"""

    try:
        response = grounding_llm.invoke([SystemMessage(content=grounding_prompt)])
        grounded_response = response.content.strip()
    except Exception as e:
        grounded_response = "I found some information. Would you like me to explain more, or shall we continue with the main topic?"

    final_message = AIMessage(
        content=f"Here's what I found: {grounded_response} Does that help?"
    )

    return {
        "messages": state["messages"] + [final_message],
        "response_type": "web_search_result",
        "content_check_done": False,
        "found_in_content": True,
        "pending_web_search": False,
        "search_query": None,
        "search_results": None
    }


# ============================================================
# ROUTING FUNCTIONS
# ============================================================

def route_after_content_check(state: LearnState) -> str:
    """Route based on whether content was found in topic."""
    if state.get("pending_web_search", False):
        return "emit_searching"
    return "agent"


def route_summarization(state: LearnState) -> str:
    """Decide if summarization needed before processing."""
    if should_update_summary(state):
        return "summarize"
    return "content_router"


def should_continue(state: LearnState) -> Literal["tools", "check_completion", "__end__"]:
    """Determine whether to continue to tools or check completion."""
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"

    return "check_completion"


def check_if_session_complete(state: LearnState) -> Literal["cleanup", "__end__"]:
    """Check if all topics have been covered."""
    current_topic = state.get("current_topic") or state.get("current_topic_content")
    phase = state.get("phase", "greeting")

    # Session is complete if we were teaching and topic is now None (done signal)
    if phase == "teaching" and current_topic is None:
        return "cleanup"

    return "__end__"


# ============================================================
# SESSION SUMMARY & CLEANUP
# ============================================================

def generate_session_summary(state: LearnState) -> LearnSessionSummary:
    """Generate LLM summary from session conversation."""
    summary_llm = ChatOpenAI(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.3
    )

    messages = state.get("messages", [])
    topics = state.get("topics", [])
    available_topics = state.get("available_topics", [])
    current_topic = state.get("selected_topic", "")

    conversation_lines = []
    for m in messages:
        if hasattr(m, 'content') and m.content:
            role = "STUDENT" if isinstance(m, HumanMessage) else "TUTOR"
            conversation_lines.append(f"{role}: {m.content}")
    conversation = "\n".join(conversation_lines[-50:])

    # Use available_topics if topics is empty (conversational flow)
    topics_list = [t.get("name", "Unknown") for t in topics] if topics else available_topics

    prompt = SUMMARY_PROMPT.format(
        topics_list=", ".join(topics_list) if topics_list else "Topics discussed",
        current_topic_index=0,
        message_count=len(messages),
        conversation=conversation[-8000:],
        output_schema=json.dumps(LearnSessionSummary.model_json_schema(), indent=2)
    )

    try:
        response = summary_llm.invoke(prompt)
        content = response.content.strip()

        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

        data = json.loads(content)
        data["message_count"] = len(messages)
        data["total_topics_planned"] = len(topics_list)
        data["topics_completed"] = 1 if current_topic else 0
        data["model_used"] = "llama-3.1-8b-instant"

        return LearnSessionSummary(**data)

    except Exception as e:
        print(f"Error generating summary: {e}")
        return LearnSessionSummary(
            session_title="Learn Session",
            summary="Session summary generation failed.",
            topics_covered=[],
            total_topics_planned=len(topics_list),
            topics_completed=0,
            overall_understanding=0.5,
            strengths=["Session completed"],
            areas_to_review=[],
            message_count=len(messages),
            model_used="fallback"
        )


def cleanup_session(state: LearnState) -> LearnState:
    """Clean up after learn session ends."""
    thread_id = state["thread_id"]
    user_id = state.get("user_id")
    lp_id = state.get("lp_id")
    doc_id = state.get("selected_doc_id")

    print(f"Learn session complete for thread: {thread_id}")

    try:
        summary = generate_session_summary(state)
        print(f"Generated session summary: {summary.session_title}")

        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if supabase_url and supabase_key:
            from supabase import create_client

            supabase = create_client(supabase_url, supabase_key)
            supabase.table("LearnSession").insert({
                "threadId": thread_id,
                "lpId": lp_id,
                "documentId": doc_id,
                "userId": user_id,
                "title": summary.session_title,
                "summary": summary.summary,
                "topicsCovered": [t.topic_name for t in summary.topics_covered] if summary.topics_covered else [],
                "topicsPlanned": summary.total_topics_planned,
                "topicsCompleted": summary.topics_completed,
                "strengths": summary.strengths,
                "areasToReview": summary.areas_to_review,
                "overallUnderstanding": int(summary.overall_understanding * 100),
                "messageCount": summary.message_count,
                "summaryJson": summary.model_dump_json(),
                "status": "COMPLETED",
            }).execute()
            print(f"LearnSession saved to Postgres: {thread_id}")

    except Exception as e:
        print(f"Failed to save LearnSession: {e}")
        import traceback
        traceback.print_exc()

    return state


# ============================================================
# BUILD GRAPH
# ============================================================

workflow = StateGraph(LearnState)

# Core nodes
workflow.add_node("summarization", summarization_node)
workflow.add_node("content_router", content_router_node)
workflow.add_node("agent", agent)
workflow.add_node("tools", tool_node)
workflow.add_node("process_response", process_tool_response)
workflow.add_node("check_completion", lambda state: state)
workflow.add_node("cleanup", cleanup_session)

# Web search flow nodes
workflow.add_node("emit_searching", emit_searching_message_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("ground_and_respond", ground_and_respond_node)

# Entry point
workflow.add_conditional_edges(
    "__start__",
    route_summarization,
    {"summarize": "summarization", "content_router": "content_router"}
)
workflow.add_edge("summarization", "content_router")

# Content routing
workflow.add_conditional_edges(
    "content_router",
    route_after_content_check,
    {"agent": "agent", "emit_searching": "emit_searching"}
)

# Web search flow
workflow.add_edge("emit_searching", "web_search")
workflow.add_edge("web_search", "ground_and_respond")
workflow.add_edge("ground_and_respond", "check_completion")

# Normal agent routing
workflow.add_conditional_edges("agent", should_continue)
workflow.add_conditional_edges("check_completion", check_if_session_complete)

# Tool flow
workflow.add_edge("tools", "process_response")
workflow.add_edge("process_response", "agent")

# Cleanup ends the graph
workflow.add_edge("cleanup", "__end__")

graph = workflow.compile(checkpointer=checkpointer)


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":
    import uuid

    print("\n" + "="*60)
    print("Learn Mode Agent Test (Conversational Flow)")
    print("="*60 + "\n")

    # Test conversational flow
    test_user_id = "test_user_" + uuid.uuid4().hex[:8]
    thread_id = f"learn_test_{uuid.uuid4().hex[:8]}"

    state = LearnState(
        messages=[HumanMessage(content="Hi, I want to study")],
        thread_id=thread_id,
        user_id=test_user_id,
        phase="greeting",
        session_started=False,
    )

    config = {"configurable": {"thread_id": thread_id}}

    print(f"Starting learn session: {thread_id}")
    print(f"User ID: {test_user_id}")
    print("-" * 40)

    try:
        final_state = graph.invoke(state, config=config)

        print("\n=== CONVERSATION ===")
        for msg in final_state["messages"]:
            if isinstance(msg, HumanMessage):
                print(f"STUDENT: {msg.content}")
            elif isinstance(msg, AIMessage) and msg.content:
                print(f"TUTOR: {msg.content}")
        print("=== End ===\n")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
