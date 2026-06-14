"""Integration tests for POST /play-tts endpoint."""

from fastapi.testclient import TestClient


class TestPlayTtsEndpoint:
    """Tests for POST /play-tts."""

    def test_play_tts_invalid_body(self, test_client: TestClient):
        """POST /play-tts with invalid body should return 400."""
        response = test_client.post(
            "/play-tts",
            json={"invalid_field": "value"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"

    def test_play_tts_missing_required_fields(self, test_client: TestClient):
        """POST /play-tts without required fields should return 400."""
        response = test_client.post(
            "/play-tts",
            json={},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"

    def test_play_tts_missing_audio_file(self, test_client: TestClient):
        """POST /play-tts without audio_file should return 400."""
        response = test_client.post(
            "/play-tts",
            json={"text": "hello"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"

    def test_play_tts_missing_text(self, test_client: TestClient):
        """POST /play-tts without text should return 400."""
        response = test_client.post(
            "/play-tts",
            json={"audio_file": "/tmp/test.mp3"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
