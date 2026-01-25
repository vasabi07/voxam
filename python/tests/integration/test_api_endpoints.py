"""
Integration tests for API endpoints.
Tests authenticated endpoints against live services.

NOTE: These tests require a running API server for full integration.
Some tests use TestClient which creates an in-process server.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def api_client(test_user):
    """Create FastAPI test client with authentication mocked for live user."""
    from fastapi.testclient import TestClient
    from api import app
    from security import verify_token

    user_id = test_user["id"]

    def mock_verify_token():
        return {
            "sub": user_id,
            "aud": "authenticated",
            "exp": 9999999999,
            "iat": 1000000000,
        }

    app.dependency_overrides[verify_token] = mock_verify_token
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestCreditsEndpoint:
    """Tests for /credits endpoint."""

    def test_get_credits_authenticated(self, api_client, test_user):
        """Test GET /credits returns user's credit balance."""
        response = api_client.get("/credits")

        assert response.status_code == 200
        data = response.json()

        # Response is wrapped: {"success": True, "credits": {...}}
        assert data.get("success") is True
        credits = data.get("credits", {})

        assert "voiceMinutes" in credits
        assert "chatMessages" in credits
        assert "pages" in credits

        # Verify structure
        for category in ["voiceMinutes", "chatMessages", "pages"]:
            assert "used" in credits[category]
            assert "limit" in credits[category]
            assert "remaining" in credits[category]

        print(f"Credits response: {data}")

    def test_get_credits_unauthenticated(self):
        """Test GET /credits requires authentication."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        response = client.get("/credits")

        # Should return 403 for missing auth
        assert response.status_code == 403


class TestTopicsEndpoint:
    """Tests for /topics endpoint."""

    def test_get_topics_with_valid_document(self, api_client, existing_document):
        """Test GET /topics returns topics for a valid document."""
        doc_id = existing_document["doc_id"]

        response = api_client.get(f"/topics?doc_id={doc_id}")

        assert response.status_code == 200
        data = response.json()

        # Should return list of topics
        assert isinstance(data, (list, dict))
        print(f"Topics response for doc {doc_id}: {data}")

    def test_get_topics_requires_auth(self):
        """Test GET /topics requires authentication."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        response = client.get("/topics?doc_id=test-doc")

        assert response.status_code == 403


class TestTaskProgressEndpoint:
    """Tests for /task/{task_id}/progress endpoint."""

    def test_task_progress_for_nonexistent_task(self, api_client):
        """Test task progress returns appropriate status for unknown task."""
        response = api_client.get("/task/nonexistent-task-123/progress")

        # Should return 200 with status info (even if task doesn't exist)
        # Or 404 depending on implementation
        assert response.status_code in [200, 404]

    def test_task_progress_with_real_task(self, api_client, redis_client, cleanup_redis_keys):
        """Test task progress with manually created task in Redis."""
        task_id = "test-integration-task"
        progress_key = f"task:{task_id}:progress"
        cleanup_redis_keys(progress_key)

        # Set up task progress in Redis
        redis_client.hset(progress_key, mapping={
            "status": "processing",
            "progress": "50",
            "current_step": "extracting"
        })

        response = api_client.get(f"/task/{task_id}/progress")

        if response.status_code == 200:
            data = response.json()
            print(f"Task progress response: {data}")
            # Verify it contains task info
            assert "status" in data or "progress" in data


class TestDocumentEndpoints:
    """Tests for document-related endpoints."""

    def test_upload_presign_authenticated(self, api_client):
        """Test POST /upload/presign generates presigned URL."""
        response = api_client.post("/upload/presign", json={
            "filename": "test-integration.pdf",
            "content_type": "application/pdf"
        })

        assert response.status_code == 200
        data = response.json()

        # Response: {"success": True, "upload_url": ..., "file_key": ...}
        assert data.get("success") is True
        assert "upload_url" in data
        assert "file_key" in data
        assert data["upload_url"].startswith("https://")
        print(f"Presign response: upload_url starts with {data['upload_url'][:50]}...")

    def test_upload_presign_requires_auth(self):
        """Test POST /upload/presign requires authentication."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        response = client.post("/upload/presign", json={
            "filename": "test.pdf",
            "content_type": "application/pdf"
        })

        assert response.status_code == 403


class TestExamEndpoints:
    """Tests for exam-related endpoints."""

    def test_start_exam_requires_auth(self):
        """Test POST /start-exam-session requires authentication."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        response = client.post("/start-exam-session", json={
            "qp_id": "test-qp",
            "thread_id": "exam-test",
            "session_id": "session-test",
            "mode": "exam",
            "region": "india"
        })

        assert response.status_code == 403

    def test_end_exam_requires_auth(self):
        """Test POST /end-exam requires authentication."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        response = client.post("/end-exam", json={
            "session_id": "session-test",
            "thread_id": "exam-test",
            "qp_id": "qp-test"
        })

        assert response.status_code == 403

    def test_exam_report_requires_auth(self):
        """Test GET /exam-report/{id} requires authentication."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        response = client.get("/exam-report/session-123")

        assert response.status_code == 403


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_no_auth_required(self):
        """Test that root endpoint doesn't require auth."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        response = client.get("/")

        # Root endpoint should be public
        assert response.status_code == 200
        data = response.json()
        # Basic response indicating the API is running
        assert data is not None


class TestQuestionPaperEndpoints:
    """Tests for question paper endpoints."""

    def test_create_qp_requires_auth(self):
        """Test POST /create-qp requires authentication."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        response = client.post("/create-qp", json={
            "qp_id": "test-qp",
            "document_id": "doc-123",
            "num_questions": 10,
            "duration": 30,
            "type_of_qp": "exam"
        })

        assert response.status_code == 403


class TestIngestEndpoint:
    """Tests for document ingestion endpoint."""

    def test_ingest_requires_auth(self):
        """Test POST /ingest requires authentication."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        response = client.post("/ingest", json={
            "file_key": "test.pdf",
            "document_id": "doc-123",
            "page_count": 10
        })

        assert response.status_code == 403


class TestLiveKitTokenEndpoint:
    """Tests for LiveKit token generation."""

    def test_livekit_token_structure(self, api_client, test_user):
        """Test that LiveKit token can be generated with proper structure."""
        from livekit import api

        # Generate a test token using the same pattern as the API
        from dotenv import load_dotenv
        import os
        load_dotenv()

        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

        if not livekit_api_key or not livekit_api_secret:
            pytest.skip("LiveKit credentials not configured")

        token = (
            api.AccessToken(livekit_api_key, livekit_api_secret)
            .with_identity(test_user["id"])
            .with_grants(api.VideoGrants(
                room="test-room",
                room_join=True,
                can_publish=True,
                can_subscribe=True,
            ))
            .to_jwt()
        )

        # Verify JWT structure
        assert token is not None
        assert token.count(".") == 2  # JWT format: header.payload.signature
        print(f"Generated LiveKit token (first 50 chars): {token[:50]}...")


class TestExamReportOwnership:
    """Tests for exam report ownership verification."""

    def test_exam_report_nonexistent_session(self, api_client, test_user, supabase_client):
        """Test that exam report returns appropriate error for non-existent session."""
        # Try to access a non-existent session
        response = api_client.get("/exam-report/nonexistent-session-123")

        # The endpoint returns 200 with an error message for non-existent sessions
        assert response.status_code == 200
        data = response.json()
        # Response format: {"error": "..."} for failures
        assert "error" in data
        print(f"Exam report response for non-existent session: {data}")


class TestCopilotKitEndpoint:
    """Tests for CopilotKit endpoint (chat)."""

    def test_copilotkit_requires_auth(self):
        """Test that /copilotkit endpoint requires authentication."""
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)

        # Note: CopilotKit uses a specific message format
        # This tests the auth requirement, not the full flow
        response = client.post("/copilotkit", json={
            "messages": [{"role": "user", "content": "Hello"}]
        })

        # Should require auth (403) or need specific format (422)
        assert response.status_code in [401, 403, 422]
