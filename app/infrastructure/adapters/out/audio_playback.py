"""Audio Playback Adapter.

Implements AudioPlaybackPort using ffplay (primary) or mpv (fallback)
to play audio files.
"""

import asyncio
import logging
import os

from app.domain.ports import AudioPlaybackPort
from app.domain.exceptions import (
    AudioFileNotFoundException,
    PlaybackFailedException,
)

logger = logging.getLogger(__name__)

PLAYBACK_TIMEOUT = 60  # seconds max for TTS playback


class AudioPlaybackAdapter(AudioPlaybackPort):
    """Audio playback adapter using ffplay as primary backend.

    Falls back to mpv if ffplay is not available.
    """

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None

    async def play(self, file_path: str) -> None:
        """Play an audio file synchronously (blocks until finished).

        Args:
            file_path: Absolute path to the audio file.

        Raises:
            AudioFileNotFoundException: If the file does not exist.
            PlaybackFailedException: If playback fails or times out.
        """
        # Check if file exists
        if not os.path.isfile(file_path):
            raise AudioFileNotFoundException(
                f"Audio file not found: {file_path}"
            )

        # Stop any existing playback
        await self.stop()

        backend = await self._detect_backend()
        if backend is None:
            raise PlaybackFailedException(
                "No playback backend available (ffplay or mpv)."
            )

        try:
            if backend == "ffplay":
                self._process = await asyncio.create_subprocess_exec(
                    "ffplay",
                    "-nodisp",              # No graphical window
                    "-autoexit",            # Exit when done
                    "-loglevel", "quiet",   # Minimal output
                    file_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                self._process = await asyncio.create_subprocess_exec(
                    "mpv",
                    "--no-video",           # No video window
                    "--really-quiet",       # Minimal output
                    file_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )

            logger.debug("Playback started for %s", file_path)

            # Wait for playback to finish with timeout
            try:
                await asyncio.wait_for(
                    self._process.wait(), timeout=PLAYBACK_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Playback timed out after %ds for %s",
                    PLAYBACK_TIMEOUT,
                    file_path,
                )
                await self.stop()
                raise PlaybackFailedException(
                    f"Playback timed out after {PLAYBACK_TIMEOUT}s."
                )

            if self._process.returncode != 0:
                _, stderr = await self._process.communicate()
                error_msg = stderr.decode(
                    "utf-8", errors="replace"
                ).strip()
                raise PlaybackFailedException(
                    f"Playback failed with code "
                    f"{self._process.returncode}: {error_msg}"
                )

        except (AudioFileNotFoundException, PlaybackFailedException):
            raise
        except FileNotFoundError:
            raise PlaybackFailedException(
                f"{backend} executable not found."
            )
        except Exception as e:
            raise PlaybackFailedException(
                f"Unexpected playback error: {e}"
            )
        finally:
            self._process = None

    async def stop(self) -> None:
        """Stop the current playback."""
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
            except Exception as e:
                logger.warning("Error stopping playback: %s", e)
            self._process = None

    async def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        if self._process is None:
            return False
        return self._process.returncode is None

    async def is_playback_available(self) -> bool:
        """Check if a playback backend is available."""
        backend = await self._detect_backend()
        return backend is not None

    async def _detect_backend(self) -> str | None:
        """Detect which playback backend is available.

        Returns 'ffplay', 'mpv', or None if none found.
        """
        for cmd in ["ffplay", "mpv"]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "which",
                    cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                return_code = await proc.wait()
                if return_code == 0:
                    return cmd
            except Exception:
                continue
        return None
