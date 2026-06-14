"""Application configuration.

Uses environment variables with CHAPPIE_ prefix for all settings.
All values have sensible defaults for local development.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any


def _env(name: str, default: Any) -> Any:
    """Read an environment variable with CHAPPIE_ prefix."""
    return os.environ.get(f"CHAPPIE_{name}", default)


@dataclass
class Config:
    """Centralized configuration for Chappie Daemon.

    All values can be overridden via environment variables
    with the CHAPPIE_ prefix.
    """

    # HTTP server
    HOST: str = field(
        default_factory=lambda: str(_env("HOST", "0.0.0.0"))
    )
    PORT: int = field(
        default_factory=lambda: int(_env("PORT", "8765"))
    )

    # n8n webhook
    N8N_WEBHOOK_URL: str = field(
        default_factory=lambda: str(
            _env(
                "N8N_WEBHOOK_URL",
                "http://localhost:5678/webhook/chappie-voice-capture",
            )
        )
    )

    # TTS audio file path (default, overridable per request)
    TTS_AUDIO_FILE: str = field(
        default_factory=lambda: str(
            _env("TTS_AUDIO_FILE", "/tmp/chappie_tts.mp3")
        )
    )

    # Logging
    LOG_LEVEL: str = field(
        default_factory=lambda: str(_env("LOG_LEVEL", "INFO"))
    )

    @property
    def log_level_int(self) -> int:
        """Get the numeric log level."""
        return getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)
