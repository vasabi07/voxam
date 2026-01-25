"""
Integration test fixtures for live service testing.
These fixtures connect to REAL services - Redis, Neo4j, Supabase, LiveKit.

NOTE: These tests require live services and should be run separately from unit tests.
Run with: pytest tests/integration/ -v
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Stop all patches from the main conftest.py to get real connections
patch.stopall()

# Force reload of environment from .env file
# This is needed because the main conftest.py may have already loaded env vars
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)
else:
    print(f"Warning: .env file not found at {env_path}")

# Reimport redis module after stopping patches to get the real module
import importlib
import redis as redis_module
importlib.reload(redis_module)


# ============================================================
# Redis Fixtures
# ============================================================

@pytest.fixture(scope="session")
def redis_client():
    """Get a live Redis client - bypasses any mocking."""
    # Use the reloaded redis module from module level
    redis_uri = os.getenv("REDIS_URI", "redis://localhost:6379")
    client = redis_module.Redis.from_url(redis_uri, decode_responses=True)

    # Verify connection
    try:
        client.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    yield client

    # Cleanup test keys after all tests
    test_keys = client.keys("test:*")
    if test_keys:
        client.delete(*test_keys)


@pytest.fixture(scope="session")
def redis_checkpointer():
    """Get a LangGraph Redis checkpointer."""
    from langgraph.checkpoint.redis import RedisSaver

    redis_uri = os.getenv("REDIS_URI", "redis://localhost:6379")

    with RedisSaver.from_conn_string(redis_uri) as checkpointer:
        checkpointer.setup()
        yield checkpointer


# ============================================================
# Neo4j Fixtures
# ============================================================

@pytest.fixture(scope="session")
def neo4j_driver():
    """Get a live Neo4j driver."""
    from neo4j import GraphDatabase

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not all([uri, user, password]):
        pytest.skip("Neo4j credentials not configured")

    driver = GraphDatabase.driver(uri, auth=(user, password))

    # Verify connection
    with driver.session() as session:
        session.run("RETURN 1")

    yield driver

    driver.close()


@pytest.fixture(scope="session")
def existing_document(neo4j_driver):
    """Find an existing document with embeddings in Neo4j."""
    with neo4j_driver.session() as session:
        result = session.run("""
            MATCH (u:User)-[:UPLOADED]->(d:Document)-[:HAS_CONTENT_BLOCK]->(cb:ContentBlock)
            WHERE cb.embedding IS NOT NULL
            RETURN u.id AS user_id, d.documentId AS doc_id, count(cb) AS block_count
            LIMIT 1
        """)
        record = result.single()

        if not record:
            pytest.skip("No existing document with embeddings found in Neo4j")

        return {
            "user_id": record["user_id"],
            "doc_id": record["doc_id"],
            "block_count": record["block_count"]
        }


# ============================================================
# Supabase Fixtures
# ============================================================

@pytest.fixture(scope="session")
def supabase_client():
    """Get a live Supabase client with service role."""
    from supabase import create_client

    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        pytest.skip("Supabase credentials not configured")

    client = create_client(url, key)
    yield client


@pytest.fixture(scope="session")
def test_user(supabase_client):
    """Find or verify a test user exists in Supabase."""
    # Try to find an existing user
    result = supabase_client.table("User").select("id, email, voiceMinutesUsed, voiceMinutesLimit").limit(1).execute()

    if not result.data:
        pytest.skip("No users found in Supabase")

    return result.data[0]


# ============================================================
# LiveKit Fixtures
# ============================================================

@pytest.fixture(scope="session")
def livekit_credentials():
    """Get LiveKit credentials."""
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not all([url, api_key, api_secret]):
        pytest.skip("LiveKit credentials not configured")

    return {
        "url": url,
        "api_key": api_key,
        "api_secret": api_secret
    }


# ============================================================
# OpenAI Fixtures (for embeddings)
# ============================================================

@pytest.fixture(scope="session")
def openai_client():
    """Get OpenAI client for embedding tests."""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OpenAI API key not configured")

    return OpenAI(api_key=api_key)


# ============================================================
# API Client Fixtures
# ============================================================

@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for the Python API."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def authenticated_headers(test_user, supabase_client):
    """
    Get authenticated headers for API requests.
    Note: For integration tests, we'll use service role to bypass JWT.
    In production tests, you'd generate a real JWT.
    """
    # For now, we'll mock authentication at the API level
    # Real integration would require a valid Supabase JWT
    return {
        "Authorization": "Bearer test-integration-token",
        "X-Test-User-Id": test_user["id"]  # Custom header for test identification
    }


# ============================================================
# Cleanup Fixtures
# ============================================================

@pytest.fixture
def cleanup_redis_keys(redis_client):
    """Fixture to track and cleanup Redis keys created during test."""
    keys_to_cleanup = []

    def track_key(key):
        keys_to_cleanup.append(key)
        return key

    yield track_key

    # Cleanup after test
    for key in keys_to_cleanup:
        redis_client.delete(key)


@pytest.fixture
def test_qp_id():
    """Generate a unique test QP ID."""
    import uuid
    return f"test-qp-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_task_id():
    """Generate a unique test task ID."""
    import uuid
    return f"test-task-{uuid.uuid4().hex[:8]}"
