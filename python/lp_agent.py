"""
Learn Pack (LP) Generator for Voxam.
Fetches topic-based content from Neo4j and stores in Redis for learn sessions.

Similar to qp_agent.py but for Learn Packs instead of Question Papers.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from neo4j import GraphDatabase
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from redis import Redis
from datetime import datetime
import os
import json

load_dotenv()

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
    raise ValueError("Missing required Neo4j environment variables")

NEO4J_AUTH = (NEO4J_USER, NEO4J_PASSWORD)

# Redis client
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")
r = Redis.from_url(REDIS_URI, decode_responses=True)

# LLM for key concept extraction
llm = init_chat_model(model="gpt-4.1", temperature=0)


# ============================================================
# MODELS
# ============================================================

class TopicInfo(BaseModel):
    """Information about a topic extracted from Neo4j."""
    name: str
    content: str
    key_concepts: List[str] = []
    pages: List[int] = []
    chunk_ids: List[str] = []


class LearnPack(BaseModel):
    """Complete Learn Pack ready for Redis storage."""
    id: str
    doc_id: str
    user_id: str
    created_at: str
    topics: List[TopicInfo]
    total_topics: int
    status: str = "READY"


class LPInputState(BaseModel):
    """Input for creating a Learn Pack."""
    lp_id: str
    document_id: str
    user_id: str
    selected_topics: List[str]  # Topic names from user selection


# ============================================================
# NEO4J QUERIES
# ============================================================

def get_neo4j_driver():
    """Get Neo4j driver."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        with driver.session() as session:
            session.run("RETURN 1")
        print("✅ Connected to Neo4j")
        return driver
    except Exception as e:
        print(f"❌ Cannot connect to Neo4j: {e}")
        raise e


def get_available_topics(document_id: str) -> List[Dict[str, Any]]:
    """
    Get all available topics from a document's content blocks.
    Topics are extracted from parent_header field.

    Returns:
        List of dicts with topic name, chunk count, and page numbers
    """
    driver = get_neo4j_driver()

    query = """
    MATCH (d:Document {documentId: $doc_id})
          -[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
    WHERE cb.parent_header IS NOT NULL AND cb.parent_header <> ''
    RETURN DISTINCT cb.parent_header AS topic,
           count(cb) AS chunk_count,
           collect(DISTINCT cb.page_number) AS pages
    ORDER BY min(cb.chunk_index)
    """

    with driver.session() as session:
        result = session.run(query, doc_id=document_id)
        topics = []
        for record in result:
            topics.append({
                "name": record["topic"],
                "chunk_count": record["chunk_count"],
                "pages": sorted([p for p in record["pages"] if p is not None])
            })

    driver.close()
    print(f"📚 Found {len(topics)} topics in document {document_id}")
    return topics


def fetch_content_for_topics(document_id: str, selected_topics: List[str]) -> List[TopicInfo]:
    """
    Fetch full content for selected topics from Neo4j.

    Args:
        document_id: Document to fetch from
        selected_topics: List of topic names to fetch

    Returns:
        List of TopicInfo objects with full content
    """
    driver = get_neo4j_driver()

    query = """
    MATCH (d:Document {documentId: $doc_id})
          -[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
    WHERE cb.parent_header IN $topics
    RETURN cb.parent_header AS topic,
           cb.block_id AS chunk_id,
           cb.text_content AS content,
           cb.combined_context AS context,
           cb.page_number AS page
    ORDER BY cb.parent_header, cb.chunk_index
    """

    with driver.session() as session:
        result = session.run(query, doc_id=document_id, topics=selected_topics)

        # Group by topic
        topic_data: Dict[str, Dict] = {}
        for record in result:
            topic_name = record["topic"]
            if topic_name not in topic_data:
                topic_data[topic_name] = {
                    "name": topic_name,
                    "chunks": [],
                    "pages": set(),
                    "chunk_ids": []
                }

            topic_data[topic_name]["chunks"].append(
                record["content"] or record["context"] or ""
            )
            if record["page"]:
                topic_data[topic_name]["pages"].add(record["page"])
            if record["chunk_id"]:
                topic_data[topic_name]["chunk_ids"].append(record["chunk_id"])

    driver.close()

    # Convert to TopicInfo objects
    topics = []
    for topic_name, data in topic_data.items():
        # Combine all chunks into one content string
        combined_content = "\n\n".join(data["chunks"])

        topics.append(TopicInfo(
            name=topic_name,
            content=combined_content,
            key_concepts=[],  # Will be extracted by LLM
            pages=sorted(list(data["pages"])),
            chunk_ids=data["chunk_ids"]
        ))

    print(f"📖 Fetched content for {len(topics)} topics")
    return topics


# ============================================================
# KEY CONCEPT EXTRACTION
# ============================================================

KEY_CONCEPT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an educational content analyzer. Extract 3-7 key concepts from the given content.

Key concepts should be:
- Core terms or ideas essential to understanding the topic
- Specific enough to be useful for study
- Not generic words like "important" or "concept"

Return ONLY a JSON array of strings, nothing else.
Example: ["mitosis", "cell cycle", "chromosomes", "DNA replication"]"""),
    ("human", """Topic: {topic_name}

Content:
{content}

Extract the key concepts as a JSON array:""")
])


def extract_key_concepts(topic: TopicInfo) -> List[str]:
    """Use LLM to extract key concepts from topic content."""
    try:
        # Limit content to avoid token limits
        truncated_content = topic.content[:3000]

        chain = KEY_CONCEPT_PROMPT | llm
        response = chain.invoke({
            "topic_name": topic.name,
            "content": truncated_content
        })

        # Parse JSON response
        concepts = json.loads(response.content)
        if isinstance(concepts, list):
            return concepts[:7]  # Limit to 7 concepts
        return []

    except Exception as e:
        print(f"⚠️ Error extracting concepts for {topic.name}: {e}")
        # Fallback: extract first few words that look like concepts
        words = topic.content.split()[:100]
        # Simple heuristic: capitalized words that aren't common
        common = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for"}
        concepts = [w.strip(".,;:") for w in words if w[0].isupper() and w.lower() not in common]
        return list(set(concepts))[:5]


# ============================================================
# LEARN PACK CREATION
# ============================================================

def create_learn_pack(input_state: LPInputState) -> LearnPack:
    """
    Create a Learn Pack from selected topics.

    1. Fetch content from Neo4j for selected topics
    2. Extract key concepts using LLM
    3. Store in Redis with 4-hour TTL
    4. Return the LearnPack object
    """
    print(f"\n{'='*60}")
    print(f"📚 Creating Learn Pack")
    print(f"LP ID: {input_state.lp_id}")
    print(f"Document: {input_state.document_id}")
    print(f"Topics: {input_state.selected_topics}")
    print(f"{'='*60}\n")

    # Step 1: Fetch content from Neo4j
    topics = fetch_content_for_topics(
        input_state.document_id,
        input_state.selected_topics
    )

    if not topics:
        raise ValueError(f"No content found for topics: {input_state.selected_topics}")

    # Step 2: Extract key concepts for each topic
    print("🧠 Extracting key concepts...")
    for topic in topics:
        concepts = extract_key_concepts(topic)
        topic.key_concepts = concepts
        print(f"   {topic.name}: {concepts}")

    # Step 3: Create LearnPack object
    learn_pack = LearnPack(
        id=input_state.lp_id,
        doc_id=input_state.document_id,
        user_id=input_state.user_id,
        created_at=datetime.utcnow().isoformat() + "Z",
        topics=[t.model_dump() for t in topics],
        total_topics=len(topics),
        status="READY"
    )

    # Step 4: Store in Redis with 4-hour TTL
    redis_key = f"lp:{input_state.lp_id}:topics"
    r.json().set(redis_key, '$', learn_pack.model_dump())
    r.expire(redis_key, 4 * 60 * 60)  # 4 hours

    print(f"✅ Learn Pack stored in Redis: {redis_key} (TTL: 4 hours)")
    print(f"   Topics: {len(topics)}")
    print(f"   Total content length: {sum(len(t.content) for t in topics)} chars")

    return learn_pack


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":
    import sys

    print("\n" + "="*60)
    print("🎓 Learn Pack Generator Test")
    print("="*60 + "\n")

    # Test document ID (replace with real one)
    test_doc_id = sys.argv[1] if len(sys.argv) > 1 else "chapter1_test"

    # Step 1: Get available topics
    print(f"📚 Fetching topics for document: {test_doc_id}")
    try:
        topics = get_available_topics(test_doc_id)

        if not topics:
            print("❌ No topics found. Make sure document is ingested.")
            exit(1)

        print(f"\nAvailable topics:")
        for i, t in enumerate(topics, 1):
            print(f"  {i}. {t['name']} ({t['chunk_count']} chunks, pages {t['pages']})")

        # Step 2: Select topics (for test, use first 2)
        selected = [t["name"] for t in topics[:2]]
        print(f"\n📋 Selected topics: {selected}")

        # Step 3: Create Learn Pack
        lp_input = LPInputState(
            lp_id=f"test_lp_{test_doc_id}",
            document_id=test_doc_id,
            user_id="test_user",
            selected_topics=selected
        )

        learn_pack = create_learn_pack(lp_input)

        print(f"\n✅ Learn Pack created successfully!")
        print(f"   ID: {learn_pack.id}")
        print(f"   Topics: {[t['name'] for t in learn_pack.topics]}")

        # Verify in Redis
        stored = r.json().get(f"lp:{learn_pack.id}:topics")
        if stored:
            print(f"   Verified in Redis: ✅")
        else:
            print(f"   Verified in Redis: ❌")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
