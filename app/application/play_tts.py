"""Play TTS Use Case.

Orchestrates the TTS playback flow:
ducking → state update → playback → volume restore → state update.
"""

import logging
import os

from app.domain import (
    AudioPlaybackPort,
    VolumeControlPort,
    StateManagementPort,
    TTSRequest,
)
from app.domain.exceptions import (
    AlreadySpeakingException,
    AudioFileNotFoundException,
    PlaybackFailedException,
    VolumeControlFailedException,
)

logger = logging.getLogger(__name__)


class PlayTTSUseCase:
    """Use case that handles TTS audio playback.

    Orchestrates ducking, state file updates, audio playback,
    and cleanup (volume restore, state reset).
    """

    def __init__(
        self,
        audio_playback_port: AudioPlaybackPort,
        volume_control_port: VolumeControlPort,
        state_management_port: StateManagementPort,
    ) -> None:
        self._audio_playback = audio_playback_port
        self._volume_control = volume_control_port
        self._state_management = state_management_port
        self._playing: bool = False
        self._pre_duck_state: dict = {}

    async def play(self, request: TTSRequest) -> None:
        """Play a TTS audio file.

        Steps:
        1. Check if already playing → raise AlreadySpeakingException
        2. Check if audio file exists → raise AudioFileNotFoundException
        3. If ducking enabled, apply volume ducking
        4. Update TTS state to 'speaking'
        5. Update global state to 'speaking'
        6. Play audio (blocks until finished)
        7. Restore volume (always, even on failure)
        8. Update both states to 'idle'

        Raises:
            AlreadySpeakingException: If already playing.
            AudioFileNotFoundException: If the audio file does not exist.
            VolumeControlFailedException: If ducking fails.
            PlaybackFailedException: If playback fails.
        """
        if self._playing:
            raise AlreadySpeakingException()

        # Check if audio file exists
        if not os.path.isfile(request.audio_file):
            raise AudioFileNotFoundException(
                f"Audio file not found: {request.audio_file}"
            )

        self._playing = True

        try:
            # Apply volume ducking if enabled
            if request.ducking:
                if await self._volume_control.is_available():
                    try:
                        self._pre_duck_state = await self._volume_control.duck()
                    except Exception as e:
                        logger.error("Volume ducking failed: %s", e)
                        raise VolumeControlFailedException(
                            "Failed to apply volume ducking."
                        )
                else:
                    logger.warning(
                        "Volume control not available, skipping ducking"
                    )

            # Update states to speaking
            await self._state_management.set_tts_state("speaking")
            await self._state_management.set_global_state("speaking")

            # Play audio (blocks until finished)
            try:
                await self._audio_playback.play(request.audio_file)
            except AudioFileNotFoundException:
                raise
            except Exception as e:
                logger.error("Audio playback failed: %s", e)
                raise PlaybackFailedException(
                    f"Failed to play audio: {e}"
                )

        finally:
            # Always restore volume and reset state
            await self._restore_volume()
            await self._state_management.set_tts_state("idle")
            await self._state_management.set_global_state("idle")
            self._playing = False

    async def is_playing(self) -> bool:
        """Check if audio is currently being played."""
        return self._playing

    async def _restore_volume(self) -> None:
        """Restore volume to pre-duck state (best-effort)."""
        if self._pre_duck_state:
            try:
                await self._volume_control.restore(self._pre_duck_state)
                self._pre_duck_state = {}
            except Exception as e:
                logger.warning("Failed to restore volume: %s", e)
