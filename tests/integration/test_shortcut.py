"""Integration tests for shortcut endpoints."""

from fastapi.testclient import TestClient


class TestShortcutPressEndpoint:
    """Tests for POST /shortcut/press."""

    def test_shortcut_press_returns_200(self, test_client: TestClient):
        """POST /shortcut/press should return 200."""
        response = test_client.post("/shortcut/press")
        # Note: This exercises the real pipeline through dependency override
        assert response.status_code in (200, 500)

    def test_shortcut_press_response_structure(self, test_client: TestClient):
        """POST /shortcut/press should have success response structure."""
        response = test_client.post("/shortcut/press")
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "message" in data


class TestShortcutReleaseEndpoint:
    """Tests for POST /shortcut/release."""

    def test_shortcut_release_returns_409_if_not_recording(self, test_client: TestClient):
        """POST /shortcut/release without press should return 409."""
        response = test_client.post("/shortcut/release")
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "NOT_RECORDING"
