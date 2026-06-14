"""Audio Capture Adapter.

Implements AudioCapturePort using arecord (primary) or pyaudio (fallback)
to capture microphone audio.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

from app.domain.models import AudioCapture
from app.domain.ports import AudioCapturePort
from app.domain.exceptions import MicrophoneUnavailableException

logger = logging.getLogger(__name__)

CAPTURE_FILE = "/tmp/chappie_capture.wav"


class AudioCaptureAdapter(AudioCapturePort):
    """Audio capture adapter using arecord as primary backend.

    Falls back to pyaudio if arecord is not available.
    """

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._session_id: str = ""

    async def start_capture(self) -> None:
        """Start recording audio from the microphone.

        Raises:
            MicrophoneUnavailableException: If mic is not available.
        """
        if not await self.is_microphone_available():
            raise MicrophoneUnavailableException(
                "No microphone backend available."
            )

        self._session_id = str(uuid.uuid4())

        # Ensure temp file directory is writable
        temp_dir = os.path.dirname(CAPTURE_FILE)
        if not os.access(temp_dir, os.W_OK):
            raise MicrophoneUnavailableException(
                f"Cannot write to {temp_dir}"
            )

        # Remove previous capture file if it exists
        if os.path.exists(CAPTURE_FILE):
            try:
                os.remove(CAPTURE_FILE)
            except OSError as e:
                logger.warning("Failed to remove previous capture: %s", e)

        try:
            self._process = await asyncio.create_subprocess_exec(
                "arecord",
                "-f", "cd",      # CD quality: 16-bit, 44100 Hz, stereo
                "-t", "wav",     # WAV format
                CAPTURE_FILE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            logger.info(
                "Audio capture started (session=%s)", self._session_id
            )
        except FileNotFoundError:
            self._process = None
            raise MicrophoneUnavailableException(
                "arecord not found on the system."
            )
        except Exception as e:
            self._process = None
            raise MicrophoneUnavailableException(
                f"Failed to start audio capture: {e}"
            )

    async def stop_capture(self) -> AudioCapture:
        """Stop recording and return captured audio data.

        Returns:
            AudioCapture with audio_data, timestamp, and session_id.

        Raises:
            MicrophoneUnavailableException: If no capture was started.
        """
        if self._process is None:
            raise MicrophoneUnavailableException("No capture in progress.")

        # Stop the recording process
        try:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("arecord did not terminate, killing...")
                self._process.kill()
                await self._process.wait()
        except Exception as e:
            logger.warning("Error stopping capture process: %s", e)

        self._process = None

        # Read the captured audio data
        if not os.path.exists(CAPTURE_FILE):
            raise MicrophoneUnavailableException(
                "Capture file not found after recording."
            )

        try:
            with open(CAPTURE_FILE, "rb") as f:
                audio_data = f.read()
        except OSError as e:
            raise MicrophoneUnavailableException(
                f"Failed to read capture file: {e}"
            )

        # Clean up the temp file
        try:
            os.remove(CAPTURE_FILE)
        except OSError as e:
            logger.warning("Failed to remove capture file: %s", e)

        return AudioCapture(
            audio_data=audio_data,
            timestamp=datetime.now(timezone.utc),
            session_id=self._session_id,
        )

    async def is_microphone_available(self) -> bool:
        """Check if microphone is available.

        Checks for arecord or pyaudio availability and tries to
        detect a microphone device.

        Returns:
            True if a microphone is available.
        """
        # Check if arecord is installed
        if await self._is_arecord_available():
            # Quick check if any capture devices are available
            try:
                proc = await asyncio.create_subprocess_exec(
                    "arecord",
                    "-l",  # List devices
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                return_code = await proc.wait()
                return return_code == 0
            except Exception:
                return False

        # Try pyaudio as fallback
        try:
            import pyaudio  # type: ignore[import-untyped]

            p = pyaudio.PyAudio()
            try:
                device_count = p.get_device_count()
                for i in range(device_count):
                    info = p.get_device_info_by_index(i)
                    if info.get("maxInputChannels", 0) > 0:
                        return True
                return False
            finally:
                p.terminate()
        except ImportError:
            return False
        except Exception as e:
            logger.warning("pyaudio check failed: %s", e)
            return False

    async def _is_arecord_available(self) -> bool:
        """Check if arecord is available on the system."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "which",
                "arecord",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return_code = await proc.wait()
            return return_code == 0
        except Exception:
            return False

    async def cleanup(self) -> None:
        """Clean up any active capture process."""
        if self._process is not None:
            try:
                self._process.terminate()
                try:
                    await asyncio.wait_for(
                        self._process.wait(), timeout=5.0
                    )
                except asyncio.TimeoutError:
                    self._process.kill()
                    await self._process.wait()
            except Exception:
                pass
            self._process = None

        if os.path.exists(CAPTURE_FILE):
            try:
                os.remove(CAPTURE_FILE)
            except OSError:
                pass
