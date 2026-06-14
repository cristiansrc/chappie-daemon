"""Tests for AudioCaptureAdapter.

Covers all branches including start_capture, stop_capture,
is_microphone_available, _is_arecord_available, and cleanup.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.exceptions import MicrophoneUnavailableException
from app.domain.models import AudioCapture
from app.infrastructure.adapters.out.audio_capture import (
    AudioCaptureAdapter,
    CAPTURE_FILE,
)

# Reusable constants
FAKE_AUDIO_DATA = b"fake_audio_data"
TEST_SESSION = "test-session-123"


def _make_mock_process(
    returncode: int | None = 0,
    wait_return: int = 0,
) -> MagicMock:
    """Create a mock subprocess.Process-like object.

    ``terminate()`` and ``kill()`` are synchronous methods
    (like the real asyncio.subprocess.Process), while
    ``wait()`` and ``communicate()`` are async coroutines.
    """
    proc = MagicMock()
    proc.terminate.return_value = None
    proc.kill.return_value = None
    proc.returncode = returncode
    proc.wait = AsyncMock(return_value=wait_return)
    proc.communicate = AsyncMock(return_value=(b"", b""))
    return proc


@pytest.fixture
def adapter() -> AudioCaptureAdapter:
    """Create an AudioCaptureAdapter instance."""
    return AudioCaptureAdapter()


def _mock_file_read(data: bytes = FAKE_AUDIO_DATA) -> MagicMock:
    """Create a mock for open() context manager."""
    mock_file = MagicMock()
    mock_file.read.return_value = data
    mock_file.__enter__.return_value = mock_file
    return mock_file


# =============================================================================
# _is_arecord_available
# =============================================================================


class TestIsArecordAvailable:
    """Tests for _is_arecord_available method."""

    @pytest.mark.asyncio
    async def test_arecord_found(self, adapter):
        """Should return True when which arecord succeeds."""
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._is_arecord_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_arecord_not_found(self, adapter):
        """Should return False when which arecord fails."""
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._is_arecord_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_arecord_check_exception(self, adapter):
        """Should return False when which raises."""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError(),
        ):
            result = await adapter._is_arecord_available()
            assert result is False


# =============================================================================
# is_microphone_available
# =============================================================================


class TestIsMicrophoneAvailable:
    """Tests for is_microphone_available method."""

    @pytest.mark.asyncio
    async def test_arecord_found_and_list_success(self, adapter):
        """Should return True when arecord is available and -l returns 0."""
        mock_which = AsyncMock()
        mock_which.wait.return_value = 0
        mock_list = AsyncMock()
        mock_list.wait.return_value = 0

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=[mock_which, mock_list],
        ) as mock_exec:
            result = await adapter.is_microphone_available()
            assert result is True
            assert mock_exec.call_count == 2

    @pytest.mark.asyncio
    async def test_arecord_found_but_no_devices(self, adapter):
        """Should return False when arecord -l returns non-zero."""
        mock_which = AsyncMock()
        mock_which.wait.return_value = 0
        mock_list = AsyncMock()
        mock_list.wait.return_value = 1

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=[mock_which, mock_list],
        ):
            result = await adapter.is_microphone_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_arecord_list_raises_exception(self, adapter):
        """Should return False when arecord -l raises."""
        mock_which = AsyncMock()
        mock_which.wait.return_value = 0

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=[mock_which, OSError("pipe error")],
        ):
            result = await adapter.is_microphone_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_arecord_missing_pyaudio_finds_input_device(self, adapter):
        """Should return True via pyaudio when arecord missing."""
        mock_which = AsyncMock()
        mock_which.wait.return_value = 1

        mock_pyaudio_module = MagicMock()
        mock_py_audio_instance = MagicMock()
        mock_pyaudio_module.PyAudio.return_value = mock_py_audio_instance
        mock_py_audio_instance.get_device_count.return_value = 3
        mock_py_audio_instance.get_device_info_by_index.side_effect = [
            {"maxInputChannels": 0},
            {"maxInputChannels": 0},
            {"maxInputChannels": 2},  # Found input device
        ]

        with patch("asyncio.create_subprocess_exec", return_value=mock_which):
            with patch.dict(
                "sys.modules", {"pyaudio": mock_pyaudio_module}
            ):
                result = await adapter.is_microphone_available()
                assert result is True
                mock_py_audio_instance.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_arecord_missing_pyaudio_no_input_device(self, adapter):
        """Should return False when pyaudio finds no input device."""
        mock_which = AsyncMock()
        mock_which.wait.return_value = 1

        mock_pyaudio_module = MagicMock()
        mock_py_audio_instance = MagicMock()
        mock_pyaudio_module.PyAudio.return_value = mock_py_audio_instance
        mock_py_audio_instance.get_device_count.return_value = 2
        mock_py_audio_instance.get_device_info_by_index.side_effect = [
            {"maxInputChannels": 0},
            {"maxInputChannels": 0},
        ]

        with patch("asyncio.create_subprocess_exec", return_value=mock_which):
            with patch.dict(
                "sys.modules", {"pyaudio": mock_pyaudio_module}
            ):
                result = await adapter.is_microphone_available()
                assert result is False
                mock_py_audio_instance.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_arecord_missing_pyaudio_not_installed(self, adapter):
        """Should return False when pyaudio is not installed."""
        # pyaudio is not installed in this venv, so import raises ImportError
        mock_which = AsyncMock()
        mock_which.wait.return_value = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_which):
            # Temporarily remove pyaudio from sys.modules cache to ensure
            # the import inside the method triggers ImportError
            import sys as _sys

            cached = _sys.modules.pop("pyaudio", None)
            try:
                result = await adapter.is_microphone_available()
                assert result is False
            finally:
                if cached is not None:
                    _sys.modules["pyaudio"] = cached

    @pytest.mark.asyncio
    async def test_arecord_missing_pyaudio_raises_exception(self, adapter):
        """Should return False when pyaudio raises unexpected error."""
        mock_which = AsyncMock()
        mock_which.wait.return_value = 1

        mock_pyaudio_module = MagicMock()
        mock_pyaudio_module.PyAudio.side_effect = RuntimeError("no audio")

        with patch("asyncio.create_subprocess_exec", return_value=mock_which):
            with patch.dict(
                "sys.modules", {"pyaudio": mock_pyaudio_module}
            ):
                result = await adapter.is_microphone_available()
                assert result is False

    @pytest.mark.asyncio
    async def test_is_microphone_available_exception_safe(self, adapter):
        """Should not raise exception even on unexpected subprocess error."""
        with patch(
            "asyncio.create_subprocess_exec", side_effect=FileNotFoundError()
        ):
            result = await adapter.is_microphone_available()
            assert result is False


# =============================================================================
# start_capture
# =============================================================================


class TestStartCapture:
    """Tests for start_capture method."""

    @pytest.mark.asyncio
    async def test_start_capture_microphone_not_available(self, adapter):
        """Should raise when mic not available."""
        with patch.object(
            adapter, "is_microphone_available", AsyncMock(return_value=False)
        ):
            with pytest.raises(MicrophoneUnavailableException):
                await adapter.start_capture()

    @pytest.mark.asyncio
    async def test_start_capture_success(self, adapter):
        """Should start capture process successfully."""
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 0

        with patch.object(
            adapter, "is_microphone_available", AsyncMock(return_value=True)
        ):
            with patch("os.access", return_value=True):
                with patch("os.path.exists", return_value=False):
                    with patch(
                        "asyncio.create_subprocess_exec", return_value=mock_proc
                    ) as mock_sub:
                        await adapter.start_capture()
                        assert adapter._process is not None
                        mock_sub.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_capture_temp_dir_not_writable(self, adapter):
        """Should raise when temp dir is not writable."""
        with patch.object(
            adapter, "is_microphone_available", AsyncMock(return_value=True)
        ):
            with patch("os.access", return_value=False):
                with pytest.raises(MicrophoneUnavailableException) as exc:
                    await adapter.start_capture()
                assert "Cannot write" in str(exc.value)

    @pytest.mark.asyncio
    async def test_start_capture_removes_previous_file(self, adapter):
        """Should remove previous capture file if it exists."""
        with patch.object(
            adapter, "is_microphone_available", AsyncMock(return_value=True)
        ):
            mock_proc = AsyncMock()
            mock_proc.wait.return_value = 0

            with patch("os.access", return_value=True):
                with patch("os.path.exists", return_value=True):
                    with patch("os.remove") as mock_remove:
                        with patch(
                            "asyncio.create_subprocess_exec", return_value=mock_proc
                        ):
                            await adapter.start_capture()
                            mock_remove.assert_called_once_with(CAPTURE_FILE)

    @pytest.mark.asyncio
    async def test_start_capture_previous_remove_fails_logged(self, adapter):
        """Should log warning (not raise) when removing previous file fails."""
        with patch.object(
            adapter, "is_microphone_available", AsyncMock(return_value=True)
        ):
            mock_proc = AsyncMock()
            mock_proc.wait.return_value = 0

            with patch("os.access", return_value=True):
                with patch("os.path.exists", return_value=True):
                    with patch("os.remove", side_effect=OSError("permission")):
                        with patch(
                            "asyncio.create_subprocess_exec", return_value=mock_proc
                        ):
                            await adapter.start_capture()
                            assert adapter._process is not None

    @pytest.mark.asyncio
    async def test_start_capture_arecord_not_found(self, adapter):
        """Should raise when arecord binary not found."""
        with patch.object(
            adapter, "is_microphone_available", AsyncMock(return_value=True)
        ):
            with patch("os.access", return_value=True):
                with patch("os.path.exists", return_value=False):
                    with patch(
                        "asyncio.create_subprocess_exec",
                        side_effect=FileNotFoundError(),
                    ):
                        with pytest.raises(MicrophoneUnavailableException) as exc:
                            await adapter.start_capture()
                        assert adapter._process is None
                        assert "arecord not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_start_capture_generic_exception(self, adapter):
        """Should raise MicrophoneUnavailableException on generic error."""
        with patch.object(
            adapter, "is_microphone_available", AsyncMock(return_value=True)
        ):
            with patch("os.access", return_value=True):
                with patch("os.path.exists", return_value=False):
                    with patch(
                        "asyncio.create_subprocess_exec",
                        side_effect=PermissionError("denied"),
                    ):
                        with pytest.raises(MicrophoneUnavailableException):
                            await adapter.start_capture()
                        assert adapter._process is None


# =============================================================================
# stop_capture
# =============================================================================


class TestStopCapture:
    """Tests for stop_capture method."""

    @pytest.fixture
    def adapter_with_process(self, adapter) -> AudioCaptureAdapter:
        """Set up adapter with a mock running process."""
        adapter._process = _make_mock_process(returncode=0, wait_return=0)
        adapter._session_id = TEST_SESSION
        return adapter

    @pytest.mark.asyncio
    async def test_stop_capture_no_process(self, adapter):
        """Should raise when no capture in progress."""
        with pytest.raises(MicrophoneUnavailableException):
            await adapter.stop_capture()

    @pytest.mark.asyncio
    async def test_stop_capture_success(self, adapter_with_process):
        """Should stop capture and return AudioCapture."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", return_value=_mock_file_read()) as mock_open:
                with patch("os.remove") as mock_remove:
                    result = await adapter_with_process.stop_capture()

        assert isinstance(result, AudioCapture)
        assert result.audio_data == FAKE_AUDIO_DATA
        assert result.session_id == TEST_SESSION
        assert adapter_with_process._process is None
        mock_open.assert_called_once_with(CAPTURE_FILE, "rb")
        mock_remove.assert_called_once_with(CAPTURE_FILE)

    @pytest.mark.asyncio
    async def test_stop_capture_process_timeout_kills(self, adapter_with_process):
        """Should kill process when terminate times out."""
        mock_proc = adapter_with_process._process
        mock_proc.wait = AsyncMock(
            side_effect=[asyncio.TimeoutError(), None]
        )

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", return_value=_mock_file_read()):
                with patch("os.remove"):
                    result = await adapter_with_process.stop_capture()

        assert isinstance(result, AudioCapture)
        assert adapter_with_process._process is None
        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_capture_terminate_exception(self, adapter_with_process):
        """Should handle exception during terminate gracefully."""
        adapter_with_process._process.terminate.side_effect = OSError("fail")

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", return_value=_mock_file_read()):
                with patch("os.remove"):
                    result = await adapter_with_process.stop_capture()

        assert isinstance(result, AudioCapture)
        assert adapter_with_process._process is None

    @pytest.mark.asyncio
    async def test_stop_capture_file_not_found(self, adapter_with_process):
        """Should raise when capture file missing after recording."""
        with patch("os.path.exists", return_value=False):
            with pytest.raises(MicrophoneUnavailableException) as exc:
                await adapter_with_process.stop_capture()
            assert "Capture file not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_stop_capture_read_error(self, adapter_with_process):
        """Should raise when capture file cannot be read."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", side_effect=OSError("read error")):
                with pytest.raises(MicrophoneUnavailableException) as exc:
                    await adapter_with_process.stop_capture()
                assert "Failed to read capture file" in str(exc.value)

    @pytest.mark.asyncio
    async def test_stop_capture_remove_failure_logged(self, adapter_with_process):
        """Should not raise when removal of temp file fails."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", return_value=_mock_file_read()):
                with patch("os.remove", side_effect=OSError("remove failed")):
                    result = await adapter_with_process.stop_capture()

        assert isinstance(result, AudioCapture)


# =============================================================================
# cleanup
# =============================================================================


class TestCleanup:
    """Tests for cleanup method."""

    @pytest.mark.asyncio
    async def test_cleanup_no_process(self, adapter):
        """Should not fail when no process is running."""
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_terminates_process(self, adapter):
        """Should terminate running process."""
        mock_proc = _make_mock_process(returncode=0, wait_return=0)
        adapter._process = mock_proc

        with patch("os.path.exists", return_value=False):
            await adapter.cleanup()

        mock_proc.terminate.assert_called_once()
        assert adapter._process is None

    @pytest.mark.asyncio
    async def test_cleanup_process_timeout_kills(self, adapter):
        """Should kill process when terminate times out."""
        mock_proc = _make_mock_process(returncode=None)
        mock_proc.wait = AsyncMock(
            side_effect=[asyncio.TimeoutError(), None]
        )
        adapter._process = mock_proc

        with patch("os.path.exists", return_value=False):
            await adapter.cleanup()

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()
        assert adapter._process is None

    @pytest.mark.asyncio
    async def test_cleanup_terminate_exception(self, adapter):
        """Should not raise when terminate raises."""
        mock_proc = _make_mock_process(returncode=0, wait_return=0)
        mock_proc.terminate.side_effect = OSError("fail")
        adapter._process = mock_proc

        with patch("os.path.exists", return_value=False):
            await adapter.cleanup()

        assert adapter._process is None

    @pytest.mark.asyncio
    async def test_cleanup_removes_capture_file(self, adapter):
        """Should remove capture file if it exists."""
        mock_proc = _make_mock_process(returncode=0, wait_return=0)
        adapter._process = mock_proc

        with patch("os.path.exists", return_value=True):
            with patch("os.remove") as mock_remove:
                await adapter.cleanup()
                mock_remove.assert_called_once_with(CAPTURE_FILE)

    @pytest.mark.asyncio
    async def test_cleanup_remove_failure_logged(self, adapter):
        """Should not raise when file removal fails."""
        mock_proc = _make_mock_process(returncode=0, wait_return=0)
        adapter._process = mock_proc

        with patch("os.path.exists", return_value=True):
            with patch("os.remove", side_effect=OSError("denied")):
                await adapter.cleanup()
