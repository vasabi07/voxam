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
from typing import Optional, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from copilotkit import CopilotKitState
from dotenv import load_dotenv

load_dotenv()

# Import retrieval function
from retrieval import retrieve_context

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")


# ============================================================
# STATE DEFINITION
# ============================================================
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

# Main model for generation (streaming enabled for better UX)
generator_llm = ChatOpenAI(
    model="nvidia/Nemotron-3-Nano-30B-A3B",
    api_key=DEEPINFRA_API_KEY,
    base_url="https://api.deepinfra.com/v1/openai",
    temperature=0.7,
    streaming=True
)


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
    # min_score=0.018: Only keep quality matches (RRF max ≈ 0.033)
    # max_chars=20000: ~5000 tokens, generous room for multi-block context
    context = retrieve_context(
        query_text=query,
        user_id=user_id,  # Filter by user's documents only
        doc_id=doc_id,    # Optional: scope to single document
        k=4,
        min_score=0.018,
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
SYSTEM_PROMPT = """You are an intelligent study assistant for Voxam, an AI-powered exam preparation platform. You help students understand their course materials through clear, accurate explanations.

INSTRUCTIONS:
1. Answer based ONLY on the provided context. Do not make up information.
2. If the context doesn't contain relevant information, say so honestly.
3. Use clear, educational language appropriate for students.
4. When referencing specific information, mention the source (e.g., "According to the document on page 5...")
5. Break down complex concepts into digestible parts.
6. If asked about topics outside the context, politely redirect to ask about the available materials.

CONTEXT FROM COURSE MATERIALS:
{context}

---
Remember: Be helpful, accurate, and educational. Cite your sources when possible."""


def generator_node(state: ChatState) -> dict:
    """
    Generates the final response using context and conversation history.
    """
    messages = state.get("messages", [])
    context = state.get("retrieved_context", "")
    
    # Build system message with context
    if context:
        system_content = SYSTEM_PROMPT.format(context=context)
    else:
        system_content = """You are an intelligent study assistant for Voxam. 
Unfortunately, I couldn't find relevant information in the course materials for this query.
Please let the user know and suggest they rephrase their question or ask about specific topics from their uploaded documents."""
    
    # Prepare messages for LLM (system + conversation history)
    llm_messages = [SystemMessage(content=system_content)]
    
    # Add conversation history (limit to recent exchanges for context window)
    for msg in messages[-10:]:  # Last 10 messages
        if isinstance(msg, HumanMessage):
            llm_messages.append(HumanMessage(content=msg.content))
        elif isinstance(msg, AIMessage):
            llm_messages.append(AIMessage(content=msg.content))
    
    # Generate response
    response = generator_llm.invoke(llm_messages)
    
    print(f"✅ Generated response ({len(response.content)} chars)")
    
    # Return AI message to be added to state
    return {"messages": [AIMessage(content=response.content)]}


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================
def route_rewriter(state: ChatState) -> str:
    """
    Router function: decides whether to rewrite or skip.
    """
    if should_rewrite(state):
        return "rewrite"
    return "skip"


def create_chat_graph():
    """
    Create the Agentic RAG chat graph.
    
    Flow:
      START
        ↓
      [Conditional: should_rewrite?]
        ├─ yes → query_rewriter → retriever → generator → END
        └─ no  → skip_rewriter → retriever → generator → END
    """
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("skip_rewriter", skip_rewriter_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("generator", generator_node)
    
    # Conditional entry: rewrite or skip
    workflow.add_conditional_edges(
        "__start__",  # LangGraph's built-in start node
        route_rewriter,
        {
            "rewrite": "query_rewriter",
            "skip": "skip_rewriter"
        }
    )
    
    # Both paths converge at retriever
    workflow.add_edge("query_rewriter", "retriever")
    workflow.add_edge("skip_rewriter", "retriever")
    
    # Retriever → Generator → END
    workflow.add_edge("retriever", "generator")
    workflow.add_edge("generator", END)
    
    # Compile with MemorySaver for now
    # TODO: Switch to Redis for production persistence across restarts
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    
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
