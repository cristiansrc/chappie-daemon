"""Global error handlers for FastAPI.

Maps domain exceptions to standardized ApiErrorResponse payloads.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    AlreadyRecordingException,
    AlreadySpeakingException,
    AudioFileNotFoundException,
    MicrophoneUnavailableException,
    NotRecordingException,
    PlaybackFailedException,
    VolumeControlFailedException,
)
from app.infrastructure.adapters.input.schemas import (
    ApiErrorDetail,
    ApiErrorResponse,
)

logger = logging.getLogger(__name__)


def _get_trace_id(request: Request) -> str:
    """Get trace_id from request state or generate a new one."""
    trace_id = getattr(request.state, "trace_id", None)
    if trace_id is None:
        trace_id = str(uuid4())
    return trace_id


def _build_error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list | None = None,
) -> JSONResponse:
    """Build a standardized error JSON response."""
    error_response = ApiErrorResponse(
        timestamp=datetime.now(timezone.utc),
        status=status_code,
        error=code.replace("_", " ").title(),
        code=code,
        message=message,
        path=request.url.path,
        trace_id=_get_trace_id(request),
        details=details or [],
    )
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(AlreadyRecordingException)
    async def handle_already_recording(
        request: Request, exc: AlreadyRecordingException
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            status_code=status.HTTP_409_CONFLICT,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(NotRecordingException)
    async def handle_not_recording(
        request: Request, exc: NotRecordingException
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            status_code=status.HTTP_409_CONFLICT,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(AlreadySpeakingException)
    async def handle_already_speaking(
        request: Request, exc: AlreadySpeakingException
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            status_code=status.HTTP_409_CONFLICT,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(MicrophoneUnavailableException)
    async def handle_microphone_unavailable(
        request: Request, exc: MicrophoneUnavailableException
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(VolumeControlFailedException)
    async def handle_volume_control_failed(
        request: Request, exc: VolumeControlFailedException
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(AudioFileNotFoundException)
    async def handle_audio_file_not_found(
        request: Request, exc: AudioFileNotFoundException
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(PlaybackFailedException)
    async def handle_playback_failed(
        request: Request, exc: PlaybackFailedException
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=exc.code,
            message=str(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = []
        for error in exc.errors():
            loc = error.get("loc", [])
            field = ".".join(str(part) for part in loc) if loc else None
            details.append(
                ApiErrorDetail(
                    field=field,
                    code="FIELD_INVALID",
                    message=error.get("msg", "Invalid field"),
                    rejected_value=error.get("input"),
                )
            )
        return _build_error_response(
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="The request contains invalid fields.",
            details=[d.model_dump() for d in details],
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Normalize HTTPException 404 to ApiErrorResponse."""
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return _build_error_response(
            request=request,
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail) if exc.detail else "Not Found",
        )

    # Override Starlette's default 404 handler for unknown routes
    @app.exception_handler(404)
    async def handle_not_found(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return _build_error_response(
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="The requested endpoint was not found.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)
        logger.exception(
            "Unhandled exception. trace_id=%s", trace_id
        )
        return _build_error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
        )
