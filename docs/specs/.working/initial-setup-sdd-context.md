# Shared Context - Chappie Daemon Initial Setup

## Current status
executed

## Canonical artifacts
- Master Spec: `/home/cristiansrc/Documentos/Proyectos/chappie-workspace/projects/chappie-daemon/docs/specs/master_spec.md`
- OpenAPI: `/home/cristiansrc/Documentos/Proyectos/chappie-workspace/projects/chappie-daemon/docs/api/openapi.yaml`
- Global Master Spec: `/home/cristiansrc/Documentos/Proyectos/chappie-workspace/docs/specs/master_spec.md`
- Global System Landscape: `/home/cristiansrc/Documentos/Proyectos/chappie-workspace/docs/architecture/system-landscape.md`

## Artifact evidence
- `master_spec.md`: Creado con la definición de arquitectura hexagonal, contratos de integración y reglas de negocio.
- `openapi.yaml`: Creado con los endpoints `POST /play-tts` y `GET /health`.

## Spec Validator Approval
verdict: ready
reviewed_at: 2026-06-14T12:00:00Z
validator_agent: spec-validator
artifact_set_reviewed: 
- /home/cristiansrc/Documentos/Proyectos/chappie-workspace/projects/chappie-daemon/docs/specs/master_spec.md
- /home/cristiansrc/Documentos/Proyectos/chappie-workspace/projects/chappie-daemon/docs/api/openapi.yaml
- /home/cristiansrc/Documentos/Proyectos/chappie-workspace/projects/chappie-daemon/docs/specs/technical_debt.md
summary: All findings resolved. OpenAPI error response matches standards, decomposition contract added, failure paths and timeouts defined, technical debt file created.
invalidated_by_changes_since: none

## Human Plan Approval: approved_by_user

## Decisions locked
- **Stack Tecnológico:** Python 3.12+, FastAPI, asyncio.
- **Arquitectura:** Hexagonal estricta (Dominio, Aplicación, Infraestructura).
- **Control de Volumen:** Se usará `wpctl` (PipeWire) para el volume ducking.
- **Captura de Audio:** Se usará `pyaudio` o `arecord` (a definir en implementación, pero abstraído por `AudioCapturePort`).
- **Detección de Atajos:** Se delega al compositor (Hyprland). El compositor llamará a los endpoints `POST /shortcut/press` y `POST /shortcut/release` del daemon. Esto evita problemas de permisos y compatibilidad de keyloggers globales en Wayland.
- **Comunicación con n8n:** HTTP POST directo al webhook de n8n.

## Validator findings
Ninguno.

## Resolved findings
1. **[high] OpenAPI Error Response Mismatch** — CORREGIDO: `ErrorResponse.details` en `openapi.yaml` ahora es un array de `ApiErrorDetail` (objects con `field`, `code`, `message`, `rejected_value`). Se añadió el schema `ApiErrorDetail`.
2. **[medium] Missing Decomposition Contract** — CORREGIDO: Añadida sección `9. Decomposition Contract` en `master_spec.md` con límites de tareas, estructura recomendada, reglas de descomposición y priorización.
3. **[medium] Missing Failure Paths and Timeouts** — CORREGIDO: Actualizada sección 3.2 con timeout (10s conexión, 30s respuesta), retry policy (3 reintentos, backoff exponencial) y failure paths. Añadidos failure paths en secciones 4.1 y 4.2. Añadidos códigos de error `409` y `503` en `openapi.yaml` para todos los endpoints.
4. **[low] Missing Technical Debt File** — CORREGIDO: Creado `docs/specs/technical_debt.md` con estructura base y deuda activa del proyecto.

## Open questions
- ¿Qué librería específica se usará para la captura de audio (`pyaudio`, `sounddevice`, o llamadas a sistema como `arecord`)? Se abstraerá en la infraestructura, pero es bueno tenerlo en cuenta para las dependencias.

## Stale terms guard
- No usar "Controller" (usar "Router" o "Adapter In").
- No usar "Service" para lógica de negocio pura (usar "UseCase").
- No usar "DTO" en el dominio (usar "Model" o "Entity").

## Next action
Task Decomposer to create task board
