"""
Knowledge Tools for Agentic Chat Agent.
Provides tools for document search, graph queries, and question retrieval.

Tools:
- search_documents: Hybrid search (vector + keyword) for content retrieval
- query_structure: Text2Cypher for structural queries (chapters, sections, counts)
- get_questions: Retrieve generated questions from QuestionSet nodes

All tools use RunnableConfig to get user_id and doc_id from the thread_id.
"""

import os
import json
import random
from pathlib import Path
from typing import Optional, List
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Import from existing modules
from retrieval import retrieve_context_with_sources
from ingestion_workflow import get_neo4j_driver


# ============================================================
# HELPER: EXTRACT USER CONTEXT FROM CONFIG
# ============================================================
def get_user_context_from_config(config: RunnableConfig) -> tuple[Optional[str], Optional[str]]:
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Lightweight LLM for Cypher generation
cypher_llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    temperature=0,
    max_tokens=500
)

# ============================================================
# NEO4J SCHEMA FOR TEXT2CYPHER
# ============================================================
CYPHER_SCHEMA = """
Neo4j Schema for user's documents:

NODES:
- User {id: String}
- Document {documentId: String, title: String, source: String}
- ContentBlock {block_id: String, text_content: String, chapter_title: String, section_title: String, content_type: String, page_start: Int, page_end: Int}
- QuestionSet {questionset_id: String, questions: JSON String, total_count: Int, doc_id: String}
- Chapter {doc_id: String, title: String}
- Section {doc_id: String, title: String, chapter: String}

RELATIONSHIPS:
- (User)-[:UPLOADED]->(Document)
- (Document)-[:HAS_CONTENT_BLOCK]->(ContentBlock)
- (Document)-[:HAS_CHAPTER]->(Chapter)
- (Chapter)-[:HAS_SECTION]->(Section)
- (Chapter)-[:CONTAINS]->(ContentBlock)
- (Section)-[:CONTAINS]->(ContentBlock)
- (ContentBlock)-[:HAS_QUESTIONS]->(QuestionSet)

CONTENT_TYPES: narrative, definition, example, theorem, procedure, summary

CRITICAL RULES:
- Always filter by user_id for security: (u:User {id: $user_id})
- Use OPTIONAL MATCH when relationships might not exist
- Return meaningful aliases (AS chapter, AS section, etc.)
- NEVER use ORDER BY with columns not in RETURN when using DISTINCT
- When using RETURN DISTINCT, only ORDER BY columns that are in the RETURN clause
- Keep queries simple - prefer Chapter and Section nodes over ContentBlock for structure queries
"""

# ============================================================
# TOOL: SEARCH DOCUMENTS (Hybrid RAG)
# ============================================================
@tool
def search_documents(query: str, config: RunnableConfig) -> str:
    """
    Search document content using semantic + keyword hybrid search.

    Use for:
    - Explanations and definitions
    - Understanding concepts
    - Finding specific content in documents

    Args:
        query: What to search for (natural language)

    Returns:
        Relevant text passages with page numbers and sources.
    """
    # Extract user_id and doc_id from config
    user_id, doc_id = get_user_context_from_config(config)

    if not user_id:
        return "Error: Unable to identify user. Please ensure you're logged in."

    print(f"🔍 search_documents: query='{query[:50]}...', user={user_id}, doc={doc_id}")

    context, sources = retrieve_context_with_sources(
        query_text=query,
        user_id=user_id,
        doc_id=doc_id,
        k=5,  # Fewer chunks for tool response
        max_chars=6000
    )

    if not context:
        return f"No relevant content found for '{query}' in your documents."

    # Format response with sources
    result = f"Found {len(sources)} relevant passages:\n\n{context}"

    # Add source summary for show_sources tool
    if sources:
        source_info = "\n\nSOURCES_FOR_CITATION: " + json.dumps([
            {
                "page": s.get("page"),
                "page_end": s.get("page_end"),
                "title": s.get("title", ""),
                "doc_id": s.get("doc_id", ""),
                "doc_title": s.get("doc_title", "")
            }
            for s in sources[:5]
        ])
        result += source_info

    return result


# ============================================================
# HELPER: EXTRACT DOC_ID FROM QUESTION
# ============================================================
import re

UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)

def extract_doc_id_from_question(question: str) -> Optional[str]:
    """Extract a UUID doc_id from the question if present."""
    match = UUID_PATTERN.search(question)
    return match.group(0) if match else None


# ============================================================
# TOOL: QUERY STRUCTURE (Text2Cypher)
# ============================================================
@tool
def query_structure(question: str, config: RunnableConfig) -> str:
    """
    Query document structure via Neo4j graph using natural language.

    Use for:
    - Listing chapters and sections
    - Counting topics, definitions, examples
    - Understanding document organization
    - Finding what content types exist

    Examples:
    - "What chapters does this document have?"
    - "List all sections in Chapter 2"
    - "How many definitions are in the document?"
    - "What topics are covered?"

    Args:
        question: Natural language question about structure

    Returns:
        Structured data (lists, counts, hierarchies)
    """
    # Extract user_id and doc_id from config
    user_id, doc_id = get_user_context_from_config(config)

    if not user_id:
        return "Error: Unable to identify user. Please ensure you're logged in."

    # Try to extract doc_id from the question if not already set
    if not doc_id:
        extracted_doc_id = extract_doc_id_from_question(question)
        if extracted_doc_id:
            doc_id = extracted_doc_id
            print(f"📎 Extracted doc_id from question: {doc_id}")

    print(f"🔍 query_structure: question='{question[:50]}...', user={user_id}, doc={doc_id}")

    driver = get_neo4j_driver()

    # Build Cypher generation prompt
    cypher_prompt = f"""Given this Neo4j schema:
{CYPHER_SCHEMA}

Generate a Cypher query to answer: "{question}"

Context:
- user_id: "{user_id}"
- doc_id: "{doc_id or 'any (query all user documents)'}"

Requirements:
- ALWAYS start with: MATCH (u:User {{id: $user_id}})-[:UPLOADED]->(d:Document)
- If doc_id is provided, add: WHERE d.documentId = $doc_id
- Use DISTINCT to avoid duplicates
- Return meaningful column names
- Limit results to 50 max
- CRITICAL: When using RETURN DISTINCT, only ORDER BY columns that appear in the RETURN clause
- Keep queries simple - use Chapter/Section nodes for structure, not ContentBlock

Return ONLY the Cypher query, no explanation or markdown."""

    try:
        # Generate Cypher
        response = cypher_llm.invoke(cypher_prompt)
        cypher = response.content.strip()

        # Clean up any markdown formatting
        if cypher.startswith("```"):
            cypher = cypher.split("```")[1]
            if cypher.startswith("cypher"):
                cypher = cypher[6:]
            cypher = cypher.strip()

        print(f"🔍 Text2Cypher generated:\n{cypher}")

        # Execute query
        with driver.session() as session:
            # Always pass doc_id (even if None) since LLM may reference it
            params = {"user_id": user_id, "doc_id": doc_id}

            result = session.run(cypher, **params)
            records = [dict(r) for r in result]

        if not records:
            return f"No results found for: {question}"

        # Format results
        return format_cypher_results(question, records)

    except Exception as e:
        print(f"❌ Text2Cypher error: {e}")
        # Fallback to simple structure query - return with error context
        # so the agent knows the query failed and can try alternatives
        return fallback_structure_query(user_id, doc_id, error_context=str(e))


def format_cypher_results(question: str, records: List[dict]) -> str:
    """Format Cypher query results into readable text."""
    if not records:
        return "No results found."

    # If single column, format as list
    if len(records[0]) == 1:
        key = list(records[0].keys())[0]
        items = [str(r[key]) for r in records if r[key]]
        return f"Found {len(items)} results:\n" + "\n".join(f"- {item}" for item in items)

    # If count query
    if len(records) == 1 and any(k.lower().startswith('count') for k in records[0].keys()):
        counts = [f"{k}: {v}" for k, v in records[0].items()]
        return "\n".join(counts)

    # Multi-column: format as structured list
    result_lines = []
    for r in records[:30]:  # Limit display
        parts = [f"{k}: {v}" for k, v in r.items() if v is not None]
        result_lines.append("• " + ", ".join(parts))

    return f"Found {len(records)} results:\n" + "\n".join(result_lines)


def fallback_structure_query(user_id: str, doc_id: Optional[str] = None, error_context: Optional[str] = None) -> str:
    """Fallback when Text2Cypher fails - return basic structure with context."""
    driver = get_neo4j_driver()

    try:
        with driver.session() as session:
            if doc_id:
                # Query for specific document structure
                result = session.run("""
                    MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document {documentId: $doc_id})
                    OPTIONAL MATCH (d)-[:HAS_CHAPTER]->(c:Chapter)
                    OPTIONAL MATCH (d)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                    WITH d,
                         collect(DISTINCT c.title) AS chapters,
                         collect(DISTINCT cb.chapter_title) AS content_chapters,
                         count(DISTINCT cb) AS block_count
                    RETURN d.title AS document,
                           d.documentId AS doc_id,
                           chapters,
                           content_chapters,
                           block_count
                """, user_id=user_id, doc_id=doc_id)
            else:
                # Query all documents
                result = session.run("""
                    MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)
                    OPTIONAL MATCH (d)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                    WITH d, count(DISTINCT cb) AS block_count
                    RETURN d.title AS document,
                           d.documentId AS doc_id,
                           block_count
                    ORDER BY d.title
                """, user_id=user_id)

            records = [dict(r) for r in result]

            if not records:
                return "No documents found for this user."

            # Format results with helpful context
            formatted = format_cypher_results("Document structure", records)

            # If we had an error, add context so agent knows this is a fallback
            if error_context:
                # Don't include raw error - just indicate we used fallback
                formatted = f"[Using basic structure query]\n\n{formatted}"

            return formatted

    except Exception as e:
        print(f"❌ Fallback query also failed: {e}")
        # Return a clear message that prevents retry loops
        return "Unable to query document structure. Please try using search_documents tool instead to find content."


# ============================================================
# TOOL: GET QUESTIONS
# ============================================================
@tool
def get_questions(
    config: RunnableConfig,
    chapter: Optional[str] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    count: int = 1
) -> str:
    """
    Retrieve generated practice questions from the database.

    Use for:
    - "Give me a question"
    - "Quiz me on chapter 2"
    - "Show me some practice problems"
    - "Test my understanding of thermodynamics"

    Args:
        chapter: Optional - filter by chapter title
        difficulty: Optional - "basic", "intermediate", or "advanced"
        question_type: Optional - "multiple_choice", "short_answer", or "long_answer"
        count: Number of questions to return (default 1)

    Returns:
        Formatted question(s) with options/key points.
    """
    # Extract user_id and doc_id from config
    user_id, doc_id = get_user_context_from_config(config)

    if not user_id:
        return "Error: Unable to identify user. Please ensure you're logged in."

    print(f"🔍 get_questions: chapter={chapter}, difficulty={difficulty}, user={user_id}, doc={doc_id}")

    driver = get_neo4j_driver()

    # Build query based on filters
    query = """
    MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)
    """

    if doc_id:
        query += "WHERE d.documentId = $doc_id\n"

    query += """
    MATCH (d)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)-[:HAS_QUESTIONS]->(qs:QuestionSet)
    """

    if chapter:
        query += f"WHERE cb.chapter_title CONTAINS $chapter\n"

    query += """
    RETURN qs.questions AS questions_json, d.title AS doc_title, cb.chapter_title AS chapter
    LIMIT 10
    """

    try:
        with driver.session() as session:
            params = {"user_id": user_id}
            if doc_id:
                params["doc_id"] = doc_id
            if chapter:
                params["chapter"] = chapter

            result = session.run(query, **params)
            records = [dict(r) for r in result]

        if not records:
            return "No practice questions found. Questions are generated during document ingestion."

        # Collect all questions from all QuestionSets
        all_questions = []
        for r in records:
            try:
                questions = json.loads(r["questions_json"]) if r["questions_json"] else []
                for q in questions:
                    q["_source_chapter"] = r.get("chapter") or "Unknown"
                    q["_source_doc"] = r.get("doc_title") or "Document"
                    all_questions.append(q)
            except json.JSONDecodeError:
                continue

        if not all_questions:
            return "No questions available in the database."

        # Filter by difficulty if specified
        if difficulty:
            filtered = [q for q in all_questions if q.get("difficulty", "").lower() == difficulty.lower()]
            if filtered:
                all_questions = filtered

        # Filter by question type if specified
        if question_type:
            filtered = [q for q in all_questions if q.get("question_type", "").lower() == question_type.lower()]
            if filtered:
                all_questions = filtered

        # Select random questions
        selected = random.sample(all_questions, min(count, len(all_questions)))

        # Format questions
        return format_questions(selected)

    except Exception as e:
        print(f"❌ get_questions error: {e}")
        return f"Error retrieving questions: {str(e)}"


def format_questions(questions: List[dict]) -> str:
    """Format questions for display."""
    if not questions:
        return "No questions to display."

    formatted = []
    for i, q in enumerate(questions, 1):
        text = q.get("text", "No question text")
        q_type = q.get("question_type", "unknown")
        difficulty = q.get("difficulty", "unknown")
        chapter = q.get("_source_chapter", "")

        parts = [f"**Question {i}** ({difficulty}, {q_type})"]
        if chapter:
            parts[0] += f" - {chapter}"
        parts.append(f"\n{text}")

        # Add options for MCQ
        if q_type == "multiple_choice" and q.get("options"):
            parts.append("\nOptions:")
            for j, opt in enumerate(q["options"]):
                letter = chr(65 + j)  # A, B, C, D
                parts.append(f"  {letter}. {opt}")

        # Add key points for long answer
        if q_type == "long_answer" and q.get("key_points"):
            parts.append("\nKey points to cover:")
            for kp in q["key_points"][:3]:
                parts.append(f"  • {kp}")

        formatted.append("\n".join(parts))

    return "\n\n---\n\n".join(formatted)


# ============================================================
# TOOL: GET RULES (Dynamic Context)
# ============================================================
@tool
def get_rules(topics: List[str], config: RunnableConfig) -> str:
    """
    Retrieve formatting and behavior rules for specific topics.

    Call this BEFORE responding when you need guidance on:
    - "math" - How to format equations and mathematical expressions
    - "sources" - How to cite document sources properly
    - "style" - Response tone and structure guidelines
    - "tools" - When to use which tool

    Args:
        topics: List of rule topics needed (e.g., ["math", "sources"])

    Returns:
        Relevant rules for the requested topics.

    Example usage:
    - User asks about physics equation → get_rules(["math", "sources"])
    - User asks for explanation → get_rules(["style", "sources"])
    - Unsure which tool → get_rules(["tools"])
    """
    rules_dir = Path(__file__).parent / "rules"

    topic_to_file = {
        "math": "math_formatting.md",
        "sources": "source_citation.md",
        "style": "response_style.md",
        "tools": "tool_selection.md",
    }

    result = []
    for topic in topics:
        topic_lower = topic.lower().strip()
        if topic_lower in topic_to_file:
            file_path = rules_dir / topic_to_file[topic_lower]
            if file_path.exists():
                content = file_path.read_text()
                result.append(f"## Rules for: {topic_lower}\n\n{content}")
                print(f"📋 Loaded rules: {topic_lower}")

    if result:
        return "\n\n---\n\n".join(result)

    available = ", ".join(topic_to_file.keys())
    return f"No rules found for: {topics}. Available topics: {available}"


# ============================================================
# EXPORT ALL TOOLS
# ============================================================
knowledge_tools = [search_documents, query_structure, get_questions, get_rules]
