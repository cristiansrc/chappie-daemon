"""Tests for HandleVoiceCaptureUseCase."""

from unittest.mock import AsyncMock

import pytest

from app.application.handle_voice_capture import (
    HandleVoiceCaptureUseCase,
)
from app.domain.exceptions import (
    AlreadyRecordingException,
    MicrophoneUnavailableException,
    NotRecordingException,
    VolumeControlFailedException,
)


@pytest.fixture
def use_case(
    mock_audio_capture_port: AsyncMock,
    mock_volume_control_port: AsyncMock,
    mock_state_management_port: AsyncMock,
    mock_orchestrator_port: AsyncMock,
) -> HandleVoiceCaptureUseCase:
    """Create a HandleVoiceCaptureUseCase with mocked ports."""
    return HandleVoiceCaptureUseCase(
        audio_capture_port=mock_audio_capture_port,
        volume_control_port=mock_volume_control_port,
        state_management_port=mock_state_management_port,
        orchestrator_client_port=mock_orchestrator_port,
    )


class TestStartCapture:
    """Tests for start_capture method."""

    @pytest.mark.asyncio
    async def test_start_capture_success(self, use_case, mock_volume_control_port, mock_state_management_port, mock_audio_capture_port):
        """Should start capture successfully with ducking."""
        result = await use_case.start_capture()
        assert result == "capture-active"
        assert await use_case.is_recording() is True
        mock_volume_control_port.duck.assert_awaited_once()
        mock_state_management_port.set_global_state.assert_awaited_with("listening")
        mock_audio_capture_port.start_capture.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_capture_ducking_not_available(self, use_case, mock_volume_control_port):
        """Should start capture even if volume control is not available."""
        mock_volume_control_port.is_available.return_value = False
        result = await use_case.start_capture()
        assert result == "capture-active"
        mock_volume_control_port.duck.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_start_capture_already_recording(self, use_case):
        """Should raise AlreadyRecordingException when already recording."""
        await use_case.start_capture()
        with pytest.raises(AlreadyRecordingException):
            await use_case.start_capture()

    @pytest.mark.asyncio
    async def test_start_capture_microphone_unavailable(self, use_case, mock_audio_capture_port):
        """Should raise MicrophoneUnavailableException when mic not available."""
        mock_audio_capture_port.is_microphone_available.return_value = False
        with pytest.raises(MicrophoneUnavailableException):
            await use_case.start_capture()

    @pytest.mark.asyncio
    async def test_start_capture_ducking_fails(self, use_case, mock_volume_control_port):
        """Should raise VolumeControlFailedException when ducking fails."""
        mock_volume_control_port.duck.side_effect = Exception("PipeWire error")
        with pytest.raises(VolumeControlFailedException):
            await use_case.start_capture()

    @pytest.mark.asyncio
    async def test_start_capture_capture_fails(self, use_case, mock_audio_capture_port, mock_volume_control_port, mock_state_management_port):
        """Should restore volume and set idle on capture failure."""
        mock_audio_capture_port.start_capture.side_effect = Exception("Capture error")
        with pytest.raises(MicrophoneUnavailableException):
            await use_case.start_capture()
        mock_volume_control_port.restore.assert_awaited_once()
        mock_state_management_port.set_global_state.assert_awaited_with("idle")


class TestStopCapture:
    """Tests for stop_capture method."""

    @pytest.mark.asyncio
    async def test_stop_capture_success(self, use_case, mock_orchestrator_port, mock_volume_control_port, mock_state_management_port):
        """Should stop capture, restore volume, send to n8n, and set idle."""
        await use_case.start_capture()
        await use_case.stop_capture()

        assert await use_case.is_recording() is False
        mock_volume_control_port.restore.assert_awaited_once()
        mock_orchestrator_port.send_audio.assert_awaited_once()
        mock_state_management_port.set_global_state.assert_any_call("thinking")
        mock_state_management_port.set_global_state.assert_any_call("idle")

    @pytest.mark.asyncio
    async def test_stop_capture_not_recording(self, use_case):
        """Should raise NotRecordingException when not recording."""
        with pytest.raises(NotRecordingException):
            await use_case.stop_capture()

    @pytest.mark.asyncio
    async def test_stop_capture_n8n_fails(self, use_case, mock_orchestrator_port, mock_state_management_port):
        """Should set state to idle even if n8n fails."""
        mock_orchestrator_port.send_audio.return_value = False
        await use_case.start_capture()
        await use_case.stop_capture()

        mock_state_management_port.set_global_state.assert_any_call("idle")

    @pytest.mark.asyncio
    async def test_stop_capture_n8n_raises_exception(self, use_case, mock_orchestrator_port, mock_state_management_port):
        """Should handle n8n exceptions gracefully and set state to idle."""
        mock_orchestrator_port.send_audio.side_effect = Exception("Connection refused")
        await use_case.start_capture()
        await use_case.stop_capture()

        mock_state_management_port.set_global_state.assert_any_call("idle")


class TestIsRecording:
    """Tests for is_recording method."""

    @pytest.mark.asyncio
    async def test_is_recording_returns_false_initially(self, use_case):
        """Should return False when not recording."""
        assert await use_case.is_recording() is False

    @pytest.mark.asyncio
    async def test_is_recording_returns_true_after_start(self, use_case):
        """Should return True after starting capture."""
        await use_case.start_capture()
        assert await use_case.is_recording() is True

    @pytest.mark.asyncio
    async def test_is_recording_returns_false_after_stop(self, use_case):
        """Should return False after stopping capture."""
        await use_case.start_capture()
        await use_case.stop_capture()
        assert await use_case.is_recording() is False
