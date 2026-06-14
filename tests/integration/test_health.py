"""Integration tests for health endpoint."""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_ok(self, test_client: TestClient):
        """GET /health should return 200 with status ok."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_has_correct_structure(self, test_client: TestClient):
        """GET /health should have the correct response structure."""
        response = test_client.get("/health")
        data = response.json()
        # HealthResponse only has 'status'
        assert list(data.keys()) == ["status"]

    def test_health_is_accessible_without_auth(self, test_client: TestClient):
        """GET /health should be publicly accessible."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
