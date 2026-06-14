"""Tests for AudioPlaybackAdapter."""

from unittest.mock import AsyncMock, patch

import pytest

from app.domain.exceptions import (
    AudioFileNotFoundException,
    PlaybackFailedException,
)
from app.infrastructure.adapters.out.audio_playback import (
    AudioPlaybackAdapter,
)


@pytest.fixture
def adapter() -> AudioPlaybackAdapter:
    """Create an AudioPlaybackAdapter instance."""
    return AudioPlaybackAdapter()


class TestIsPlaybackAvailable:
    """Tests for is_playback_available method."""

    @pytest.mark.asyncio
    async def test_no_backend_available(self, adapter):
        """Should return False when no backend is available."""
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter.is_playback_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_exception_handling(self, adapter):
        """Should return False on exception."""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError(),
        ):
            result = await adapter.is_playback_available()
            assert result is False


class TestPlay:
    """Tests for play method."""

    @pytest.mark.asyncio
    async def test_play_file_not_found(self, adapter):
        """Should raise AudioFileNotFoundException for nonexistent file."""
        with pytest.raises(AudioFileNotFoundException):
            await adapter.play("/tmp/nonexistent_file.wav")

    @pytest.mark.asyncio
    async def test_play_no_backend(self, adapter, tmp_path):
        """Should raise PlaybackFailedException when no backend available."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"data")

        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 1
        mock_proc.communicate.return_value = (b"", b"")

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=[mock_proc, mock_proc],
        ):
            with pytest.raises(PlaybackFailedException):
                await adapter.play(str(audio_file))


class TestStop:
    """Tests for stop method."""

    @pytest.mark.asyncio
    async def test_stop_no_process(self, adapter):
        """Should not fail when no process is running."""
        await adapter.stop()
        # No exception expected


class TestIsPlaying:
    """Tests for is_playing method."""

    @pytest.mark.asyncio
    async def test_is_playing_no_process(self, adapter):
        """Should return False when no playback process exists."""
        assert await adapter.is_playing() is False
