"""Shared test fixtures for Chappie Daemon tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.domain.models import AudioCapture, TTSRequest
from app.domain.ports import (
    AudioCapturePort,
    AudioPlaybackPort,
    OrchestratorClientPort,
    StateManagementPort,
    VolumeControlPort,
)


# ----- Factory helpers -----

def make_mock_audio_capture(
    audio_data: bytes = b"fake_audio_data",
    session_id: str = "test-session-123",
) -> AudioCapture:
    """Create an AudioCapture instance for testing."""
    return AudioCapture(
        audio_data=audio_data,
        timestamp=datetime.now(timezone.utc),
        session_id=session_id,
    )


def make_tts_request(
    audio_file: str = "/tmp/test_tts.mp3",
    text: str = "Hello, this is a test.",
    ducking: bool = True,
) -> TTSRequest:
    """Create a TTSRequest instance for testing."""
    return TTSRequest(
        audio_file=audio_file,
        text=text,
        ducking=ducking,
    )


# ----- Mock port fixtures -----

@pytest.fixture
def mock_audio_capture_port() -> AsyncMock:
    """Create a mock AudioCapturePort."""
    mock = AsyncMock(spec=AudioCapturePort)
    mock.start_capture = AsyncMock()
    mock.stop_capture = AsyncMock(
        return_value=make_mock_audio_capture()
    )
    mock.is_microphone_available = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_audio_playback_port() -> AsyncMock:
    """Create a mock AudioPlaybackPort."""
    mock = AsyncMock(spec=AudioPlaybackPort)
    mock.play = AsyncMock()
    mock.stop = AsyncMock()
    mock.is_playing = AsyncMock(return_value=False)
    mock.is_playback_available = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_volume_control_port() -> AsyncMock:
    """Create a mock VolumeControlPort."""
    mock = AsyncMock(spec=VolumeControlPort)
    mock.duck = AsyncMock(return_value={"sink_42": 0.75})
    mock.restore = AsyncMock()
    mock.is_available = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_state_management_port() -> AsyncMock:
    """Create a mock StateManagementPort."""
    mock = AsyncMock(spec=StateManagementPort)
    mock.set_global_state = AsyncMock()
    mock.set_tts_state = AsyncMock()
    mock.set_text_enabled = AsyncMock()
    mock.get_global_state = AsyncMock(return_value="idle")
    mock.get_tts_state = AsyncMock(return_value="idle")
    return mock


@pytest.fixture
def mock_orchestrator_port() -> AsyncMock:
    """Create a mock OrchestratorClientPort."""
    mock = AsyncMock(spec=OrchestratorClientPort)
    mock.send_audio = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_orchestrator_port_failure() -> AsyncMock:
    """Create a mock OrchestratorClientPort that fails."""
    mock = AsyncMock(spec=OrchestratorClientPort)
    mock.send_audio = AsyncMock(return_value=False)
    return mock


# ----- FastAPI TestClient fixture -----

@pytest.fixture
def test_client() -> TestClient:
    """Create a TestClient with the fully wired app."""
    from app.main import create_app

    app = create_app()
    return TestClient(app)
