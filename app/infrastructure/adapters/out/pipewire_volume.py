"""PipeWire Volume Adapter.

Implements VolumeControlPort using wpctl (PipeWire) commands
via asyncio subprocess.
"""

import asyncio
import logging
import re
from typing import Dict

from app.domain.ports import VolumeControlPort

logger = logging.getLogger(__name__)

WPDTL_COMMAND_TIMEOUT = 5  # seconds per wpctl command


class PipeWireVolumeAdapter(VolumeControlPort):
    """Volume control adapter using PipeWire's wpctl command.

    Reduces all active sinks to 10% volume (ducking) and restores
    original volumes afterwards.
    """

    async def duck(self) -> Dict[str, float]:
        """Reduce all active sinks to 10% volume.

        Returns:
            Dict mapping sink IDs to their original volume levels.
        """
        sinks = await self._get_active_sinks()
        original_state: Dict[str, float] = {}

        for sink_id in sinks:
            try:
                original_volume = await self._get_sink_volume(sink_id)
                if original_volume is not None:
                    original_state[sink_id] = original_volume
                    await self._set_sink_volume(sink_id, 0.10)
                    logger.debug(
                        "Ducked sink %s from %.2f to 0.10",
                        sink_id,
                        original_volume,
                    )
            except Exception as e:
                logger.warning(
                    "Failed to duck sink %s: %s", sink_id, e
                )

        return original_state

    async def restore(self, state: Dict[str, float]) -> None:
        """Restore sinks to their original volume levels.

        Args:
            state: Dict mapping sink IDs to original volumes.
        """
        for sink_id, original_volume in state.items():
            try:
                await self._set_sink_volume(sink_id, original_volume)
                logger.debug(
                    "Restored sink %s to volume %.2f",
                    sink_id,
                    original_volume,
                )
            except Exception as e:
                logger.warning(
                    "Failed to restore sink %s: %s", sink_id, e
                )

    async def is_available(self) -> bool:
        """Check if wpctl is available on the system.

        Returns:
            True if wpctl is found, False otherwise.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "which",
                "wpctl",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return_code = await proc.wait()
            return return_code == 0
        except Exception:
            return False

    async def _get_active_sinks(self) -> list[str]:
        """Get list of active audio sink IDs.

        Uses wpctl status and parses output to find sink IDs.
        """
        sinks: list[str] = []
        try:
            proc = await asyncio.create_subprocess_exec(
                "wpctl",
                "status",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(), timeout=WPDTL_COMMAND_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                logger.warning("wpctl status timed out")
                return sinks

            output = stdout.decode("utf-8", errors="replace")

            # Parse sink IDs from wpctl status output
            # Format: ├─ Sinks: or │  └─ Sinks:, then numbered items
            in_sinks_section = False
            for line in output.splitlines():
                stripped = line.strip()
                if "Sinks:" in stripped or "sinks:" in stripped.lower():
                    in_sinks_section = True
                    continue

                if in_sinks_section:
                    # Check for numbered sink entries like "• 51.alsa_output..."
                    match = re.match(r".*?[•·]\s*(\d+)\.", stripped)
                    if match:
                        sinks.append(match.group(1))
                    # Exit if we hit a new section
                    if any(
                        section in stripped.lower()
                        for section in [
                            "sources:",
                            "clients:",
                            "source:",
                        ]
                    ):
                        break

        except Exception as e:
            logger.warning("Failed to list sinks: %s", e)

        return sinks

    async def _get_sink_volume(self, sink_id: str) -> float | None:
        """Get current volume of a sink (0.0 to 1.0+).

        Returns None if unable to read volume.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "wpctl",
                "get-volume",
                sink_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(), timeout=WPDTL_COMMAND_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                logger.warning("wpctl get-volume %s timed out", sink_id)
                return None

            output = stdout.decode("utf-8", errors="replace").strip()
            # Parse volume value e.g. "Volume: 0.75"
            match = re.search(r"Volume:\s+([\d.]+)", output)
            if match:
                return float(match.group(1))

            logger.warning(
                "Could not parse volume from wpctl output: %s", output
            )
            return None

        except Exception as e:
            logger.warning(
                "Failed to get volume for sink %s: %s", sink_id, e
            )
            return None

    async def _set_sink_volume(self, sink_id: str, volume: float) -> None:
        """Set volume of a sink to a specific level."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "wpctl",
                "set-volume",
                sink_id,
                f"{volume:.2f}",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=WPDTL_COMMAND_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise RuntimeError(
                    f"wpctl set-volume {sink_id} timed out"
                )

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    f"wpctl set-volume failed: {error_msg}"
                )

        except Exception as e:
            logger.warning(
                "Failed to set volume for sink %s: %s", sink_id, e
            )
            raise
