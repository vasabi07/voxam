"""
Agentic RAG Chat Agent for Voxam.
Uses Query Rewriting + Hybrid Search Retrieval + Contextual Generation.

Flow:
  1. Query Rewriter (conditional) - contextualizes follow-up questions
  2. Retriever - calls Hybrid Search (Vector + Keyword + RRF)
  3. Generator - synthesizes response with citations
"""

import os
import re
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END, START
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.checkpoint.redis.base import BaseRedisSaver, CHECKPOINT_PREFIX, CHECKPOINT_BLOB_PREFIX, CHECKPOINT_WRITE_PREFIX, REDIS_KEY_SEPARATOR
import redis.asyncio as redis
import asyncio
from copilotkit import CopilotKitState
from copilotkit.langgraph import copilotkit_customize_config
from dotenv import load_dotenv

load_dotenv()

# Import retrieval function
from retrieval import retrieve_context

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")

# Helper class to handle Redis serialization issues and async loop binding
# SafeAsyncRedisSaver removed for stability revert



# ============================================================
# STATE DEFINITION
# ============================================================
# Route options for Adaptive RAG
ROUTE_RAG = "rag"
ROUTE_TOOL = "tool"
ROUTE_DIRECT = "direct"

# Pydantic model for structured routing output
class RouteClassification(BaseModel):
    """Classification of user query intent."""
    route: Literal["rag", "tool", "direct"] = Field(
        description="The classification of the user query. 'rag' for questions needing document context, 'tool' for actions like creating exams or uploading, 'direct' for greetings and meta questions."
    )
class ChatState(CopilotKitState):
    """
    Extended CopilotKitState with RAG-specific fields.
    CopilotKitState extends MessagesState and includes copilotkit context.
    """
    # RAG fields
    rewritten_query: Optional[str]       # Contextualized query (if rewritten)
    retrieved_context: Optional[str]     # Context from hybrid search
    citations: Optional[List[str]]       # Source citations [Doc:X page:Y]
    doc_id: Optional[str]                # Active document ID (for scoped retrieval)
    user_id: Optional[str]               # User ID for document isolation
    route: Optional[str]                 # Intent route: "rag", "tool", or "direct"
    needs_web_search: Optional[bool]     # True if no context found and user wants web search


# ============================================================
# LLM INSTANCES
# ============================================================
# Using Nemotron 3 Nano 30B on DeepInfra - cheap, fast, excellent for RAG
# Cost: ₹0.012 per chat (75% cheaper than GPT-4o-mini)
rewriter_llm = ChatOpenAI(
    model="nvidia/Nemotron-3-Nano-30B-A3B",
    api_key=DEEPINFRA_API_KEY,
    base_url="https://api.deepinfra.com/v1/openai",
    temperature=0
)

# Router LLM for intent classification (fast, deterministic)
router_llm = ChatOpenAI(
    model="nvidia/Nemotron-3-Nano-30B-A3B",
    api_key=DEEPINFRA_API_KEY,
    base_url="https://api.deepinfra.com/v1/openai",
    temperature=0,  # Deterministic for consistent routing
    max_tokens=10   # Only need a single word response
)

# Main model for generation (streaming enabled for better UX)
_base_generator_llm = ChatOpenAI(
    model="nvidia/Nemotron-3-Nano-30B-A3B",
    api_key=DEEPINFRA_API_KEY,
    base_url="https://api.deepinfra.com/v1/openai",
    temperature=0.7,
    streaming=True
)


# ============================================================
# UI TOOLS FOR GENERATIVE UI (A2UI)
# ============================================================
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


# Bind tools to generator LLM
ui_tools = [request_qp_form, request_upload_ui]
generator_llm = _base_generator_llm.bind_tools(ui_tools)


# ============================================================
# NODE 0: ROUTER (Adaptive RAG)
# ============================================================
async def router_node(state: ChatState, config) -> dict:
    """
    LLM-based router that classifies query intent.
    Uses simple text parsing since DeepInfra doesn't support LangChain's json_schema.
    
    Routes to:
    - "rag": Needs document context (questions about course material)
    - "tool": User wants an action (create exam, upload file)
    - "direct": Can answer without context (greetings, meta questions)
    """
    messages = state.get("messages", [])
    if not messages:
        return {"route": ROUTE_DIRECT}
    
    query = messages[-1].content.strip().lower()
    
    # Fast-path: Simple pattern matching for obvious cases
    # This avoids an LLM call for trivial queries
    greeting_patterns = ["hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye"]
    tool_patterns = ["create exam", "create quiz", "create test", "create question", 
                     "generate exam", "generate quiz", "generate test", "generate question",
                     "upload", "ingest", "add document", "add file", "i want to create", 
                     "i wanna create", "make an exam", "make a quiz"]
    
    for pattern in greeting_patterns:
        if query == pattern or query.startswith(pattern + " ") or query.startswith(pattern + "!"):
            print(f"🔀 Router (fast): '{query[:30]}...' → direct")
            return {"route": ROUTE_DIRECT}
    
    for pattern in tool_patterns:
        if pattern in query:
            print(f"🔀 Router (fast): '{query[:30]}...' → tool")
            return {"route": ROUTE_TOOL}
    
    # LLM-based classification for ambiguous cases (text response, manually parsed)
    router_prompt = f"""Classify this user query into exactly one category.

QUERY: "{query}"

Respond with ONLY one word: rag, tool, or direct

- rag: Questions about course content, explanations, definitions, concepts, or anything that needs document search
- tool: User wants to CREATE something (exam, quiz, test) or UPLOAD a document  
- direct: Simple greetings, thanks, meta questions about capabilities

RESPOND WITH ONLY ONE WORD:"""

    try:
        result = await router_llm.ainvoke([SystemMessage(content=router_prompt)])
        response = result.content.strip().lower()
        
        # Parse the single-word response
        if "tool" in response:
            route = ROUTE_TOOL
        elif "direct" in response:
            route = ROUTE_DIRECT
        else:
            route = ROUTE_RAG  # Default to RAG for safety
            
        print(f"🔀 Router (LLM): '{query[:30]}...' → {route}")
    except Exception as e:
        # Fallback to RAG on any error
        print(f"⚠️ Router error, defaulting to RAG: {e}")
        route = ROUTE_RAG
    
    return {"route": route}


# ============================================================
# REGEX PATTERNS FOR SKIP OPTIMIZATION
# ============================================================
# Skip rewriting ONLY for simple greetings/farewells (no ambiguity)
SKIP_REWRITE_PATTERNS = [
    r"^(hi|hello|hey|thanks|thank you|bye|goodbye|ok|okay|yes|no|sure)[\s!?.]*$",
]

# Anaphoric references that ALWAYS need rewriting (even in "what is X" questions)
ANAPHORIC_PATTERNS = [
    r"\b(it|this|that|these|those|they|them|he|she|his|her|its)\b",
    r"\b(more|further|additional|another|same|other)\b",
    r"\b(above|previous|earlier|mentioned|former|latter)\b",
]


# ============================================================
# NODE 1: QUERY REWRITER (Conditional)
# ============================================================
def should_rewrite(state: ChatState) -> bool:
    """
    Determine if the query needs rewriting based on:
    1. Conversation history length
    2. Presence of pronouns/references ("it", "that", "this", "more")
    3. Skip patterns for standalone queries
    """
    messages = state.get("messages", [])
    
    # Need at least 2 exchanges (4 messages) for context-dependent questions
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if len(human_messages) <= 1:
        return False
    
    # Get latest query
    latest_msg = messages[-1]
    if not isinstance(latest_msg, HumanMessage):
        return False
    
    query = latest_msg.content.lower().strip()
    
    # FIRST: Check for anaphoric references - these ALWAYS need rewriting
    # (even "what is that?" needs to become "what is photosynthesis?")
    for pattern in ANAPHORIC_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    
    # THEN: Check skip patterns (only pure greetings with no references)
    for pattern in SKIP_REWRITE_PATTERNS:
        if re.match(pattern, query, re.IGNORECASE):
            return False
    
    # Short queries (< 4 words) after conversation likely need context
    if len(query.split()) < 4 and len(human_messages) > 1:
        return True
    
    return False


def query_rewriter_node(state: ChatState) -> dict:
    """
    Rewrites the query to be self-contained using conversation history.
    Only called if should_rewrite() returns True.
    """
    messages = state.get("messages", [])
    latest_query = messages[-1].content
    
    # Build conversation summary for context (last 6 messages max)
    recent_messages = messages[-7:-1]  # Exclude latest query
    conversation_context = "\n".join([
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content[:200]}"
        for m in recent_messages
    ])
    
    rewrite_prompt = f"""You are a query rewriter for a RAG system. Your task is to rewrite the user's latest query to be self-contained, incorporating necessary context from the conversation history.

CONVERSATION HISTORY:
{conversation_context}

LATEST USER QUERY: "{latest_query}"

INSTRUCTIONS:
1. If the query contains pronouns or references (it, this, that, more, etc.), resolve them using conversation context
2. Make the query specific and searchable
3. Keep it concise (1-2 sentences max)
4. If the query is already self-contained, return it unchanged

REWRITTEN QUERY:"""
    
    # Run without config - CopilotKit won't intercept this as it's a "naked" sync call
    response = rewriter_llm.invoke([SystemMessage(content=rewrite_prompt)])
    rewritten = response.content.strip().strip('"')
    
    print(f"🔄 Query Rewritten: '{latest_query}' → '{rewritten}'")
    
    return {"rewritten_query": rewritten}


def skip_rewriter_node(state: ChatState) -> dict:
    """
    Passthrough node when rewriting is skipped.
    Uses the original query as-is.
    """
    messages = state.get("messages", [])
    original_query = messages[-1].content if messages else ""
    
    print(f"⏭️  Skipping rewrite, using original: '{original_query}'")
    
    return {"rewritten_query": original_query}


# ============================================================
# NODE 2: RETRIEVER
# ============================================================
def get_user_context(state: ChatState) -> tuple[Optional[str], Optional[str]]:
    """
    Extracts user_id and doc_id from CopilotKit context.
    Returns (user_id, doc_id) tuple.
    """
    copilotkit = state.get("copilotkit", {})
    context_items = copilotkit.get("context", [])
    
    user_id = None
    doc_id = None
    
    for item in context_items:
        # Handle both dict and Pydantic Context objects
        if hasattr(item, 'description'):
            # Pydantic object
            desc = item.description
            value = item.value if hasattr(item, 'value') else {}
        else:
            # Dict fallback
            desc = item.get("description", "")
            value = item.get("value", {})
        
        # Handle value as dict or object
        if hasattr(value, 'get'):
            # It's a dict
            value_dict = value
        elif hasattr(value, '__dict__'):
            # It's an object, convert to dict
            value_dict = value.__dict__ if hasattr(value, '__dict__') else {}
        else:
            value_dict = {}
        
        if desc == "The current user's information":
            user_id = value_dict.get("user_id") if isinstance(value_dict, dict) else getattr(value, 'user_id', None)
        elif desc == "The current document context":
            doc_id = value_dict.get("doc_id") if isinstance(value_dict, dict) else getattr(value, 'doc_id', None)
    
    return user_id, doc_id


def retriever_node(state: ChatState) -> dict:
    """
    Retrieves relevant context using Hybrid Search.
    Uses rewritten_query if available, otherwise original query.
    Filters by user_id for document isolation, optionally scoped to single doc.
    """
    # Get the query to search
    query = state.get("rewritten_query")
    if not query:
        messages = state.get("messages", [])
        query = messages[-1].content if messages else ""
    
    # Get user_id and doc_id from CopilotKit context
    user_id, doc_id = get_user_context(state)
    
    # Fallback to state fields if copilotkit context not available
    if not user_id:
        user_id = state.get("user_id")
    if not doc_id:
        doc_id = state.get("doc_id")
    
    scope = f"doc:{doc_id}" if doc_id else "all docs"
    print(f"🔍 Retrieving context for: '{query}' (user: {user_id or 'ALL'}, {scope})")
    
    # Call hybrid search with smart filtering:
    # k=4: Fetch top candidates (chunks are title-based, fewer needed)
    # min_vector_score=0.60: Primary relevance filter - excludes semantically distant results
    # min_score=0.01: Secondary RRF threshold for final ranking
    # max_chars=20000: ~5000 tokens, generous room for multi-block context
    context = retrieve_context(
        query_text=query,
        user_id=user_id,  # Filter by user's documents only
        doc_id=doc_id,    # Optional: scope to single document
        k=4,
        min_score=0.01,   # Lowered since vector filter handles relevance
        min_vector_score=0.60,  # Filter out unrelated queries (score < 0.60)
        max_chars=20000
    )
    
    # Extract citations from context
    citations = []
    if context:
        # Parse [Doc:X page:Y] patterns
        citation_pattern = r'\[Doc:([^\]]+)\s+(?:page:|pgs:)([^\]]+)\]'
        matches = re.findall(citation_pattern, context)
        citations = [f"Doc:{m[0]} page:{m[1]}" for m in matches]
        citations = list(dict.fromkeys(citations))  # Dedupe preserving order
    
    print(f"📚 Retrieved {len(citations)} sources")
    
    return {
        "retrieved_context": context,
        "citations": citations
    }


# ============================================================
# NODE 3: GENERATOR
# ============================================================
SYSTEM_PROMPT = """You are an intelligent study assistant for Voxam, an AI-powered exam preparation platform.

INSTRUCTIONS:
1. Answer based ONLY on the provided context. Do not invent information.
2. Use clear, educational language appropriate for students.
3. Cite sources when possible (e.g., "According to the document on page 5...").
4. Break down complex concepts into digestible parts.

CONTEXT FROM COURSE MATERIALS:
{context}

---
Be helpful, accurate, and educational."""


async def generator_node(state: ChatState, config) -> dict:
    """
    Generates the final response using context and conversation history.
    Handles both text responses AND tool calls (for Generative UI).
    Uses async streaming for proper AG-UI event handling.
    """
    messages = state.get("messages", [])
    context = state.get("retrieved_context", "")
    needs_web_search = state.get("needs_web_search", False)
    
    # Debug: Log the state values
    print(f"🔧 Generator state: context={len(context)} chars, needs_web_search={needs_web_search}")
    
    # Enable tool call emission for Generative UI
    # This ensures tool calls are streamed to the frontend via AG-UI
    config = copilotkit_customize_config(
        config,
        emit_tool_calls=True,  # Enable tool call streaming for Generative UI
        emit_messages=True,    # Enable message streaming
    )
    
    # Build system message based on state
    if context:
        # Normal RAG path - we have relevant context
        system_content = SYSTEM_PROMPT.format(context=context)
    elif needs_web_search:
        # User approved web search - provide a helpful response
        # TODO: Integrate actual web search API (Tavily/Brave)
        system_content = """You are an intelligent study assistant for Voxam.

The user approved a web search, but this feature is not yet fully implemented.

Respond with:
1. Acknowledge that web search is coming soon
2. Briefly explain what you know about the topic from general knowledge
3. Suggest they can ask about topics from their uploaded course materials in the meantime

Keep it friendly and helpful (3-4 sentences max)."""
    else:
        # No context found and user declined web search
        system_content = """You are an intelligent study assistant for Voxam.

I couldn't find relevant information in the uploaded course materials for this question.

Respond with a SHORT, friendly message:
1. Acknowledge you don't have information on this topic in the available materials.
2. Suggest they could ask about a different topic from their uploaded documents.

DO NOT suggest creating exams or uploading documents unless the user specifically asked for that.
Keep your response brief (2-3 sentences max)."""
    
    # Prepare messages for LLM (system + conversation history)
    llm_messages = [SystemMessage(content=system_content)]
    
    # Add conversation history (limit to recent exchanges for context window)
    for msg in messages[-10:]:  # Last 10 messages
        if isinstance(msg, HumanMessage):
            llm_messages.append(HumanMessage(content=msg.content))
        elif isinstance(msg, AIMessage):
            llm_messages.append(AIMessage(content=msg.content))
    
    # Use streaming with config for proper AG-UI event handling
    # Accumulate chunks properly to build the complete response
    full_response = None
    async for chunk in generator_llm.astream(llm_messages, config=config):
        if full_response is None:
            full_response = chunk
        else:
            full_response = full_response + chunk  # Accumulate chunks properly
    
    # Check if this is a tool call or a regular text response
    if full_response.tool_calls:
        # LLM wants to call a tool (Generative UI)
        print(f"🔧 Tool call detected: {[tc['name'] for tc in full_response.tool_calls]}")
        # Return the full AIMessage with tool_calls intact
        return {"messages": [full_response]}
    else:
        # Regular text response
        print(f"✅ Generated response ({len(full_response.content)} chars)")
        return {"messages": [AIMessage(content=full_response.content)]}


# ============================================================
# NODE 4: HITL WEB SEARCH CHECK
# ============================================================
def should_offer_web_search(state: ChatState) -> str:
    """
    Check if we should offer web search (no context found).
    Returns "offer" to trigger HITL, "skip" to go straight to generator.
    """
    # Force skip to disable HITL for stability
    return "skip"



async def hitl_web_search_node(state: ChatState, config) -> dict:
    """
    Human-in-the-Loop node for web search confirmation.
    Uses interrupt() to pause execution and ask the user.
    The frontend handles the UI via useLangGraphInterrupt.
    """
    messages = state.get("messages", [])
    query = messages[-1].content if messages else "your question"
    
    print(f"⏸️ Triggering HITL for web search: {query[:50]}...")
    
    # Interrupt with a payload that the frontend can render
    result = interrupt({
        "type": "web_search_confirmation",
        "message": f"I couldn't find information about this in your course materials. Would you like me to search the web?",
        "query": query[:100],  # Truncated for display
        "options": ["Yes, search the web", "No, thanks"]
    })
    
    print(f"🔄 HITL result received: {result} (type: {type(result).__name__})")
    
    # Handle result - could be string, dict, or JSON string depending on AG-UI version
    approved = False
    if isinstance(result, dict):
        approved = result.get("approved", False)
    elif isinstance(result, str):
        # Try parsing as JSON first
        import json
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                approved = parsed.get("approved", False)
        except (json.JSONDecodeError, TypeError):
            # Check if it's a simple string like "true" or contains "approved"
            approved = "true" in result.lower() or "yes" in result.lower()
    
    if approved:
        print(f"✅ User approved web search")
        return {"needs_web_search": True}
    else:
        print(f"❌ User declined web search")
        return {"needs_web_search": False}


# ============================================================
# GRAPH CONSTRUCTION - ADAPTIVE RAG
# ============================================================
def route_by_intent(state: ChatState) -> str:
    """
    Route based on router_node's classification.
    """
    route = state.get("route", ROUTE_RAG)
    return route


def route_rewriter(state: ChatState) -> str:
    """
    Router function: decides whether to rewrite or skip.
    Only called when route is "rag".
    """
    if should_rewrite(state):
        return "rewrite"
    return "skip"


async def direct_generator_node(state: ChatState, config) -> dict:
    """
    Generate response for direct queries (greetings, meta questions).
    No RAG context needed - simpler and faster.
    """
    messages = state.get("messages", [])
    
    # Enable streaming for AG-UI
    config = copilotkit_customize_config(
        config,
        emit_tool_calls=True,
        emit_messages=True,
    )
    
    system_content = """You are an intelligent study assistant for Voxam, an AI-powered exam preparation platform.

You can help students with:
- Answering questions about their uploaded course materials
- Creating exams and quizzes from their documents
- Uploading new documents for study

Be friendly, helpful, and concise. If the user wants to perform an action like creating an exam or uploading a document, use the appropriate tool."""
    
    llm_messages = [SystemMessage(content=system_content)]
    for msg in messages[-6:]:
        if isinstance(msg, HumanMessage):
            llm_messages.append(HumanMessage(content=msg.content))
        elif isinstance(msg, AIMessage):
            llm_messages.append(AIMessage(content=msg.content))
    
    full_response = None
    async for chunk in generator_llm.astream(llm_messages, config=config):
        if full_response is None:
            full_response = chunk
        else:
            full_response = full_response + chunk
    
    if full_response.tool_calls:
        print(f"🔧 Direct: Tool call detected: {[tc['name'] for tc in full_response.tool_calls]}")
        return {"messages": [full_response]}
    else:
        print(f"✅ Direct response ({len(full_response.content)} chars)")
        return {"messages": [AIMessage(content=full_response.content)]}


def create_chat_graph():
    """
    Create the Adaptive RAG chat graph.
    
    Flow:
      START
        ↓
      router (LLM classifies intent)
        ├─ "direct" → direct_generator → END
        ├─ "tool"   → generator (with tools, no RAG) → END
        └─ "rag"    → [rewrite?] → retriever → [HITL check] → generator → END
                         ├─ yes → query_rewriter → retriever
                         └─ no  → skip_rewriter → retriever
                                                     ├─ no context → hitl_web_search → generator
                                                     └─ has context → generator
    """
    workflow = StateGraph(ChatState)
    
    # Add all nodes
    workflow.add_node("router", router_node)
    workflow.add_node("direct_generator", direct_generator_node)
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("skip_rewriter", skip_rewriter_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("hitl_web_search", hitl_web_search_node)  # HITL node
    workflow.add_node("generator", generator_node)
    
    # Combined routing function for router node
    def combined_route(state: ChatState) -> str:
        route = state.get("route", ROUTE_RAG)
        if route == ROUTE_DIRECT:
            return "direct"
        elif route == ROUTE_TOOL:
            return "tool"
        elif route == ROUTE_RAG:
            if should_rewrite(state):
                return "rag_rewrite"
            else:
                return "rag_skip"
        return "rag_skip"
    
    # START → Router
    workflow.add_edge(START, "router")
    
    # Router → appropriate path
    workflow.add_conditional_edges(
        "router",
        combined_route,
        {
            "direct": "direct_generator",
            "tool": "generator",
            "rag_rewrite": "query_rewriter",
            "rag_skip": "skip_rewriter",
        }
    )
    
    # Direct path → END
    workflow.add_edge("direct_generator", END)
    
    # Tool path → END (generator handles tool calls)
    workflow.add_edge("generator", END)
    
    # RAG paths converge at retriever
    workflow.add_edge("query_rewriter", "retriever")
    workflow.add_edge("skip_rewriter", "retriever")
    
    # Retriever → HITL check or Generator
    workflow.add_conditional_edges(
        "retriever",
        should_offer_web_search,
        {
            "offer": "hitl_web_search",
            "skip": "generator",
        }
    )
    
    # HITL → Generator (after user responds)
    workflow.add_edge("hitl_web_search", "generator")
    
    # Use Redis checkpointer for persistent state across restarts
    # This is required for AG-UI/CopilotKit to properly handle:
    # - Thread continuity
    # - HITL interrupt/resume
    # - Message ID lookups
    # Use MemorySaver for stable (non-persistent) state
    # This prevents serialization issues and "Message ID not found" (as long as server stays up)
    # Use MemorySaver for stable (non-persistent) state
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
    print("⚠️ Using MemorySaver (persistence disabled)")
    
    graph = workflow.compile(checkpointer=checkpointer)
    
    return graph


# Create the graph instance (imported by CopilotKit)
chat_graph = create_chat_graph()


# ============================================================
# CLI TEST
# ============================================================
if __name__ == "__main__":
    print("🧪 Testing Agentic RAG Chat Agent...\n")
    
    # Test conversation
    test_messages = [
        "What is photosynthesis?",
        "Tell me more about the light reactions",  # Should trigger rewrite
        "What are the products?",  # Should trigger rewrite (short + context)
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
        ai_response = result["messages"][-1].content
        print(f"\n🤖 Response:\n{ai_response[:500]}...")
        
        # Print citations if available
        if result.get("citations"):
            print(f"\n📚 Sources: {result['citations']}")
