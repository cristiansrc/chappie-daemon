"""Integration tests for shortcut endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.application.handle_voice_capture import HandleVoiceCaptureUseCase
from app.domain.exceptions import NotRecordingException
from app.infrastructure.adapters.input.router import get_voice_capture_usecase


@pytest.fixture
def mock_voice_capture_usecase() -> AsyncMock:
    """Create a mocked HandleVoiceCaptureUseCase."""
    mock = AsyncMock(spec=HandleVoiceCaptureUseCase)
    mock.start_capture = AsyncMock()
    mock.stop_capture = AsyncMock()
    return mock


class TestShortcutPressEndpoint:
    """Tests for POST /shortcut/press."""

    def test_shortcut_press_returns_200(
        self,
        test_client: TestClient,
        mock_voice_capture_usecase: AsyncMock,
    ):
        """POST /shortcut/press should return 200."""
        test_client.app.dependency_overrides[get_voice_capture_usecase] = (
            lambda: mock_voice_capture_usecase
        )
        response = test_client.post("/shortcut/press")
        assert response.status_code == 200
        mock_voice_capture_usecase.start_capture.assert_awaited_once()

    def test_shortcut_press_response_structure(
        self,
        test_client: TestClient,
        mock_voice_capture_usecase: AsyncMock,
    ):
        """POST /shortcut/press should have success response structure."""
        test_client.app.dependency_overrides[get_voice_capture_usecase] = (
            lambda: mock_voice_capture_usecase
        )
        response = test_client.post("/shortcut/press")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "message" in data


class TestShortcutReleaseEndpoint:
    """Tests for POST /shortcut/release."""

    def test_shortcut_release_returns_409_if_not_recording(
        self,
        test_client: TestClient,
        mock_voice_capture_usecase: AsyncMock,
    ):
        """POST /shortcut/release without press should return 409."""
        mock_voice_capture_usecase.stop_capture.side_effect = (
            NotRecordingException()
        )
        test_client.app.dependency_overrides[get_voice_capture_usecase] = (
            lambda: mock_voice_capture_usecase
        )
        response = test_client.post("/shortcut/release")
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "NOT_RECORDING"
        mock_voice_capture_usecase.stop_capture.assert_awaited_once()
