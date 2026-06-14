"""Tests for PipeWireVolumeAdapter."""

from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.adapters.out.pipewire_volume import (
    PipeWireVolumeAdapter,
)


@pytest.fixture
def adapter() -> PipeWireVolumeAdapter:
    """Create a PipeWireVolumeAdapter instance."""
    return PipeWireVolumeAdapter()


class TestIsAvailable:
    """Tests for is_available method."""

    @pytest.mark.asyncio
    async def test_is_available_wpctl_found(self, adapter):
        """Should return True when wpctl is available."""
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 0

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ) as mock_subprocess:
            result = await adapter.is_available()
            assert result is True
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_available_wpctl_not_found(self, adapter):
        """Should return False when wpctl is not available."""
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await adapter.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_exception(self, adapter):
        """Should return False when subprocess raises exception."""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError(),
        ):
            result = await adapter.is_available()
            assert result is False


class TestDuck:
    """Tests for duck method."""

    @pytest.mark.asyncio
    async def test_duck_no_sinks(self, adapter):
        """Should return empty dict when no sinks available."""
        mock_proc_status = AsyncMock()
        mock_proc_status.communicate.return_value = (
            b"Sinks:\n",
            b"",
        )
        mock_proc_status.wait.return_value = 0

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_proc_status,
        ):
            result = await adapter.duck()
            assert result == {}


class TestRestore:
    """Tests for restore method."""

    @pytest.mark.asyncio
    async def test_restore_empty_state(self, adapter):
        """Should not fail with empty state."""
        await adapter.restore({})
        # No exception expected

    @pytest.mark.asyncio
    async def test_restore_exception_logged(self, adapter):
        """Should log warning on restore failure, not raise."""
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 1
        mock_proc.communicate.return_value = (b"", b"error".decode("utf-8").encode())

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            # Should not raise exception
            await adapter.restore({"sink_42": 0.75})
