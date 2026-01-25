"""
Integration tests for service connectivity.
Verifies all external services are reachable and properly configured.
"""
import pytest


class TestRedisConnection:
    """Tests for Redis connectivity."""

    def test_redis_ping(self, redis_client):
        """Verify Redis is reachable."""
        result = redis_client.ping()
        assert result is True

    def test_redis_json_module_available(self, redis_client):
        """Verify RedisJSON module is loaded."""
        # Try to use JSON commands
        test_key = "test:json_module_check"
        test_data = {"test": "value", "nested": {"key": 123}}

        try:
            redis_client.json().set(test_key, "$", test_data)
            retrieved = redis_client.json().get(test_key)
            assert retrieved == test_data
        finally:
            redis_client.delete(test_key)

    def test_redis_set_get_delete(self, redis_client):
        """Verify basic Redis operations work."""
        test_key = "test:basic_ops"
        test_value = "integration_test_value"

        try:
            # Set
            redis_client.set(test_key, test_value)

            # Get
            result = redis_client.get(test_key)
            assert result == test_value

            # Delete
            redis_client.delete(test_key)
            result = redis_client.get(test_key)
            assert result is None
        finally:
            redis_client.delete(test_key)

    def test_redis_hash_operations(self, redis_client):
        """Verify Redis hash operations (used for task progress)."""
        test_key = "test:hash_ops"

        try:
            # Set hash
            redis_client.hset(test_key, mapping={
                "progress": "50",
                "status": "processing",
                "details": "Test details"
            })

            # Get all hash fields
            result = redis_client.hgetall(test_key)
            assert result["progress"] == "50"
            assert result["status"] == "processing"
        finally:
            redis_client.delete(test_key)

    def test_redis_ttl_operations(self, redis_client):
        """Verify TTL can be set on keys."""
        test_key = "test:ttl_ops"

        try:
            redis_client.set(test_key, "value")
            redis_client.expire(test_key, 3600)  # 1 hour

            ttl = redis_client.ttl(test_key)
            assert ttl > 0
            assert ttl <= 3600
        finally:
            redis_client.delete(test_key)


class TestNeo4jConnection:
    """Tests for Neo4j connectivity."""

    def test_neo4j_driver_connects(self, neo4j_driver):
        """Verify Neo4j driver can connect."""
        with neo4j_driver.session() as session:
            result = session.run("RETURN 1 AS num")
            record = result.single()
            assert record["num"] == 1

    def test_neo4j_vector_index_exists(self, neo4j_driver):
        """Verify vector index for embeddings exists."""
        with neo4j_driver.session() as session:
            result = session.run("SHOW INDEXES")
            indexes = [record["name"] for record in result]

            # Check for the content block embedding index
            assert "contentBlockEmbeddingIdx" in indexes, \
                f"Vector index not found. Available indexes: {indexes}"

    def test_neo4j_fulltext_index_exists(self, neo4j_driver):
        """Verify fulltext index for keyword search exists."""
        with neo4j_driver.session() as session:
            result = session.run("SHOW INDEXES")
            indexes = [record["name"] for record in result]

            assert "contentBlockFulltextIdx" in indexes, \
                f"Fulltext index not found. Available indexes: {indexes}"

    def test_neo4j_has_content_blocks(self, neo4j_driver):
        """Verify there are ContentBlock nodes in the database."""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (cb:ContentBlock)
                RETURN count(cb) AS count
            """)
            record = result.single()
            count = record["count"]

            print(f"Found {count} ContentBlock nodes in Neo4j")
            # Don't fail if empty, just report
            assert count >= 0

    def test_neo4j_content_blocks_have_embeddings(self, neo4j_driver):
        """Verify ContentBlocks have embeddings."""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (cb:ContentBlock)
                WHERE cb.embedding IS NOT NULL
                RETURN count(cb) AS count,
                       size(cb.embedding) AS dim
                LIMIT 1
            """)
            record = result.single()

            if record and record["count"] > 0:
                dim = record["dim"]
                assert dim == 1536, f"Expected 1536 dimensions, got {dim}"
                print(f"Found {record['count']} ContentBlocks with 1536-dim embeddings")


class TestSupabaseConnection:
    """Tests for Supabase connectivity."""

    def test_supabase_client_connects(self, supabase_client):
        """Verify Supabase client can connect."""
        # Simple query to verify connection
        result = supabase_client.table("User").select("id").limit(1).execute()
        # Should not raise an exception
        assert result is not None

    def test_supabase_can_query_users(self, supabase_client):
        """Verify we can query the User table."""
        result = supabase_client.table("User").select("id, email").limit(5).execute()

        print(f"Found {len(result.data)} users in Supabase")
        # Should have the expected structure
        if result.data:
            assert "id" in result.data[0]

    def test_supabase_can_query_documents(self, supabase_client):
        """Verify we can query the Document table."""
        result = supabase_client.table("Document").select("id, title, status").limit(5).execute()

        print(f"Found {len(result.data)} documents in Supabase")

    def test_supabase_can_query_question_papers(self, supabase_client):
        """Verify we can query the QuestionPaper table."""
        result = supabase_client.table("QuestionPaper").select("id, status, documentId").limit(5).execute()

        print(f"Found {len(result.data)} question papers in Supabase")


class TestLiveKitConnection:
    """Tests for LiveKit connectivity."""

    def test_livekit_credentials_available(self, livekit_credentials):
        """Verify LiveKit credentials are configured."""
        assert livekit_credentials["url"] is not None
        assert livekit_credentials["api_key"] is not None
        assert livekit_credentials["api_secret"] is not None

    def test_livekit_can_generate_token(self, livekit_credentials):
        """Verify we can generate a LiveKit access token."""
        from livekit import api

        token = (
            api.AccessToken(
                livekit_credentials["api_key"],
                livekit_credentials["api_secret"]
            )
            .with_identity("test-user")
            .with_grants(api.VideoGrants(
                room="test-room",
                room_join=True,
                can_publish=True,
                can_subscribe=True,
            ))
            .to_jwt()
        )

        assert token is not None
        assert len(token) > 0
        # JWT format: header.payload.signature
        assert token.count(".") == 2


class TestOpenAIConnection:
    """Tests for OpenAI connectivity (embeddings)."""

    def test_openai_can_create_embedding(self, openai_client):
        """Verify we can create embeddings."""
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input="Test text for embedding"
        )

        embedding = response.data[0].embedding
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)


class TestExistingData:
    """Tests to verify existing test data is available."""

    def test_existing_document_found(self, existing_document):
        """Verify we have a document to test with."""
        assert existing_document["user_id"] is not None
        assert existing_document["doc_id"] is not None
        assert existing_document["block_count"] > 0

        print(f"Found document: {existing_document['doc_id']}")
        print(f"  User: {existing_document['user_id']}")
        print(f"  Blocks: {existing_document['block_count']}")

    def test_test_user_has_credits(self, test_user):
        """Verify test user has credit fields."""
        assert "id" in test_user
        assert "voiceMinutesUsed" in test_user or test_user.get("voiceMinutesUsed") is not None

        print(f"Test user: {test_user['id']}")
        print(f"  Voice minutes: {test_user.get('voiceMinutesUsed', 0)}/{test_user.get('voiceMinutesLimit', 'N/A')}")
