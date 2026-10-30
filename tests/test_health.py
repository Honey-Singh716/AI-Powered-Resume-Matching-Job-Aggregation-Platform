"""
Tests for GET /api/health and HEAD /api/health.

Covered:
  1. GET /api/health  → HTTP 200
  2. GET /api/health  → JSON body {"status": "healthy"}
  3. HEAD /api/health → HTTP 200
  4. HEAD /api/health → empty response body
  5. Both methods work without any Authorization header
  6. Protected routes still require authentication (401/403)
"""

import pytest


# ─────────────────────────────── GET tests ───────────────────────────────────

class TestHealthGet:
    def test_get_returns_200(self, client):
        """GET /api/health must return HTTP 200."""
        response = client.get("/api/health")
        assert response.status_code == 200, (
            f"Expected 200 but got {response.status_code}"
        )

    def test_get_returns_healthy_json(self, client):
        """GET /api/health must return {\"status\": \"healthy\"}."""
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body == {"status": "healthy"}, (
            f"Unexpected body: {body}"
        )

    def test_get_requires_no_auth(self, client):
        """GET /api/health must succeed with no Authorization header."""
        # Ensure there is absolutely no auth header on this request
        response = client.get("/api/health", headers={})
        assert response.status_code == 200

    def test_get_content_type_is_json(self, client):
        """GET /api/health must respond with application/json content type."""
        response = client.get("/api/health")
        assert "application/json" in response.headers.get("content-type", "")


# ─────────────────────────────── HEAD tests ──────────────────────────────────

class TestHealthHead:
    def test_head_returns_200(self, client):
        """HEAD /api/health must return HTTP 200."""
        response = client.request("HEAD", "/api/health")
        assert response.status_code == 200, (
            f"Expected 200 but got {response.status_code}"
        )

    def test_head_returns_empty_body(self, client):
        """HEAD /api/health must return an empty response body (per HTTP spec)."""
        response = client.request("HEAD", "/api/health")
        assert response.status_code == 200
        assert response.content == b"", (
            f"Expected empty body but got: {response.content!r}"
        )

    def test_head_requires_no_auth(self, client):
        """HEAD /api/health must succeed with no Authorization header."""
        response = client.request("HEAD", "/api/health", headers={})
        assert response.status_code == 200

    def test_head_has_content_type_header(self, client):
        """
        HEAD response must carry the same Content-Type header a GET would,
        even though the body is empty (RFC 7231 §4.3.2).
        """
        head_resp = client.request("HEAD", "/api/health")
        get_resp = client.get("/api/health")
        assert head_resp.status_code == 200
        # Both should advertise application/json
        assert "application/json" in head_resp.headers.get("content-type", "")
        assert head_resp.headers.get("content-type") == get_resp.headers.get("content-type")


# ─────────────────────────────── Auth protection ─────────────────────────────

class TestProtectedRoutes:
    def test_upload_resume_requires_auth(self, client):
        """POST /upload_resume must reject requests without a JWT (401)."""
        response = client.post("/upload_resume", files={})
        assert response.status_code in (401, 422), (
            f"Expected 401 or 422 (unprocessable) without auth, got {response.status_code}"
        )

    def test_my_profile_requires_auth(self, client):
        """GET /my-profile must return 401 without a JWT."""
        response = client.get("/my-profile")
        assert response.status_code == 401, (
            f"Expected 401 without auth, got {response.status_code}"
        )

    def test_recommended_jobs_requires_auth(self, client):
        """GET /recommended-jobs must return 401 without a JWT."""
        response = client.get("/recommended-jobs")
        assert response.status_code == 401, (
            f"Expected 401 without auth, got {response.status_code}"
        )

    def test_admin_dashboard_requires_auth(self, client):
        """GET /admin/dashboard/summary must return 401 without a JWT."""
        response = client.get("/admin/dashboard/summary")
        assert response.status_code == 401, (
            f"Expected 401 without auth, got {response.status_code}"
        )

    def test_post_jobs_requires_auth(self, client):
        """POST /jobs must return 401 without a JWT."""
        response = client.post("/jobs", json={})
        assert response.status_code in (401, 422), (
            f"Expected 401 or 422 without auth, got {response.status_code}"
        )

    def test_my_applications_requires_auth(self, client):
        """GET /my-applications must return 401 without a JWT."""
        response = client.get("/my-applications")
        assert response.status_code == 401, (
            f"Expected 401 without auth, got {response.status_code}"
        )

    def test_candidates_search_requires_auth(self, client):
        """GET /candidates/search must return 401 without a JWT."""
        response = client.get("/candidates/search?query=python")
        assert response.status_code == 401, (
            f"Expected 401 without auth, got {response.status_code}"
        )


# ─────────────────────────────── Public routes ───────────────────────────────

class TestPublicRoutes:
    def test_register_endpoint_exists(self, client):
        """POST /users/register should be reachable (not 404/405)."""
        # A 422 means FastAPI accepted the route but rejected the payload — that's fine.
        response = client.post("/users/register", json={})
        assert response.status_code != 404, "Register endpoint not found"

    def test_login_endpoint_exists(self, client):
        """POST /auth/login should be reachable."""
        response = client.post("/auth/login", data={"username": "x", "password": "x"})
        assert response.status_code != 404, "Login endpoint not found"

    def test_jobs_list_is_public(self, client):
        """GET /jobs must be accessible without auth (per README)."""
        response = client.get("/jobs")
        # 200 or pagination-default response; 401 would be a regression
        assert response.status_code != 401, (
            "GET /jobs should be public but returned 401"
        )

    def test_legacy_health_still_works(self, client):
        """GET /health (legacy) must still return 200 for backwards compat."""
        response = client.get("/health")
        assert response.status_code == 200
