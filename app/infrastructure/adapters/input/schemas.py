"""Pydantic schemas for the FastAPI router.

These are the API DTOs for request/response serialization.
They belong exclusively to the infrastructure layer.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlayTtsRequest(BaseModel):
    """Request body for POST /play-tts."""

    audio_file: str = Field(
        ..., description="Absolute path to the audio file to play."
    )
    text: str = Field(
        ..., description="Text being spoken (for logs/state)."
    )
    ducking: bool = Field(
        default=True,
        description="Whether to apply volume ducking during playback.",
    )


class SuccessResponse(BaseModel):
    """Generic success response."""

    status: str = "success"
    message: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"


class ApiErrorDetail(BaseModel):
    """Detailed error information for a specific field."""

    field: str | None = Field(
        default=None,
        description="Field that caused the error (if applicable).",
    )
    code: str = Field(
        ..., description="Stable error code for this specific issue."
    )
    message: str = Field(
        ..., description="Human-readable error description."
    )
    rejected_value: Any | None = Field(
        default=None,
        description="Rejected value that caused the error (if applicable).",
    )


class ApiErrorResponse(BaseModel):
    """Standard error response for all API errors."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(
        ..., description="UTC timestamp of when the error occurred."
    )
    status: int = Field(..., description="HTTP status code.")
    error: str = Field(..., description="Short error name/title.")
    code: str = Field(..., description="Stable business/technical error code.")
    message: str = Field(
        ..., description="Human-readable error message."
    )
    path: str = Field(..., description="Request URL path.")
    trace_id: str = Field(
        ..., description="Unique request trace identifier."
    )
    details: list[ApiErrorDetail] = Field(
        default_factory=list,
        description="List of detailed errors (may be empty).",
    )
