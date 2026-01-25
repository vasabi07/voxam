"""
Hybrid Search retrieval for chat agent.
Uses Neo4j vector indexes + Fulltext indexes with Reciprocal Rank Fusion (RRF).
Supports user-scoped retrieval for document isolation.
"""

from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from ingestion_workflow import embed_text, get_neo4j_driver

load_dotenv()

# USER-FILTERED HYBRID SEARCH QUERY (Vector + Keyword + RRF Fusion)
# Pre-fetches user's ContentBlocks, then runs vector/keyword search within that set
# Supports optional doc_id for single-document scoping
# Now also filters by min_vector_score to exclude semantically distant results
RETRIEVAL_QUERY = """
// Step 1: Get ContentBlocks owned by this user (optionally filtered to single doc)
MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
WHERE $doc_id = '' OR d.documentId = $doc_id
WITH collect(cb) AS userBlocks, collect(id(cb)) AS userBlockIds, $qvec AS qvec, $query_text AS qt, $min_vector_score AS minVecScore

// Step 2: Vector Search (returns top candidates from ENTIRE index)
CALL db.index.vector.queryNodes($index_name, $limit * 3, qvec)
YIELD node, score AS vectorScore
// Filter to only user's blocks AND filter by min vector similarity
WHERE id(node) IN userBlockIds AND vectorScore >= minVecScore
WITH userBlocks, userBlockIds, qt, collect({node: node, score: vectorScore}) AS vectorResults

// Step 3: Keyword Search
CALL db.index.fulltext.queryNodes('contentBlockFulltextIdx', qt, {limit: $limit * 3})
YIELD node, score AS keywordScore
// Filter to only user's blocks
WHERE id(node) IN userBlockIds
WITH vectorResults, collect({node: node, score: keywordScore}) AS keywordResults

// Step 4: Prepare ranked lists for RRF
WITH [r IN vectorResults | r.node] AS vectorNodes,
     [r IN keywordResults | r.node] AS keywordNodes

// Step 5: RRF Fusion - combine all unique candidates
UNWIND (vectorNodes + keywordNodes) AS candidate
WITH DISTINCT candidate, vectorNodes, keywordNodes

// Calculate 0-based Rank in each list (or null if not found)
WITH candidate, 
     [x IN range(0, size(vectorNodes)-1) WHERE vectorNodes[x] = candidate][0] AS vRank,
     [x IN range(0, size(keywordNodes)-1) WHERE keywordNodes[x] = candidate][0] AS kRank

// Apply RRF Formula: Score = 1 / (60 + rank + 1)
WITH candidate,
     CASE WHEN vRank IS NOT NULL THEN 1.0 / (60 + vRank + 1) ELSE 0.0 END AS vScore,
     CASE WHEN kRank IS NOT NULL THEN 1.0 / (60 + kRank + 1) ELSE 0.0 END AS kScore

// Step 6: Traverse to parent Document to get doc_id and title
MATCH (d:Document)-[:HAS_CONTENT_BLOCK]->(candidate)

RETURN candidate, (vScore + kScore) AS score, d.documentId AS doc_id, d.title AS doc_title
ORDER BY score DESC
LIMIT $limit
"""

# Fallback query without user filtering (for backwards compatibility / testing)
# Also filters by min_vector_score to exclude semantically distant results
RETRIEVAL_QUERY_NO_USER = """
// 1. Vector Search (Semantic) - filter by min similarity
CALL db.index.vector.queryNodes($index_name, $limit * 2, $qvec)
YIELD node, score
WHERE score >= $min_vector_score
WITH collect(node) AS vectorNodes, $query_text AS qt

// 2. Keyword Search (Exact Match)
CALL db.index.fulltext.queryNodes('contentBlockFulltextIdx', qt, {limit: $limit})
YIELD node, score
WITH vectorNodes, collect(node) AS keywordNodes

// 3. RRF Fusion Calculation
UNWIND (vectorNodes + keywordNodes) AS candidate
WITH DISTINCT candidate, vectorNodes, keywordNodes

WITH candidate,
     [x IN range(0, size(vectorNodes)-1) WHERE vectorNodes[x] = candidate][0] AS vRank,
     [x IN range(0, size(keywordNodes)-1) WHERE keywordNodes[x] = candidate][0] AS kRank

WITH candidate,
     CASE WHEN vRank IS NOT NULL THEN 1.0 / (60 + vRank + 1) ELSE 0.0 END AS vScore,
     CASE WHEN kRank IS NOT NULL THEN 1.0 / (60 + kRank + 1) ELSE 0.0 END AS kScore

// Traverse to parent Document to get doc_id and title
MATCH (d:Document)-[:HAS_CONTENT_BLOCK]->(candidate)

RETURN candidate, (vScore + kScore) AS score, d.documentId AS doc_id, d.title AS doc_title
ORDER BY score DESC
LIMIT $limit
"""

# HIERARCHY-AWARE RETRIEVAL QUERY
# Supports optional chapter/section filtering for scoped queries
RETRIEVAL_QUERY_HIERARCHY = """
// Step 1: Get ContentBlocks owned by user, optionally filtered by chapter/section
MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
WHERE ($doc_id = '' OR d.documentId = $doc_id)
  AND ($chapter = '' OR cb.chapter_title = $chapter)
  AND ($section = '' OR cb.section_title = $section)
  AND ($content_type = '' OR cb.content_type = $content_type)
WITH collect(cb) AS userBlocks, collect(id(cb)) AS userBlockIds, $qvec AS qvec, $query_text AS qt, $min_vector_score AS minVecScore

// Step 2: Vector Search
CALL db.index.vector.queryNodes($index_name, $limit * 3, qvec)
YIELD node, score AS vectorScore
WHERE id(node) IN userBlockIds AND vectorScore >= minVecScore
WITH userBlocks, userBlockIds, qt, collect({node: node, score: vectorScore}) AS vectorResults

// Step 3: Keyword Search
CALL db.index.fulltext.queryNodes('contentBlockFulltextIdx', qt, {limit: $limit * 3})
YIELD node, score AS keywordScore
WHERE id(node) IN userBlockIds
WITH vectorResults, collect({node: node, score: keywordScore}) AS keywordResults

// Step 4: RRF Fusion
WITH [r IN vectorResults | r.node] AS vectorNodes,
     [r IN keywordResults | r.node] AS keywordNodes
UNWIND (vectorNodes + keywordNodes) AS candidate
WITH DISTINCT candidate, vectorNodes, keywordNodes

WITH candidate,
     [x IN range(0, size(vectorNodes)-1) WHERE vectorNodes[x] = candidate][0] AS vRank,
     [x IN range(0, size(keywordNodes)-1) WHERE keywordNodes[x] = candidate][0] AS kRank

WITH candidate,
     CASE WHEN vRank IS NOT NULL THEN 1.0 / (60 + vRank + 1) ELSE 0.0 END AS vScore,
     CASE WHEN kRank IS NOT NULL THEN 1.0 / (60 + kRank + 1) ELSE 0.0 END AS kScore

// Traverse to parent Document to get doc_id and title
MATCH (d:Document)-[:HAS_CONTENT_BLOCK]->(candidate)

RETURN candidate, (vScore + kScore) AS score, d.documentId AS doc_id, d.title AS doc_title
ORDER BY score DESC
LIMIT $limit
"""


def retrieve_context_with_sources(
    query_text: str,
    user_id: str = None,
    doc_id: str = None,
    chapter: str = None,
    section: str = None,
    content_type: str = None,
    index_name: str = "contentBlockEmbeddingIdx",
    k: int = 8,
    min_score: float = 0.018,
    min_vector_score: float = 0.60,
    max_chars: int = 12000
) -> tuple[str, List[Dict[str, Any]]]:
    """
    Retrieve context with optional hierarchy filtering and return both formatted context and sources.

    Args:
        query_text: User query string
        user_id: User ID for document isolation
        doc_id: Optional document ID to scope to single document
        chapter: Optional chapter title to scope retrieval
        section: Optional section title to scope retrieval
        content_type: Optional content type filter (definition, example, theorem, etc.)
        index_name: Name of Neo4j vector index
        k: Number of candidate results
        min_score: Minimum RRF score threshold
        min_vector_score: Minimum vector similarity
        max_chars: Character budget for context

    Returns:
        Tuple of (context_string, sources_list)
        sources_list contains dicts with: page, title, excerpt, doc_id, chapter, section, content_type
    """
    driver = get_neo4j_driver()
    qvec = embed_text(query_text)

    if not qvec:
        return "", []

    # Use hierarchy-aware query if any hierarchy filters are specified
    use_hierarchy = chapter or section or content_type
    if user_id:
        query = RETRIEVAL_QUERY_HIERARCHY if use_hierarchy else RETRIEVAL_QUERY
    else:
        query = RETRIEVAL_QUERY_NO_USER

    with driver.session() as session:
        try:
            params = {
                "qvec": qvec,
                "query_text": query_text,
                "index_name": index_name,
                "limit": k,
                "min_vector_score": min_vector_score,
                "user_id": user_id or "",
                "doc_id": doc_id or "",
            }
            # Add hierarchy params only for hierarchy query
            if use_hierarchy:
                params["chapter"] = chapter or ""
                params["section"] = section or ""
                params["content_type"] = content_type or ""

            result = session.run(query, **params)

            # Extract doc_id and doc_title directly from query results (graph traversal)
            items = [
                {
                    "node": dict(record["candidate"]),
                    "score": record["score"],
                    "doc_id": record.get("doc_id"),
                    "doc_title": record.get("doc_title") or "Document"
                }
                for record in result
            ]
            items = [item for item in items if item["score"] >= min_score]

        except Exception as e:
            print(f"❌ Neo4j query failed: {e}")
            return "", []

    seen_block_ids = set()
    context_parts = []
    sources = []
    total_chars = 0

    for item in items:
        node = item["node"]
        block_id = node.get("block_id", "unknown")

        if block_id in seen_block_ids:
            continue
        seen_block_ids.add(block_id)

        # Extract page info and document info (from graph traversal)
        page_start = node.get("page_start") or node.get("page_number") or node.get("page_from")
        page_end = node.get("page_end") or page_start
        doc_id_val = item.get("doc_id") or "?"
        doc_title_val = item.get("doc_title") or "Document"

        # Build page info string
        if page_start:
            if page_end and page_end != page_start:
                page_info = f"pages:{page_start}-{page_end}"
            else:
                page_info = f"page:{page_start}"
        else:
            page_info = "page:?"

        content = node.get("combined_context") or node.get("text_content", "")[:3500]
        prefix = f"[Doc:{doc_id_val} {page_info}]\n"
        block_text = prefix + content

        if total_chars + len(block_text) > max_chars:
            break

        context_parts.append(block_text)
        total_chars += len(block_text)

        # Add to sources list (for citation display)
        # Extract first meaningful line as title
        first_lines = [l.strip() for l in content.split('\n') if l.strip() and len(l.strip()) > 10]
        title = first_lines[0][:60] + "..." if first_lines else f"Section {len(sources)+1}"
        excerpt = content[:150].strip() + "..." if len(content) > 150 else content.strip()

        sources.append({
            "page": page_start,
            "page_end": page_end if page_end != page_start else None,
            "title": title,
            "excerpt": excerpt,
            "doc_id": doc_id_val,
            "doc_title": doc_title_val,
            # Hierarchy fields
            "chapter": node.get("chapter_title"),
            "section": node.get("section_title"),
            "content_type": node.get("content_type", "narrative"),
        })

    context = "\n\n---\n\n".join(context_parts)
    print(f"📄 Built context: {len(context_parts)} blocks, {total_chars} chars, {len(sources)} sources")

    return context, sources


def retrieve_context(
    query_text: str,
    user_id: str = None,    # User ID for document isolation
    doc_id: str = None,     # Optional: scope to single document
    index_name: str = "contentBlockEmbeddingIdx",
    k: int = 8,             # Candidates to fetch (RRF will rank them)
    min_score: float = 0.018,  # RRF threshold - filters low-quality matches
    min_vector_score: float = 0.60,  # Vector similarity threshold - 0.60 filters unrelated (0.55) while keeping relevant (0.65+)
    max_chars: int = 12000     # Character budget (~3000 tokens)
) -> str:
    """
    Retrieve context using Hybrid Search (Vector + Keyword + RRF).
    
    Args:
        query_text: User query string
        user_id: User ID to filter documents (None = all documents, for testing)
        doc_id: Optional document ID to scope chat to single document
        index_name: Name of Neo4j vector index
        k: Number of candidate results to fetch
        min_score: Minimum RRF score threshold (0.033 max, 0.018 ≈ top 3-4)
        min_vector_score: Minimum vector similarity (0.0-1.0). 0.65 filters out unrelated queries
        max_chars: Character budget for context (~4 chars = 1 token)
    
    Returns:
        Formatted context string with provenance headers
    """
    driver = get_neo4j_driver()
    
    # Generate query embedding
    print("🔍 Generating query embedding...")
    qvec = embed_text(query_text)
    
    if not qvec:
        print("❌ Failed to generate query embedding")
        return ""
    
    # Choose query based on whether user_id is provided
    if user_id:
        scope = f"doc: {doc_id}" if doc_id else "all docs"
        print(f"🔎 Running User-Scoped Hybrid Search (user: {user_id}, {scope}, min_vec: {min_vector_score})")
        query = RETRIEVAL_QUERY
    else:
        print(f"🔎 Running Global Hybrid Search (no user filter - testing mode, min_vec: {min_vector_score})")
        query = RETRIEVAL_QUERY_NO_USER
    
    with driver.session() as session:
        try:
            result = session.run(
                query,
                qvec=qvec,
                query_text=query_text,
                index_name=index_name,
                limit=k,
                min_vector_score=min_vector_score,  # New parameter for vector similarity filter
                user_id=user_id or "",  # Pass empty string if None
                doc_id=doc_id or ""      # Pass empty string for all docs
            )
            
            items = [
                {
                    "node": dict(record["candidate"]),
                    "score": record["score"]
                }
                for record in result
            ]
            
            print(f"✅ Fetched {len(items)} candidates via Hybrid Search")
            
            # Filter by RRF score threshold (quality gate)
            pre_filter_count = len(items)
            items = [item for item in items if item["score"] >= min_score]
            
            # If nothing passes the threshold, we have NO relevant context
            # This allows HITL to trigger and offer web search
            if not items:
                print(f"⚠️  0/{pre_filter_count} passed score threshold (>= {min_score}) - no relevant context")
            else:
                print(f"✅ {len(items)}/{pre_filter_count} passed score threshold (>= {min_score})")
            
        except Exception as e:
            print(f"❌ Neo4j query failed: {e}")
            print("💡 Hint: Did you run 'CREATE FULLTEXT INDEX contentBlockFulltextIdx ...'?")
            return ""
    
    # Build context with deduplication and token budget
    seen_block_ids = set()
    context_parts = []
    total_chars = 0
    
    for item in items:
        node = item["node"]
        block_id = node.get("block_id", "unknown")
        
        # Deduplicate
        if block_id in seen_block_ids:
            continue
        seen_block_ids.add(block_id)
        
        # Format with provenance (Updated for new schema)
        doc_id = node.get("doc_id", "?")
        
        # Handle page fields from different ingestion sources:
        # - Llama ingestion: page_start, page_end
        # - Old unstructured.io: page_from, page_to, page_number
        page_start = node.get("page_start")
        page_end = node.get("page_end")
        
        if page_start is not None:
            if page_end and page_end != page_start:
                page_info = f"pages:{page_start}-{page_end}"
            else:
                page_info = f"page:{page_start}"
        else:
            # Fallback for older data
            page_num = node.get("page_number")
            if page_num is not None:
                page_info = f"page:{page_num}"
            else:
                page_from = node.get("page_from")
                page_to = node.get("page_to")
                page_info = f"pgs:{page_from}-{page_to}" if page_from and page_to else "page:?"
        
        # Prefix: [Doc:xyz page:5] [RRF Score: 0.03]
        prefix = f"[Doc:{doc_id} {page_info}] [RRF Score: {item['score']:.4f}]\n"
        
        # Use combined_context (same content that was embedded for semantic match)
        # Fallback to text_content with reasonable truncation
        content = node.get("combined_context") or node.get("text_content", "")[:3500]
        
        block_text = prefix + content
        
        # Check character budget
        if total_chars + len(block_text) > max_chars:
            print(f"⚠️  Token budget reached, stopping at {len(context_parts)} blocks")
            break
        
        context_parts.append(block_text)
        total_chars += len(block_text)
    
    context = "\n\n---\n\n".join(context_parts)
    print(f"📄 Built context: {len(context_parts)} blocks, {total_chars} chars")
    
    return context


def search_contentblocks(
    query_text: str,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Debug function: Returns raw blocks using Hybrid Search.
    """
    driver = get_neo4j_driver()
    qvec = embed_text(query_text)
    
    if not qvec:
        return []
    
    # Re-use the hybrid query for consistency
    with driver.session() as session:
        result = session.run(
            RETRIEVAL_QUERY,
            qvec=qvec,
            query_text=query_text,
            index_name="contentBlockEmbeddingIdx",
            k=top_k
        )
        
        return [
            {
                "block_id": record["candidate"].get("block_id"),
                "text": record["candidate"].get("text_content", "")[:200],
                "score": record["score"],
                "page": record["candidate"].get("page_number")
            } 
            for record in result
        ]




if __name__ == "__main__":
    print("🧪 Testing retrieval module...")
    
    # Test query
    test_query = "Explain the process of photosynthesis"
    
    print(f"\n🔍 Query: {test_query}\n")
    
    # Test context retrieval with k=10 (pure vector search)
    context = retrieve_context(test_query, k=10)
    
    if context:
        print("\n📄 RETRIEVED CONTEXT:")
        print("=" * 80)
        print(context)
        print("=" * 80)
    else:
        print("❌ No context retrieved")
    
    # Test simple search
    print("\n\n🔍 Testing simple vector search...")
    blocks = search_contentblocks(test_query, top_k=3)
    
    if blocks:
        print(f"\n✅ Found {len(blocks)} blocks:")
        for i, block in enumerate(blocks, 1):
            print(f"\n{i}. Block: {block['block_id']}")
            print(f"   Score: {block['score']:.3f}")
            print(f"   Pages: {block['page_from']}-{block['page_to']}")
            print(f"   Text: {block['text'][:200]}...")
    else:
        print("❌ No blocks found")
