"""
Tests for authorization and IDOR prevention in the Python backend.

NOTE: These tests document the current authorization behavior of the API.
Some endpoints lack proper IDOR protection (marked with SECURITY_GAP comments).
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestDocumentOwnership:
    """Tests for document ownership verification."""

    def test_delete_document_with_valid_auth(self, authenticated_client, test_user_id):
        """Test that DELETE /documents/{id} works with authentication."""
        # SECURITY_GAP: This endpoint does NOT verify document ownership
        # It deletes any document regardless of owner. Should be fixed in API.
        with patch("neo4j.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_gdb.driver.return_value = mock_driver
            mock_driver.session.return_value.__enter__.return_value = mock_session
            mock_session.run.return_value = MagicMock()

            with patch("boto3.client") as mock_boto:
                mock_r2 = MagicMock()
                mock_boto.return_value = mock_r2
                mock_r2.list_objects_v2.return_value = {"Contents": []}

                with patch("redis.Redis") as mock_redis:
                    mock_redis_client = MagicMock()
                    mock_redis.from_url.return_value = mock_redis_client
                    mock_redis_client.keys.return_value = []

                    response = authenticated_client.delete("/documents/doc-123")

                    # Currently succeeds without ownership check
                    assert response.status_code == 200

    def test_retry_document_verifies_ownership(self, authenticated_client, test_user_id):
        """Test that POST /documents/{id}/retry verifies user owns document."""
        # This endpoint DOES check ownership but returns 200 with error, not 403
        with patch("supabase.create_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            # Document owned by DIFFERENT user
            other_user_id = "other-user-id"
            mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "id": "doc-123",
                    "userId": other_user_id,  # Different user
                    "status": "FAILED",
                    "fileKey": "documents/test.pdf"
                }
            )

            response = authenticated_client.post("/documents/doc-123/retry")

            # Returns 200 with error message (not 403)
            # SECURITY_GAP: Should return 403 status code for IDOR prevention
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") == False
            assert "Unauthorized" in data.get("error", "")

    def test_retry_document_allows_owner(self, authenticated_client, test_user_id):
        """Test that POST /documents/{id}/retry allows document owner."""
        with patch("supabase.create_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            # Document owned by test user
            mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "id": "doc-123",
                    "userId": test_user_id,
                    "status": "FAILED",
                    "fileKey": "documents/test.pdf"
                }
            )
            mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            with patch("tasks.ingestion.ingest_document") as mock_task:
                mock_task.delay.return_value = MagicMock(id="task-123")

                response = authenticated_client.post("/documents/doc-123/retry")

                assert response.status_code == 200
                data = response.json()
                assert data.get("success") == True


class TestExamReportOwnership:
    """Tests for exam report ownership verification - this endpoint HAS proper protection."""

    def test_exam_report_verifies_ownership_returns_403(self, authenticated_client, test_user_id):
        """Test that GET /exam-report/{id} returns 403 when user doesn't own session."""
        other_user_id = "other-user-id"

        with patch("supabase.create_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            # Session owned by DIFFERENT user
            mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "id": "session-123",
                    "userId": other_user_id,  # Different user
                }
            )

            response = authenticated_client.get("/exam-report/session-123")

            # This endpoint DOES return 403 for IDOR protection
            assert response.status_code == 403

    def test_exam_report_allows_owner(self, authenticated_client, test_user_id):
        """Test that GET /exam-report/{id} allows session owner."""
        with patch("supabase.create_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            # First call: session ownership check
            # Second call: report fetch
            mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
                MagicMock(data={"id": "session-123", "userId": test_user_id}),
                MagicMock(data={"id": "report-123", "totalScore": 85})
            ]

            response = authenticated_client.get("/exam-report/session-123")

            assert response.status_code == 200
            data = response.json()
            assert data.get("success") == True


class TestThreadIDScoping:
    """Tests for thread_id ownership validation in CopilotKit endpoints."""

    def test_copilotkit_resume_validates_thread_ownership(self, client, test_user_id):
        """Test that /copilotkit/resume/{thread_id} validates thread belongs to user."""
        # Thread ID format: "chat-{user_id}" or "chat-{user_id}-{doc_id}"
        valid_thread_id = f"chat-{test_user_id}"

        with patch("security.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": test_user_id, "aud": "authenticated"}

            with patch("security.get_jwks_client") as mock_jwks:
                mock_key = MagicMock()
                mock_key.key = "mock-key"
                mock_jwks.return_value.get_signing_key_from_jwt.return_value = mock_key

                with patch("security.jwt.decode") as mock_decode:
                    mock_decode.return_value = {"sub": test_user_id, "aud": "authenticated"}

                    with patch("api.get_chat_graph") as mock_graph:
                        mock_graph.return_value.ainvoke = AsyncMock(return_value={"messages": []})

                        response = client.post(
                            f"/copilotkit/resume/{valid_thread_id}",
                            json={"approved": True},
                            headers={"Authorization": "Bearer test-token"}
                        )

                        # Should not return 403 for valid thread
                        assert response.status_code != 403

    def test_copilotkit_resume_rejects_cross_user_thread(self, client, test_user_id):
        """Test that /copilotkit/resume rejects threads belonging to other users."""
        other_user_id = "other-user-id"
        other_user_thread = f"chat-{other_user_id}"

        with patch("security.get_jwks_client") as mock_jwks:
            mock_key = MagicMock()
            mock_key.key = "mock-key"
            mock_jwks.return_value.get_signing_key_from_jwt.return_value = mock_key

            with patch("security.jwt.decode") as mock_decode:
                mock_decode.return_value = {"sub": test_user_id, "aud": "authenticated"}

                response = client.post(
                    f"/copilotkit/resume/{other_user_thread}",
                    json={"approved": True},
                    headers={"Authorization": "Bearer test-token"}
                )

                # Should return 403 Forbidden for cross-user access
                assert response.status_code == 403

    def test_thread_id_validation_handles_uuid_with_hyphens(self, client):
        """Test that thread_id validation correctly handles UUID user_ids with hyphens."""
        # UUID format user_id: "123e4567-e89b-12d3-a456-426614174000"
        uuid_user_id = "123e4567-e89b-12d3-a456-426614174000"
        thread_id = f"chat-{uuid_user_id}"

        with patch("security.get_jwks_client") as mock_jwks:
            mock_key = MagicMock()
            mock_key.key = "mock-key"
            mock_jwks.return_value.get_signing_key_from_jwt.return_value = mock_key

            with patch("security.jwt.decode") as mock_decode:
                mock_decode.return_value = {"sub": uuid_user_id, "aud": "authenticated"}

                with patch("api.get_chat_graph") as mock_graph:
                    mock_graph.return_value.ainvoke = AsyncMock(return_value={"messages": []})

                    response = client.post(
                        f"/copilotkit/resume/{thread_id}",
                        json={"approved": True},
                        headers={"Authorization": "Bearer test-token"}
                    )

                    # Should correctly validate UUID user_id
                    # This tests the known issue with hyphen parsing
                    assert response.status_code != 403

    def test_thread_id_with_doc_id_validates_correctly(self, client, test_user_id):
        """Test thread_id format "chat-{user_id}-{doc_id}" validates correctly."""
        doc_id = "doc-123"
        thread_id = f"chat-{test_user_id}-{doc_id}"

        with patch("security.get_jwks_client") as mock_jwks:
            mock_key = MagicMock()
            mock_key.key = "mock-key"
            mock_jwks.return_value.get_signing_key_from_jwt.return_value = mock_key

            with patch("security.jwt.decode") as mock_decode:
                mock_decode.return_value = {"sub": test_user_id, "aud": "authenticated"}

                with patch("api.get_chat_graph") as mock_graph:
                    mock_graph.return_value.ainvoke = AsyncMock(return_value={"messages": []})

                    response = client.post(
                        f"/copilotkit/resume/{thread_id}",
                        json={"approved": True},
                        headers={"Authorization": "Bearer test-token"}
                    )

                    # Should correctly validate
                    assert response.status_code != 403


class TestAuthenticationRequired:
    """Tests verifying endpoints require authentication."""

    def test_credits_requires_auth(self, client):
        """Test that GET /credits requires authentication."""
        response = client.get("/credits")
        # HTTPBearer returns 403 for missing auth
        assert response.status_code == 403

    def test_upload_presign_requires_auth(self, client):
        """Test that POST /upload/presign requires authentication."""
        response = client.post("/upload/presign", json={
            "filename": "test.pdf",
            "content_type": "application/pdf"
        })
        assert response.status_code == 403

    def test_ingest_requires_auth(self, client):
        """Test that POST /ingest requires authentication."""
        response = client.post("/ingest", json={
            "file_key": "test.pdf",
            "document_id": "doc-123",
            "page_count": 10
        })
        assert response.status_code == 403

    def test_create_qp_requires_auth(self, client):
        """Test that POST /create-qp requires authentication."""
        response = client.post("/create-qp", json={
            "qp_id": "qp-123",
            "document_id": "doc-123",
            "num_questions": 10,
            "duration": 30,
            "type_of_qp": "exam"
        })
        assert response.status_code == 403

    def test_start_exam_requires_auth(self, client):
        """Test that POST /start-exam-session requires authentication."""
        response = client.post("/start-exam-session", json={
            "qp_id": "qp-123",
            "thread_id": "exam-user-123",
            "session_id": "session-123",
            "mode": "exam",
            "region": "india"
        })
        assert response.status_code == 403

    def test_end_exam_requires_auth(self, client):
        """Test that POST /end-exam requires authentication."""
        response = client.post("/end-exam", json={
            "session_id": "session-123",
            "thread_id": "exam-user-123",
            "qp_id": "qp-123"
        })
        assert response.status_code == 403

    def test_exam_report_requires_auth(self, client):
        """Test that GET /exam-report/{id} requires authentication."""
        response = client.get("/exam-report/session-123")
        assert response.status_code == 403

    def test_topics_requires_auth(self, client):
        """Test that GET /topics requires authentication."""
        response = client.get("/topics?doc_id=doc-123")
        assert response.status_code == 403
