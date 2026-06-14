"""Tests for AudioCaptureAdapter."""

from unittest.mock import AsyncMock, patch

import pytest

from app.domain.exceptions import MicrophoneUnavailableException
from app.infrastructure.adapters.out.audio_capture import (
    AudioCaptureAdapter,
    CAPTURE_FILE,
)


@pytest.fixture
def adapter() -> AudioCaptureAdapter:
    """Create an AudioCaptureAdapter instance."""
    return AudioCaptureAdapter()


class TestIsMicrophoneAvailable:
    """Tests for is_microphone_available method."""

    @pytest.mark.asyncio
    async def test_not_available_no_arecord(self, adapter):
        """Should return False when arecord is not available."""
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch.object(adapter, "_is_arecord_available", AsyncMock(return_value=False)):
                result = await adapter.is_microphone_available()
                assert result is False

    @pytest.mark.asyncio
    async def test_is_microphone_available_exception_safe(self, adapter):
        """Should not raise exception even on error."""
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            result = await adapter.is_microphone_available()
            assert result is False


class TestStartCapture:
    """Tests for start_capture method."""

    @pytest.mark.asyncio
    async def test_start_capture_microphone_not_available(self, adapter):
        """Should raise MicrophoneUnavailableException when mic not available."""
        with patch.object(adapter, "is_microphone_available", AsyncMock(return_value=False)):
            with pytest.raises(MicrophoneUnavailableException):
                await adapter.start_capture()

    @pytest.mark.asyncio
    async def test_start_capture_success(self, adapter):
        """Should start capture process successfully."""
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 0

        with patch.object(adapter, "is_microphone_available", AsyncMock(return_value=True)):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                await adapter.start_capture()
                assert adapter._process is not None

    @pytest.mark.asyncio
    async def test_start_capture_cleanup_previous(self, adapter):
        """Should remove previous capture file if it exists."""
        import os
        # Create a dummy capture file
        with open(CAPTURE_FILE, "w") as f:
            f.write("old_data")

        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 0

        with patch.object(adapter, "is_microphone_available", AsyncMock(return_value=True)):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                await adapter.start_capture()
                assert not os.path.exists(CAPTURE_FILE) or os.path.getsize(CAPTURE_FILE) == 0

        # Cleanup
        if os.path.exists(CAPTURE_FILE):
            os.remove(CAPTURE_FILE)


class TestCleanup:
    """Tests for cleanup method."""

    @pytest.mark.asyncio
    async def test_cleanup_no_process(self, adapter):
        """Should not fail when no process is running."""
        await adapter.cleanup()
        # No exception expected
