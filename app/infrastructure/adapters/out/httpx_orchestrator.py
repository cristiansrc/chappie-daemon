"""HTTPX Orchestrator Adapter.

Implements OrchestratorClientPort for sending captured audio
to the n8n orchestrator via HTTP POST with retry policy.
"""

import asyncio
import base64
import logging
from typing import Any

import httpx

from app.domain.models import AudioCapture
from app.domain.ports import OrchestratorClientPort

logger = logging.getLogger(__name__)

# Default webhook URL
DEFAULT_N8N_WEBHOOK_URL = (
    "http://localhost:5678/webhook/chappie-voice-capture"
)

# Timeout configuration
HTTP_TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=30.0,
    write=10.0,
    pool=10.0,
)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = [1.0, 2.0, 4.0]  # seconds


class HttpxOrchestratorAdapter(OrchestratorClientPort):
    """HTTPX-based adapter for sending audio to n8n orchestrator.

    Implements retry policy with exponential backoff:
    - 5xx, timeout, connection refused → retry up to 3 times
    - 4xx → no retry (client error)
    """

    def __init__(
        self, webhook_url: str = DEFAULT_N8N_WEBHOOK_URL
    ) -> None:
        self._webhook_url = webhook_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        return self._client

    async def send_audio(self, audio: AudioCapture) -> bool:
        """Send captured audio to n8n with retry policy.

        Args:
            audio: The captured audio data to send.

        Returns:
            True if the audio was sent successfully,
            False if all retries exhausted or non-retryable error.
        """
        # Build payload
        payload = self._build_payload(audio)

        last_exception: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                client = await self._get_client()
                response = await client.post(
                    self._webhook_url,
                    json=payload,
                )

                if response.is_success:
                    logger.info(
                        "Audio sent to n8n (session=%s, status=%d)",
                        audio.session_id,
                        response.status_code,
                    )
                    return True

                # 4xx: client error, do not retry
                if 400 <= response.status_code < 500:
                    logger.warning(
                        "n8n rejected audio with %d (session=%s): %s",
                        response.status_code,
                        audio.session_id,
                        response.text[:500],
                    )
                    return False

                # 5xx: server error, retry
                logger.warning(
                    "n8n returned %d (attempt %d/%d, session=%s)",
                    response.status_code,
                    attempt,
                    MAX_RETRIES,
                    audio.session_id,
                )
                last_exception = httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(
                    "n8n connection failed (attempt %d/%d, session=%s): %s",
                    attempt,
                    MAX_RETRIES,
                    audio.session_id,
                    e,
                )
                last_exception = e

            except Exception as e:
                logger.error(
                    "Unexpected error sending to n8n (attempt %d/%d, "
                    "session=%s): %s",
                    attempt,
                    MAX_RETRIES,
                    audio.session_id,
                    e,
                )
                last_exception = e
                return False  # Do not retry on unexpected errors

            # Wait before next retry
            if attempt < MAX_RETRIES:
                backoff = RETRY_BACKOFF[attempt - 1]
                await asyncio.sleep(backoff)

        logger.error(
            "Failed to send audio to n8n after %d attempts "
            "(session=%s): %s",
            MAX_RETRIES,
            audio.session_id,
            last_exception,
        )
        return False

    def _build_payload(self, audio: AudioCapture) -> dict[str, Any]:
        """Build the JSON payload for the n8n webhook.

        Args:
            audio: The captured audio data.

        Returns:
            Dict with audio_base64, timestamp, session_id,
            and include_screen.
        """
        audio_base64 = base64.b64encode(audio.audio_data).decode("ascii")
        return {
            "audio_base64": audio_base64,
            "timestamp": audio.timestamp.isoformat(),
            "session_id": audio.session_id,
            "include_screen": False,
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
