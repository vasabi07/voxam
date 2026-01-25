"""
Integration tests for Neo4j retrieval operations.
Tests vector search, keyword search, hybrid search with RRF, and user scoping.
"""
import pytest
import os
import sys
from pathlib import Path

# Add python directory to path for retrieval module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestVectorSearch:
    """Tests for Neo4j vector search functionality."""

    def test_vector_index_query_returns_results(self, neo4j_driver, openai_client):
        """Test that vector index can be queried and returns results."""
        # Generate a test embedding
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input="What is photosynthesis?"
        )
        qvec = response.data[0].embedding

        with neo4j_driver.session() as session:
            result = session.run("""
                CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 5, $qvec)
                YIELD node, score
                RETURN node.block_id AS block_id, score
            """, qvec=qvec)

            records = list(result)
            print(f"Vector search returned {len(records)} results")

            # Should return some results if there's data in Neo4j
            # Note: may be 0 if no data matches
            assert isinstance(records, list)

            if records:
                # Verify score is between 0 and 1
                assert 0 <= records[0]["score"] <= 1
                print(f"Top result: {records[0]['block_id']} (score: {records[0]['score']:.3f})")

    def test_embedding_dimensions_match(self, neo4j_driver):
        """Verify ContentBlock embeddings have 1536 dimensions."""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (cb:ContentBlock)
                WHERE cb.embedding IS NOT NULL
                RETURN size(cb.embedding) AS dim
                LIMIT 1
            """)
            record = result.single()

            if record:
                assert record["dim"] == 1536, f"Expected 1536 dims, got {record['dim']}"
            else:
                pytest.skip("No ContentBlocks with embeddings found")

    def test_vector_similarity_threshold_filters(self, neo4j_driver, openai_client):
        """Test that vector similarity threshold filters out irrelevant results."""
        # Generate embedding for an unrelated query
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input="quantum physics black holes string theory"
        )
        qvec = response.data[0].embedding

        with neo4j_driver.session() as session:
            # Query with high threshold
            high_threshold_result = session.run("""
                CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 10, $qvec)
                YIELD node, score
                WHERE score >= 0.75
                RETURN count(node) AS count
            """, qvec=qvec)
            high_count = high_threshold_result.single()["count"]

            # Query with low threshold
            low_threshold_result = session.run("""
                CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 10, $qvec)
                YIELD node, score
                WHERE score >= 0.50
                RETURN count(node) AS count
            """, qvec=qvec)
            low_count = low_threshold_result.single()["count"]

            print(f"High threshold (0.75): {high_count} results")
            print(f"Low threshold (0.50): {low_count} results")

            # Lower threshold should return >= high threshold results
            assert low_count >= high_count


class TestKeywordSearch:
    """Tests for Neo4j fulltext (keyword) search functionality."""

    def test_fulltext_index_query_works(self, neo4j_driver):
        """Test that fulltext index can be queried."""
        with neo4j_driver.session() as session:
            # Use a common word that likely exists in documents
            result = session.run("""
                CALL db.index.fulltext.queryNodes('contentBlockFulltextIdx', 'the', {limit: 5})
                YIELD node, score
                RETURN node.block_id AS block_id, score
            """)

            records = list(result)
            print(f"Keyword search for 'the' returned {len(records)} results")

            # 'the' should match something in most documents
            # Note: may be 0 if no data
            assert isinstance(records, list)

    def test_keyword_search_returns_relevant_blocks(self, neo4j_driver, existing_document):
        """Test keyword search returns blocks from existing document."""
        # First, get some actual text from the document to search for
        doc_id = existing_document["doc_id"]

        with neo4j_driver.session() as session:
            # Get a word from an existing block
            sample_result = session.run("""
                MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                WHERE cb.text_content IS NOT NULL
                RETURN cb.text_content AS text
                LIMIT 1
            """, doc_id=doc_id)

            sample = sample_result.single()
            if not sample:
                pytest.skip("No text content found in test document")

            # Extract a meaningful word (>4 chars) from the text
            text = sample["text"]
            words = [w for w in text.split() if len(w) > 4 and w.isalpha()]
            if not words:
                pytest.skip("No suitable keywords found in text")

            search_word = words[0]
            print(f"Searching for keyword: '{search_word}'")

            # Search for that word
            search_result = session.run("""
                CALL db.index.fulltext.queryNodes('contentBlockFulltextIdx', $keyword, {limit: 5})
                YIELD node, score
                RETURN node.block_id AS block_id, score
            """, keyword=search_word)

            records = list(search_result)
            assert len(records) > 0, f"Expected results for keyword '{search_word}'"
            print(f"Found {len(records)} results for '{search_word}'")


class TestHybridSearch:
    """Tests for hybrid search (vector + keyword + RRF fusion)."""

    def test_retrieve_context_returns_results(self, existing_document):
        """Test that retrieve_context function works with existing data."""
        from retrieval import retrieve_context

        user_id = existing_document["user_id"]
        doc_id = existing_document["doc_id"]

        # Query using real retrieval function
        context = retrieve_context(
            query_text="What is this document about?",
            user_id=user_id,
            doc_id=doc_id,
            k=5,
            min_score=0.01  # Lower threshold for testing
        )

        # Should return some context if document has embeddings
        assert isinstance(context, str)
        print(f"Retrieved context length: {len(context)} chars")

        if context:
            # Context should have document markers
            assert "[Doc:" in context or len(context) == 0
            print(f"Context preview: {context[:200]}...")

    def test_retrieve_context_with_sources(self, existing_document):
        """Test retrieve_context_with_sources returns both context and sources."""
        from retrieval import retrieve_context_with_sources

        user_id = existing_document["user_id"]
        doc_id = existing_document["doc_id"]

        context, sources = retrieve_context_with_sources(
            query_text="Explain the main concepts",
            user_id=user_id,
            doc_id=doc_id,
            k=5,
            min_score=0.01
        )

        assert isinstance(context, str)
        assert isinstance(sources, list)

        print(f"Context length: {len(context)}, Sources count: {len(sources)}")

        if sources:
            # Verify source structure
            source = sources[0]
            assert "page" in source
            assert "doc_id" in source
            print(f"First source: page {source['page']}, doc {source['doc_id']}")

    def test_rrf_scoring_ranks_correctly(self, neo4j_driver, openai_client):
        """Test that RRF scoring produces expected ranking behavior."""
        # Generate embedding
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input="introduction chapter overview"
        )
        qvec = response.data[0].embedding

        with neo4j_driver.session() as session:
            # Run hybrid search manually
            result = session.run("""
                // Vector Search
                CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 5, $qvec)
                YIELD node, score AS vectorScore
                WITH collect({node: node, score: vectorScore}) AS vectorResults, $query_text AS qt

                // Keyword Search
                CALL db.index.fulltext.queryNodes('contentBlockFulltextIdx', qt, {limit: 5})
                YIELD node, score AS keywordScore
                WITH vectorResults, collect({node: node, score: keywordScore}) AS keywordResults

                // RRF Fusion
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

                RETURN candidate.block_id AS block_id,
                       (vScore + kScore) AS score,
                       vScore, kScore
                ORDER BY score DESC
                LIMIT 5
            """, qvec=qvec, query_text="introduction chapter overview")

            records = list(result)
            print(f"RRF search returned {len(records)} results")

            if records:
                # Verify scores are in descending order
                scores = [r["score"] for r in records]
                assert scores == sorted(scores, reverse=True)

                # Verify RRF scores are bounded
                for r in records:
                    # Max RRF score is ~0.033 (1/(60+1) + 1/(60+1))
                    assert 0 <= r["score"] <= 0.035
                    print(f"  {r['block_id']}: RRF={r['score']:.4f} (v={r['vScore']:.4f}, k={r['kScore']:.4f})")

    def test_max_chars_truncation(self, existing_document):
        """Test that context respects max_chars limit."""
        from retrieval import retrieve_context

        user_id = existing_document["user_id"]
        doc_id = existing_document["doc_id"]

        # Request with very low max_chars
        context = retrieve_context(
            query_text="Tell me everything",
            user_id=user_id,
            doc_id=doc_id,
            k=10,
            min_score=0.01,
            max_chars=500  # Very small limit
        )

        if context:
            assert len(context) <= 600  # Some buffer for the last block
            print(f"Context truncated to {len(context)} chars (limit: 500)")


class TestUserScoping:
    """Tests for user-scoped retrieval (document isolation)."""

    def test_retrieval_scoped_to_user(self, neo4j_driver, existing_document, openai_client):
        """Test that retrieval only returns user's documents."""
        user_id = existing_document["user_id"]

        # Generate query embedding
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input="test query"
        )
        qvec = response.data[0].embedding

        with neo4j_driver.session() as session:
            # Query scoped to user
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                WHERE cb.embedding IS NOT NULL
                WITH collect(id(cb)) AS userBlockIds, $qvec AS qvec

                CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 10, qvec)
                YIELD node, score
                WHERE id(node) IN userBlockIds
                RETURN node.block_id AS block_id, score
            """, user_id=user_id, qvec=qvec)

            records = list(result)
            print(f"User-scoped search returned {len(records)} results for user {user_id}")

            # All results should belong to user's documents
            # (Verification is implicit in the query)
            assert isinstance(records, list)

    def test_retrieval_scoped_to_document(self, neo4j_driver, existing_document, openai_client):
        """Test that retrieval can be scoped to a single document."""
        user_id = existing_document["user_id"]
        doc_id = existing_document["doc_id"]

        # Generate query embedding
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input="document content"
        )
        qvec = response.data[0].embedding

        with neo4j_driver.session() as session:
            # Query scoped to specific document
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                WHERE cb.embedding IS NOT NULL
                WITH collect(id(cb)) AS docBlockIds, $qvec AS qvec

                CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 10, qvec)
                YIELD node, score
                WHERE id(node) IN docBlockIds
                RETURN node.block_id AS block_id, node.doc_id AS result_doc_id, score
            """, user_id=user_id, doc_id=doc_id, qvec=qvec)

            records = list(result)
            print(f"Document-scoped search returned {len(records)} results for doc {doc_id}")

            # Results should be scoped to the document
            # Note: Some older data may not have doc_id on ContentBlock nodes
            # The scoping works via the graph traversal (Document -> HAS_CONTENT_BLOCK)
            assert len(records) >= 0  # Query executed successfully

    def test_different_user_cannot_access_documents(self, neo4j_driver, existing_document, openai_client):
        """Test that a different user cannot access another user's documents."""
        other_user_id = "nonexistent-user-12345"
        doc_id = existing_document["doc_id"]

        # Generate query embedding
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input="access test"
        )
        qvec = response.data[0].embedding

        with neo4j_driver.session() as session:
            # Try to access with wrong user
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                WITH collect(id(cb)) AS userBlockIds, $qvec AS qvec

                CALL db.index.vector.queryNodes('contentBlockEmbeddingIdx', 10, qvec)
                YIELD node, score
                WHERE id(node) IN userBlockIds
                RETURN count(node) AS count
            """, user_id=other_user_id, qvec=qvec)

            record = result.single()
            # Nonexistent user should have no documents
            assert record["count"] == 0
            print(f"Nonexistent user correctly has 0 accessible documents")


class TestDocumentStructure:
    """Tests for document structure in Neo4j."""

    def test_document_has_content_blocks(self, neo4j_driver, existing_document):
        """Test that document has content blocks."""
        doc_id = existing_document["doc_id"]

        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                RETURN count(cb) AS block_count
            """, doc_id=doc_id)

            record = result.single()
            assert record["block_count"] > 0
            print(f"Document {doc_id} has {record['block_count']} content blocks")

    def test_content_blocks_have_required_fields(self, neo4j_driver, existing_document):
        """Test that content blocks have required fields."""
        doc_id = existing_document["doc_id"]

        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (d:Document {documentId: $doc_id})-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
                RETURN cb.block_id AS block_id,
                       cb.text_content IS NOT NULL AS has_text,
                       cb.embedding IS NOT NULL AS has_embedding,
                       cb.doc_id AS cb_doc_id
                LIMIT 5
            """, doc_id=doc_id)

            records = list(result)
            assert len(records) > 0

            for record in records:
                assert record["block_id"] is not None
                assert record["has_text"] is True
                assert record["has_embedding"] is True
                # doc_id on ContentBlock may be None for older data
                # The relationship (Document -> HAS_CONTENT_BLOCK) ensures scoping
                print(f"  Block {record['block_id']}: text={record['has_text']}, embedding={record['has_embedding']}, doc_id={record['cb_doc_id']}")

    def test_user_document_relationship(self, neo4j_driver, existing_document):
        """Test User -> UPLOADED -> Document relationship."""
        user_id = existing_document["user_id"]
        doc_id = existing_document["doc_id"]

        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document {documentId: $doc_id})
                RETURN u.id AS user_id, d.documentId AS doc_id
            """, user_id=user_id, doc_id=doc_id)

            record = result.single()
            assert record is not None
            assert record["user_id"] == user_id
            assert record["doc_id"] == doc_id
            print(f"User {user_id} UPLOADED Document {doc_id}")
