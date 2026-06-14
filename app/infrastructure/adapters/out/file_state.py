"""File State Adapter.

Implements StateManagementPort by writing state files in /tmp/
for reading by chappie-quickshell.
"""

import asyncio
import logging
import os
import tempfile

from app.domain.ports import StateManagementPort

logger = logging.getLogger(__name__)

# File paths
GLOBAL_STATE_FILE = "/tmp/chappie_state.txt"
TTS_STATE_FILE = "/tmp/chappie_tts_state.txt"
TEXT_ENABLED_FILE = "/tmp/chappie_text_enabled.txt"

# Valid states
VALID_GLOBAL_STATES = {
    "idle", "listening", "thinking", "working", "speaking"
}
VALID_TTS_STATES = {"speaking", "idle"}


class FileStateAdapter(StateManagementPort):
    """State management adapter using files in /tmp/.

    All file operations are best-effort: failures are logged but
    do not raise exceptions (the daemon should not crash due to
    state file write errors).
    """

    async def set_global_state(self, state: str) -> None:
        """Write the global state to /tmp/chappie_state.txt.

        Args:
            state: One of: idle, listening, thinking, working, speaking.

        Raises:
            ValueError: If the state is not valid.
        """
        if state not in VALID_GLOBAL_STATES:
            raise ValueError(
                f"Invalid global state: {state}. "
                f"Valid values: {', '.join(sorted(VALID_GLOBAL_STATES))}"
            )
        await self._atomic_write(GLOBAL_STATE_FILE, state)

    async def set_tts_state(self, state: str) -> None:
        """Write the TTS state to /tmp/chappie_tts_state.txt.

        Args:
            state: Either 'speaking' or 'idle'.

        Raises:
            ValueError: If the state is not valid.
        """
        if state not in VALID_TTS_STATES:
            raise ValueError(
                f"Invalid TTS state: {state}. "
                f"Valid values: {', '.join(sorted(VALID_TTS_STATES))}"
            )
        await self._atomic_write(TTS_STATE_FILE, state)

    async def set_text_enabled(self, enabled: bool) -> None:
        """Write the text enabled flag to /tmp/chappie_text_enabled.txt.

        Args:
            enabled: True to enable text display, False to disable.
        """
        value = "true" if enabled else "false"
        await self._atomic_write(TEXT_ENABLED_FILE, value)

    async def get_global_state(self) -> str:
        """Read the global state from /tmp/chappie_state.txt.

        Returns "idle" if the file does not exist.
        """
        return await self._read_with_default(GLOBAL_STATE_FILE, "idle")

    async def get_tts_state(self) -> str:
        """Read the TTS state from /tmp/chappie_tts_state.txt.

        Returns "idle" if the file does not exist.
        """
        return await self._read_with_default(TTS_STATE_FILE, "idle")

    async def _atomic_write(self, file_path: str, content: str) -> None:
        """Write content to a file atomically using temp + rename.

        Best-effort: logs errors but does not raise exceptions.
        """
        try:
            # Create parent directory if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            # Write to temp file and rename atomically
            fd, tmp_path = tempfile.mkstemp(
                dir=parent_dir or "/tmp",
                prefix=".chappie_",
                suffix=".tmp",
            )
            try:
                os.write(fd, content.encode("utf-8"))
            finally:
                os.close(fd)

            os.chmod(tmp_path, 0o644)
            os.replace(tmp_path, file_path)
        except OSError as e:
            logger.warning(
                "Failed to write state file %s: %s", file_path, e
            )

    async def _read_with_default(
        self, file_path: str, default: str
    ) -> str:
        """Read a file's content, returning default if file doesn't exist.

        Args:
            file_path: Path to the file to read.
            default: Value to return if file doesn't exist.

        Returns:
            File content (stripped) or default value.
        """
        try:
            loop = asyncio.get_running_loop()

            def _read() -> str:
                try:
                    with open(file_path, "r") as f:
                        content = f.read().strip()
                        return content if content else default
                except FileNotFoundError:
                    return default
                except OSError as e:
                    logger.warning(
                        "Failed to read state file %s: %s",
                        file_path,
                        e,
                    )
                    return default

            return await loop.run_in_executor(None, _read)
        except Exception as e:
            logger.warning(
                "Unexpected error reading %s: %s", file_path, e
            )
            return default
