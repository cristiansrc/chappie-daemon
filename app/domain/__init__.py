# Domain Layer

from app.domain.models import AudioCapture, TTSRequest, SystemState
from app.domain.ports import (
    AudioCapturePort,
    AudioPlaybackPort,
    VolumeControlPort,
    ShortcutDetectionPort,
    StateManagementPort,
    OrchestratorClientPort,
)
from app.domain.exceptions import (
    AlreadyRecordingException,
    NotRecordingException,
    AlreadySpeakingException,
    MicrophoneUnavailableException,
    VolumeControlFailedException,
    AudioFileNotFoundException,
    PlaybackFailedException,
)

__all__ = [
    # Models
    "AudioCapture",
    "TTSRequest",
    "SystemState",
    # Ports
    "AudioCapturePort",
    "AudioPlaybackPort",
    "VolumeControlPort",
    "ShortcutDetectionPort",
    "StateManagementPort",
    "OrchestratorClientPort",
    # Exceptions
    "AlreadyRecordingException",
    "NotRecordingException",
    "AlreadySpeakingException",
    "MicrophoneUnavailableException",
    "VolumeControlFailedException",
    "AudioFileNotFoundException",
    "PlaybackFailedException",
]
