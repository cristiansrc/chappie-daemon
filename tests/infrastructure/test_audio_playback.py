"""Tests for AudioPlaybackAdapter.

Covers all branches including play, stop, is_playing,
is_playback_available, and _detect_backend.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.exceptions import (
    AudioFileNotFoundException,
    PlaybackFailedException,
)
from app.infrastructure.adapters.out.audio_playback import (
    AudioPlaybackAdapter,
    PLAYBACK_TIMEOUT,
)


def _make_mock_process(
    returncode: int | None = 0,
    wait_return: int = 0,
) -> MagicMock:
    """Create a mock subprocess.Process-like object."""
    proc = MagicMock()
    proc.terminate.return_value = None
    proc.kill.return_value = None
    proc.returncode = returncode
    proc.wait = AsyncMock(return_value=wait_return)
    proc.communicate = AsyncMock(return_value=(b"", b""))
    return proc


@pytest.fixture
def adapter() -> AudioPlaybackAdapter:
    """Create an AudioPlaybackAdapter instance."""
    return AudioPlaybackAdapter()


@pytest.fixture
def audio_file(tmp_path) -> str:
    """Create a temporary audio file and return its path."""
    path = tmp_path / "test_audio.wav"
    path.write_bytes(b"fake_audio_content")
    return str(path)


# =============================================================================
# _detect_backend
# =============================================================================


class TestDetectBackend:
    """Tests for _detect_backend method."""

    @pytest.mark.asyncio
    async def test_detects_ffplay_first(self, adapter):
        """Should return 'ffplay' when ffplay is available."""
        mock_ffplay = AsyncMock()
        mock_ffplay.wait.return_value = 0

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_ffplay
        ) as mock_exec:
            result = await adapter._detect_backend()
            assert result == "ffplay"
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_detects_mpv_fallback(self, adapter):
        """Should return 'mpv' when ffplay missing but mpv available."""
        mock_ffplay = AsyncMock()
        mock_ffplay.wait.return_value = 1
        mock_mpv = AsyncMock()
        mock_mpv.wait.return_value = 0

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=[mock_ffplay, mock_mpv],
        ):
            result = await adapter._detect_backend()
            assert result == "mpv"

    @pytest.mark.asyncio
    async def test_no_backend_available(self, adapter):
        """Should return None when neither ffplay nor mpv is found."""
        mock_fail = AsyncMock()
        mock_fail.wait.return_value = 1

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=[mock_fail, mock_fail],
        ):
            result = await adapter._detect_backend()
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self, adapter):
        """Should return None when which raises."""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError(),
        ):
            result = await adapter._detect_backend()
            assert result is None


# =============================================================================
# is_playback_available
# =============================================================================


class TestIsPlaybackAvailable:
    """Tests for is_playback_available method."""

    @pytest.mark.asyncio
    async def test_returns_true_when_backend_found(self, adapter):
        """Should return True when a backend is detected."""
        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value="ffplay")
        ):
            result = await adapter.is_playback_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_backend(self, adapter):
        """Should return False when no backend is available."""
        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value=None)
        ):
            result = await adapter.is_playback_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_handles_exception(self, adapter):
        """Should propagate exception from _detect_backend."""
        with patch.object(
            adapter,
            "_detect_backend",
            AsyncMock(side_effect=RuntimeError("unexpected")),
        ):
            with pytest.raises(RuntimeError):
                await adapter.is_playback_available()


# =============================================================================
# play
# =============================================================================


class TestPlay:
    """Tests for play method."""

    @pytest.mark.asyncio
    async def test_play_file_not_found(self, adapter):
        """Should raise AudioFileNotFoundException for nonexistent file."""
        with pytest.raises(AudioFileNotFoundException):
            await adapter.play("/tmp/nonexistent_file.wav")

    @pytest.mark.asyncio
    async def test_play_no_backend(self, adapter, audio_file):
        """Should raise PlaybackFailedException when no backend."""
        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value=None)
        ):
            with pytest.raises(PlaybackFailedException) as exc:
                await adapter.play(audio_file)
            assert "No playback backend" in str(exc.value)

    @pytest.mark.asyncio
    async def test_play_success_with_ffplay(self, adapter, audio_file):
        """Should play with ffplay and complete successfully."""
        mock_proc = _make_mock_process(returncode=0, wait_return=0)

        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value="ffplay")
        ):
            with patch(
                "asyncio.create_subprocess_exec", return_value=mock_proc
            ) as mock_exec:
                await adapter.play(audio_file)

        assert adapter._process is None
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert args[0] == "ffplay"

    @pytest.mark.asyncio
    async def test_play_success_with_mpv(self, adapter, audio_file):
        """Should play with mpv and complete successfully."""
        mock_proc = _make_mock_process(returncode=0, wait_return=0)

        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value="mpv")
        ):
            with patch(
                "asyncio.create_subprocess_exec", return_value=mock_proc
            ) as mock_exec:
                await adapter.play(audio_file)

        assert adapter._process is None
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert args[0] == "mpv"

    @pytest.mark.asyncio
    async def test_play_timeout(self, adapter, audio_file):
        """Should raise PlaybackFailedException when playback times out."""
        mock_proc = _make_mock_process(returncode=None)
        mock_proc.wait = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value="ffplay")
        ):
            with patch(
                "asyncio.create_subprocess_exec", return_value=mock_proc
            ):
                with pytest.raises(PlaybackFailedException) as exc:
                    await adapter.play(audio_file)
                assert "timed out" in str(exc.value)

        assert adapter._process is None

    @pytest.mark.asyncio
    async def test_play_nonzero_returncode(self, adapter, audio_file):
        """Should raise PlaybackFailedException when return code != 0."""
        mock_proc = _make_mock_process(returncode=1, wait_return=0)
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"Error: device busy")
        )

        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value="ffplay")
        ):
            with patch(
                "asyncio.create_subprocess_exec", return_value=mock_proc
            ):
                with pytest.raises(PlaybackFailedException) as exc:
                    await adapter.play(audio_file)
                assert "returncode 1" in str(exc.value) or "Error" in str(
                    exc.value
                )

    @pytest.mark.asyncio
    async def test_play_backend_not_found(self, adapter, audio_file):
        """Should raise when backend executable not found."""
        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value="ffplay")
        ):
            with patch(
                "asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError(),
            ):
                with patch.object(
                    adapter, "stop", AsyncMock()
                ):
                    with pytest.raises(PlaybackFailedException) as exc:
                        await adapter.play(audio_file)
                    assert "executable not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_play_unexpected_exception(self, adapter, audio_file):
        """Should raise when unexpected error occurs."""
        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value="ffplay")
        ):
            with patch(
                "asyncio.create_subprocess_exec",
                side_effect=PermissionError("access denied"),
            ):
                with patch.object(
                    adapter, "stop", AsyncMock()
                ):
                    with pytest.raises(PlaybackFailedException) as exc:
                        await adapter.play(audio_file)
                    assert "Unexpected playback error" in str(exc.value)

    @pytest.mark.asyncio
    async def test_play_exception_re_raised(self, adapter, audio_file):
        """Should re-raise PlaybackFailedException from backend."""
        with patch.object(
            adapter, "_detect_backend", AsyncMock(return_value="ffplay")
        ):
            with patch(
                "asyncio.create_subprocess_exec",
                side_effect=PlaybackFailedException("backend error"),
            ):
                with patch.object(
                    adapter, "stop", AsyncMock()
                ):
                    with pytest.raises(PlaybackFailedException):
                        await adapter.play(audio_file)


# =============================================================================
# stop
# =============================================================================


class TestStop:
    """Tests for stop method."""

    @pytest.mark.asyncio
    async def test_stop_no_process(self, adapter):
        """Should not fail when no process is running."""
        await adapter.stop()

    @pytest.mark.asyncio
    async def test_stop_terminates_process(self, adapter):
        """Should terminate running process."""
        mock_proc = _make_mock_process(returncode=0, wait_return=0)
        adapter._process = mock_proc

        await adapter.stop()

        mock_proc.terminate.assert_called_once()
        assert adapter._process is None

    @pytest.mark.asyncio
    async def test_stop_timeout_then_kill(self, adapter):
        """Should kill process when terminate times out."""
        mock_proc = _make_mock_process(returncode=None)
        mock_proc.wait = AsyncMock(
            side_effect=[asyncio.TimeoutError(), None]
        )
        adapter._process = mock_proc

        await adapter.stop()

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()
        assert adapter._process is None

    @pytest.mark.asyncio
    async def test_stop_exception_logged(self, adapter):
        """Should handle exceptions during stop gracefully."""
        mock_proc = _make_mock_process(returncode=0, wait_return=0)
        mock_proc.terminate.side_effect = OSError("fail")
        adapter._process = mock_proc

        await adapter.stop()

        assert adapter._process is None


# =============================================================================
# is_playing
# =============================================================================


class TestIsPlaying:
    """Tests for is_playing method."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_process(self, adapter):
        """Should return False when no playback process exists."""
        assert await adapter.is_playing() is False

    @pytest.mark.asyncio
    async def test_returns_true_when_process_running(self, adapter):
        """Should return True when process is still running."""
        mock_proc = _make_mock_process(returncode=None)
        adapter._process = mock_proc

        assert await adapter.is_playing() is True

    @pytest.mark.asyncio
    async def test_returns_false_when_process_completed(self, adapter):
        """Should return False when process has completed."""
        mock_proc = _make_mock_process(returncode=0)
        adapter._process = mock_proc

        assert await adapter.is_playing() is False
