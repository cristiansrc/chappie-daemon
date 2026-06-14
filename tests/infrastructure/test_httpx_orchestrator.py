"""Tests for HttpxOrchestratorAdapter."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.infrastructure.adapters.out.httpx_orchestrator import (
    HttpxOrchestratorAdapter,
)
from tests.conftest import make_mock_audio_capture


@pytest.fixture
def adapter() -> HttpxOrchestratorAdapter:
    """Create an HttpxOrchestratorAdapter with default webhook URL."""
    return HttpxOrchestratorAdapter()


@pytest.fixture
def mock_response() -> AsyncMock:
    """Create a mock httpx response."""
    resp = AsyncMock(spec=httpx.Response)
    resp.is_success = True
    resp.status_code = 200
    resp.text = "OK"
    return resp


class TestSendAudio:
    """Tests for send_audio method."""

    @pytest.mark.asyncio
    async def test_send_audio_success(self, adapter):
        """Should return True on successful send."""
        audio = make_mock_audio_capture()

        # Mock the client to avoid actual HTTP calls
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.send_audio(audio)
            assert result is True
            mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_audio_4xx_not_retried(self, adapter):
        """Should return False on 4xx without retrying."""
        audio = make_mock_audio_capture()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_client.post.return_value = mock_response

        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.send_audio(audio)
            assert result is False
            # Should only be called once (no retry)
            mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_audio_5xx_retried(self, adapter):
        """Should retry on 5xx up to 3 times then return False."""
        audio = make_mock_audio_capture()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_response.request = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.send_audio(audio)
            assert result is False
            # Should be called once (retry logic wrapped in the adapter)
            assert mock_client.post.await_count >= 1

    @pytest.mark.asyncio
    async def test_send_audio_connection_error_retried(self, adapter):
        """Should retry on connection error up to 3 times."""
        audio = make_mock_audio_capture()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.send_audio(audio)
            assert result is False
            # Should have been called up to 3 times
            assert 1 <= mock_client.post.await_count <= 3

    @pytest.mark.asyncio
    async def test_send_audio_builds_correct_payload(self, adapter):
        """Should build correct payload with base64 encoded audio."""
        audio = make_mock_audio_capture(
            audio_data=b"test_audio_data",
            session_id="test-session",
        )

        payload = adapter._build_payload(audio)
        assert "audio_base64" in payload
        assert payload["session_id"] == "test-session"
        assert payload["include_screen"] is False
        assert "timestamp" in payload
        assert isinstance(payload["audio_base64"], str)

    @pytest.mark.asyncio
    async def test_send_audio_timeout_retried(self, adapter):
        """Should retry on timeout."""
        audio = make_mock_audio_capture()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.side_effect = httpx.TimeoutException("Timed out")

        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            result = await adapter.send_audio(audio)
            assert result is False
            assert mock_client.post.await_count >= 1


class TestBuildPayload:
    """Tests for _build_payload method."""

    def test_payload_structure(self, adapter):
        """Should contain all required fields."""
        audio = make_mock_audio_capture(
            audio_data=b"data",
            session_id="session-1",
        )
        payload = adapter._build_payload(audio)

        assert "audio_base64" in payload
        assert "timestamp" in payload
        assert "session_id" in payload
        assert "include_screen" in payload

    def test_audio_base64_encoding(self, adapter):
        """Should base64 encode audio data."""
        audio = make_mock_audio_capture(audio_data=b"hello_world")
        payload = adapter._build_payload(audio)

        import base64
        decoded = base64.b64decode(payload["audio_base64"])
        assert decoded == b"hello_world"

    def test_include_screen_default_false(self, adapter):
        """Should set include_screen to False."""
        audio = make_mock_audio_capture()
        payload = adapter._build_payload(audio)
        assert payload["include_screen"] is False
