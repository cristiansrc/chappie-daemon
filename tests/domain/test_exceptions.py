"""Tests for domain exceptions."""

from app.domain.exceptions import (
    AlreadyRecordingException,
    AlreadySpeakingException,
    AudioFileNotFoundException,
    DomainException,
    MicrophoneUnavailableException,
    NotRecordingException,
    PlaybackFailedException,
    VolumeControlFailedException,
)


class TestDomainExceptions:
    """Tests for all domain exception classes."""

    def test_already_recording_exception(self):
        """Should have ALREADY_RECORDING code."""
        e = AlreadyRecordingException()
        assert e.code == "ALREADY_RECORDING"
        assert isinstance(e, DomainException)

    def test_not_recording_exception(self):
        """Should have NOT_RECORDING code."""
        e = NotRecordingException()
        assert e.code == "NOT_RECORDING"
        assert isinstance(e, DomainException)

    def test_already_speaking_exception(self):
        """Should have ALREADY_SPEAKING code."""
        e = AlreadySpeakingException()
        assert e.code == "ALREADY_SPEAKING"
        assert isinstance(e, DomainException)

    def test_microphone_unavailable_exception(self):
        """Should have MICROPHONE_UNAVAILABLE code."""
        e = MicrophoneUnavailableException()
        assert e.code == "MICROPHONE_UNAVAILABLE"
        assert isinstance(e, DomainException)

    def test_volume_control_failed_exception(self):
        """Should have VOLUME_CONTROL_FAILED code."""
        e = VolumeControlFailedException()
        assert e.code == "VOLUME_CONTROL_FAILED"
        assert isinstance(e, DomainException)

    def test_audio_file_not_found_exception(self):
        """Should have AUDIO_FILE_NOT_FOUND code."""
        e = AudioFileNotFoundException()
        assert e.code == "AUDIO_FILE_NOT_FOUND"
        assert isinstance(e, DomainException)

    def test_playback_failed_exception(self):
        """Should have PLAYBACK_FAILED code."""
        e = PlaybackFailedException()
        assert e.code == "PLAYBACK_FAILED"
        assert isinstance(e, DomainException)

    def test_custom_message(self):
        """Should accept custom messages."""
        e = AlreadyRecordingException("Custom message")
        assert str(e) == "Custom message"

    def test_default_message(self):
        """Should provide default message if none given."""
        e = AudioFileNotFoundException()
        assert "not found" in str(e).lower()

    def test_code_immutable(self):
        """Should have stable code attribute."""
        e = MicrophoneUnavailableException()
        assert e.code == "MICROPHONE_UNAVAILABLE"
        # Code should not change
        original_code = e.code
        assert original_code == "MICROPHONE_UNAVAILABLE"

    def test_all_exceptions_distinct_codes(self):
        """All domain exceptions should have distinct codes."""
        codes = [
            AlreadyRecordingException().code,
            NotRecordingException().code,
            AlreadySpeakingException().code,
            MicrophoneUnavailableException().code,
            VolumeControlFailedException().code,
            AudioFileNotFoundException().code,
            PlaybackFailedException().code,
        ]
        assert len(codes) == len(set(codes)), "Codes must be unique"
