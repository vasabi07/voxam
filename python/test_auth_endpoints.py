"""
Test authentication on protected endpoints.
Tests that:
1. Endpoints return 401 without auth
2. Endpoints return 401 with invalid token
3. verify_token dependency works correctly
"""

import requests
from fastapi.testclient import TestClient
import sys

# Import the app
from api import app

client = TestClient(app)

# Test endpoints that should require auth
PROTECTED_ENDPOINTS = [
    ("POST", "/ingest", {"file_key": "test.pdf", "document_id": "test-id"}),
    ("POST", "/start-exam-session", {"qp_id": "test", "thread_id": "test", "mode": "exam", "region": "india"}),
    ("POST", "/create-qp", {"qp_id": "test", "document_id": "test", "duration": 30, "num_questions": 10}),
    ("POST", "/end-exam", {"session_id": "test", "thread_id": "test", "qp_id": "test"}),
    ("GET", "/exam-report/test-session-id", None),
    ("GET", "/topics?doc_id=test", None),
    ("POST", "/create-lp", {"lp_id": "test", "doc_id": "test", "topics": ["test"]}),
    ("POST", "/start-learn-session", {"lp_id": "test", "thread_id": "test", "region": "india"}),
]

# Endpoints that should NOT require auth (public)
PUBLIC_ENDPOINTS = [
    ("GET", "/", None),
]

def test_endpoint(method: str, path: str, body: dict = None, headers: dict = None):
    """Test a single endpoint."""
    if method == "GET":
        response = client.get(path, headers=headers)
    elif method == "POST":
        response = client.post(path, json=body, headers=headers)
    return response

def main():
    print("=" * 60)
    print("Testing Authentication on Protected Endpoints")
    print("=" * 60)

    all_passed = True

    # Test 1: Protected endpoints should return 401/403 without auth
    print("\n[TEST 1] Protected endpoints without auth header:")
    print("-" * 40)
    for method, path, body in PROTECTED_ENDPOINTS:
        response = test_endpoint(method, path, body)
        # Should get 401 (Unauthorized) or 403 (Forbidden)
        if response.status_code in [401, 403]:
            print(f"  ✅ {method} {path}: {response.status_code} (expected)")
        else:
            print(f"  ❌ {method} {path}: {response.status_code} (expected 401/403)")
            print(f"     Response: {response.json()}")
            all_passed = False

    # Test 2: Protected endpoints should return 401 with invalid token
    print("\n[TEST 2] Protected endpoints with invalid token:")
    print("-" * 40)
    invalid_headers = {"Authorization": "Bearer invalid_token_here"}
    for method, path, body in PROTECTED_ENDPOINTS:
        response = test_endpoint(method, path, body, invalid_headers)
        if response.status_code == 401:
            print(f"  ✅ {method} {path}: 401 (expected)")
        else:
            print(f"  ❌ {method} {path}: {response.status_code} (expected 401)")
            all_passed = False

    # Test 3: Public endpoints should work without auth
    print("\n[TEST 3] Public endpoints without auth:")
    print("-" * 40)
    for method, path, body in PUBLIC_ENDPOINTS:
        response = test_endpoint(method, path, body)
        if response.status_code == 200:
            print(f"  ✅ {method} {path}: 200 (expected)")
        else:
            print(f"  ❌ {method} {path}: {response.status_code} (expected 200)")
            all_passed = False

    # Test 4: Check /copilotkit/resume requires auth (already protected by middleware)
    print("\n[TEST 4] /copilotkit/resume endpoint (middleware protected):")
    print("-" * 40)
    response = client.post("/copilotkit/resume/test-thread", json={"approved": True})
    if response.status_code == 401:
        print(f"  ✅ POST /copilotkit/resume/test-thread: 401 (expected)")
    else:
        print(f"  ❌ POST /copilotkit/resume/test-thread: {response.status_code} (expected 401)")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Authentication is working correctly!")
    else:
        print("❌ SOME TESTS FAILED - Check the output above")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
