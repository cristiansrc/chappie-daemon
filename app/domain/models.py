"""Domain models for Chappie Daemon.

These are pure domain models with no dependencies on frameworks,
ORM, or infrastructure concerns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class SystemState(str, Enum):
    """Represents the possible states of the Chappie system."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    WORKING = "working"
    SPEAKING = "speaking"


@dataclass
class TTSRequest:
    """A request to play a Text-to-Speech audio file.

    Attributes:
        audio_file: Absolute path to the audio file to play.
        text: Text being spoken (for logging/state).
        ducking: Whether to apply volume ducking during playback.
    """

    audio_file: str
    text: str
    ducking: bool = True


@dataclass
class AudioCapture:
    """Captured audio data from the microphone.

    Attributes:
        audio_data: Raw bytes of the captured audio (WAV format).
        timestamp: UTC timestamp when the capture was stopped.
        session_id: Unique identifier for this capture session.
    """

    audio_data: bytes
    timestamp: datetime
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
