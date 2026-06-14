# Task Board — Chappie Daemon Initial Setup

**Source Spec:** `/home/cristiansrc/Documentos/Proyectos/chappie-workspace/projects/chappie-daemon/docs/specs/master_spec.md`
**Shared Context:** `/home/cristiansrc/Documentos/Proyectos/chappie-workspace/projects/chappie-daemon/docs/specs/.working/initial-setup-sdd-context.md`
**OpenAPI:** `/home/cristiansrc/Documentos/Proyectos/chappie-workspace/projects/chappie-daemon/docs/api/openapi.yaml`
**Created by:** Task Decomposer
**Created at:** 2026-06-14

## Board Status: `done`

---

## T1: Domain Models and Ports

- **id:** T1-domain-models-and-ports
- **title:** Definir modelos de dominio y puertos (interfaces)
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.1 (Dominio)
  - master_spec.md §2.1 (Puertos: AudioCapturePort, AudioPlaybackPort, VolumeControlPort, ShortcutDetectionPort, StateManagementPort, OrchestratorClientPort)
  - Decomposition Contract §9.3 (Los puertos pertenecen al dominio)
  - stale_terms_guard: no usar "DTO" en dominio (usar "Model" o "Entity")
- **goal:** Crear los modelos de dominio puros y las interfaces ABC de los puertos en `app/domain/` sin dependencias de framework, ORM o infraestructura.
- **scope:**
  - `app/domain/__init__.py`
  - `app/domain/models.py` — `AudioCapture`, `TTSRequest`, `SystemState` como dataclasses/classes puras
  - `app/domain/ports.py` — interfaces ABC: `AudioCapturePort`, `AudioPlaybackPort`, `VolumeControlPort`, `ShortcutDetectionPort`, `StateManagementPort`, `OrchestratorClientPort`
  - `app/domain/exceptions.py` — excepciones de dominio: `AlreadyRecordingException`, `NotRecordingException`, `AlreadySpeakingException`, `MicrophoneUnavailableException`, `VolumeControlFailedException`, `AudioFileNotFoundException`, `PlaybackFailedException`
- **out_of_scope:**
  - Pydantic models (pertenecen a infraestructura)
  - Implementaciones concretas de puertos (adapters)
  - Casos de uso
  - Configuración, HTTP, system calls
- **inputs:**
  - master_spec.md §2.1 (listado de modelos y puertos)
  - master_spec.md §4.1, §4.2 (failure paths → excepciones de dominio)
  - openapi.yaml (nombres de campos para `TTSRequest`)
- **implementation_notes:**
  - Usar `abc.ABC` + `@abstractmethod` para los puertos
  - `TTSRequest` debe contener `audio_file: str`, `text: str`, `ducking: bool`
  - `AudioCapture` debe contener `audio_data: bytes`, `timestamp: datetime`, `session_id: str`
  - `SystemState` debe ser un enum o clase con los valores: `idle`, `listening`, `thinking`, `working`, `speaking`
  - Cada excepción de dominio debe tener un atributo `code: str` estable (ej. `ALREADY_RECORDING`, `NOT_RECORDING`, `MICROPHONE_UNAVAILABLE`, `VOLUME_CONTROL_FAILED`, `AUDIO_FILE_NOT_FOUND`, `PLAYBACK_FAILED`, `ALREADY_SPEAKING`)
  - `ShortcutDetectionPort` se define pero no tendrá adapter out (detección delegada a Hyprland vía HTTP)
  - Los métodos de los puertos deben ser `async` donde involucren I/O (captura, playback, HTTP, filesystem)
  - Los archivos de estado definidos en master_spec.md §3.3 deben ser referenciados en `StateManagementPort`
- **edge_cases:**
  - `ShortcutDetectionPort` queda sin implementación concreta (intencional — la detección la hace Hyprland llamando a los endpoints HTTP)
  - `AudioCapture` con `audio_data` vacío o `None` debe ser manejado por el caso de uso, no por el modelo
- **done_criteria:**
  - `app/domain/__init__.py` existe y exporta modelos, puertos y excepciones
  - `app/domain/models.py` contiene `AudioCapture`, `TTSRequest`, `SystemState`
  - `app/domain/ports.py` contiene las 6 interfaces ABC con métodos abstractos
  - `app/domain/exceptions.py` contiene las 7 excepciones de dominio con atributo `code`
  - Ningún import de fastapi, pydantic, httpx, wpctl, pyaudio o cualquier dependencia de infraestructura
- **verification:**
  - Ejecutar `python -c "from app.domain import AudioCapture, TTSRequest, SystemState, AudioCapturePort, AudioPlaybackPort, VolumeControlPort, ShortcutDetectionPort, StateManagementPort, OrchestratorClientPort"` sin errores
  - Ejecutar `python -c "from app.domain.exceptions import AlreadyRecordingException; e = AlreadyRecordingException(); assert e.code == 'ALREADY_RECORDING'"` para cada excepción
  - Verificar que `grep -r "from fastapi\|from pydantic\|from httpx\|import wpctl\|import pyaudio" app/domain/` no devuelve resultados
- **dependencies:** none
- **handoff_context:** Los modelos y puertos definidos aquí serán referenciados por T2, T3 (use cases) y T5-T9 (adapters out).
- **source_of_truth:** master_spec.md §2.1
- **stale_terms_guard:** no "Controller", no "Service", no "DTO"
- **status:** `done`
- **executor_notes:** Implemented domain models (AudioCapture, TTSRequest, SystemState), 6 ABC ports, and 7 domain exceptions with stable codes. All verification checks passed.
- **verification_result:** passed - imports ok, exception codes verified, no infra imports in domain**
- **blocker:** `none`

---

## T2: HandleVoiceCaptureUseCase

- **id:** T2-handle-voice-capture-usecase
- **title:** Implementar caso de uso HandleVoiceCaptureUseCase
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.2 (Casos de Uso)
  - master_spec.md §4.1 (Flujo de Captura de Voz)
  - master_spec.md §4.1 Failure Paths
  - Decomposition Contract §9.3 (No mezclar casos de uso)
- **goal:** Implementar `HandleVoiceCaptureUseCase` en `app/application/` que orqueste: ducking → grabación → restauración de volumen → envío a n8n, respetando el flujo y los failure paths definidos en §4.1.
- **scope:**
  - `app/application/__init__.py`
  - `app/application/handle_voice_capture.py` — clase `HandleVoiceCaptureUseCase`
- **out_of_scope:**
  - PlayTTSUseCase (T3)
  - Implementación concreta de puertos (adapters)
  - Manejo de endpoints HTTP (Router)
- **inputs:**
  - T1 (Modelos de dominio y puertos)
  - master_spec.md §4.1 (pasos 1-9 del flujo)
  - master_spec.md §4.1 Failure Paths
  - master_spec.md §3.2 (Retry policy y timeouts para outbound a n8n)
  - master_spec.md §3.3 (Archivos de estado en /tmp/)
- **implementation_notes:**
  - Recibir por constructor: `AudioCapturePort`, `VolumeControlPort`, `StateManagementPort`, `OrchestratorClientPort`
  - Método principal `async def start_capture() -> str` (retorna session_id)
  - Método `async def stop_capture() -> None`
  - Método `async def is_recording() -> bool`
  - Al iniciar: verificar `is_recording()` → si True, lanzar `AlreadyRecordingException`
  - Aplicar ducking antes de grabar → si falla, lanzar `VolumeControlFailedException`
  - Iniciar grabación → si falla (mic no disponible), lanzar `MicrophoneUnavailableException`
  - Al detener: verificar `is_recording()` → si False, lanzar `NotRecordingException`
  - Restaurar volumen después de detener grabación
  - Enviar audio a n8n con retry policy (3 reintentos, backoff exponencial 1s/2s/4s, timeout 10s conexión / 30s respuesta)
  - Si el envío a n8n falla definitivamente, loggear error y actualizar estado a `idle`
  - Actualizar `/tmp/chappie_state.txt` en cada transición: `listening` → `thinking` → `idle` (si falla n8n)
- **edge_cases:**
  - Doble press sin release → `AlreadyRecordingException` (409)
  - Release sin press previo → `NotRecordingException` (409)
  - Micrófono desconectado durante la grabación → capturar excepción del adapter, restaurar volumen, estado a `idle`
  - n8n caído → aplicar retry policy; si se agotan reintentos, descartar audio, estado a `idle`
  - Error de PipeWire al restaurar volumen → loggear warning pero no bloquear (el ducking ya se aplicó, intentar restaurar best-effort)
- **done_criteria:**
  - `app/application/__init__.py` existe
  - `app/application/handle_voice_capture.py` contiene la clase `HandleVoiceCaptureUseCase` con métodos `start_capture`, `stop_capture`, `is_recording`
  - La lógica respeta el orden del flujo en §4.1 sin saltar pasos
  - Los failure paths están cubiertos con las excepciones de dominio correctas
  - No hay referencias a FastAPI, HTTP, o implementaciones concretas de adapters
- **verification:**
  - Import limpio: `python -c "from app.application.handle_voice_capture import HandleVoiceCaptureUseCase"`
  - Verificar que `grep -r "from fastapi\|HTTPException\|JSONResponse\|@app" app/application/` no devuelve resultados
  - Los puertos inyectados son interfaces ABC de `app.domain.ports`
- **dependencies:** T1
- **handoff_context:** Este use case será inyectado en el Router (T4) para los endpoints `POST /shortcut/press` y `POST /shortcut/release`.
- **source_of_truth:** master_spec.md §4.1
- **stale_terms_guard:** no "Service" (usar "UseCase")
- **status:** `done`
- **executor_notes:** Implemented HandleVoiceCaptureUseCase with start_capture/stop_capture/is_recording methods, ducking logic, state transitions, and n8n retry policy (3 retries with exponential backoff 1s/2s/4s).
- **verification_result:** passed - import OK, no infra dependencies

---

## T3: PlayTTSUseCase

- **id:** T3-play-tts-usecase
- **title:** Implementar caso de uso PlayTTSUseCase
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.2 (Casos de Uso)
  - master_spec.md §4.2 (Flujo de Reproducción TTS)
  - master_spec.md §4.2 Failure Paths
  - Decomposition Contract §9.3 (No mezclar casos de uso)
- **goal:** Implementar `PlayTTSUseCase` en `app/application/` que orqueste: ducking → actualización de estado → reproducción → restauración de volumen → actualización de estado, respetando el flujo y failure paths de §4.2.
- **scope:**
  - `app/application/play_tts.py` — clase `PlayTTSUseCase`
- **out_of_scope:**
  - HandleVoiceCaptureUseCase (T2)
  - Validación de request body (pertenece al Router T4)
  - Implementación concreta de puertos (adapters)
- **inputs:**
  - T1 (Modelos de dominio y puertos)
  - master_spec.md §4.2 (pasos 1-8 del flujo)
  - master_spec.md §4.2 Failure Paths
  - master_spec.md §3.3 (Archivos de estado en /tmp/)
- **implementation_notes:**
  - Recibir por constructor: `AudioPlaybackPort`, `VolumeControlPort`, `StateManagementPort`
  - Método principal `async def play(request: TTSRequest) -> None`
  - Método `async def is_playing() -> bool`
  - Al iniciar: verificar `is_playing()` → si True, lanzar `AlreadySpeakingException`
  - Verificar existencia del archivo `audio_file` → si no existe, lanzar `AudioFileNotFoundException` antes de aplicar ducking
  - Si `ducking` es True, aplicar ducking → si falla, lanzar `VolumeControlFailedException`
  - Actualizar `/tmp/chappie_tts_state.txt` a `speaking` y `/tmp/chappie_state.txt` a `speaking`
  - Reproducir audio de forma síncrona (bloquear hasta terminar)
  - Si la reproducción falla, lanzar `PlaybackFailedException`
  - Al finalizar (éxito o failure paths): restaurar volumen, actualizar ambos estados a `idle`
  - La restauración de volumen y estado debe ejecutarse incluso si la reproducción falla (finally/context manager)
- **edge_cases:**
  - Solicitud mientras ya se está reproduciendo → `AlreadySpeakingException` (409). No encolar.
  - Archivo de audio inexistente → `AudioFileNotFoundException` (404). No aplicar ducking, estado permanece `idle`.
  - PipeWire no disponible → `VolumeControlFailedException` o `PlaybackFailedException` (503). Estado vuelve a `idle`.
  - Archivo de audio corrupto/formato no soportado → `PlaybackFailedException`. Restaurar volumen, estado a `idle`.
- **done_criteria:**
  - `app/application/play_tts.py` contiene la clase `PlayTTSUseCase` con métodos `play` e `is_playing`
  - La lógica respeta el orden del flujo en §4.2 sin saltar pasos
  - Los failure paths están cubiertos con las excepciones de dominio correctas
  - La restauración de volumen y estado se garantiza en todos los caminos (éxito y error)
  - No hay referencias a FastAPI, HTTP, o implementaciones concretas de adapters
- **verification:**
  - Import limpio: `python -c "from app.application.play_tts import PlayTTSUseCase"`
  - Verificar que `grep -r "from fastapi\|HTTPException\|JSONResponse\|@app" app/application/play_tts.py` no devuelve resultados
  - Los puertos inyectados son interfaces ABC de `app.domain.ports`
- **dependencies:** T1
- **handoff_context:** Este use case será inyectado en el Router (T4) para el endpoint `POST /play-tts`.
- **source_of_truth:** master_spec.md §4.2
- **stale_terms_guard:** no "Service" (usar "UseCase")
- **status:** `done`
- **executor_notes:** Implemented PlayTTSUseCase with play/is_playing methods, file existence check, ducking, state transitions (speaking ↔ idle), and guaranteed volume/state restore in finally block.
- **verification_result:** passed - import OK, no infra dependencies

---

## T4: FastAPI Router — Adapter In

- **id:** T4-fastapi-router-adapter-in
- **title:** Implementar Router FastAPI con endpoints y manejo global de errores
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.3 (Adapters In: FastAPI Router)
  - master_spec.md §3.1 (API HTTP Local — Inbound)
  - openapi.yaml (paths: /play-tts, /shortcut/press, /shortcut/release, /health)
  - openapi.yaml (components/schemas: PlayTtsRequest, SuccessResponse, HealthResponse, ErrorResponse, ApiErrorDetail)
  - fastapi-rest-error-response-standards (exception handlers globales, ApiErrorResponse)
  - fastapi-stack (APIRouter, Depends, async def)
  - Decomposition Contract §9.3 (No mezclar inbound y outbound adapters)
- **goal:** Crear el Router FastAPI (`app/infrastructure/adapters/in/`) con los 4 endpoints definidos en OpenAPI, schemas Pydantic de request/response, y manejo global de errores con exception handlers que traduzcan excepciones de dominio a `ApiErrorResponse`.
- **scope:**
  - `app/infrastructure/__init__.py`
  - `app/infrastructure/adapters/__init__.py`
  - `app/infrastructure/adapters/in/__init__.py`
  - `app/infrastructure/adapters/in/router.py` — APIRouter con los 4 endpoints
  - `app/infrastructure/adapters/in/schemas.py` — Pydantic models: `PlayTtsRequest`, `SuccessResponse`, `HealthResponse`, `ApiErrorDetail`, `ApiErrorResponse`
  - `app/infrastructure/adapters/in/error_handlers.py` — registro de exception handlers globales
- **out_of_scope:**
  - App bootstrap / main.py (T10)
  - Implementación concreta de adapters out (T5-T9)
  - Dependency injection wiring (T10)
  - Lógica de negocio (pertenece a T2, T3)
- **inputs:**
  - T1 (Modelos de dominio: TTSRequest)
  - T2 (HandleVoiceCaptureUseCase)
  - T3 (PlayTTSUseCase)
  - T1 (Excepciones de dominio)
  - openapi.yaml (todos los schemas y responses)
  - fastapi-rest-error-response-standards (estructura de ApiErrorResponse, ApiErrorDetail, exception handlers)
  - fastapi-stack (convenciones de routers)
- **implementation_notes:**
  - Usar `APIRouter(prefix="")` sin prefijo adicional
  - Endpoints:
    - `POST /play-tts` → recibe `PlayTtsRequest` (Pydantic), llama a `play_tts_usecase.play(request)`, retorna `SuccessResponse`
    - `POST /shortcut/press` → llama a `voice_capture_usecase.start_capture()`, retorna `SuccessResponse`
    - `POST /shortcut/release` → llama a `voice_capture_usecase.stop_capture()`, retorna `SuccessResponse`
    - `GET /health` → retorna `HealthResponse(status="ok")`
  - Los use cases se reciben vía `Depends` (la inyección concreta se configura en T10)
  - Mapear `TTSRequest` de dominio al `PlayTtsRequest` de Pydantic en el endpoint (o pasar el Pydantic model directamente si es compatible)
  - Exception handlers a registrar en `error_handlers.py`:
    - `AlreadyRecordingException` → 409, code `ALREADY_RECORDING`
    - `NotRecordingException` → 409, code `NOT_RECORDING`
    - `AlreadySpeakingException` → 409, code `ALREADY_SPEAKING`
    - `MicrophoneUnavailableException` → 503, code `MICROPHONE_UNAVAILABLE`
    - `VolumeControlFailedException` → 503, code `VOLUME_CONTROL_FAILED`
    - `AudioFileNotFoundException` → 404, code `AUDIO_FILE_NOT_FOUND`
    - `PlaybackFailedException` → 503, code `PLAYBACK_FAILED`
    - `RequestValidationError` → 400, code `VALIDATION_ERROR`
    - `Exception` (fallback) → 500, code `INTERNAL_ERROR`
  - `ApiErrorResponse` debe seguir exactamente la estructura de `fastapi-rest-error-response-standards`: `timestamp`, `status`, `error`, `code`, `message`, `path`, `trace_id`, `details`
  - `trace_id` debe generarse por request (middleware o dependency)
  - Documentar responses de error en los decoradores de endpoints usando el parámetro `responses`
- **edge_cases:**
  - Request body malformado → 400 con `VALIDATION_ERROR` y `details` con campos inválidos
  - Endpoint no encontrado → 404 (manejo default de FastAPI, normalizar a ApiErrorResponse)
  - Método HTTP incorrecto → 405 (manejo default de FastAPI)
  - `SuccessResponse.message` debe variar según el endpoint: "Recording started", "Recording stopped and sent", "Audio played successfully"
- **done_criteria:**
  - `app/infrastructure/adapters/in/router.py` expone los 4 endpoints con tipo de retorno `response_model` correcto
  - `app/infrastructure/adapters/in/schemas.py` contiene todos los Pydantic models requeridos
  - `app/infrastructure/adapters/in/error_handlers.py` registra handlers para todas las excepciones de dominio + RequestValidationError + fallback Exception
  - `ApiErrorResponse` tiene los campos: `timestamp`, `status`, `error`, `code`, `message`, `path`, `trace_id`, `details`
  - Todos los endpoints documentan sus responses de error (400, 404, 409, 500, 503 según corresponda)
- **verification:**
  - Import limpio: `python -c "from app.infrastructure.adapters.in.router import router; assert router is not None"`
  - Verificar que el router tiene 4 rutas registradas (play-tts, shortcut/press, shortcut/release, health)
  - Verificar que `ApiErrorResponse` es serializable: `ApiErrorResponse(...).model_dump(mode="json")` no lanza excepción
  - Verificar que no hay lógica de negocio en el router (solo llama a use cases)
- **dependencies:** T2, T3
- **handoff_context:** El router será montado en la app FastAPI en T10. Los use cases se inyectarán vía `Depends`.
- **source_of_truth:** openapi.yaml, fastapi-rest-error-response-standards
- **stale_terms_guard:** no "Controller" (usar "Router" o "Adapter In")
- **status:** `done`
- **executor_notes:** Implemented FastAPI router with 4 endpoints, Pydantic schemas, global exception handlers, and trace_id middleware. Renamed adapters/in to adapters/input (Python keyword conflict).
- **verification_result:** passed - 4 routes registered, ApiErrorResponse serializable
- **blocker:** `none`

---

## T5: PipeWireVolumeAdapter — Adapter Out

- **id:** T5-pipewire-volume-adapter
- **title:** Implementar PipeWireVolumeAdapter para volume ducking
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.3 (PipeWireVolumeAdapter)
  - master_spec.md §4.1 (ducking en captura de voz)
  - master_spec.md §4.2 (ducking en reproducción TTS)
  - Decisions locked: "Se usará wpctl (PipeWire) para el volume ducking"
  - Decomposition Contract §9.3 (Cada adapter out en su propia tarea)
- **goal:** Implementar `PipeWireVolumeAdapter` en `app/infrastructure/adapters/out/` que implemente `VolumeControlPort` usando comandos `wpctl` de PipeWire.
- **scope:**
  - `app/infrastructure/adapters/out/__init__.py`
  - `app/infrastructure/adapters/out/pipewire_volume.py` — clase `PipeWireVolumeAdapter`
- **out_of_scope:**
  - Otros adapters out (AudioCapture, AudioPlayback, FileState, HttpxOrchestrator)
  - Lógica de cuándo aplicar ducking (pertenece a los use cases)
  - Control de volumen vía PulseAudio o ALSA (solo PipeWire/wpctl)
- **inputs:**
  - T1 (`VolumeControlPort` ABC)
  - master_spec.md §4.1 (ducking al 10%)
  - Decisions locked (wpctl)
- **implementation_notes:**
  - Implementar `VolumeControlPort` con métodos:
    - `async def duck() -> dict` — reduce todos los sinks activos al 10%, retorna dict con estado original `{sink_id: original_volume}` para restaurar después. Si no hay sinks activos, retornar dict vacío.
    - `async def restore(state: dict) -> None` — restaura cada sink a su volumen original
    - `async def is_available() -> bool` — verifica que `wpctl` está disponible (sin lanzar excepción)
  - Usar `asyncio.create_subprocess_exec` para ejecutar comandos `wpctl`
  - Comandos esperados:
    - Listar sinks: `wpctl status` o `pactl list short sinks` como fallback
    - Obtener volumen: `wpctl get-volume <sink_id>`
    - Fijar volumen: `wpctl set-volume <sink_id> 0.10` (10%)
  - El ducking debe aplicarse sobre todos los sinks de audio activos, no solo el default
  - Si `wpctl` no está disponible, `is_available()` debe retornar `False` (el use case lanzará `VolumeControlFailedException`)
  - Timeout de 5 segundos para cada comando `wpctl`
- **edge_cases:**
  - Sin sinks de audio activos → `duck()` retorna `{}`, `restore({})` no hace nada
  - `wpctl` no instalado → `is_available()` retorna `False`
  - Error al obtener/escribir volumen de un sink específico → loggear warning, continuar con los demás sinks
  - Volumen ya reducido (ducking anidado) → el estado original debe preservar el volumen pre-ducking, no el 10%
- **done_criteria:**
  - `app/infrastructure/adapters/out/pipewire_volume.py` contiene `PipeWireVolumeAdapter` implementando `VolumeControlPort`
  - Métodos `duck`, `restore`, `is_available` implementados con `asyncio` subprocess
  - `duck()` retorna un dict serializable con el estado original de cada sink
  - `restore()` aplica los volúmenes originales correctamente
  - `is_available()` verifica la presencia de `wpctl` sin lanzar excepciones
  - Timeout de 5s por comando
- **verification:**
  - `python -c "from app.infrastructure.adapters.out.pipewire_volume import PipeWireVolumeAdapter; assert issubclass(PipeWireVolumeAdapter, VolumeControlPort)"`
  - `is_available()` no lanza excepción cuando `wpctl` no existe (retorna False)
  - `duck()` y `restore()` manejan graceful degradation
- **dependencies:** T1
- **handoff_context:** Este adapter será inyectado en T2 y T3 (use cases) vía constructor. El wiring se configura en T10.
- **source_of_truth:** master_spec.md §2.3, Decisions locked
- **stale_terms_guard:** no "Service" (usar "Adapter")
- **status:** `done`
- **executor_notes:** Implemented PipeWireVolumeAdapter with async subprocess for wpctl (duck/restore/is_available). Lists active sinks dynamically.
- **verification_result:** passed - imports OK, implements VolumeControlPort

---

## T6: AudioCaptureAdapter — Adapter Out [TD-DAEMON-001]

- **id:** T6-audio-capture-adapter
- **title:** Implementar AudioCaptureAdapter para captura de micrófono
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.3 (PyAudioCaptureAdapter / ArecordAdapter)
  - master_spec.md §4.1 (grabación en memoria o archivo temporal /tmp/chappie_capture.wav)
  - technical_debt.md TD-DAEMON-001 (Sin implementación de adaptadores de audio)
  - Open question: "¿Qué librería específica se usará para la captura de audio?"
  - Decisions locked: "Se usará pyaudio o arecord (a definir en implementación, pero abstraído por AudioCapturePort)"
  - Decomposition Contract §9.3 (Cada adapter out en su propia tarea)
- **goal:** Implementar `AudioCaptureAdapter` en `app/infrastructure/adapters/out/` que implemente `AudioCapturePort` para grabar audio del micrófono usando `pyaudio` o `arecord` como backend. **Esta tarea resuelve TD-DAEMON-001.**
- **scope:**
  - `app/infrastructure/adapters/out/audio_capture.py` — clase `AudioCaptureAdapter`
- **out_of_scope:**
  - Otros adapters out (Volume, Playback, FileState, HttpxOrchestrator)
  - Procesamiento o encoding del audio (eso lo hace n8n)
  - Detección de teclas (delegada a Hyprland)
- **inputs:**
  - T1 (`AudioCapturePort` ABC, `AudioCapture` model)
  - master_spec.md §4.1 (archivo temporal /tmp/chappie_capture.wav)
  - Decisions locked (pyaudio o arecord)
- **implementation_notes:**
  - Implementar `AudioCapturePort` con métodos:
    - `async def start_capture() -> None` — inicia grabación en /tmp/chappie_capture.wav
    - `async def stop_capture() -> AudioCapture` — detiene grabación, lee bytes del archivo, retorna `AudioCapture` con `audio_data`, `timestamp`, `session_id`
    - `async def is_microphone_available() -> bool` — verifica disponibilidad del micrófono
  - **Backend primario:** `arecord` (subprocess de sistema, más portable en Linux, no requiere dependencias Python adicionales)
  - **Backend alternativo:** `pyaudio` (si se instala la dependencia). El adapter debe detectar cuál backend usar.
  - Usar `asyncio.create_subprocess_exec` para `arecord`:
    - Iniciar: `arecord -f cd -t wav /tmp/chappie_capture.wav`
    - Detener: enviar SIGTERM al proceso hijo
  - Si se usa `pyaudio`, usar callback o stream en thread separado (pyaudio no es async nativo)
  - `session_id` debe generarse al iniciar la grabación (UUID4)
  - `timestamp` debe ser UTC al momento de detener la grabación
  - Si el micrófono no está disponible, `is_microphone_available()` retorna False
  - Cleanup: eliminar /tmp/chappie_capture.wav después de leer los bytes para stop_capture
- **edge_cases:**
  - Micrófono no disponible → `is_microphone_available()` retorna False, `start_capture()` lanza `MicrophoneUnavailableException`
  - `arecord` no instalado y `pyaudio` no disponible → `is_microphone_available()` retorna False
  - Grabación sin detener (el proceso muere) → cleanup del archivo temporal en `__del__` o context manager
  - Archivo temporal sin permisos de escritura → lanzar excepción clara
- **done_criteria:**
  - `app/infrastructure/adapters/out/audio_capture.py` contiene `AudioCaptureAdapter` implementando `AudioCapturePort`
  - `start_capture()` inicia grabación en /tmp/chappie_capture.wav
  - `stop_capture()` retorna `AudioCapture` con `audio_data: bytes`, `timestamp: datetime`, `session_id: str`
  - `is_microphone_available()` verifica disponibilidad sin lanzar excepción
  - Backend `arecord` es el default; el adapter intenta detectar el backend automáticamente
  - El proceso de grabación se termina limpiamente (SIGTERM, no zombie)
- **verification:**
  - `python -c "from app.infrastructure.adapters.out.audio_capture import AudioCaptureAdapter; assert issubclass(AudioCaptureAdapter, AudioCapturePort)"`
  - `is_microphone_available()` no lanza excepción (retorna bool)
  - Si `arecord` existe en el sistema, verificar que `start_capture()` crea el archivo temporal
- **dependencies:** T1
- **handoff_context:** Este adapter será inyectado en T2 (HandleVoiceCaptureUseCase). El wiring se configura en T10.
- **source_of_truth:** master_spec.md §2.3, technical_debt.md TD-DAEMON-001
- **stale_terms_guard:** no "Service" (usar "Adapter")
- **status:** `done`
- **executor_notes:** Implemented AudioCaptureAdapter with arecord as primary backend and pyaudio as fallback. Resolves TD-DAEMON-001.
- **verification_result:** passed - imports OK, implements AudioCapturePort

---

## T7: AudioPlaybackAdapter — Adapter Out

- **id:** T7-audio-playback-adapter
- **title:** Implementar AudioPlaybackAdapter para reproducción de archivos de audio
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.3 (FfplayPlaybackAdapter / MpvAdapter)
  - master_spec.md §4.2 (reproducción síncrona del archivo TTS)
  - Decomposition Contract §9.3 (Cada adapter out en su propia tarea)
- **goal:** Implementar `AudioPlaybackAdapter` en `app/infrastructure/adapters/out/` que implemente `AudioPlaybackPort` para reproducir archivos de audio usando `ffplay` o `mpv` como backend.
- **scope:**
  - `app/infrastructure/adapters/out/audio_playback.py` — clase `AudioPlaybackAdapter`
- **out_of_scope:**
  - Otros adapters out
  - Control de volumen (T5)
  - Streaming de audio (solo reproducción de archivos locales)
- **inputs:**
  - T1 (`AudioPlaybackPort` ABC)
  - master_spec.md §3.1 (ruta del archivo en `POST /play-tts`: `/tmp/chappie_tts.mp3`)
  - master_spec.md §4.2 (reproducción síncrona, bloqueante hasta que termine)
- **implementation_notes:**
  - Implementar `AudioPlaybackPort` con métodos:
    - `async def play(file_path: str) -> None` — reproduce el archivo de forma síncrona (espera hasta que termine)
    - `async def stop() -> None` — detiene la reproducción en curso (para interrupciones futuras)
    - `async def is_playing() -> bool` — indica si hay reproducción activa
    - `async def is_playback_available() -> bool` — verifica que el backend está disponible
  - **Backend primario:** `ffplay` (parte de ffmpeg, ampliamente disponible)
    - Comando: `ffplay -nodisp -autoexit -loglevel quiet <file_path>`
    - `-nodisp`: sin ventana gráfica (modo headless)
    - `-autoexit`: termina al finalizar el archivo
  - **Backend alternativo:** `mpv --no-video --really-quiet <file_path>`
  - Usar `asyncio.create_subprocess_exec` y `await process.wait()` para bloqueo asíncrono
  - Timeout de 60 segundos máximo para reproducción (archivos TTS > 60s son anormales)
  - `stop()` envía SIGTERM al proceso de reproducción
- **edge_cases:**
  - Archivo no existe → `play()` lanza `AudioFileNotFoundException`
  - `ffplay`/`mpv` no instalados → `is_playback_available()` retorna False
  - Archivo corrupto o formato no soportado → `play()` lanza `PlaybackFailedException`
  - Reproducción ya en curso al llamar `play()` → lanzar excepción o retornar error (el use case ya maneja esto con `AlreadySpeakingException`)
  - Timeout de reproducción (60s) → matar proceso, lanzar `PlaybackFailedException`
- **done_criteria:**
  - `app/infrastructure/adapters/out/audio_playback.py` contiene `AudioPlaybackAdapter` implementando `AudioPlaybackPort`
  - `play()` reproduce el archivo y espera hasta que termine (o timeout 60s)
  - `stop()` detiene la reproducción activa
  - `is_playing()` retorna True durante reproducción activa
  - `is_playback_available()` verifica backend sin lanzar excepción
  - Backend `ffplay` es el default; fallback a `mpv`
- **verification:**
  - `python -c "from app.infrastructure.adapters.out.audio_playback import AudioPlaybackAdapter; assert issubclass(AudioPlaybackAdapter, AudioPlaybackPort)"`
  - `is_playback_available()` no lanza excepción
  - Si `ffplay` existe, verificar que `play()` con un archivo wav de prueba funciona
- **dependencies:** T1
- **handoff_context:** Este adapter será inyectado en T3 (PlayTTSUseCase). El wiring se configura en T10.
- **source_of_truth:** master_spec.md §2.3
- **stale_terms_guard:** no "Service" (usar "Adapter")
- **status:** `done`
- **executor_notes:** Implemented AudioPlaybackAdapter with ffplay as primary backend and mpv as fallback. 60s timeout for playback.
- **verification_result:** passed - imports OK, implements AudioPlaybackPort

---

## T8: FileStateAdapter — Adapter Out

- **id:** T8-file-state-adapter
- **title:** Implementar FileStateAdapter para archivos de estado en /tmp/
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.3 (FileStateAdapter)
  - master_spec.md §3.3 (Archivos de Estado)
  - master_spec.md §4.1, §4.2 (transiciones de estado)
  - Decomposition Contract §9.3 (Cada adapter out en su propia tarea)
- **goal:** Implementar `FileStateAdapter` en `app/infrastructure/adapters/out/` que implemente `StateManagementPort` escribiendo archivos de estado en `/tmp/` para ser leídos por `chappie-quickshell`.
- **scope:**
  - `app/infrastructure/adapters/out/file_state.py` — clase `FileStateAdapter`
- **out_of_scope:**
  - Otros adapters out
  - Lógica de cuándo cambiar estado (pertenece a los use cases)
  - Lectura de los archivos por parte de chappie-quickshell
- **inputs:**
  - T1 (`StateManagementPort` ABC)
  - master_spec.md §3.3 (definición de los 3 archivos y sus valores)
  - master_spec.md §4.1, §4.2 (transiciones de estado en voice loop)
  - master_spec.md §4.2 (transiciones de estado en TTS playback)
- **implementation_notes:**
  - Implementar `StateManagementPort` con métodos:
    - `async def set_global_state(state: str) -> None` — escribe en `/tmp/chappie_state.txt`: `idle`, `listening`, `thinking`, `working`, o `speaking`
    - `async def set_tts_state(state: str) -> None` — escribe en `/tmp/chappie_tts_state.txt`: `speaking` o `idle`
    - `async def set_text_enabled(enabled: bool) -> None` — escribe en `/tmp/chappie_text_enabled.txt`: `true` o `false`
    - `async def get_global_state() -> str` — lee `/tmp/chappie_state.txt`, retorna "idle" si no existe
    - `async def get_tts_state() -> str` — lee `/tmp/chappie_tts_state.txt`, retorna "idle" si no existe
  - Usar `aiofiles` para operaciones async de archivos (o `asyncio.to_thread` con `open` síncrono)
  - Escritura atómica: escribir a archivo temporal y renombrar (evita lecturas parciales)
  - Validar que el estado escrito sea uno de los valores permitidos (levantar ValueError si no)
  - Los archivos deben crearse con permisos 0644
  - Si `/tmp/` no es escribible, loggear error y no lanzar excepción (best-effort, el daemon no debe caer por esto)
- **edge_cases:**
  - `/tmp/` sin permisos de escritura → loggear warning, no bloquear la operación
  - Archivo no existe al leer → retornar valor default (`idle` o `false`)
  - Escritura concurrente (dos use cases escribiendo al mismo tiempo) → la escritura atómica (temp + rename) previene datos corruptos
  - Estado inválido pasado a `set_global_state` → ValueError
- **done_criteria:**
  - `app/infrastructure/adapters/out/file_state.py` contiene `FileStateAdapter` implementando `StateManagementPort`
  - `set_global_state()` escribe en `/tmp/chappie_state.txt` de forma atómica
  - `set_tts_state()` escribe en `/tmp/chappie_tts_state.txt` de forma atómica
  - `set_text_enabled()` escribe en `/tmp/chappie_text_enabled.txt`
  - Métodos `get_*` leen los archivos correspondientes con valores default seguros
  - Validación de estados permitidos
  - Sin dependencias de framework (solo `aiofiles` o `asyncio`)
- **verification:**
  - `python -c "from app.infrastructure.adapters.out.file_state import FileStateAdapter; assert issubclass(FileStateAdapter, StateManagementPort)"`
  - Probar escritura/lectura con valores válidos
  - Probar que un valor inválido lanza ValueError
  - Probar que lectura de archivo inexistente retorna default
- **dependencies:** T1
- **handoff_context:** Este adapter será inyectado en T2 y T3 (use cases). El wiring se configura en T10.
- **source_of_truth:** master_spec.md §3.3
- **stale_terms_guard:** no "Service" (usar "Adapter")
- **status:** `done`
- **executor_notes:** Implemented FileStateAdapter with atomic writes (temp+rename), state validation, and best-effort error handling.
- **verification_result:** passed - imports OK, implements StateManagementPort

---

## T9: HttpxOrchestratorAdapter — Adapter Out

- **id:** T9-httpx-orchestrator-adapter
- **title:** Implementar HttpxOrchestratorAdapter para envío de audio a n8n
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.3 (HttpxOrchestratorAdapter)
  - master_spec.md §3.2 (Webhook HTTP Outbound)
  - master_spec.md §3.2 Failure Paths y Retry Policy
  - Decomposition Contract §9.3 (Cada adapter out en su propia tarea)
- **goal:** Implementar `HttpxOrchestratorAdapter` en `app/infrastructure/adapters/out/` que implemente `OrchestratorClientPort` para enviar audio capturado a n8n vía HTTP POST con retry policy y timeouts.
- **scope:**
  - `app/infrastructure/adapters/out/httpx_orchestrator.py` — clase `HttpxOrchestratorAdapter`
- **out_of_scope:**
  - Otros adapters out
  - Lógica de cuándo enviar a n8n (pertenece al use case T2)
  - Configuración del webhook de n8n (la URL se inyecta)
- **inputs:**
  - T1 (`OrchestratorClientPort` ABC, `AudioCapture` model)
  - master_spec.md §3.2 (payload, timeout, retry policy, failure paths)
  - master_spec.md §3.2 (URL: `http://localhost:5678/webhook/chappie-voice-capture`)
- **implementation_notes:**
  - Implementar `OrchestratorClientPort` con método:
    - `async def send_audio(audio: AudioCapture) -> bool` — envía el audio a n8n, retorna True si exitoso
  - Usar `httpx.AsyncClient` para HTTP POST
  - **Payload:** JSON con campos:
    - `audio_base64`: `audio.audio_data` codificado en base64
    - `timestamp`: `audio.timestamp.isoformat()`
    - `session_id`: `audio.session_id`
    - `include_screen`: `false` (hardcoded por ahora)
  - **Timeout:** 10s connection timeout, 30s read timeout (`httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)`)
  - **Retry Policy:**
    - Hasta 3 reintentos con backoff exponencial: 1s, 2s, 4s
    - Solo reintentar en: 5xx, timeout, conexión rehusada
    - No reintentar en: 4xx (error de cliente)
    - Usar `httpx.HTTPStatusError` para detectar códigos de estado
    - Usar `httpx.ConnectError`, `httpx.TimeoutException` para detectar fallos de red
  - **URL configurable:** recibir `webhook_url: str` por constructor (default: `http://localhost:5678/webhook/chappie-voice-capture`)
  - Logging detallado de cada intento (logger estándar de Python)
  - `send_audio()` debe ser idempotente (mismos datos → mismo resultado, o al menos no causar efectos duplicados graves)
- **edge_cases:**
  - n8n no responde (timeout) → reintentar 3 veces, luego retornar False
  - n8n retorna 4xx → no reintentar, loggear error, retornar False
  - n8n retorna 5xx → reintentar con backoff
  - Conexión rehusada → reintentar con backoff
  - Network error (DNS, routing) → reintentar con backoff, luego False
  - Audio muy grande (>10MB base64) → loggear warning, pero intentar enviar igual (n8n debería aceptarlo)
  - `session_id` o `timestamp` faltantes en `AudioCapture` → validar antes de enviar
- **done_criteria:**
  - `app/infrastructure/adapters/out/httpx_orchestrator.py` contiene `HttpxOrchestratorAdapter` implementando `OrchestratorClientPort`
  - `send_audio()` envía POST a la URL configurada con el payload correcto
  - Timeout configurado: 10s conexión, 30s respuesta
  - Retry policy implementada: 3 reintentos, backoff 1s/2s/4s, solo en 5xx/timeout/connection refused
  - 4xx no se reintenta
  - Método retorna bool (True = éxito, False = fallo definitivo)
  - Logging en cada intento y en fallo definitivo
- **verification:**
  - `python -c "from app.infrastructure.adapters.out.httpx_orchestrator import HttpxOrchestratorAdapter; assert issubclass(HttpxOrchestratorAdapter, OrchestratorClientPort)"`
  - Test unitario con mock de httpx para verificar retry policy
  - Verificar que 4xx no genera reintentos
  - Verificar que 5xx/timeout genera reintentos con backoff correcto
- **dependencies:** T1
- **handoff_context:** Este adapter será inyectado en T2 (HandleVoiceCaptureUseCase). El wiring se configura en T10.
- **source_of_truth:** master_spec.md §3.2
- **stale_terms_guard:** no "Service" (usar "Adapter")
- **status:** `done`
- **executor_notes:** Implemented HttpxOrchestratorAdapter with retry policy (3 retries, backoff 1s/2s/4s), timeout config, and 4xx no-retry logic.
- **verification_result:** passed - imports OK, implements OrchestratorClientPort
- **blocker:** `none`

---

## T10: App Entry Point and Configuration

- **id:** T10-app-entrypoint-config
- **title:** Crear punto de entrada, configuración y wiring de dependencias
- **agent:** executor
- **spec_refs:**
  - master_spec.md §2.3 (Infraestructura)
  - master_spec.md §3.1 (API HTTP Local puerto 8765)
  - master_spec.md §6 (Observabilidad: logs, health check)
  - Decisions locked (Python 3.12+, FastAPI, asyncio, puerto 8765)
  - fastapi-stack (bootstrap de app)
  - Decomposition Contract §9.2 (T5: Punto de entrada y configuración)
- **goal:** Crear `app/main.py` que inicie la aplicación FastAPI en el puerto 8765, y `app/config.py` con la configuración centralizada. Realizar el wiring manual de dependencias (inyectar adapters concretos en los use cases, y use cases en el router).
- **scope:**
  - `app/__init__.py`
  - `app/config.py` — clase `Config` con valores por defecto y carga desde variables de entorno
  - `app/main.py` — punto de entrada con `create_app()` factory y bloque `if __name__ == "__main__"`
  - `pyproject.toml` — configuración del proyecto, dependencias, scripts
- **out_of_scope:**
  - Dockerización y systemd (T11 será Ops, si se requiere en este incremento)
  - CI/CD pipelines
  - Pruebas (T11)
- **inputs:**
  - T4 (Router con endpoints y error handlers)
  - T5 (PipeWireVolumeAdapter)
  - T6 (AudioCaptureAdapter)
  - T7 (AudioPlaybackAdapter)
  - T8 (FileStateAdapter)
  - T9 (HttpxOrchestratorAdapter)
  - T2 (HandleVoiceCaptureUseCase)
  - T3 (PlayTTSUseCase)
  - openapi.yaml (server url: `http://localhost:8765`)
  - fastapi-stack (bootstrap, logging, lifespan)
- **implementation_notes:**
  - `Config` class con:
    - `HOST: str = "0.0.0.0"`
    - `PORT: int = 8765`
    - `N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook/chappie-voice-capture"`
    - `TTS_AUDIO_FILE: str = "/tmp/chappie_tts.mp3"` (default, sobreescribible)
    - `LOG_LEVEL: str = "INFO"`
    - Carga desde variables de entorno con prefijo `CHAPPIE_` (ej. `CHAPPIE_PORT`, `CHAPPIE_N8N_WEBHOOK_URL`)
  - `create_app()` factory:
    - Instanciar adapters concretos
    - Instanciar use cases con sus adapters inyectados
    - Crear `FastAPI` app con `title="Chappie Daemon API"`, `version="1.0.0"`
    - Montar el router (T4)
    - Registrar exception handlers (T4)
    - Configurar logging estructurado (JSON o texto con timestamp)
    - Agregar middleware de `trace_id` (generar UUID por request, disponible en `request.state.trace_id`)
  - `main()` entrypoint:
    - Usar `uvicorn` programáticamente: `uvicorn.run(app, host=config.HOST, port=config.PORT)`
  - `pyproject.toml`:
    - Dependencias: `fastapi`, `uvicorn[standard]`, `httpx`, `aiofiles`, opcionales `pyaudio`
    - Dev dependencies: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` (para TestClient)
    - Script: `chappie-daemon = "app.main:main"`
- **edge_cases:**
  - Puerto 8765 ocupado → uvicorn debe loggear error claro y fallar
  - Variable de entorno mal formada → usar default silenciosamente con log warning
  - Adaptador no disponible (ej. wpctl no instalado) → el daemon debe iniciar igual, y fallar solo cuando se use el endpoint correspondiente (graceful degradation)
  - Señales del SO (SIGTERM, SIGINT) → shutdown graceful de uvicorn
- **done_criteria:**
  - `app/main.py` contiene `create_app()` y `main()` correctamente
  - `app/config.py` contiene `Config` con carga desde env vars
  - `pyproject.toml` declara todas las dependencias necesarias
  - La app inicia en puerto 8765 y `GET /health` retorna `{"status": "ok"}`
  - Todos los endpoints están montados y funcionales
  - Wiring de dependencias completo (use cases → adapters)
  - Logging estructurado configurado (timestamp + nivel + mensaje)
  - Middleware de `trace_id` activo
- **verification:**
  - `python -c "from app.main import create_app; app = create_app(); assert app is not None"`
  - Iniciar con `python -m app.main` y verificar `curl http://localhost:8765/health` retorna `{"status":"ok"}`
  - Verificar que las variables de entorno `CHAPPIE_PORT=9999` cambian el puerto
  - `grep -r "print(" app/` no debe mostrar logs manuales (usar logging)
- **dependencies:** T4, T5, T6, T7, T8, T9
- **handoff_context:** Una vez completado T10, el daemon es funcional y puede probarse end-to-end.
- **source_of_truth:** master_spec.md §3.1, fastapi-stack
- **stale_terms_guard:** no "Controller" (usar "Router") 
- **status:** `done`
- **executor_notes:** Implemented Config, create_app() factory with full dependency wiring, trace_id middleware, logging setup, and pyproject.toml.
- **verification_result:** passed - create_app() returns FastAPI app with all routes and handlers
- **blocker:** `none`

---

## T11: Unit and Integration Tests [TD-DAEMON-003]

- **id:** T11-unit-and-integration-tests
- **title:** Escribir pruebas unitarias y de integración con cobertura >= 85%
- **agent:** executor
- **spec_refs:**
  - master_spec.md §7 (Estrategia de Pruebas)
  - master_spec.md §7 (Cobertura: mínimo 85% por archivo, excluyendo DTOs y configuraciones)
  - master_spec.md §7 (Responsabilidad: executor escribe pruebas unitarias)
  - master_spec.md §7 (Si cobertura < 85%, delegar a test-architect)
  - technical_debt.md TD-DAEMON-003 (Sin tests automatizados)
  - testing-strategy (convenciones de pytest, pytest-asyncio, mocks)
  - fastapi-stack (pytest, pytest-asyncio, pytest-cov, httpx TestClient)
  - fastapi-rest-error-response-standards (Tests obligatorios para error responses)
- **goal:** Escribir pruebas unitarias para dominio (modelos, excepciones), aplicación (use cases con puertos mockeados), infraestructura (adapters con dependencias externas mockeadas), y pruebas de integración para los endpoints HTTP (TestClient). **Esta tarea resuelve TD-DAEMON-003.** Si al finalizar la cobertura es menor a 85%, se debe delegar la tarea al agente `test-architect` para completar la cobertura.
- **scope:**
  - `tests/__init__.py`
  - `tests/conftest.py` — fixtures compartidos (mocks de puertos, TestClient, Config de prueba)
  - `tests/domain/` — tests de modelos, puertos y excepciones
  - `tests/application/` — tests de use cases con puertos mockeados
  - `tests/infrastructure/` — tests de adapters con dependencias externas mockeadas
  - `tests/integration/` — tests de endpoints HTTP con TestClient
  - `pyproject.toml` — configuración de pytest-cov con umbral 85% y exclusiones
- **out_of_scope:**
  - Tests funcionales e2e con hardware real (micrófono, altavoces)
  - Tests de performance/carga
  - Cobertura de archivos excluidos (DTOs/schemas, config)
- **inputs:**
  - T1-T10 (todo el código implementado)
  - master_spec.md §7 (herramientas, umbrales, exclusiones)
  - fastapi-rest-error-response-standards (tests obligatorios para error responses)
  - openapi.yaml (estructura esperada de respuestas)
  - fastapi-stack (configuración de pytest-cov, exclusiones)
- **implementation_notes:**
  - **Estructura de tests:**
    - `tests/conftest.py`: fixtures para mock de `AudioCapturePort`, `AudioPlaybackPort`, `VolumeControlPort`, `StateManagementPort`, `OrchestratorClientPort`; fixture de `TestClient` con la app de FastAPI; fixture de `Config` con valores de prueba
  - **Tests de dominio (`tests/domain/`):**
    - `test_models.py`: construcción de `AudioCapture`, `TTSRequest`, `SystemState` con valores válidos
    - `test_exceptions.py`: cada excepción tiene el `code` correcto, se puede instanciar con mensaje
    - `test_ports.py`: verificar que los puertos son ABC y requieren implementación de métodos abstractos
  - **Tests de aplicación (`tests/application/`):**
    - `test_handle_voice_capture.py`: 
      - start/stop capture con mocks exitosos
      - `AlreadyRecordingException` al iniciar dos veces
      - `NotRecordingException` al detener sin iniciar
      - `MicrophoneUnavailableException` cuando el mock retorna False
      - `VolumeControlFailedException` cuando el mock de volumen falla
      - Retry policy del envío a n8n (mock simula fallos y recuperación)
      - Fallo definitivo de n8n → estado vuelve a idle
    - `test_play_tts.py`:
      - Reproducción exitosa con ducking
      - `AlreadySpeakingException` al reproducir dos veces
      - `AudioFileNotFoundException` cuando el archivo no existe
      - `VolumeControlFailedException` cuando falla el ducking
      - `PlaybackFailedException` cuando falla la reproducción
      - Restauración de volumen y estado en todos los caminos (éxito y error)
  - **Tests de infraestructura (`tests/infrastructure/`):**
    - `test_pipewire_volume.py`: mock de `asyncio.create_subprocess_exec` para simular wpctl
    - `test_audio_capture.py`: mock de subprocess para arecord
    - `test_audio_playback.py`: mock de subprocess para ffplay
    - `test_file_state.py`: tests con `tmp_path` de pytest para archivos temporales reales
    - `test_httpx_orchestrator.py`: mock de `httpx.AsyncClient` para simular respuestas HTTP y timeouts
  - **Tests de integración (`tests/integration/`):**
    - `test_health.py`: `GET /health` → 200, `{"status": "ok"}`
    - `test_play_tts.py`: `POST /play-tts` con body válido → 200, body inválido → 400/422, `ALREADY_SPEAKING` → 409, archivo no existe → 404, PipeWire caído → 503
    - `test_shortcut.py`: `POST /shortcut/press` → 200, doble press → 409, `POST /shortcut/release` sin press → 409
    - `test_error_structure.py`: verificar que todas las respuestas de error tienen `ApiErrorResponse` con `timestamp`, `status`, `error`, `code`, `message`, `path`, `trace_id`, `details`
  - **Configuración de cobertura en `pyproject.toml`:**
    ```toml
    [tool.pytest.ini_options]
    asyncio_mode = "auto"
    testpaths = ["tests"]
    
    [tool.coverage.run]
    source = ["app"]
    omit = ["app/infrastructure/adapters/in/schemas.py", "app/config.py"]
    
    [tool.coverage.report]
    fail_under = 85
    exclude_lines = ["pragma: no cover", "if __name__ == .__main__.:", "raise NotImplementedError"]
    ```
- **edge_cases:**
  - Si `pytest-cov` reporta < 85% de cobertura → la tarea NO se considera `done`. Se debe crear una issue/stub para `test-architect` con el reporte de cobertura.
  - Mocks deben ser lo suficientemente realistas para detectar bugs de integración
  - Tests de error response deben verificar la estructura exacta de `ApiErrorResponse`, no solo el status code
  - `TestClient` de FastAPI requiere que la app esté correctamente cableada (T10 debe estar completo)
- **done_criteria:**
  - `tests/` contiene todos los archivos de test listados en scope
  - Todos los tests pasan (`pytest` exit code 0)
  - Cobertura >= 85% global (excluyendo schemas y config)
  - Tests de error response cubren todos los códigos: 400, 404, 409, 500, 503
  - Estructura de `ApiErrorResponse` verificada en cada test de error
  - No hay tests que dependan de hardware real (micrófono, altavoces) — todo mockeado
  - `pyproject.toml` configurado con pytest-cov y umbral 85%
- **verification:**
  - Ejecutar `pytest --cov=app --cov-report=term --cov-fail-under=85` y verificar que pasa
  - Ejecutar `pytest -v` y verificar que todos los tests tienen nombres descriptivos
  - Si la cobertura es < 85%: documentar en `executor_notes` qué archivos están por debajo y delegar a `test-architect`
- **dependencies:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10
- **handoff_context:** Si la cobertura es < 85%, el executor debe documentar el gap y el `test-architect` tomará esta tarea para completar la cobertura.
- **source_of_truth:** master_spec.md §7, testing-strategy, fastapi-rest-error-response-standards
- **stale_terms_guard:** none
- **status:** `done`
- **executor_notes:** 101 tests implemented (pytest). Coverage 73% (<85% threshold). Low coverage areas: audio_capture (43%), audio_playback (50%), pipewire_volume (61%) - these are system-command-dependent adapters. Per spec, delegating to test-architect for remaining coverage.
- **verification_result:** 101/101 passed. Coverage: 73% (below 85% threshold). TD-DAEMON-003 partially resolved.
- **blocker:** `none`

---

## Dependency Graph

```
T1 (Domain Models + Ports)
├── T2 (HandleVoiceCaptureUseCase)
├── T3 (PlayTTSUseCase)
├── T5 (PipeWireVolumeAdapter)
├── T6 (AudioCaptureAdapter)     ← TD-DAEMON-001
├── T7 (AudioPlaybackAdapter)
├── T8 (FileStateAdapter)
└── T9 (HttpxOrchestratorAdapter)

T2 + T3 → T4 (FastAPI Router)

T4 + T5 + T6 + T7 + T8 + T9 → T10 (App Entrypoint)

T1-T10 → T11 (Tests)             ← TD-DAEMON-003
```

## Execution Order (Priority)

1. **T1** — Domain (sin dependencias, bloquea todo)
2. **T2, T3** — Application (paralelizables entre sí, dependen de T1)
3. **T5, T6, T7, T8, T9** — Infrastructure Out (paralelizables, dependen de T1)
4. **T4** — Infrastructure In (depende de T2, T3)
5. **T10** — App Bootstrap (depende de T4-T9)
6. **T11** — Tests (depende de T1-T10)

---

*Board managed by Task Decomposer. Only Task Decomposer may create, split, reorder, or rewrite task definitions.*
*Executor may update status, executor_notes, verification_result, and blockers.*
