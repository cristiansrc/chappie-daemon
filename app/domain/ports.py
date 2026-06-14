"""Domain ports (interfaces) for Chappie Daemon.

These are abstract base classes that define the contracts
between the application core and the outside world.
All ports use async methods where I/O is involved.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict

from app.domain.models import AudioCapture, TTSRequest


class AudioCapturePort(ABC):
    """Port for capturing audio from the microphone."""

    @abstractmethod
    async def start_capture(self) -> None:
        """Start recording audio from the microphone."""
        ...

    @abstractmethod
    async def stop_capture(self) -> AudioCapture:
        """Stop recording and return captured audio data."""
        ...

    @abstractmethod
    async def is_microphone_available(self) -> bool:
        """Check if the microphone is available for capture."""
        ...


class AudioPlaybackPort(ABC):
    """Port for playing audio files."""

    @abstractmethod
    async def play(self, file_path: str) -> None:
        """Play an audio file synchronously (blocks until finished)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the current playback."""
        ...

    @abstractmethod
    async def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        ...

    @abstractmethod
    async def is_playback_available(self) -> bool:
        """Check if the playback backend is available."""
        ...


class VolumeControlPort(ABC):
    """Port for controlling system volume (ducking)."""

    @abstractmethod
    async def duck(self) -> Dict[str, float]:
        """Reduce all active sinks to 10% volume.

        Returns:
            A dict mapping sink IDs to their original volume levels,
            to be used later for restoration.
        """
        ...

    @abstractmethod
    async def restore(self, state: Dict[str, float]) -> None:
        """Restore sinks to their original volume levels.

        Args:
            state: The dict returned by duck() with original volumes.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the volume control backend is available."""
        ...


class ShortcutDetectionPort(ABC):
    """Port for detecting global shortcut presses.

    NOTE: This port is intentionally left without a concrete adapter.
    Shortcut detection is delegated to the Hyprland compositor, which
    calls the HTTP endpoints directly.
    """

    @abstractmethod
    async def on_shortcut_press(self) -> None:
        """Called when the global shortcut is pressed."""
        ...

    @abstractmethod
    async def on_shortcut_release(self) -> None:
        """Called when the global shortcut is released."""
        ...


class StateManagementPort(ABC):
    """Port for managing Chappie state files in /tmp/."""

    @abstractmethod
    async def set_global_state(self, state: str) -> None:
        """Write the global state to /tmp/chappie_state.txt.

        Valid states: idle, listening, thinking, working, speaking.
        """
        ...

    @abstractmethod
    async def set_tts_state(self, state: str) -> None:
        """Write the TTS state to /tmp/chappie_tts_state.txt.

        Valid states: speaking, idle.
        """
        ...

    @abstractmethod
    async def set_text_enabled(self, enabled: bool) -> None:
        """Write the text enabled flag to /tmp/chappie_text_enabled.txt."""
        ...

    @abstractmethod
    async def get_global_state(self) -> str:
        """Read the global state from /tmp/chappie_state.txt.

        Returns "idle" if the file does not exist.
        """
        ...

    @abstractmethod
    async def get_tts_state(self) -> str:
        """Read the TTS state from /tmp/chappie_tts_state.txt.

        Returns "idle" if the file does not exist.
        """
        ...


class OrchestratorClientPort(ABC):
    """Port for sending captured audio to n8n orchestrator."""

    @abstractmethod
    async def send_audio(self, audio: AudioCapture) -> bool:
        """Send captured audio to the n8n orchestrator.

        Returns:
            True if the audio was sent successfully, False otherwise.
        """
        ...
