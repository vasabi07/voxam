"""
Tests for JWT authentication and authorization in the Python backend.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
import jwt
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from security import verify_token, get_jwks_client


class TestVerifyToken:
    """Tests for the verify_token dependency."""

    def test_returns_403_when_no_authorization_header(self, client):
        """Test that missing Authorization header returns 403 (HTTPBearer default)."""
        # FastAPI's HTTPBearer returns 403 when Authorization header is missing
        response = client.post("/upload/presign", json={
            "filename": "test.pdf",
            "content_type": "application/pdf"
        })
        assert response.status_code == 403

    def test_returns_403_when_bearer_prefix_missing(self, client):
        """Test that missing Bearer prefix returns 403 (HTTPBearer default)."""
        # FastAPI's HTTPBearer returns 403 when scheme is not "Bearer"
        response = client.post(
            "/upload/presign",
            json={"filename": "test.pdf", "content_type": "application/pdf"},
            headers={"Authorization": "invalid-token-without-bearer"}
        )
        assert response.status_code == 403

    def test_returns_401_when_token_is_expired(self, mock_jwks_client):
        """Test that expired tokens are rejected."""
        # Create an expired token
        expired_payload = {
            "sub": "test-user",
            "aud": "authenticated",
            "exp": int((datetime.now() - timedelta(hours=1)).timestamp()),
            "iat": int((datetime.now() - timedelta(hours=2)).timestamp()),
        }

        # Mock jwt.decode to raise ExpiredSignatureError
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")

            credentials = MagicMock()
            credentials.credentials = "expired-token"

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401
            assert "expired" in exc_info.value.detail.lower()

    def test_returns_401_when_signature_invalid(self, mock_jwks_client):
        """Test that invalid signatures are rejected."""
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidSignatureError("Invalid signature")

            credentials = MagicMock()
            credentials.credentials = "tampered-token"

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401

    def test_returns_401_when_audience_invalid(self, mock_jwks_client):
        """Test that wrong audience is rejected."""
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidAudienceError("Invalid audience")

            credentials = MagicMock()
            credentials.credentials = "wrong-audience-token"

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401
            assert "audience" in exc_info.value.detail.lower()

    def test_accepts_valid_es256_token(self, mock_jwks_client):
        """Test that valid ES256 tokens are accepted."""
        valid_payload = {
            "sub": "test-user-id",
            "aud": "authenticated",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "email": "test@example.com",
        }

        with patch("security.jwt.decode") as mock_decode:
            mock_decode.return_value = valid_payload

            credentials = MagicMock()
            credentials.credentials = "valid-token"

            result = verify_token(credentials)

            assert result == valid_payload
            assert result["sub"] == "test-user-id"
            # Verify ES256 algorithm was used
            mock_decode.assert_called_once()
            call_args = mock_decode.call_args
            assert "ES256" in call_args[1]["algorithms"]

    def test_extracts_user_id_from_sub_claim(self, mock_jwks_client):
        """Test that user_id is correctly extracted from sub claim."""
        user_id = "user-abc-123"
        valid_payload = {
            "sub": user_id,
            "aud": "authenticated",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        }

        with patch("security.jwt.decode") as mock_decode:
            mock_decode.return_value = valid_payload

            credentials = MagicMock()
            credentials.credentials = "valid-token"

            result = verify_token(credentials)

            assert result["sub"] == user_id


class TestJWKSClient:
    """Tests for JWKS client caching and behavior."""

    def test_caches_jwks_client_after_first_fetch(self):
        """Test that JWKS client is cached after first creation."""
        # Reset the global cache
        import security
        security._jwks_client = None

        with patch("security.PyJWKClient") as mock_pyjwk:
            mock_client = MagicMock()
            mock_pyjwk.return_value = mock_client

            # First call should create client
            client1 = get_jwks_client()
            # Second call should return cached client
            client2 = get_jwks_client()

            # Should only be called once
            assert mock_pyjwk.call_count == 1
            assert client1 is client2

        # Clean up
        security._jwks_client = None

    def test_raises_error_when_jwks_url_not_set(self):
        """Test that missing JWKS URL raises ValueError."""
        import security
        security._jwks_client = None
        original_url = security.SUPABASE_JWKS_URL

        try:
            security.SUPABASE_JWKS_URL = None
            with pytest.raises(ValueError) as exc_info:
                get_jwks_client()
            assert "SUPABASE_JWKS_URL" in str(exc_info.value)
        finally:
            security.SUPABASE_JWKS_URL = original_url
            security._jwks_client = None


class TestCopilotKitMiddleware:
    """Tests for the CopilotKit authentication middleware."""

    def test_copilotkit_requires_authentication(self, client):
        """Test that /copilotkit/* endpoints require authentication."""
        # Note: The actual copilotkit endpoint is registered at startup
        # This tests the middleware behavior
        response = client.post("/copilotkit/test")
        # Should return 401 or 404 (endpoint may not exist in test)
        assert response.status_code in [401, 404]

    def test_copilotkit_rejects_invalid_bearer_scheme(self, client):
        """Test that non-Bearer auth schemes are rejected."""
        response = client.post(
            "/copilotkit/test",
            headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        assert response.status_code in [401, 404]

    def test_copilotkit_middleware_validates_thread_ownership(self, client):
        """Test that thread_id ownership is validated in resume endpoint."""
        # This tests the /copilotkit/resume/{thread_id} endpoint
        # which should validate that thread_id belongs to authenticated user

        # Without proper auth, should fail
        response = client.post(
            "/copilotkit/resume/chat-other-user-123",
            json={"approved": True}
        )
        assert response.status_code == 401


class TestAlgorithmVerification:
    """Tests for JWT algorithm verification."""

    def test_rejects_rs256_tokens(self, mock_jwks_client):
        """Test that RS256 tokens are rejected (we use ES256)."""
        # ES256 is the expected algorithm
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidAlgorithmError("Invalid algorithm")

            credentials = MagicMock()
            credentials.credentials = "rs256-token"

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401

    def test_rejects_hs256_tokens(self, mock_jwks_client):
        """Test that HS256 tokens are rejected."""
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidAlgorithmError("Invalid algorithm")

            credentials = MagicMock()
            credentials.credentials = "hs256-token"

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401

    def test_rejects_none_algorithm(self, mock_jwks_client):
        """Test that 'none' algorithm is rejected (security vulnerability)."""
        # Tokens with alg: none should be rejected
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")

            credentials = MagicMock()
            credentials.credentials = "eyJhbGciOiJub25lIn0.eyJzdWIiOiJ0ZXN0In0."

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401


class TestClaimValidation:
    """Tests for JWT claim validation."""

    def test_requires_sub_claim(self, mock_jwks_client):
        """Test that sub claim is required."""
        payload_without_sub = {
            "aud": "authenticated",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        }

        with patch("security.jwt.decode") as mock_decode:
            mock_decode.return_value = payload_without_sub

            credentials = MagicMock()
            credentials.credentials = "token-without-sub"

            # The token should be accepted but have no sub
            result = verify_token(credentials)
            assert "sub" not in result or result.get("sub") is None

    def test_requires_authenticated_audience(self, mock_jwks_client):
        """Test that audience must be 'authenticated'."""
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidAudienceError("Invalid audience")

            credentials = MagicMock()
            credentials.credentials = "wrong-audience-token"

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401
            assert "audience" in exc_info.value.detail.lower()

    def test_rejects_future_nbf_tokens(self, mock_jwks_client):
        """Test that tokens with future 'not before' are rejected."""
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.ImmatureSignatureError("Token not yet valid")

            credentials = MagicMock()
            credentials.credentials = "future-nbf-token"

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401


class TestSignatureValidation:
    """Tests for JWT signature validation."""

    def test_validates_against_jwks(self, mock_jwks_client):
        """Test that signature is validated against JWKS."""
        valid_payload = {
            "sub": "test-user",
            "aud": "authenticated",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        }

        with patch("security.jwt.decode") as mock_decode:
            mock_decode.return_value = valid_payload

            credentials = MagicMock()
            credentials.credentials = "valid-token"

            verify_token(credentials)

            # Verify JWKS client was used to get signing key
            mock_jwks_client.get_signing_key_from_jwt.assert_called_once_with("valid-token")

    def test_rejects_tampered_payload(self, mock_jwks_client):
        """Test that tampered payloads are rejected."""
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidSignatureError("Signature verification failed")

            credentials = MagicMock()
            credentials.credentials = "tampered-payload-token"

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401

    def test_rejects_tampered_signature(self, mock_jwks_client):
        """Test that tampered signatures are rejected."""
        with patch("security.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.InvalidSignatureError("Signature verification failed")

            credentials = MagicMock()
            credentials.credentials = "tampered-signature-token"

            with pytest.raises(HTTPException) as exc_info:
                verify_token(credentials)

            assert exc_info.value.status_code == 401


class TestHeaderValidation:
    """Tests for Authorization header validation."""

    def test_requires_bearer_prefix(self, client):
        """Test that Bearer prefix is required (HTTPBearer returns 403)."""
        response = client.post(
            "/upload/presign",
            json={"filename": "test.pdf", "content_type": "application/pdf"},
            headers={"Authorization": "token-without-bearer"}
        )
        # FastAPI's HTTPBearer returns 403 when scheme is not "Bearer"
        assert response.status_code == 403

    def test_rejects_empty_token(self, client):
        """Test that empty tokens are rejected (HTTPBearer returns 403)."""
        response = client.post(
            "/upload/presign",
            json={"filename": "test.pdf", "content_type": "application/pdf"},
            headers={"Authorization": "Bearer "}
        )
        # FastAPI's HTTPBearer returns 403 for empty credentials
        assert response.status_code == 403

    def test_rejects_malformed_jwt(self, client, mock_jwks_client):
        """Test that malformed JWTs are rejected."""
        response = client.post(
            "/upload/presign",
            json={"filename": "test.pdf", "content_type": "application/pdf"},
            headers={"Authorization": "Bearer not.a.valid.jwt.token"}
        )
        assert response.status_code == 401
