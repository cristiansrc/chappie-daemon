"""Tests for domain models."""

from datetime import datetime, timezone

from app.domain.models import AudioCapture, SystemState, TTSRequest


class TestTTSRequest:
    """Tests for TTSRequest domain model."""

    def test_create_with_required_fields(self):
        """Should create TTSRequest with only required fields."""
        request = TTSRequest(
            audio_file="/tmp/test.mp3",
            text="Hello world",
        )
        assert request.audio_file == "/tmp/test.mp3"
        assert request.text == "Hello world"
        assert request.ducking is True  # default

    def test_create_with_ducking_false(self):
        """Should create TTSRequest with ducking disabled."""
        request = TTSRequest(
            audio_file="/tmp/test.mp3",
            text="Hello",
            ducking=False,
        )
        assert request.ducking is False

    def test_create_with_all_fields(self):
        """Should create TTSRequest with all fields."""
        request = TTSRequest(
            audio_file="/tmp/test.mp3",
            text="Test",
            ducking=False,
        )
        assert request.audio_file == "/tmp/test.mp3"
        assert request.text == "Test"
        assert request.ducking is False


class TestAudioCapture:
    """Tests for AudioCapture domain model."""

    def test_create_with_minimal_fields(self):
        """Should create AudioCapture with audio_data and timestamp."""
        now = datetime.now(timezone.utc)
        capture = AudioCapture(
            audio_data=b"audio_data",
            timestamp=now,
        )
        assert capture.audio_data == b"audio_data"
        assert capture.timestamp == now
        assert capture.session_id is not None  # auto-generated UUID

    def test_create_with_all_fields(self):
        """Should create AudioCapture with all fields specified."""
        now = datetime.now(timezone.utc)
        capture = AudioCapture(
            audio_data=b"data",
            timestamp=now,
            session_id="custom-session",
        )
        assert capture.session_id == "custom-session"

    def test_session_id_unique(self):
        """Should generate unique session IDs."""
        now = datetime.now(timezone.utc)
        capture1 = AudioCapture(audio_data=b"a", timestamp=now)
        capture2 = AudioCapture(audio_data=b"b", timestamp=now)
        assert capture1.session_id != capture2.session_id

    def test_audio_data_bytes_type(self):
        """Should store audio data as bytes."""
        now = datetime.now(timezone.utc)
        capture = AudioCapture(
            audio_data=b"\x00\x01\x02",
            timestamp=now,
        )
        assert isinstance(capture.audio_data, bytes)
        assert len(capture.audio_data) == 3


class TestSystemState:
    """Tests for SystemState enum."""

    def test_has_all_states(self):
        """Should have all required states."""
        states = [s.value for s in SystemState]
        assert "idle" in states
        assert "listening" in states
        assert "thinking" in states
        assert "working" in states
        assert "speaking" in states

    def test_idle_is_default(self):
        """Should be able to reference idle state."""
        assert SystemState.IDLE.value == "idle"

    def test_transition_order(self):
        """Should allow comparison between states."""
        assert SystemState.IDLE != SystemState.LISTENING
        assert SystemState.SPEAKING == SystemState.SPEAKING
