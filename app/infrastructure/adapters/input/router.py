"""FastAPI Router — Adapter In.

Exposes the HTTP endpoints for the Chappie Daemon:
- POST /play-tts: Trigger TTS playback
- POST /shortcut/press: Start voice capture
- POST /shortcut/release: Stop voice capture and send to n8n
- GET /health: Health check
"""

import logging

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from app.application.handle_voice_capture import HandleVoiceCaptureUseCase
from app.application.play_tts import PlayTTSUseCase
from app.infrastructure.adapters.input.schemas import (
    HealthResponse,
    PlayTtsRequest,
    SuccessResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="")

# Placeholder dependencies — replaced by real wiring in T10


async def get_voice_capture_usecase() -> HandleVoiceCaptureUseCase:
    """Dependency placeholder for HandleVoiceCaptureUseCase.

    Will be overridden in T10 (main.py) via app.dependency_overrides.
    """
    raise NotImplementedError(
        "HandleVoiceCaptureUseCase not wired yet. "
        "Configure in app/main.py create_app()."
    )


async def get_play_tts_usecase() -> PlayTTSUseCase:
    """Dependency placeholder for PlayTTSUseCase.

    Will be overridden in T10 (main.py) via app.dependency_overrides.
    """
    raise NotImplementedError(
        "PlayTTSUseCase not wired yet. "
        "Configure in app/main.py create_app()."
    )


@router.post(
    "/play-tts",
    response_model=SuccessResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Play TTS audio",
    description="Receive a TTS playback request with volume ducking.",
    responses={
        200: {
            "description": "Audio played successfully",
            "model": SuccessResponse,
        },
        400: {"description": "Invalid request body"},
        404: {"description": "Audio file not found"},
        409: {"description": "Already speaking"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable (PipeWire)"},
    },
)
async def play_tts(
    request: PlayTtsRequest,
    play_tts_usecase: PlayTTSUseCase = Depends(get_play_tts_usecase),
) -> SuccessResponse:
    """Handle POST /play-tts request."""

    # Convert Pydantic request to domain TTSRequest
    from app.domain.models import TTSRequest as DomainTTSRequest

    domain_request = DomainTTSRequest(
        audio_file=request.audio_file,
        text=request.text,
        ducking=request.ducking,
    )

    await play_tts_usecase.play(domain_request)

    return SuccessResponse(message="Audio played successfully")


@router.post(
    "/shortcut/press",
    response_model=SuccessResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Start voice capture (shortcut pressed)",
    description="Start recording and apply volume ducking.",
    responses={
        200: {"description": "Recording started", "model": SuccessResponse},
        409: {"description": "Already recording"},
        500: {"description": "Internal server error"},
        503: {"description": "Microphone unavailable"},
    },
)
async def shortcut_press(
    voice_capture_usecase: HandleVoiceCaptureUseCase = Depends(
        get_voice_capture_usecase
    ),
) -> SuccessResponse:
    """Handle POST /shortcut/press request."""
    await voice_capture_usecase.start_capture()
    return SuccessResponse(message="Recording started")


@router.post(
    "/shortcut/release",
    response_model=SuccessResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Stop voice capture (shortcut released)",
    description="Stop recording, restore volume, and send to n8n.",
    responses={
        200: {
            "description": "Recording stopped and sent",
            "model": SuccessResponse,
        },
        409: {"description": "Not recording"},
        500: {"description": "Internal server error"},
        503: {"description": "n8n unavailable"},
    },
)
async def shortcut_release(
    voice_capture_usecase: HandleVoiceCaptureUseCase = Depends(
        get_voice_capture_usecase
    ),
) -> SuccessResponse:
    """Handle POST /shortcut/release request."""
    await voice_capture_usecase.stop_capture()
    return SuccessResponse(message="Recording stopped and sent")


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Health check",
    description="Verify the daemon is running.",
    responses={
        200: {"description": "Daemon OK", "model": HealthResponse},
        500: {"description": "Internal server error"},
    },
)
async def health() -> HealthResponse:
    """Handle GET /health request."""
    return HealthResponse(status="ok")
