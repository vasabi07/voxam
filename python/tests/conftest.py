"""
Shared pytest fixtures for VOXAM Python backend tests.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Set test environment variables before importing app
os.environ.setdefault("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_JWKS_URL", "https://test.supabase.co/.well-known/jwks.json")
os.environ.setdefault("LIVEKIT_URL", "wss://test.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "test-api-key")
os.environ.setdefault("LIVEKIT_API_SECRET", "test-api-secret")
os.environ.setdefault("DEEPGRAM_API_KEY", "test-deepgram-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test")
os.environ.setdefault("REDIS_URI", "redis://localhost:6379")


# ============================================================
# Module-level mocking to prevent Redis connection on import
# ============================================================

# Create mock Redis components before any imports
_mock_redis_saver = MagicMock()
_mock_redis_saver.__enter__ = MagicMock(return_value=_mock_redis_saver)
_mock_redis_saver.__exit__ = MagicMock(return_value=None)
_mock_redis_saver.setup = MagicMock()

_mock_redis_client = MagicMock()
_mock_redis_client.json.return_value.get.return_value = []
_mock_redis_client.get.return_value = None
_mock_redis_client.set.return_value = True

# Patch RedisSaver before exam_agent imports
_redis_saver_patch = patch("langgraph.checkpoint.redis.RedisSaver.from_conn_string", return_value=_mock_redis_saver)
_redis_patch = patch("redis.Redis", return_value=_mock_redis_client)

# Start patches before imports
_redis_saver_patch.start()
_redis_patch.start()


# ============================================================
# FastAPI Test Client
# ============================================================

@pytest.fixture
def client():
    """Create a FastAPI test client without auth override."""
    from fastapi.testclient import TestClient
    from api import app
    return TestClient(app)


@pytest.fixture
def authenticated_client(test_user_id):
    """Create a FastAPI test client with authentication mocked."""
    from fastapi.testclient import TestClient
    from api import app
    from security import verify_token

    def mock_verify_token():
        return {
            "sub": test_user_id,
            "aud": "authenticated",
            "exp": 9999999999,
            "iat": 1000000000,
        }

    app.dependency_overrides[verify_token] = mock_verify_token
    client = TestClient(app)
    yield client
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client_other_user(other_user_id):
    """Create a FastAPI test client authenticated as a different user (for IDOR tests)."""
    from fastapi.testclient import TestClient
    from api import app
    from security import verify_token

    def mock_verify_token():
        return {
            "sub": other_user_id,
            "aud": "authenticated",
            "exp": 9999999999,
            "iat": 1000000000,
        }

    app.dependency_overrides[verify_token] = mock_verify_token
    client = TestClient(app)
    yield client
    # Clean up
    app.dependency_overrides.clear()


# ============================================================
# Authentication Fixtures
# ============================================================

@pytest.fixture
def test_user_id():
    """Standard test user ID."""
    return "test-user-id-12345"


@pytest.fixture
def other_user_id():
    """Another user ID for IDOR tests."""
    return "other-user-id-67890"


@pytest.fixture
def valid_jwt_payload(test_user_id):
    """Valid JWT payload for authenticated user."""
    return {
        "sub": test_user_id,
        "aud": "authenticated",
        "exp": 9999999999,
        "iat": 1000000000,
        "email": "test@example.com",
    }


@pytest.fixture
def auth_headers():
    """Authorization headers with test token."""
    return {"Authorization": "Bearer test-valid-token"}


@pytest.fixture
def mock_verify_token(valid_jwt_payload):
    """Mock the verify_token dependency to return valid payload."""
    with patch("security.verify_token") as mock:
        mock.return_value = valid_jwt_payload
        yield mock


@pytest.fixture
def mock_verify_token_other_user(other_user_id):
    """Mock verify_token to return a different user (for IDOR tests)."""
    payload = {
        "sub": other_user_id,
        "aud": "authenticated",
        "exp": 9999999999,
        "iat": 1000000000,
    }
    with patch("security.verify_token") as mock:
        mock.return_value = payload
        yield mock


# ============================================================
# External Service Mocks
# ============================================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("credits.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j driver."""
    with patch("ingestion_workflow.get_neo4j_driver") as mock:
        driver = MagicMock()
        session = MagicMock()
        driver.session.return_value.__enter__ = MagicMock(return_value=session)
        driver.session.return_value.__exit__ = MagicMock(return_value=None)
        mock.return_value = driver
        yield driver, session


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("redis.Redis") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for embeddings and completions."""
    with patch("openai.OpenAI") as mock:
        client = MagicMock()
        # Mock embeddings
        client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1] * 1536)]
        )
        # Mock chat completions
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(
                message=MagicMock(content="Test response")
            )]
        )
        mock.return_value = client
        yield client


@pytest.fixture
def mock_livekit():
    """Mock LiveKit API."""
    with patch("livekit.api.LiveKitAPI") as mock:
        api_client = MagicMock()
        mock.return_value = api_client
        yield api_client


@pytest.fixture
def mock_celery():
    """Mock Celery task sending."""
    with patch("celery_app.celery.send_task") as mock:
        mock.return_value = MagicMock(id="task-123")
        yield mock


# ============================================================
# JWKS Mocking (for JWT verification tests)
# ============================================================

@pytest.fixture
def mock_jwks_client():
    """Mock the JWKS client for JWT verification tests."""
    with patch("security.get_jwks_client") as mock:
        jwks_client = MagicMock()
        signing_key = MagicMock()
        signing_key.key = "mock-signing-key"
        jwks_client.get_signing_key_from_jwt.return_value = signing_key
        mock.return_value = jwks_client
        yield jwks_client


# ============================================================
# Database State Fixtures
# ============================================================

@pytest.fixture
def mock_user_with_credits(mock_supabase, test_user_id):
    """Setup mock user with available credits."""
    user_data = {
        "id": test_user_id,
        "email": "test@example.com",
        "voiceMinutesUsed": 10,
        "voiceMinutesLimit": 60,
        "chatMessagesUsed": 5,
        "chatMessagesLimit": 100,
        "pagesUsed": 10,
        "pagesLimit": 50,
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=user_data)
    return user_data


@pytest.fixture
def mock_user_no_credits(mock_supabase, test_user_id):
    """Setup mock user with no credits remaining."""
    user_data = {
        "id": test_user_id,
        "email": "test@example.com",
        "voiceMinutesUsed": 60,
        "voiceMinutesLimit": 60,
        "chatMessagesUsed": 100,
        "chatMessagesLimit": 100,
        "pagesUsed": 50,
        "pagesLimit": 50,
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=user_data)
    return user_data


@pytest.fixture
def mock_document(test_user_id):
    """Mock document data owned by test user."""
    return {
        "id": "doc-123",
        "title": "Test Document",
        "status": "READY",
        "userId": test_user_id,
        "fileKey": "documents/test.pdf",
        "pageCount": 10,
    }


@pytest.fixture
def mock_question_paper(test_user_id):
    """Mock question paper data owned by test user."""
    return {
        "id": "qp-123",
        "status": "READY",
        "documentId": "doc-123",
        "userId": test_user_id,
        "duration": 30,
        "numQuestions": 10,
    }


@pytest.fixture
def mock_exam_session(test_user_id):
    """Mock exam session data owned by test user."""
    return {
        "id": "session-123",
        "status": "SCHEDULED",
        "mode": "exam",
        "userId": test_user_id,
        "qpId": "qp-123",
        "documentId": "doc-123",
    }


# ============================================================
# LLM Response Helpers
# ============================================================

@pytest.fixture
def create_mock_llm_response():
    """Factory for creating mock LLM responses."""
    def _create(content: str):
        return MagicMock(
            choices=[MagicMock(
                message=MagicMock(content=content)
            )]
        )
    return _create


# ============================================================
# Async Fixtures
# ============================================================

@pytest.fixture
def mock_async_supabase():
    """Mock async Supabase operations."""
    async def _mock_execute():
        return MagicMock(data={"id": "test-id"})

    with patch("credits.get_supabase_client") as mock:
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute = _mock_execute
        mock.return_value = client
        yield client
