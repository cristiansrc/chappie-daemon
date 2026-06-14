"""Domain exceptions for Chappie Daemon.

Each exception carries a stable `code` attribute that can be mapped
to HTTP error codes by the infrastructure layer.
"""


class DomainException(Exception):
    """Base class for all domain exceptions."""

    def __init__(self, message: str = "", code: str = ""):
        self.code = code
        super().__init__(message or self._default_message())

    def _default_message(self) -> str:
        """Return a default message based on the exception code."""
        messages = {
            "ALREADY_RECORDING": "Already recording audio.",
            "NOT_RECORDING": "No recording in progress.",
            "ALREADY_SPEAKING": "Already speaking.",
            "MICROPHONE_UNAVAILABLE": "Microphone is not available.",
            "VOLUME_CONTROL_FAILED": "Volume control failed.",
            "AUDIO_FILE_NOT_FOUND": "Audio file not found.",
            "PLAYBACK_FAILED": "Audio playback failed.",
        }
        return messages.get(self.code, "An unexpected domain error occurred.")


class AlreadyRecordingException(DomainException):
    """Raised when trying to start a capture while one is already in progress."""

    def __init__(self, message: str = ""):
        super().__init__(message=message, code="ALREADY_RECORDING")


class NotRecordingException(DomainException):
    """Raised when trying to stop a capture when none is in progress."""

    def __init__(self, message: str = ""):
        super().__init__(message=message, code="NOT_RECORDING")


class AlreadySpeakingException(DomainException):
    """Raised when trying to play TTS while already speaking."""

    def __init__(self, message: str = ""):
        super().__init__(message=message, code="ALREADY_SPEAKING")


class MicrophoneUnavailableException(DomainException):
    """Raised when the microphone is not available."""

    def __init__(self, message: str = ""):
        super().__init__(message=message, code="MICROPHONE_UNAVAILABLE")


class VolumeControlFailedException(DomainException):
    """Raised when volume ducking or restoration fails."""

    def __init__(self, message: str = ""):
        super().__init__(message=message, code="VOLUME_CONTROL_FAILED")


class AudioFileNotFoundException(DomainException):
    """Raised when the TTS audio file does not exist."""

    def __init__(self, message: str = ""):
        super().__init__(message=message, code="AUDIO_FILE_NOT_FOUND")


class PlaybackFailedException(DomainException):
    """Raised when audio playback fails."""

    def __init__(self, message: str = ""):
        super().__init__(message=message, code="PLAYBACK_FAILED")
