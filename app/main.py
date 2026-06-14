"""Chappie Daemon — Main Entry Point.

Creates and runs the FastAPI application with all dependency wiring.
"""

import logging
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request

from app.config import Config
from app.infrastructure.adapters.input.error_handlers import (
    register_exception_handlers,
)
from app.infrastructure.adapters.input.router import (
    get_play_tts_usecase,
    get_voice_capture_usecase,
    router,
)

logger = logging.getLogger("chappie")


def setup_logging(config: Config) -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=config.log_level_int,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        stream=sys.stdout,
    )


def create_app(config: Config | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    This factory function wires all dependencies:
    - Creates concrete adapter instances
    - Injects adapters into use cases
    - Injects use cases into the router via dependency_overrides
    - Registers exception handlers

    Args:
        config: Application configuration. If None, uses defaults.

    Returns:
        Configured FastAPI application instance.
    """
    if config is None:
        config = Config()

    setup_logging(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        logger.info(
            "Chappie Daemon starting on %s:%d",
            config.HOST,
            config.PORT,
        )
        yield
        logger.info("Chappie Daemon shutting down")

    app = FastAPI(
        title="Chappie Daemon API",
        description="Local voice assistant daemon for Chappie ecosystem.",
        version="1.0.0",
        lifespan=lifespan,
        # Disable default 422 for validation errors (use our 400 handler)
        validation_error_status_code=400,
    )

    # --- Wire dependencies ---

    # Create adapters out
    from app.infrastructure.adapters.out.pipewire_volume import (
        PipeWireVolumeAdapter,
    )
    from app.infrastructure.adapters.out.audio_capture import (
        AudioCaptureAdapter,
    )
    from app.infrastructure.adapters.out.audio_playback import (
        AudioPlaybackAdapter,
    )
    from app.infrastructure.adapters.out.file_state import (
        FileStateAdapter,
    )
    from app.infrastructure.adapters.out.httpx_orchestrator import (
        HttpxOrchestratorAdapter,
    )

    volume_adapter = PipeWireVolumeAdapter()
    audio_capture_adapter = AudioCaptureAdapter()
    audio_playback_adapter = AudioPlaybackAdapter()
    state_adapter = FileStateAdapter()
    orchestrator_adapter = HttpxOrchestratorAdapter(
        webhook_url=config.N8N_WEBHOOK_URL
    )

    # Create use cases
    from app.application.handle_voice_capture import (
        HandleVoiceCaptureUseCase,
    )
    from app.application.play_tts import PlayTTSUseCase

    voice_capture_usecase = HandleVoiceCaptureUseCase(
        audio_capture_port=audio_capture_adapter,
        volume_control_port=volume_adapter,
        state_management_port=state_adapter,
        orchestrator_client_port=orchestrator_adapter,
    )

    play_tts_usecase = PlayTTSUseCase(
        audio_playback_port=audio_playback_adapter,
        volume_control_port=volume_adapter,
        state_management_port=state_adapter,
    )

    # Override router dependency placeholders with real instances
    app.dependency_overrides[get_voice_capture_usecase] = (
        lambda: voice_capture_usecase
    )
    app.dependency_overrides[get_play_tts_usecase] = (
        lambda: play_tts_usecase
    )

    # --- Trace ID middleware ---
    @app.middleware("http")
    async def add_trace_id(request: Request, call_next):
        """Add a unique trace_id to each request."""
        trace_id = str(uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response

    # --- Register routers ---
    app.include_router(router)

    # --- Register exception handlers ---
    register_exception_handlers(app)

    logger.info(
        "Chappie Daemon initialized (n8n webhook: %s)",
        config.N8N_WEBHOOK_URL,
    )
    return app


def main() -> None:
    """Run the Chappie Daemon server."""
    config = Config()
    app = create_app(config)

    logger.info(
        "Starting Chappie Daemon on %s:%d",
        config.HOST,
        config.PORT,
    )
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
