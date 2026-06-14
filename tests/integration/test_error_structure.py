"""Integration tests for error response structure.

Verifies that all error responses follow the ApiErrorResponse schema.
"""

from fastapi.testclient import TestClient

REQUIRED_ERROR_FIELDS = [
    "timestamp",
    "status",
    "error",
    "code",
    "message",
    "path",
    "trace_id",
    "details",
]


class TestErrorResponseStructure:
    """Verify error responses match ApiErrorResponse schema."""

    def _assert_error_structure(self, data: dict, expected_status: int):
        """Assert the error response has all required fields."""
        for field in REQUIRED_ERROR_FIELDS:
            assert field in data, f"Missing field: {field}"

        assert data["status"] == expected_status
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["error"], str)
        assert isinstance(data["code"], str)
        assert isinstance(data["message"], str)
        assert isinstance(data["path"], str)
        assert isinstance(data["trace_id"], str)
        assert isinstance(data["details"], list)

    def test_validation_error_structure(self, test_client: TestClient):
        """400 VALIDATION_ERROR should have correct structure."""
        response = test_client.post(
            "/play-tts",
            json={},
        )
        assert response.status_code == 400
        data = response.json()
        self._assert_error_structure(data, 400)
        assert data["code"] == "VALIDATION_ERROR"
        assert len(data["details"]) > 0

    def test_not_found_structure(self, test_client: TestClient):
        """404 error should have correct structure."""
        response = test_client.get("/nonexistent")
        # FastAPI returns 404 for unknown routes
        data = response.json()
        self._assert_error_structure(data, response.status_code)

    def test_not_recording_structure(self, test_client: TestClient):
        """409 NOT_RECORDING should have correct structure."""
        response = test_client.post("/shortcut/release")
        assert response.status_code == 409
        data = response.json()
        self._assert_error_structure(data, 409)
        assert data["code"] == "NOT_RECORDING"

    def test_trace_id_present(self, test_client: TestClient):
        """Every error should have a unique trace_id."""
        response = test_client.post("/shortcut/release")
        data = response.json()
        assert len(data["trace_id"]) > 0
        # Should be UUID format
        assert len(data["trace_id"].split("-")) == 5

    def test_path_matches_request(self, test_client: TestClient):
        """Path should match the request URL."""
        response = test_client.post("/shortcut/release")
        data = response.json()
        assert data["path"] == "/shortcut/release"

    def test_error_title_format(self, test_client: TestClient):
        """Error title should be human readable."""
        response = test_client.post("/shortcut/release")
        data = response.json()
        assert data["error"] == "Not Recording"
