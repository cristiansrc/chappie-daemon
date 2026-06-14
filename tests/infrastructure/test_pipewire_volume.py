"""Tests for PipeWireVolumeAdapter.

Covers all branches including duck, restore, is_available,
_get_active_sinks, _get_sink_volume, and _set_sink_volume.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.adapters.out.pipewire_volume import (
    PipeWireVolumeAdapter,
)


def _make_mock_proc(
    returncode: int | None = 0,
    communicate_return: tuple[bytes, bytes] = (b"", b""),
) -> MagicMock:
    """Create a mock subprocess.Process-like object.

    ``kill()`` is a synchronous method on the real
    ``asyncio.subprocess.Process``.
    """
    proc = MagicMock()
    proc.kill.return_value = None
    proc.returncode = returncode
    proc.wait = AsyncMock(return_value=returncode or 0)
    proc.communicate = AsyncMock(return_value=communicate_return)
    return proc


@pytest.fixture
def adapter() -> PipeWireVolumeAdapter:
    """Create a PipeWireVolumeAdapter instance."""
    return PipeWireVolumeAdapter()


# =============================================================================
# is_available
# =============================================================================


class TestIsAvailable:
    """Tests for is_available method."""

    @pytest.mark.asyncio
    async def test_returns_true_when_wpctl_found(self, adapter):
        """Should return True when wpctl is available."""
        mock_proc = _make_mock_proc(returncode=0, communicate_return=(b"", b""))

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ) as mock_sub:
            result = await adapter.is_available()
            assert result is True
            mock_sub.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_wpctl_not_found(self, adapter):
        """Should return False when wpctl is not available."""
        mock_proc = _make_mock_proc(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self, adapter):
        """Should return False when subprocess raises exception."""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError(),
        ):
            result = await adapter.is_available()
            assert result is False


# =============================================================================
# _get_active_sinks
# =============================================================================


class TestGetActiveSinks:
    """Tests for _get_active_sinks method."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_timeout(self, adapter):
        """Should return empty list when wpctl status times out."""
        mock_proc = _make_mock_proc()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._get_active_sinks()
            assert result == []
            mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_parses_single_sink(self, adapter):
        """Should parse a single sink ID from wpctl output."""
        mock_proc = _make_mock_proc()
        output = (
            "PipeWire\n"
            " \u251c\u2500 Clients\n"
            " \u251c\u2500 Sinks:\n"
            " \u2502  \u2022 51.alsa_output.pci-0000_00_1f.3.analog-stereo\n"
            " \u251c\u2500 Sources:\n"
        )
        mock_proc.communicate.return_value = (output.encode("utf-8"), b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._get_active_sinks()
            assert result == ["51"]

    @pytest.mark.asyncio
    async def test_parses_multiple_sinks(self, adapter):
        """Should parse multiple sink IDs from wpctl output."""
        mock_proc = _make_mock_proc()
        output = (
            "PipeWire\n"
            " \u251c\u2500 Sinks:\n"
            " \u2502  \u2022 51.alsa_output.pci-0000_00_1f.3.analog-stereo\n"
            " \u2502  \u2022 52.alsa_output.usb-Bose-00.analog-stereo\n"
            " \u251c\u2500 Sources:\n"
        )
        mock_proc.communicate.return_value = (output.encode("utf-8"), b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._get_active_sinks()
            assert result == ["51", "52"]

    @pytest.mark.asyncio
    async def test_stops_at_next_section(self, adapter):
        """Should stop parsing when a new section is encountered."""
        mock_proc = _make_mock_proc()
        output = (
            "PipeWire\n"
            " \u251c\u2500 Sinks:\n"
            " \u2502  \u2022 51.alsa_output.pci-0000_00_1f.3.analog-stereo\n"
            " \u251c\u2500 Clients:\n"
            " \u2502  \u2022 100.pipewire\n"
        )
        mock_proc.communicate.return_value = (output.encode("utf-8"), b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._get_active_sinks()
            assert result == ["51"]

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_sinks(self, adapter):
        """Should return empty list when no sinks are in output."""
        mock_proc = _make_mock_proc()
        output = "PipeWire\n" " \u251c\u2500 Sources:\n"
        mock_proc.communicate.return_value = (output.encode("utf-8"), b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._get_active_sinks()
            assert result == []

    @pytest.mark.asyncio
    async def test_handles_exception(self, adapter):
        """Should return empty list on exception."""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=OSError("pipe broken"),
        ):
            result = await adapter._get_active_sinks()
            assert result == []


# =============================================================================
# _get_sink_volume
# =============================================================================


class TestGetSinkVolume:
    """Tests for _get_sink_volume method."""

    @pytest.mark.asyncio
    async def test_parses_volume_successfully(self, adapter):
        """Should parse volume from wpctl get-volume output."""
        mock_proc = _make_mock_proc(
            communicate_return=(b"Volume: 0.75\n", b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._get_sink_volume("51")
            assert result == 0.75

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self, adapter):
        """Should return None when get-volume times out."""
        mock_proc = _make_mock_proc()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._get_sink_volume("51")
            assert result is None
            mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_cannot_parse(self, adapter):
        """Should return None when volume cannot be parsed."""
        mock_proc = _make_mock_proc(
            communicate_return=(b"Volume: unknown\n", b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter._get_sink_volume("51")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self, adapter):
        """Should return None on unexpected exception."""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=OSError("pipe error"),
        ):
            result = await adapter._get_sink_volume("51")
            assert result is None


# =============================================================================
# _set_sink_volume
# =============================================================================


class TestSetSinkVolume:
    """Tests for _set_sink_volume method."""

    @pytest.mark.asyncio
    async def test_sets_volume_successfully(self, adapter):
        """Should set volume without error."""
        mock_proc = _make_mock_proc(returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            # Should not raise
            await adapter._set_sink_volume("51", 0.10)

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self, adapter):
        """Should raise RuntimeError when set-volume times out."""
        mock_proc = _make_mock_proc()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(RuntimeError) as exc:
                await adapter._set_sink_volume("51", 0.10)
            assert "timed out" in str(exc.value)
            mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_nonzero_returncode(self, adapter):
        """Should raise RuntimeError when wpctl returns non-zero."""
        mock_proc = _make_mock_proc(
            returncode=1,
            communicate_return=(b"", b"Volume not supported for this sink"),
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(RuntimeError) as exc:
                await adapter._set_sink_volume("51", 0.10)
            assert "wpctl set-volume failed" in str(exc.value)

    @pytest.mark.asyncio
    async def test_raises_on_exception(self, adapter):
        """Should re-raise unexpected exception from subprocess."""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError(),
        ):
            with pytest.raises(FileNotFoundError):
                await adapter._set_sink_volume("51", 0.10)


# =============================================================================
# duck
# =============================================================================


class TestDuck:
    """Tests for duck method."""

    @pytest.mark.asyncio
    async def test_duck_no_sinks(self, adapter):
        """Should return empty dict when no sinks available."""
        with patch.object(
            adapter, "_get_active_sinks", AsyncMock(return_value=[])
        ):
            result = await adapter.duck()
            assert result == {}

    @pytest.mark.asyncio
    async def test_duck_all_sinks_successfully(self, adapter):
        """Should duck all active sinks and return original volumes."""
        with patch.object(
            adapter, "_get_active_sinks", AsyncMock(return_value=["51", "52"])
        ):
            with patch.object(
                adapter,
                "_get_sink_volume",
                AsyncMock(side_effect=[0.75, 0.50]),
            ) as mock_get:
                with patch.object(
                    adapter, "_set_sink_volume", AsyncMock()
                ) as mock_set:
                    result = await adapter.duck()

        assert result == {"51": 0.75, "52": 0.50}
        assert mock_get.call_count == 2
        assert mock_set.call_count == 2
        mock_set.assert_any_call("51", 0.10)
        mock_set.assert_any_call("52", 0.10)

    @pytest.mark.asyncio
    async def test_duck_skips_sink_when_get_volume_none(self, adapter):
        """Should skip sink when get-volume returns None."""
        with patch.object(
            adapter, "_get_active_sinks", AsyncMock(return_value=["51"])
        ):
            with patch.object(
                adapter, "_get_sink_volume", AsyncMock(return_value=None)
            ):
                with patch.object(
                    adapter, "_set_sink_volume", AsyncMock()
                ) as mock_set:
                    result = await adapter.duck()

        assert result == {}
        mock_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_duck_logs_and_continues_on_exception(self, adapter):
        """Should log warning and continue when a sink fails."""
        with patch.object(
            adapter, "_get_active_sinks", AsyncMock(return_value=["51", "52"])
        ):
            with patch.object(
                adapter,
                "_get_sink_volume",
                AsyncMock(side_effect=[0.75, RuntimeError("device busy")]),
            ):
                with patch.object(
                    adapter, "_set_sink_volume", AsyncMock()
                ) as mock_set:
                    result = await adapter.duck()

        # First sink succeeded, second was skipped due to exception
        assert result == {"51": 0.75}
        mock_set.assert_called_once_with("51", 0.10)


# =============================================================================
# restore
# =============================================================================


class TestRestore:
    """Tests for restore method."""

    @pytest.mark.asyncio
    async def test_restore_empty_state(self, adapter):
        """Should not fail with empty state."""
        await adapter.restore({})

    @pytest.mark.asyncio
    async def test_restore_all_sinks_successfully(self, adapter):
        """Should restore all sinks to original volumes."""
        with patch.object(
            adapter, "_set_sink_volume", AsyncMock()
        ) as mock_set:
            await adapter.restore({"51": 0.75, "52": 0.50})

        assert mock_set.call_count == 2
        mock_set.assert_any_call("51", 0.75)
        mock_set.assert_any_call("52", 0.50)

    @pytest.mark.asyncio
    async def test_restore_logs_and_continues_on_exception(self, adapter):
        """Should log warning and continue when a sink restore fails."""
        mock_set = AsyncMock()
        mock_set.side_effect = [RuntimeError("failed"), None]

        with patch.object(adapter, "_set_sink_volume", mock_set):
            # Should not raise
            await adapter.restore({"51": 0.75, "52": 0.50})

        assert mock_set.call_count == 2
