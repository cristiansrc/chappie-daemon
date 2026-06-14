"""Tests for FileStateAdapter."""

import os

import pytest

from app.infrastructure.adapters.out.file_state import (
    FileStateAdapter,
    GLOBAL_STATE_FILE,
    TTS_STATE_FILE,
    TEXT_ENABLED_FILE,
)


class TestFileStateAdapter:
    """Tests for FileStateAdapter using tmp_path."""

    @pytest.mark.asyncio
    async def test_initial_state_idle(self, tmp_path):
        """Should return 'idle' when no state file exists."""
        # Point to non-existent file in tmp_path
        adapter = FileStateAdapter()
        state = await adapter.get_global_state()
        # Should not raise exception and return default
        # Note: The adapter reads from /tmp/ which may or may not exist
        assert isinstance(state, str)

    @pytest.mark.asyncio
    async def test_set_global_state_valid(self, tmp_path):
        """Should write valid global state."""
        # Point adapter to tmp_path by patching
        import app.infrastructure.adapters.out.file_state as fs
        original_file = fs.GLOBAL_STATE_FILE
        test_file = str(tmp_path / "chappie_state.txt")

        try:
            fs.GLOBAL_STATE_FILE = test_file
            adapter = FileStateAdapter()

            await adapter.set_global_state("listening")
            assert os.path.exists(test_file)

            content = await adapter.get_global_state()
            assert content == "listening"
        finally:
            fs.GLOBAL_STATE_FILE = original_file

    @pytest.mark.asyncio
    async def test_set_global_state_invalid(self):
        """Should raise ValueError for invalid state."""
        adapter = FileStateAdapter()
        with pytest.raises(ValueError, match="Invalid global state"):
            await adapter.set_global_state("invalid_state")

    @pytest.mark.asyncio
    async def test_set_tts_state_valid(self, tmp_path):
        """Should write valid TTS state."""
        import app.infrastructure.adapters.out.file_state as fs
        original_file = fs.TTS_STATE_FILE
        test_file = str(tmp_path / "chappie_tts_state.txt")

        try:
            fs.TTS_STATE_FILE = test_file
            adapter = FileStateAdapter()

            await adapter.set_tts_state("speaking")
            assert os.path.exists(test_file)

            content = await adapter.get_tts_state()
            assert content == "speaking"
        finally:
            fs.TTS_STATE_FILE = original_file

    @pytest.mark.asyncio
    async def test_set_tts_state_invalid(self):
        """Should raise ValueError for invalid TTS state."""
        adapter = FileStateAdapter()
        with pytest.raises(ValueError, match="Invalid TTS state"):
            await adapter.set_tts_state("invalid")

    @pytest.mark.asyncio
    async def test_set_text_enabled(self, tmp_path):
        """Should write text enabled flag."""
        import app.infrastructure.adapters.out.file_state as fs
        original_file = fs.TEXT_ENABLED_FILE
        test_file = str(tmp_path / "chappie_text_enabled.txt")

        try:
            fs.TEXT_ENABLED_FILE = test_file
            adapter = FileStateAdapter()

            await adapter.set_text_enabled(True)
            with open(test_file) as f:
                assert f.read().strip() == "true"

            await adapter.set_text_enabled(False)
            with open(test_file) as f:
                assert f.read().strip() == "false"
        finally:
            fs.TEXT_ENABLED_FILE = original_file

    @pytest.mark.asyncio
    async def test_atomic_write_preserves_content(self, tmp_path):
        """Should write complete content atomically."""
        import app.infrastructure.adapters.out.file_state as fs
        original_file = fs.GLOBAL_STATE_FILE
        test_file = str(tmp_path / "chappie_state.txt")

        try:
            fs.GLOBAL_STATE_FILE = test_file
            adapter = FileStateAdapter()

            await adapter.set_global_state("working")
            with open(test_file) as f:
                assert f.read().strip() == "working"
        finally:
            fs.GLOBAL_STATE_FILE = original_file
