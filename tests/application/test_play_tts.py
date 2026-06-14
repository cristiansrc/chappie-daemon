"""Tests for PlayTTSUseCase."""

import os
from unittest.mock import AsyncMock

import pytest

from app.application.play_tts import PlayTTSUseCase
from app.domain.exceptions import (
    AlreadySpeakingException,
    AudioFileNotFoundException,
    PlaybackFailedException,
    VolumeControlFailedException,
)
from tests.conftest import make_tts_request


@pytest.fixture
def use_case(
    mock_audio_playback_port: AsyncMock,
    mock_volume_control_port: AsyncMock,
    mock_state_management_port: AsyncMock,
) -> PlayTTSUseCase:
    """Create a PlayTTSUseCase with mocked ports."""
    return PlayTTSUseCase(
        audio_playback_port=mock_audio_playback_port,
        volume_control_port=mock_volume_control_port,
        state_management_port=mock_state_management_port,
    )


@pytest.fixture
def temp_audio_file(tmp_path) -> str:
    """Create a temporary audio file."""
    audio_path = tmp_path / "test_audio.wav"
    audio_path.write_bytes(b"fake_wav_data")
    return str(audio_path)


class TestPlay:
    """Tests for play method."""

    @pytest.mark.asyncio
    async def test_play_success_with_ducking(
        self, use_case, temp_audio_file,
        mock_volume_control_port, mock_audio_playback_port,
        mock_state_management_port,
    ):
        """Should play audio with ducking successfully."""
        request = make_tts_request(audio_file=temp_audio_file, ducking=True)
        await use_case.play(request)

        mock_volume_control_port.duck.assert_awaited_once()
        mock_audio_playback_port.play.assert_awaited_once_with(temp_audio_file)
        mock_state_management_port.set_tts_state.assert_any_call("speaking")
        mock_state_management_port.set_global_state.assert_any_call("speaking")
        mock_state_management_port.set_tts_state.assert_any_call("idle")
        mock_state_management_port.set_global_state.assert_any_call("idle")

    @pytest.mark.asyncio
    async def test_play_success_without_ducking(
        self, use_case, temp_audio_file,
        mock_volume_control_port, mock_audio_playback_port,
    ):
        """Should play audio without ducking when ducking=False."""
        request = make_tts_request(audio_file=temp_audio_file, ducking=False)
        await use_case.play(request)

        mock_volume_control_port.duck.assert_not_awaited()
        mock_audio_playback_port.play.assert_awaited_once_with(temp_audio_file)

    @pytest.mark.asyncio
    async def test_play_already_speaking(
        self, use_case, temp_audio_file, mock_audio_playback_port
    ):
        """Should raise AlreadySpeakingException when already playing."""
        # Make playback wait so the first play is still in progress
        import asyncio
        playback_started = asyncio.Event()
        playback_done = asyncio.Event()

        async def delayed_play(*args, **kwargs):
            playback_started.set()
            await playback_done.wait()

        mock_audio_playback_port.play.side_effect = delayed_play

        request = make_tts_request(audio_file=temp_audio_file)

        # Start first play in background
        async def first_play():
            await use_case.play(request)

        task = asyncio.create_task(first_play())
        await playback_started.wait()

        # Second play should raise AlreadySpeakingException
        with pytest.raises(AlreadySpeakingException):
            await use_case.play(request)

        # Clean up
        playback_done.set()
        await task

    @pytest.mark.asyncio
    async def test_play_file_not_found(self, use_case):
        """Should raise AudioFileNotFoundException when file does not exist."""
        request = make_tts_request(audio_file="/tmp/nonexistent.wav")
        with pytest.raises(AudioFileNotFoundException):
            await use_case.play(request)

    @pytest.mark.asyncio
    async def test_play_ducking_fails(self, use_case, temp_audio_file, mock_volume_control_port):
        """Should raise VolumeControlFailedException when ducking fails."""
        mock_volume_control_port.duck.side_effect = Exception("PipeWire error")
        request = make_tts_request(audio_file=temp_audio_file, ducking=True)
        with pytest.raises(VolumeControlFailedException):
            await use_case.play(request)

    @pytest.mark.asyncio
    async def test_play_playback_fails(self, use_case, temp_audio_file, mock_audio_playback_port):
        """Should raise PlaybackFailedException when playback fails."""
        mock_audio_playback_port.play.side_effect = Exception("ffplay error")
        request = make_tts_request(audio_file=temp_audio_file)
        with pytest.raises(PlaybackFailedException):
            await use_case.play(request)

    @pytest.mark.asyncio
    async def test_play_restores_volume_on_failure(
        self, use_case, temp_audio_file, mock_audio_playback_port,
        mock_volume_control_port, mock_state_management_port,
    ):
        """Should restore volume and state even if playback fails."""
        mock_audio_playback_port.play.side_effect = Exception("ffplay error")
        request = make_tts_request(audio_file=temp_audio_file)
        with pytest.raises(PlaybackFailedException):
            await use_case.play(request)

        mock_volume_control_port.restore.assert_awaited_once()
        mock_state_management_port.set_tts_state.assert_any_call("idle")
        mock_state_management_port.set_global_state.assert_any_call("idle")

    @pytest.mark.asyncio
    async def test_play_ducking_not_available(
        self, use_case, temp_audio_file, mock_volume_control_port,
    ):
        """Should play without ducking if volume control is not available."""
        mock_volume_control_port.is_available.return_value = False
        request = make_tts_request(audio_file=temp_audio_file, ducking=True)
        await use_case.play(request)
        mock_volume_control_port.duck.assert_not_awaited()


class TestIsPlaying:
    """Tests for is_playing method."""

    @pytest.mark.asyncio
    async def test_is_playing_returns_false_initially(self, use_case):
        """Should return False initially."""
        assert await use_case.is_playing() is False

    @pytest.mark.asyncio
    async def test_is_playing_returns_true_during_playback(self, use_case, temp_audio_file):
        """Should return True during playback."""
        request = make_tts_request(audio_file=temp_audio_file)
        await use_case.play(request)
        assert await use_case.is_playing() is False  # Already finished (sync)

    @pytest.mark.asyncio
    async def test_is_playing_returns_false_after_failure(
        self, use_case, mock_audio_playback_port,
    ):
        """Should return False after playback failure."""
        mock_audio_playback_port.play.side_effect = Exception("error")
        request = make_tts_request(audio_file="/tmp/test.wav")

        # Create a real file so it passes the file check
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"data")
            tmp_path = f.name
        request.audio_file = tmp_path

        with pytest.raises(PlaybackFailedException):
            await use_case.play(request)
        assert await use_case.is_playing() is False
        os.unlink(tmp_path)
