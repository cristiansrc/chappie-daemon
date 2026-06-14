"""Tests for domain ports (abstract base classes)."""

from app.domain.ports import (
    AudioCapturePort,
    AudioPlaybackPort,
    OrchestratorClientPort,
    ShortcutDetectionPort,
    StateManagementPort,
    VolumeControlPort,
)


class TestPortsAreAbstract:
    """Verify all ports are ABCs that require implementation."""

    def test_audio_capture_port_cannot_be_instantiated(self):
        """Should raise TypeError when instantiating AudioCapturePort."""
        try:
            AudioCapturePort()  # type: ignore
            assert False, "Should have raised TypeError"
        except TypeError as e:
            assert "Can't instantiate abstract class" in str(e)

    def test_audio_playback_port_cannot_be_instantiated(self):
        """Should raise TypeError when instantiating AudioPlaybackPort."""
        try:
            AudioPlaybackPort()  # type: ignore
            assert False, "Should have raised TypeError"
        except TypeError as e:
            assert "Can't instantiate abstract class" in str(e)

    def test_volume_control_port_cannot_be_instantiated(self):
        """Should raise TypeError when instantiating VolumeControlPort."""
        try:
            VolumeControlPort()  # type: ignore
            assert False, "Should have raised TypeError"
        except TypeError as e:
            assert "Can't instantiate abstract class" in str(e)

    def test_shortcut_detection_port_cannot_be_instantiated(self):
        """Should raise TypeError when instantiating ShortcutDetectionPort."""
        try:
            ShortcutDetectionPort()  # type: ignore
            assert False, "Should have raised TypeError"
        except TypeError as e:
            assert "Can't instantiate abstract class" in str(e)

    def test_state_management_port_cannot_be_instantiated(self):
        """Should raise TypeError when instantiating StateManagementPort."""
        try:
            StateManagementPort()  # type: ignore
            assert False, "Should have raised TypeError"
        except TypeError as e:
            assert "Can't instantiate abstract class" in str(e)

    def test_orchestrator_client_port_cannot_be_instantiated(self):
        """Should raise TypeError when instantiating OrchestratorClientPort."""
        try:
            OrchestratorClientPort()  # type: ignore
            assert False, "Should have raised TypeError"
        except TypeError as e:
            assert "Can't instantiate abstract class" in str(e)
