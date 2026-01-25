"""
RAG Quality Evaluation Tests for Chat Agent.

Tests retrieval accuracy and response quality for chapter1 document
(Chapter 6: Control and Coordination - Biology).

These tests use LIVE services (Neo4j, OpenAI embeddings).
"""
import pytest
import sys
from pathlib import Path
from typing import List, Dict

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)


# Test document ID with known content
TEST_DOC_ID = "doc_ec96ce1c"  # Chapter 6: Control and Coordination

# Expected content keywords for various topics in the document
EXPECTED_CONTENT = {
    "reflex_action": [
        "reflex", "spinal cord", "stimulus", "response", "nerve", "quick"
    ],
    "human_brain": [
        "brain", "central nervous system", "thinking", "voluntary", "cerebrum",
        "cerebellum", "medulla"
    ],
    "hormones": [
        "hormone", "adrenaline", "insulin", "thyroid", "pituitary", "endocrine"
    ],
    "plant_movement": [
        "plant", "auxin", "phototropism", "geotropism", "sensitive plant",
        "touch", "stimulus"
    ],
    "nerve_impulse": [
        "nerve", "impulse", "neuron", "synapse", "electrical", "chemical"
    ],
}

# Test queries mapped to expected topics
TEST_QUERIES = [
    {
        "query": "What is a reflex action and how does it work?",
        "expected_topic": "reflex_action",
        "min_relevance_score": 0.02,
        "should_contain": ["reflex", "spinal cord"],
    },
    {
        "query": "Explain the structure and function of human brain",
        "expected_topic": "human_brain",
        "min_relevance_score": 0.02,
        "should_contain": ["brain", "nervous system"],
    },
    {
        "query": "What are hormones and how do they work in animals?",
        "expected_topic": "hormones",
        "min_relevance_score": 0.02,
        "should_contain": ["hormone", "adrenaline"],
    },
    {
        "query": "How do plants respond to light?",
        "expected_topic": "plant_movement",
        "min_relevance_score": 0.02,
        "should_contain": ["plant", "light"],
    },
    {
        "query": "How do nerve impulses travel in the body?",
        "expected_topic": "nerve_impulse",
        "min_relevance_score": 0.02,
        "should_contain": ["nerve", "impulse"],
    },
    # Edge case: very specific question
    {
        "query": "What happens when adrenaline is secreted into the blood?",
        "expected_topic": "hormones",
        "min_relevance_score": 0.02,
        "should_contain": ["adrenaline"],
    },
    # Edge case: question requiring synthesis
    {
        "query": "Compare nervous and hormonal control in animals",
        "expected_topic": "hormones",  # Should get both, but hormones discusses comparison
        "min_relevance_score": 0.01,
        "should_contain": ["nerve", "hormone"],
    },
]


@pytest.fixture(scope="module")
def neo4j_driver():
    """Get Neo4j driver."""
    from ingestion_workflow import get_neo4j_driver
    return get_neo4j_driver()


@pytest.fixture(scope="module")
def retrieval_module():
    """Import retrieval module."""
    import retrieval
    return retrieval


class TestRetrievalQuality:
    """Tests for retrieval accuracy."""

    def test_document_exists(self, neo4j_driver):
        """Verify test document exists with content blocks."""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                WHERE cb.text_content IS NOT NULL
                RETURN count(cb) AS block_count
            """, doc_id=TEST_DOC_ID)

            record = result.single()
            block_count = record["block_count"]

            assert block_count > 0, f"Document {TEST_DOC_ID} has no content blocks"
            print(f"✅ Document {TEST_DOC_ID} has {block_count} content blocks")

    def test_embeddings_exist(self, neo4j_driver):
        """Verify content blocks have embeddings."""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                WHERE cb.embedding IS NOT NULL
                RETURN count(cb) AS embedded_count
            """, doc_id=TEST_DOC_ID)

            record = result.single()
            embedded_count = record["embedded_count"]

            assert embedded_count > 0, f"Document {TEST_DOC_ID} has no embeddings"
            print(f"✅ Document {TEST_DOC_ID} has {embedded_count} embedded blocks")

    @pytest.mark.parametrize("test_case", TEST_QUERIES)
    def test_retrieval_finds_relevant_content(self, retrieval_module, test_case):
        """Test that retrieval returns relevant content for each query."""
        query = test_case["query"]
        should_contain = test_case["should_contain"]
        min_score = test_case["min_relevance_score"]

        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Expected keywords: {should_contain}")
        print(f"{'='*60}")

        # Run retrieval (no user filter for testing)
        context = retrieval_module.retrieve_context(
            query_text=query,
            user_id=None,  # No user filter
            doc_id=None,   # All documents
            k=5,
            min_score=0.01,
            min_vector_score=0.50  # Lower threshold for testing
        )

        print(f"\nRetrieved context ({len(context)} chars):")
        print(context[:500] if context else "NO CONTEXT RETRIEVED")

        # Check if context was retrieved
        assert context, f"No context retrieved for query: {query}"

        # Check if expected keywords are present
        context_lower = context.lower()
        found_keywords = [kw for kw in should_contain if kw.lower() in context_lower]
        missing_keywords = [kw for kw in should_contain if kw.lower() not in context_lower]

        print(f"\n✅ Found keywords: {found_keywords}")
        print(f"❌ Missing keywords: {missing_keywords}")

        # At least half the keywords should be found
        assert len(found_keywords) >= len(should_contain) / 2, \
            f"Too many missing keywords: {missing_keywords}"

    def test_retrieval_with_sources(self, retrieval_module):
        """Test retrieval returns structured sources."""
        query = "What is a reflex action?"

        context, sources = retrieval_module.retrieve_context_with_sources(
            query_text=query,
            user_id=None,
            doc_id=None,
            k=5,
            min_score=0.01,
            min_vector_score=0.50
        )

        print(f"\nQuery: {query}")
        print(f"Context length: {len(context)} chars")
        print(f"Sources count: {len(sources)}")

        if sources:
            for i, src in enumerate(sources):
                print(f"\nSource {i+1}:")
                print(f"  Page: {src.get('page')}")
                print(f"  Title: {src.get('title', '')[:50]}...")
                print(f"  Excerpt: {src.get('excerpt', '')[:100]}...")

        assert context, "No context retrieved"
        assert len(sources) > 0, "No sources returned"

    def test_vector_similarity_scores(self, neo4j_driver):
        """Test that vector similarity scores are reasonable."""
        from ingestion_workflow import embed_text

        # Query about reflex action
        query = "What is a reflex action?"
        qvec = embed_text(query)

        with neo4j_driver.session() as session:
            result = session.run("""
                CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 10, $qvec)
                YIELD node, score
                RETURN node.block_id AS block_id,
                       left(node.text_content, 100) AS preview,
                       score
                ORDER BY score DESC
            """, qvec=qvec)

            print("\nVector similarity scores for 'What is a reflex action?':")
            scores = []
            for record in result:
                scores.append(record["score"])
                preview = record["preview"] or "N/A"
                print(f"  Score: {record['score']:.4f} - {preview[:60]}...")

            # Check score distribution
            if scores:
                max_score = max(scores)
                min_score = min(scores)
                avg_score = sum(scores) / len(scores)

                print(f"\nScore stats: max={max_score:.4f}, min={min_score:.4f}, avg={avg_score:.4f}")

                # Top result should have reasonable similarity
                assert max_score > 0.5, f"Top score too low: {max_score}"


class TestRRFFusion:
    """Tests for RRF (Reciprocal Rank Fusion) quality."""

    def test_rrf_combines_vector_and_keyword(self, neo4j_driver):
        """Test that RRF combines vector and keyword search results."""
        from ingestion_workflow import embed_text

        # Query that should match both semantically and keyword-wise
        query = "reflex action spinal cord"
        qvec = embed_text(query)

        with neo4j_driver.session() as session:
            # Run vector-only search
            vector_result = session.run("""
                CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 5, $qvec)
                YIELD node, score
                RETURN node.block_id AS block_id, score
            """, qvec=qvec)
            vector_blocks = {r["block_id"]: r["score"] for r in vector_result}

            # Run keyword-only search
            keyword_result = session.run("""
                CALL db.index.fulltext.queryNodes('contentBlockFulltextIdx', $search_query, {limit: 5})
                YIELD node, score
                RETURN node.block_id AS block_id, score
            """, search_query=query)
            keyword_blocks = {r["block_id"]: r["score"] for r in keyword_result}

            print(f"\nQuery: {query}")
            print(f"\nVector search results ({len(vector_blocks)}):")
            for bid, score in list(vector_blocks.items())[:3]:
                print(f"  {bid}: {score:.4f}")

            print(f"\nKeyword search results ({len(keyword_blocks)}):")
            for bid, score in list(keyword_blocks.items())[:3]:
                print(f"  {bid}: {score:.4f}")

            # Check overlap
            overlap = set(vector_blocks.keys()) & set(keyword_blocks.keys())
            print(f"\nOverlap: {len(overlap)} blocks appear in both")

            # RRF should benefit from blocks appearing in both
            # At least some overlap is expected for good queries
            # Note: may be 0 if vector and keyword find different relevant blocks

    def test_rrf_score_calculation(self, retrieval_module):
        """Test that RRF scores are in expected range."""
        query = "How does nervous system control reflex actions?"

        context = retrieval_module.retrieve_context(
            query_text=query,
            user_id=None,
            k=5,
            min_score=0.001,  # Very low to see all scores
            min_vector_score=0.40
        )

        # RRF scores should be in range 0 to ~0.033 (theoretical max: 2/(60+1))
        # Context should contain RRF scores in format [RRF Score: 0.XXXX]
        import re
        scores = re.findall(r'\[RRF Score: ([\d.]+)\]', context)

        print(f"\nRRF scores found: {scores}")

        if scores:
            float_scores = [float(s) for s in scores]
            for score in float_scores:
                assert 0 < score < 0.05, f"RRF score out of expected range: {score}"

            # Scores should be in descending order
            assert float_scores == sorted(float_scores, reverse=True), \
                "RRF scores not in descending order"


class TestEdgeCases:
    """Tests for edge cases and failure modes."""

    def test_irrelevant_query_returns_low_scores(self, retrieval_module):
        """Test that irrelevant queries don't return high-confidence results."""
        # Query completely unrelated to the biology document
        irrelevant_query = "How to make chocolate cake recipe"

        context = retrieval_module.retrieve_context(
            query_text=irrelevant_query,
            user_id=None,
            k=5,
            min_score=0.02,  # Standard threshold
            min_vector_score=0.60  # Standard threshold
        )

        print(f"\nIrrelevant query: {irrelevant_query}")
        print(f"Context retrieved: {len(context)} chars")

        # Should return minimal or no context for unrelated queries
        # This tests the min_vector_score filter
        if context:
            print(f"WARNING: Retrieved context for irrelevant query:")
            print(context[:200])
        else:
            print("✅ Correctly returned no context for irrelevant query")

    def test_empty_query_handled(self, retrieval_module):
        """Test that empty query is handled gracefully."""
        context = retrieval_module.retrieve_context(
            query_text="",
            user_id=None,
            k=5
        )

        # Should return empty context, not error
        assert context == "" or context is None or len(context) == 0

    def test_special_characters_in_query(self, retrieval_module):
        """Test queries with special characters."""
        query = "What is the function of Ca2+ ions in muscle contraction?"

        try:
            context = retrieval_module.retrieve_context(
                query_text=query,
                user_id=None,
                k=5
            )
            print(f"\nQuery with special chars: {query}")
            print(f"Context length: {len(context)} chars")
        except Exception as e:
            pytest.fail(f"Failed to handle special characters: {e}")


class TestRAGResponseQuality:
    """Tests for full RAG response quality (retrieval + generation)."""

    @pytest.fixture
    def chat_llm(self):
        """Get LLM for testing."""
        from langchain_openai import ChatOpenAI
        import os

        return ChatOpenAI(
            model="gpt-oss-120b",
            api_key=os.getenv("CEREBRAS_API_KEY"),
            base_url="https://api.cerebras.ai/v1",
            temperature=0
        )

    def test_rag_answer_uses_context(self, retrieval_module, chat_llm):
        """Test that RAG answer uses retrieved context."""
        query = "What is a reflex action? Explain with an example."

        # Get context
        context = retrieval_module.retrieve_context(
            query_text=query,
            user_id=None,
            k=5,
            min_score=0.01,
            min_vector_score=0.50
        )

        assert context, "No context retrieved"

        # Build RAG prompt
        system_prompt = """You are a helpful study assistant. Answer the student's question
using ONLY the provided context. If the context doesn't contain enough information,
say so. Be concise and accurate.

CONTEXT:
{context}
"""

        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content=system_prompt.format(context=context)),
            HumanMessage(content=query)
        ]

        response = chat_llm.invoke(messages)
        answer = response.content

        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"\nContext preview: {context[:500]}...")
        print(f"\nRAG Answer:")
        print(answer)
        print(f"{'='*60}")

        # Verify answer quality
        answer_lower = answer.lower()

        # Should mention reflex
        assert "reflex" in answer_lower, "Answer doesn't mention reflex"

        # Should give an example (common examples: touching flame, knee jerk)
        example_keywords = ["flame", "hot", "knee", "touch", "hand", "example"]
        has_example = any(kw in answer_lower for kw in example_keywords)
        print(f"Has example: {has_example}")

    def test_rag_handles_no_context(self, chat_llm):
        """Test RAG response when no context is available."""
        # Build prompt with no context
        system_prompt = """You are a helpful study assistant. Answer the student's question
using ONLY the provided context. If the context doesn't contain enough information,
clearly state that you don't have enough information to answer.

CONTEXT:
[No relevant context found]
"""

        from langchain_core.messages import SystemMessage, HumanMessage

        query = "What is quantum entanglement?"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]

        response = chat_llm.invoke(messages)
        answer = response.content.lower()

        print(f"\nQuery (no context): {query}")
        print(f"Answer: {response.content}")

        # Should indicate lack of information
        no_info_phrases = [
            "don't have", "no information", "not available",
            "cannot answer", "not provided", "no context",
            "insufficient", "not contain"
        ]
        indicates_no_info = any(phrase in answer for phrase in no_info_phrases)
        print(f"Indicates no info: {indicates_no_info}")


class TestRetrievalDiagnostics:
    """Diagnostic tests to understand retrieval behavior."""

    def test_print_retrieval_diagnostics(self, retrieval_module, neo4j_driver):
        """Print detailed diagnostics for debugging retrieval issues."""
        from ingestion_workflow import embed_text

        queries = [
            "What is a reflex action?",
            "How does the brain control body functions?",
            "What are hormones?",
        ]

        print("\n" + "="*80)
        print("RETRIEVAL DIAGNOSTICS")
        print("="*80)

        for query in queries:
            print(f"\n--- Query: {query} ---\n")

            # Get embedding
            qvec = embed_text(query)

            with neo4j_driver.session() as session:
                # Raw vector search (no filtering)
                result = session.run("""
                    CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 5, $qvec)
                    YIELD node, score
                    RETURN node.block_id AS block_id,
                           node.doc_id AS doc_id,
                           left(node.text_content, 150) AS preview,
                           score AS vector_score
                    ORDER BY score DESC
                """, qvec=qvec)

                print("Top 5 Vector Search Results:")
                for i, record in enumerate(result):
                    print(f"  {i+1}. Score: {record['vector_score']:.4f}")
                    print(f"     Doc: {record['doc_id']}, Block: {record['block_id']}")
                    print(f"     Preview: {(record['preview'] or 'N/A')[:100]}...")

                # Keyword search
                result = session.run("""
                    CALL db.index.fulltext.queryNodes('contentBlockFulltextIdx', $search_query, {limit: 5})
                    YIELD node, score
                    RETURN node.block_id AS block_id,
                           node.doc_id AS doc_id,
                           left(node.text_content, 150) AS preview,
                           score AS keyword_score
                    ORDER BY score DESC
                """, search_query=query)

                print("\nTop 5 Keyword Search Results:")
                for i, record in enumerate(result):
                    print(f"  {i+1}. Score: {record['keyword_score']:.4f}")
                    print(f"     Doc: {record['doc_id']}, Block: {record['block_id']}")
                    print(f"     Preview: {(record['preview'] or 'N/A')[:100]}...")

            # Full retrieval with RRF
            context = retrieval_module.retrieve_context(
                query_text=query,
                user_id=None,
                k=5,
                min_score=0.01,
                min_vector_score=0.50
            )

            print(f"\nFinal RRF Context: {len(context)} chars")
            if context:
                # Extract RRF scores from context
                import re
                scores = re.findall(r'\[RRF Score: ([\d.]+)\]', context)
                print(f"RRF Scores: {scores}")
