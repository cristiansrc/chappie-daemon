"""Handle Voice Capture Use Case.

Orchestrates the voice capture flow:
ducking → recording → volume restore → send to n8n.
"""

import logging
from datetime import datetime, timezone

from app.domain import (
    AudioCapturePort,
    VolumeControlPort,
    StateManagementPort,
    OrchestratorClientPort,
)
from app.domain.exceptions import (
    AlreadyRecordingException,
    MicrophoneUnavailableException,
    NotRecordingException,
    VolumeControlFailedException,
)

logger = logging.getLogger(__name__)


class HandleVoiceCaptureUseCase:
    """Use case that handles the full voice capture lifecycle.

    This includes ducking, recording, restoring volume, and sending
    audio to n8n for processing.
    """

    def __init__(
        self,
        audio_capture_port: AudioCapturePort,
        volume_control_port: VolumeControlPort,
        state_management_port: StateManagementPort,
        orchestrator_client_port: OrchestratorClientPort,
    ) -> None:
        self._audio_capture = audio_capture_port
        self._volume_control = volume_control_port
        self._state_management = state_management_port
        self._orchestrator = orchestrator_client_port
        self._recording: bool = False
        self._pre_duck_state: dict = {}

    async def start_capture(self) -> str:
        """Start a voice capture session.

        Steps:
        1. Check if already recording → raise AlreadyRecordingException
        2. Apply volume ducking (all sinks to 10%)
        3. Set state to 'listening'
        4. Start microphone capture

        Returns:
            The session_id for this capture session.

        Raises:
            AlreadyRecordingException: If already recording.
            VolumeControlFailedException: If ducking fails.
            MicrophoneUnavailableException: If mic is not available.
        """
        if self._recording:
            raise AlreadyRecordingException()

        # Check microphone availability
        if not await self._audio_capture.is_microphone_available():
            raise MicrophoneUnavailableException()

        # Apply volume ducking
        if await self._volume_control.is_available():
            try:
                self._pre_duck_state = await self._volume_control.duck()
            except Exception as e:
                logger.error("Volume ducking failed: %s", e)
                raise VolumeControlFailedException(
                    "Failed to apply volume ducking."
                )
        else:
            logger.warning("Volume control not available, skipping ducking")

        # Update state to listening
        await self._state_management.set_global_state("listening")

        # Start recording
        try:
            await self._audio_capture.start_capture()
        except Exception as e:
            # Restore volume on capture failure
            await self._restore_volume()
            await self._state_management.set_global_state("idle")
            logger.error("Failed to start capture: %s", e)
            raise MicrophoneUnavailableException(
                "Failed to start microphone capture."
            )

        self._recording = True
        logger.info("Voice capture started")
        return "capture-active"

    async def stop_capture(self) -> None:
        """Stop the current voice capture session.

        Steps:
        1. Check if recording → raise NotRecordingException
        2. Stop capture and get AudioCapture
        3. Restore original volume
        4. Set state to 'thinking'
        5. Send audio to n8n with retry policy
        6. Update state to 'idle' (handled in send flow)

        Raises:
            NotRecordingException: If not currently recording.
        """
        if not self._recording:
            raise NotRecordingException()

        self._recording = False

        # Stop capture
        try:
            audio_capture = await self._audio_capture.stop_capture()
            audio_capture.timestamp = datetime.now(timezone.utc)
        except Exception as e:
            logger.error("Failed to stop capture: %s", e)
            await self._restore_volume()
            await self._state_management.set_global_state("idle")
            return

        # Restore volume (best-effort)
        await self._restore_volume()

        # Update state to thinking
        await self._state_management.set_global_state("thinking")

        # Send to n8n (retry policy handled by adapter)
        try:
            success = await self._orchestrator.send_audio(audio_capture)
        except Exception as e:
            logger.error(
                "Failed to send audio to n8n (session=%s): %s",
                audio_capture.session_id,
                e,
            )
            success = False

        if success:
            logger.info(
                "Audio sent to n8n successfully (session=%s)",
                audio_capture.session_id,
            )
        else:
            logger.error(
                "Failed to send audio to n8n (session=%s)",
                audio_capture.session_id,
            )

        # Always set state back to idle after sending (success or failure)
        await self._state_management.set_global_state("idle")

    async def is_recording(self) -> bool:
        """Check if a capture session is currently active."""
        return self._recording

    async def _restore_volume(self) -> None:
        """Restore volume to pre-duck state (best-effort)."""
        if self._pre_duck_state:
            try:
                await self._volume_control.restore(self._pre_duck_state)
                self._pre_duck_state = {}
            except Exception as e:
                logger.warning("Failed to restore volume: %s", e)


