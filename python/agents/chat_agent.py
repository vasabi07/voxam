"""
Unified Agentic Chat Agent for Voxam.

Architecture: Agentic RAG (loop, not pipeline)
- LLM has autonomy to self-correct, ask clarifying questions, and chain tools
- No router - LLM decides which tools to use based on query
- Multi-step reasoning: Cypher for structure → RAG for content → Response

Flow:
  START → credit_check → [summarize?] → agent_node (LLM with ALL tools)
                                           ↓
                              ┌────────────┴────────────┐
                              ↓                         ↓
                        tool_calls?                  no tools
                              ↓                         ↓
                         tool_node                    END
                         (execute)
                              ↓
                         agent_node ← loop back for follow-up

Tools:
  - search_documents: Hybrid search (vector + keyword) for content retrieval
  - query_structure: Text2Cypher for structural queries (chapters, sections, counts)
  - get_questions: Retrieve generated questions from QuestionSet nodes
  - request_qp_form, request_upload_ui, request_learn_form: UI tools
  - web_search: Fallback web search (with user confirmation)
"""

import os
import re
import uuid
from typing import Optional, List, Literal
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.redis import AsyncRedisSaver
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Import retrieval function and knowledge tools
from retrieval import retrieve_context, retrieve_context_with_sources
from agents.chat_tools import knowledge_tools, search_documents, query_structure, get_questions, get_rules

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Helper class to handle Redis serialization issues and async loop binding
# SafeAsyncRedisSaver removed for stability revert



# ============================================================
# STATE DEFINITION
# ============================================================
# Summarization thresholds
SUMMARIZATION_TRIGGER_THRESHOLD = 20   # Summarize when unsummarized messages exceed this
SUMMARIZATION_CHAR_THRESHOLD = 8000    # Or when unsummarized chars exceed this (~2000 tokens)
CONTEXT_MESSAGES_TO_LLM = 16           # Only pass last N messages to LLM (increased for multi-turn tool conversations)
MAX_MESSAGES_IN_REDIS = 50             # Trim oldest messages beyond this (storage limit)


class ChatState(MessagesState):
    """
    Unified agent state for agentic RAG.
    Using MessagesState for LangGraph compatibility.
    Context (user_id, doc_id) is extracted from threadId.
    """
    # Credit check field
    credit_check_passed: Optional[bool] = None      # True if user has credits, False if exhausted
    # Context fields (extracted from thread_id)
    doc_id: Optional[str] = None                # Active document ID (for scoped retrieval)
    user_id: Optional[str] = None               # User ID for document isolation
    # Summarization fields
    conversation_summary: Optional[str] = None      # Running summary of older history
    summary_message_index: Optional[int] = None     # Index up to which messages are summarized
    # Working memory - tracks current task/intent across clarifying questions
    working_context: Optional[str] = None           # e.g., "User wants sections for document X"


# ============================================================
# LLM INSTANCES
# ============================================================
# Main agent model (streaming enabled for better UX)
_base_llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    temperature=0.7,
    streaming=True
)

# Summarization LLM - Groq Llama 3.1 8B (cheapest, fast for simple task)
summarization_llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    temperature=0
)


# ============================================================
# CREDIT CHECK NODE
# ============================================================
# Checks user's chat message credits before processing.
# Deducts 1 message on each user query.

def credit_check_node(state: ChatState, config: RunnableConfig = None) -> dict:
    """
    Check and deduct chat message credits before processing.
    Returns error message if user has no credits remaining.
    """
    from credits import check_chat_messages, deduct_chat_message

    # Get user_id from config (reuse helper function)
    user_id, _ = get_user_context_from_config(config)

    # If no user_id, skip credit check (for testing)
    if not user_id:
        print("⚠️ No user_id in thread_id, skipping credit check")
        return {"credit_check_passed": True}

    # Check credits
    has_credits, remaining = check_chat_messages(user_id)

    if not has_credits:
        print(f"❌ User {user_id} has no chat credits remaining")
        return {
            "credit_check_passed": False,
            "messages": [AIMessage(
                content="You've reached your chat message limit for this billing cycle. "
                       "Please upgrade your plan or wait for your credits to reset to continue chatting."
            )]
        }

    # Deduct 1 message credit
    deduct_chat_message(user_id, count=1)
    print(f"💬 Deducted 1 chat message from user {user_id}. Remaining: {remaining - 1}")

    return {"credit_check_passed": True}


# ============================================================
# GENERATIVE UI TOOLS (A2UI)
# ============================================================
# These tools render UI components in the chat.
# The tool call IS the response - no follow-up text generation needed.
# Frontend uses useRenderToolCall() to handle these.

@tool
def request_qp_form(doc_id: Optional[str] = None) -> str:
    """
    Display a form to create a question paper.
    Use this when the user wants to generate a quiz, exam, test, or question paper.
    The frontend will render an interactive form to collect exam parameters.
    """
    return f"Displaying QP Form for document: {doc_id or 'user will select'}"


@tool
def request_upload_ui() -> str:
    """
    Display a file upload interface.
    Use this when the user wants to upload, ingest, or add a document/file.
    The frontend will render a file upload dropzone.
    """
    return "Displaying Upload UI"


@tool
def request_learn_form(doc_id: Optional[str] = None) -> str:
    """
    Display a form to create a learn/study session.
    Use this when the user wants to study, learn, get tutored, review topics,
    start a learning session, or understand their course material better.
    The frontend will render an interactive form to select topics for learning.
    """
    return f"Displaying Learn Pack Form for document: {doc_id or 'user will select'}"


@tool
def show_sources(sources: list[dict]) -> str:
    """
    Display source citations from the user's documents.
    Use this at the END of your response when you've referenced specific pages or sections.

    Args:
        sources: List of source objects with 'page', 'title', and optional 'excerpt' keys.
                 Example: [{"page": 5, "title": "Chapter 2", "excerpt": "key concept..."}]

    Call this AFTER providing your explanation to show where the information came from.
    """
    if not sources:
        return "No sources to display"
    return f"Displaying {len(sources)} source citations"


# Gen UI tools - render UI, no follow-up needed
# NOTE: show_sources removed - sources are now embedded in response text
ui_tools = [request_qp_form, request_upload_ui, request_learn_form]


# ============================================================
# RESPONSE TOOLS
# ============================================================
# These tools return data that the LLM uses to generate a response.
# After calling these, the LLM should generate a text message using the result.
# Frontend uses useRenderToolCall() to show loading/status during execution.

@tool
def web_search(query: str) -> str:
    """
    Search the web for information not found in the user's documents.
    Use this ONLY when:
    1. You couldn't find relevant information in the user's course materials
    2. You asked the user if they want to search the web
    3. The user explicitly confirmed they want web search (said yes, sure, ok, etc.)

    DO NOT use this tool unless the user has confirmed.
    After calling this, generate a helpful response using the search results.
    """
    print(f"🌐 Web search requested for: {query}")

    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        print("⚠️ TAVILY_API_KEY not configured, using fallback")
        return f"""Web search results for '{query}':
[Web search not configured - using general knowledge instead]
Please provide a clear, educational response about this topic."""

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=tavily_api_key)

        # Search with educational focus
        response = client.search(
            query=query,
            search_depth="advanced",  # More thorough search
            max_results=5,
            include_answer=True,  # Get a direct answer if available
            include_raw_content=False,
        )

        # Format results
        results = []

        # Include direct answer if available
        if response.get("answer"):
            results.append(f"**Summary:** {response['answer']}\n")

        # Include top search results
        for i, result in enumerate(response.get("results", [])[:5], 1):
            title = result.get("title", "Untitled")
            content = result.get("content", "")[:500]  # Limit content length
            url = result.get("url", "")

            results.append(f"**{i}. {title}**\n{content}\nSource: {url}\n")

        if results:
            formatted_results = "\n".join(results)
            print(f"✅ Tavily returned {len(response.get('results', []))} results")
            return f"""Web search results for '{query}':\n\n{formatted_results}

Use these results to provide a comprehensive, educational response. Cite sources where appropriate."""
        else:
            return f"""Web search for '{query}' returned no results.
Please provide a response based on your general knowledge."""

    except Exception as e:
        print(f"❌ Tavily search failed: {e}")
        return f"""Web search for '{query}' encountered an error: {str(e)}
Please provide a response based on your general knowledge."""


# Response tools - return data, LLM generates follow-up response
response_tools = [web_search]

# ============================================================
# UNIFIED AGENT LLM (All Tools)
# ============================================================
# Agentic RAG: LLM has all tools and decides which to use.
# No router - the LLM is intelligent enough to pick the right tool.

# All tools available to the agent
all_agent_tools = knowledge_tools + ui_tools + response_tools

# Unified agent LLM with all tools bound
agent_llm = _base_llm.bind_tools(all_agent_tools)

# ToolNode for executing tools (knowledge tools + web_search)
# UI tools are handled by frontend, but included for LLM awareness
agent_tool_node = ToolNode(knowledge_tools + response_tools)


# ============================================================
# HELPER: EXTRACT USER CONTEXT FROM CONFIG
# ============================================================
def get_user_context_from_config(config: dict) -> tuple[Optional[str], Optional[str]]:
    """
    Extracts user_id and doc_id from config's thread_id.
    ThreadId format: "chat-{user_id}" or "chat-{user_id}-{doc_id}"
    UUIDs are 36 chars (8-4-4-4-12 format with dashes).
    Returns (user_id, doc_id) tuple.
    """
    configurable = config.get("configurable", {}) if config else {}
    thread_id = configurable.get("thread_id", "")

    user_id = None
    doc_id = None

    if thread_id and thread_id.startswith("chat-"):
        # Remove "chat-" prefix
        remainder = thread_id[5:]  # Skip "chat-"

        # UUID is 36 characters (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
        if len(remainder) >= 36:
            user_id = remainder[:36]

            # Check if there's a doc_id after another dash
            if len(remainder) > 37 and remainder[36] == "-":
                doc_id = remainder[37:]  # Everything after "user_id-"

    return user_id, doc_id


# ============================================================
# UNIFIED AGENT PROMPT
# ============================================================
AGENT_PROMPT = """You are Voxam, an intelligent study assistant with access to the user's documents.

TOOLS:
- search_documents(query): Find content by meaning (explanations, concepts, definitions)
- query_structure(question): Get document structure (chapters, sections, topics)
- get_questions(chapter?, difficulty?, count?): Retrieve practice questions
- get_rules(topics): Get formatting rules - call with ["math"], ["sources"], ["style"], or ["tools"]
- request_qp_form(): Show form to create an exam/quiz/test
- request_upload_ui(): Show form to upload a new document
- request_learn_form(): Show form to start a learning session
- web_search(query): Search web (only after user confirms)

WORKFLOW:
1. If query involves math/equations → call get_rules(["math"]) first
2. If you'll use search_documents → call get_rules(["sources"]) first to learn citation format
3. Use appropriate tool for the task
4. Follow the retrieved rules exactly

DECISION PROCESS:
- Structure questions ("what chapters?", "how many?") → query_structure
- Content questions ("explain X", "what is Y?") → search_documents
- Practice requests ("quiz me") → get_questions
- Actions ("upload", "create exam") → request_*_form tools

{user_documents_section}
{active_document_section}
{summary_section}

WORKING CONTEXT:
{working_context}

CORE RULES:
1. When search_documents returns SOURCES_FOR_CITATION, embed it at the END of your response as: <!-- SOURCES: [...] -->
2. If multiple documents exist and user doesn't specify, ask which one
3. When user answers a clarifying question, USE that answer to complete the task
4. GENERAL CHAT: When no document selected, respond neutrally. Don't assume study intent.
5. SOURCE TRANSPARENCY:
   - If answering from search_documents results → include the sources marker (<!-- SOURCES: [...] -->)
   - If answering from general knowledge (topic not found in documents or no document selected) → end response with:
     "*This answer is from general knowledge, not your documents.*"

Respond based on the conversation history and working context above."""


async def get_user_documents_list(user_id: str) -> str:
    """
    Get list of user's documents from Neo4j for context awareness.
    """
    if not user_id:
        return "No documents available (user not authenticated)"

    from ingestion_workflow import get_neo4j_driver

    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)
                RETURN d.title AS title, d.documentId AS doc_id
                ORDER BY d.title
                LIMIT 10
            """, user_id=user_id)
            docs = [{"title": r["title"], "doc_id": r["doc_id"]} for r in result]

        if not docs:
            return "No documents uploaded yet."

        return "USER'S DOCUMENTS:\n" + "\n".join([
            f"- {d['title']} (id: {d['doc_id']})" for d in docs
        ])
    except Exception as e:
        print(f"⚠️ Failed to get user documents: {e}")
        return "Documents list unavailable."


def build_working_context(messages: list) -> str:
    """
    Build working context from recent messages.
    Detects clarifying question → answer patterns and preserves intent.

    This helps the agent understand when a short user response (UUID, number, "yes")
    is answering a previous clarifying question, not a new standalone query.
    """
    if not messages:
        return ""

    # Get the current user message
    current_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and msg.content:
            current_msg = msg.content.strip()
            break

    if not current_msg:
        return ""

    # If user's message is substantial (> 5 words), it's probably a complete query
    if len(current_msg.split()) > 5:
        return current_msg

    # Check for patterns suggesting this is a response to a clarifying question
    is_short_response = (
        re.match(r'^[a-f0-9\-]{36}$', current_msg.lower()) or  # UUID
        re.match(r'^\d+$', current_msg) or  # Number
        current_msg.lower() in ['yes', 'no', 'ok', 'sure', 'yeah', 'yep', 'nope'] or
        len(current_msg.split()) <= 3
    )

    if not is_short_response:
        return current_msg

    # Look for the last AI message that asked a question
    for msg in reversed(messages[:-1]):
        if isinstance(msg, AIMessage) and msg.content and '?' in msg.content:
            ai_content = msg.content.strip()
            # Truncate long questions
            if len(ai_content) > 200:
                ai_content = ai_content[:200] + "..."
            return f"[Answering: {ai_content}] User response: {current_msg}"

    return current_msg


async def agent_node(state: ChatState, config: RunnableConfig = None) -> dict:
    """
    Unified agent node that can use any tool based on query needs.
    Loops until no more tool calls (handled by graph structure).

    The agent decides:
    - Structure questions → query_structure tool
    - Content questions → search_documents tool
    - Practice questions → get_questions tool
    - Actions → request_*_form tools
    - Ambiguous → asks clarifying question in response
    """
    messages = state.get("messages", [])
    conversation_summary = state.get("conversation_summary", "")

    # Get user_id and doc_id from config's thread_id
    user_id, doc_id = get_user_context_from_config(config)

    # Build working context (captures intent across clarifying questions)
    working_context = build_working_context(messages)

    print(f"🤖 Agent processing: '{working_context[:80]}...' (user: {user_id}, doc: {doc_id})")

    # Build context sections for the prompt
    user_documents_section = await get_user_documents_list(user_id) if user_id else ""

    if doc_id:
        active_document_section = f"ACTIVE DOCUMENT: Currently viewing document with ID: {doc_id}"
    else:
        active_document_section = "ACTIVE DOCUMENT: None selected (general chat mode)"

    if conversation_summary:
        summary_section = f"""
CONVERSATION SUMMARY (background context, do NOT repeat):
{conversation_summary}
"""
    else:
        summary_section = ""

    # Build the system prompt
    system_content = AGENT_PROMPT.format(
        user_documents_section=user_documents_section,
        active_document_section=active_document_section,
        summary_section=summary_section,
        working_context=working_context
    )

    # Prepare messages for LLM
    llm_messages = [SystemMessage(content=system_content)]

    # Add recent conversation messages - INCLUDE ToolMessage for tool results
    # The agent needs to see tool results to know when to stop or try alternatives.
    recent_messages = []
    for m in messages[-CONTEXT_MESSAGES_TO_LLM:]:
        if isinstance(m, HumanMessage):
            recent_messages.append(HumanMessage(content=m.content))
        elif isinstance(m, AIMessage):
            # Include AIMessage even if content is empty (it may have tool_calls)
            recent_messages.append(m)
        elif isinstance(m, ToolMessage):
            # Include tool results so agent sees what tools returned
            recent_messages.append(m)

    # Take last N conversation messages
    llm_messages.extend(recent_messages[-CONTEXT_MESSAGES_TO_LLM:])

    # Stream response using unified agent_llm (has all tools)
    full_response = None
    async for chunk in agent_llm.astream(llm_messages, config=config):
        if full_response is None:
            full_response = chunk
        else:
            full_response = full_response + chunk

    # Check for tool calls
    if full_response.tool_calls:
        tool_names = [tc['name'] for tc in full_response.tool_calls]
        print(f"🔧 Agent tool calls: {tool_names}")
        return {"messages": [full_response], "user_id": user_id, "doc_id": doc_id}
    else:
        print(f"✅ Agent response ({len(full_response.content)} chars)")
        return {"messages": [AIMessage(content=full_response.content)], "user_id": user_id, "doc_id": doc_id}


# ============================================================
# CONVERSATION SUMMARIZATION
# ============================================================
def should_update_summary(state: ChatState) -> bool:
    """
    Check if we need to update the conversation summary.
    Triggers when unsummarized messages exceed threshold OR char limit.
    Does NOT delete messages - just updates the summary.
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


SUMMARIZATION_PROMPT = """You are a conversation summarizer for an educational chat assistant.

{existing_summary_section}

RECENT CONVERSATION TO SUMMARIZE:
{conversation}

INSTRUCTIONS:
1. Create a concise summary that captures:
   - What the user is trying to accomplish (their current goal/task)
   - Key topics discussed (educational concepts, questions asked)
   - Important clarifications made (document selection, chapter choices)
   - Any pending actions (agent asked for clarification, waiting for response)
2. Keep it brief (3-5 sentences max)
3. Focus on information useful for continuing the conversation
4. If extending an existing summary, incorporate new information seamlessly

SUMMARY:"""


async def summarization_node(state: ChatState, config) -> dict:
    """
    Updates the conversation summary with newly unsummarized messages.
    Does NOT delete messages - they stay in Redis for UI scroll-back.
    Only trims messages if they exceed MAX_MESSAGES_IN_REDIS.
    """
    messages = state.get("messages", [])
    existing_summary = state.get("conversation_summary", "")
    summary_index = state.get("summary_message_index", 0)

    # Messages to add to summary (from last summary point to N messages before end)
    end_index = max(0, len(messages) - CONTEXT_MESSAGES_TO_LLM)
    messages_to_summarize = messages[summary_index:end_index]

    if not messages_to_summarize:
        print("⏭️ No messages to summarize")
        return {}

    # Build conversation text (exclude tool calls to prevent "upload", "create exam" pollution)
    convo_lines = []
    for m in messages_to_summarize:
        if isinstance(m, HumanMessage):
            convo_lines.append(f"User: {m.content}")
        elif isinstance(m, AIMessage) and m.content:
            # Skip messages that are primarily tool calls (no meaningful text content)
            # These pollute the summary with "upload", "create exam" mentions
            if hasattr(m, 'tool_calls') and m.tool_calls and len(m.content) < 50:
                continue
            convo_lines.append(f"Assistant: {m.content[:500]}")  # Truncate long responses

    convo_text = "\n".join(convo_lines)

    # Skip summarization if no meaningful conversation after filtering
    if not convo_lines:
        print("⏭️ No meaningful conversation to summarize (only tool calls)")
        return {}

    # Build existing summary section
    if existing_summary:
        existing_summary_section = f"""EXISTING SUMMARY OF EARLIER CONVERSATION:
{existing_summary}

Now extend this summary with the new conversation below:"""
    else:
        existing_summary_section = "This is the first summarization of this conversation."

    # Generate summary
    prompt = SUMMARIZATION_PROMPT.format(
        existing_summary_section=existing_summary_section,
        conversation=convo_text[-4000:]  # Limit input to avoid context overflow
    )

    try:
        response = await summarization_llm.ainvoke([SystemMessage(content=prompt)])
        new_summary = response.content.strip()
        if not new_summary:
            print("⚠️ Empty summary returned, keeping existing state")
            return {}
        print(f"✂️ Summarized {len(messages_to_summarize)} messages into {len(new_summary)} chars")
    except Exception as e:
        print(f"⚠️ Summarization failed: {e}")
        return {}

    result = {
        "conversation_summary": new_summary,
        "summary_message_index": end_index,
    }

    # Optionally trim very old messages (beyond MAX_MESSAGES_IN_REDIS)
    if len(messages) > MAX_MESSAGES_IN_REDIS:
        trimmed_messages = messages[-MAX_MESSAGES_IN_REDIS:]
        result["messages"] = trimmed_messages
        print(f"🗑️ Trimmed messages from {len(messages)} to {len(trimmed_messages)}")

    return result


# ============================================================
# GRAPH CONSTRUCTION - UNIFIED AGENT LOOP
# ============================================================
def should_continue(state: ChatState) -> str:
    """
    Check if we should execute tools or end.

    - Knowledge tools (search_documents, query_structure, get_questions, get_rules) → execute → loop back
    - Response tools (web_search) → execute → loop back
    - UI tools (request_*_form) → END (frontend handles)
    - No tools → END
    """
    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_message = messages[-1]
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return "end"

    # UI tools that frontend handles (no execution needed)
    # NOTE: show_sources removed - sources are now embedded in response text
    ui_tool_names = {"request_qp_form", "request_upload_ui", "request_learn_form"}

    # Knowledge/response tools that need execution
    execute_tool_names = {"search_documents", "query_structure", "get_questions", "get_rules", "web_search"}

    for tc in last_message.tool_calls:
        tool_name = tc.get("name")
        if tool_name in execute_tool_names:
            print(f"🔄 Tool needs execution: {tool_name}")
            return "tools"

    # All tool calls are UI tools - frontend handles them
    print(f"🎨 UI tools detected: {[tc.get('name') for tc in last_message.tool_calls]} - ending")
    return "end"


def create_chat_workflow():
    """
    Create the Unified Agent chat workflow (uncompiled).

    Flow:
      START → credit_check → [summarize?] → agent_node (LLM with ALL tools)
                                               ↓
                                  ┌────────────┴────────────┐
                                  ↓                         ↓
                            tool_calls?                  no tools
                                  ↓                         ↓
                             tool_node                    END
                             (execute)
                                  ↓
                             agent_node ← loop back for follow-up

    Unified agent LLM has ALL tools:
      - Knowledge tools: search_documents, query_structure, get_questions, get_rules
      - UI tools: request_qp_form, request_upload_ui, request_learn_form
      - Response tools: web_search
    """
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("credit_check", credit_check_node)
    workflow.add_node("summarization", summarization_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", agent_tool_node)

    # Routing after credit check
    def route_after_credit_check(state: ChatState) -> str:
        """Credit check passed - check if summarization needed before agent."""
        if not state.get("credit_check_passed", True):
            return "end"
        if should_update_summary(state):
            return "summarization"
        return "agent"

    # START → Credit check
    workflow.add_edge(START, "credit_check")

    # Credit check → Conditional: summarization (if needed) OR agent OR END (no credits)
    workflow.add_conditional_edges(
        "credit_check",
        route_after_credit_check,
        {
            "summarization": "summarization",
            "agent": "agent",
            "end": END,
        }
    )

    # Summarization → Agent
    workflow.add_edge("summarization", "agent")

    # Agent → Conditional: tools (if tool calls) OR END (no tools / UI tools)
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )

    # Tools → Agent (loop back for follow-up after tool execution)
    workflow.add_edge("tools", "agent")

    return workflow


# ============================================================
# LAZY GRAPH INITIALIZATION
# ============================================================
# Graph must be created lazily because:
# 1. AsyncRedisSaver requires an event loop (doesn't exist at module import)
# 2. AG-UI/CopilotKit uses async methods that need async-compatible checkpointer

_chat_graph_cache = None

def get_chat_graph():
    """
    Lazy factory for chat graph with AsyncRedisSaver.
    Creates the graph on first call and caches it.
    Must be called within an async context (e.g., FastAPI request handler).
    """
    global _chat_graph_cache
    
    if _chat_graph_cache is not None:
        return _chat_graph_cache
    
    workflow = create_chat_workflow()
    REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")
    
    try:
        checkpointer = AsyncRedisSaver(redis_url=REDIS_URI)
        print(f"✅ Using AsyncRedisSaver for persistence ({REDIS_URI})")
        _chat_graph_cache = workflow.compile(checkpointer=checkpointer)
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")
        print("⚠️ Falling back to MemorySaver (no persistence)")
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
        _chat_graph_cache = workflow.compile(checkpointer=checkpointer)
    
    return _chat_graph_cache


# For backwards compatibility - create sync version for CLI testing
def create_chat_graph():
    """Create graph with MemorySaver for sync contexts (CLI testing)."""
    workflow = create_chat_workflow()
    from langgraph.checkpoint.memory import MemorySaver
    return workflow.compile(checkpointer=MemorySaver())


# Backwards compatibility export (uses MemorySaver, for CLI only)
chat_graph = create_chat_graph()


# ============================================================
# CLI TEST
# ============================================================
if __name__ == "__main__":
    print("🧪 Testing Unified Agent Chat...\n")

    # Test conversation
    test_messages = [
        "Hello!",  # Simple greeting
        "What chapters does my document have?",  # Should use query_structure
        "Explain the main concept",  # Should use search_documents
    ]

    config = {"configurable": {"thread_id": "test-thread-1"}}

    for i, query in enumerate(test_messages, 1):
        print(f"\n{'='*60}")
        print(f"Turn {i}: {query}")
        print('='*60)

        result = chat_graph.invoke(
            {"messages": [HumanMessage(content=query)]},
            config=config
        )

        # Print response
        last_msg = result["messages"][-1]
        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
            print(f"\n🔧 Tool calls: {[tc['name'] for tc in last_msg.tool_calls]}")
        if last_msg.content:
            print(f"\n🤖 Response:\n{last_msg.content[:500]}...")
