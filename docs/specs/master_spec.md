# Master Spec - Chappie Daemon

**Estado:** awaiting-human-plan-approval  
**Owner:** Planner  
**Última actualización:** 2026-06-14  
**Proyecto:** chappie-daemon  

---

## 1. Propósito del Sistema

`chappie-daemon` es el componente local responsable de la captura de audio, control de volumen (ducking), reproducción de síntesis de voz (TTS) y gestión de estado visual para el ecosistema Chappie. Actúa como el puente entre el hardware local (micrófono, altavoces, teclado) y el orquestador central (n8n).

---

## 2. Arquitectura (Hexagonal)

El proyecto sigue una Arquitectura Hexagonal estricta implementada en Python 3.12+ con `asyncio` y `FastAPI`.

### 2.1 Dominio (`app/domain`)
- **Modelos:** `AudioCapture`, `TTSRequest`, `SystemState`.
- **Puertos (Interfaces):**
  - `AudioCapturePort`: Para grabar audio del micrófono.
  - `AudioPlaybackPort`: Para reproducir archivos de audio.
  - `VolumeControlPort`: Para aplicar y restaurar volume ducking.
  - `ShortcutDetectionPort`: Para detectar el atajo global (SUPER+ALT+C).
  - `StateManagementPort`: Para escribir el estado en archivos temporales.
  - `OrchestratorClientPort`: Para enviar el audio capturado a n8n.

### 2.2 Aplicación (`app/application`)
- **Casos de Uso:**
  - `HandleVoiceCaptureUseCase`: Orquesta la detección del atajo, ducking, grabación, restauración de volumen y envío a n8n.
  - `PlayTTSUseCase`: Orquesta la recepción de una solicitud TTS, ducking, escritura de estado "speaking", reproducción, restauración de volumen y escritura de estado "idle".

### 2.3 Infraestructura (`app/infrastructure`)
- **Adapters In:**
  - `FastAPI Router`: Expone los endpoints `POST /play-tts`, `POST /shortcut/press` y `POST /shortcut/release`.
  - `ShortcutListener`: Eliminado. Decisión arquitectónica: El asistente operará exclusivamente bajo Hyprland. Se usarán los endpoints HTTP llamados por el compositor.
- **Adapters Out:**
  - `PipeWireVolumeAdapter`: Implementa `VolumeControlPort` usando comandos de sistema (`wpctl`).
  - `PyAudioCaptureAdapter` / `ArecordAdapter`: Implementa `AudioCapturePort`.
  - `FfplayPlaybackAdapter` / `MpvAdapter`: Implementa `AudioPlaybackPort`.
  - `FileStateAdapter`: Implementa `StateManagementPort` escribiendo en `/tmp/`.
  - `HttpxOrchestratorAdapter`: Implementa `OrchestratorClientPort` enviando POST a n8n.

---

## 3. Contratos de Integración

### 3.1 API HTTP Local (Inbound)
Expuesta vía FastAPI en el puerto `8765`.

**Endpoint:** `POST /play-tts`
- **Propósito:** Recibe una solicitud para reproducir un archivo de audio TTS generado por `chappie-notification`.
- **Request Body (JSON):**
  ```json
  {
    "audio_file": "/tmp/chappie_tts.mp3",
    "text": "Texto que se está reproduciendo",
    "ducking": true
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "status": "success",
    "message": "Audio played successfully"
  }
  ```

**Endpoint:** `POST /shortcut/press`
- **Propósito:** Inicia la grabación de voz y aplica ducking. Llamado por el compositor (ej. Hyprland) al presionar el atajo.
- **Response (200 OK):** `{"status": "success", "message": "Recording started"}`

**Endpoint:** `POST /shortcut/release`
- **Propósito:** Detiene la grabación, restaura el volumen y envía el audio a n8n. Llamado por el compositor al soltar el atajo.
- **Response (200 OK):** `{"status": "success", "message": "Recording stopped and sent"}`

### 3.2 Webhook HTTP (Outbound)
Enviado a n8n.

**Endpoint:** `POST http://localhost:5678/webhook/chappie-voice-capture`
- **Propósito:** Enviar el audio capturado para su procesamiento.
- **Payload (Multipart/Form-Data o JSON con Base64):**
  ```json
  {
    "audio_base64": "<base64_encoded_wav>",
    "timestamp": "2026-06-14T12:00:00Z",
    "session_id": "uuid",
    "include_screen": false
  }
  ```
- **Timeout:** 10 segundos para el establecimiento de conexión. 30 segundos para la respuesta completa.
- **Retry Policy:** Hasta 3 reintentos con backoff exponencial (1s, 2s, 4s). Si todos fallan, se registra el error en logs y se descarta el audio. No se reintenta en segundo plano para no bloquear nuevos ciclos de captura.
- **Failure Paths:**
  - `4xx` (ej. webhook mal configurado): No reintentar. Loggear error y continuar.
  - `5xx` / timeout / conexión rehusada: Aplicar retry policy. Si se agotan los reintentos, loggear y descartar.
  - **n8n caído (conexión rehusada):** Se reintenta hasta 3 veces. Si persiste, se descarta el audio y se actualiza `/tmp/chappie_state.txt` a `idle`. El usuario no recibe respuesta del asistente.
  - **Error de red (DNS, routing):** Mismo comportamiento que n8n caído.

### 3.3 Archivos de Estado (Outbound)
Escritos en `/tmp/` para ser leídos por `chappie-quickshell`.

- `/tmp/chappie_tts_state.txt`: Contiene `speaking` o `idle`.
- `/tmp/chappie_text_enabled.txt`: Contiene `true` o `false`.
- `/tmp/chappie_state.txt`: Contiene `idle`, `listening`, `thinking`, `working`, o `speaking`.

---

## 4. Reglas de Negocio

### 4.1 Flujo de Captura de Voz (Voice Loop)
1. El compositor (Hyprland) detecta que el usuario presiona `SUPER+ALT+C` y llama a `POST /shortcut/press`.
2. Se aplica volume ducking (reducción al 10%) en todos los sinks de audio activos.
3. Se actualiza `/tmp/chappie_state.txt` a `listening`.
4. Se inicia la grabación del micrófono en memoria o archivo temporal (`/tmp/chappie_capture.wav`).
5. El compositor detecta que el usuario suelta `SUPER+ALT+C` y llama a `POST /shortcut/release`.
6. Se detiene la grabación.
7. Se restaura el volumen original en todos los sinks.
8. Se actualiza `/tmp/chappie_state.txt` a `thinking`.
9. Se envía el audio a n8n vía HTTP POST.

**Failure Paths - Captura de Voz:**
- **`POST /shortcut/press` mientras ya se está grabando:** Responder `409 Conflict` con código `ALREADY_RECORDING`. No iniciar nueva grabación ni modificar el ducking.
- **`POST /shortcut/release` sin grabación activa:** Responder `409 Conflict` con código `NOT_RECORDING`. No realizar ninguna acción.
- **Micrófono no disponible al llamar a `/shortcut/press`:** Responder `503 Service Unavailable` con código `MICROPHONE_UNAVAILABLE`. No aplicar ducking ni cambiar estado.
- **Error de PipeWire al aplicar ducking:** Responder `503 Service Unavailable` con código `VOLUME_CONTROL_FAILED`. No iniciar grabación.
- **Error al enviar audio a n8n en paso 9:** Ver política de reintentos en sección 3.2. Si falla definitivamente, actualizar estado a `idle` y registrar error en logs.

### 4.2 Flujo de Reproducción TTS
1. Se recibe `POST /play-tts`.
2. Si `ducking` es true, se aplica volume ducking al 10%.
3. Se actualiza `/tmp/chappie_tts_state.txt` a `speaking`.
4. Se actualiza `/tmp/chappie_state.txt` a `speaking`.
5. Se reproduce el archivo de audio de forma síncrona (bloqueando hasta que termine).
6. Al finalizar, se restaura el volumen original.
7. Se actualiza `/tmp/chappie_tts_state.txt` a `idle`.
8. Se actualiza `/tmp/chappie_state.txt` a `idle`.

**Failure Paths - Reproducción TTS:**
- **`POST /play-tts` mientras ya se está reproduciendo:** Responder `409 Conflict` con código `ALREADY_SPEAKING`. No encolar la reproducción. La solicitud debe ser reintentada por el emisor (chappie-notification) si es necesario.
- **Archivo de audio inexistente en `audio_file`:** Responder `404 Not Found` con código `AUDIO_FILE_NOT_FOUND`. Restaurar volumen si se aplicó ducking. Estado permanece `idle`.
- **PipeWire no disponible al aplicar ducking o reproducir:** Responder `503 Service Unavailable` con código `PLAYBACK_FAILED`. Estado vuelve a `idle`.

---

## 5. Seguridad y Permisos
- El daemon debe ejecutarse en el espacio de usuario (sin `sudo`).
- Requiere acceso al servidor de audio (PipeWire/PulseAudio).
- Requiere permisos para leer eventos de entrada (teclado) si se usa `evdev` (puede requerir pertenecer al grupo `input`).

---

## 6. Observabilidad
- **Logs:** Salida estándar (stdout/stderr) capturada por systemd (journalctl). Formato estructurado (JSON o texto claro con timestamps).
- **Health Check:** Endpoint `GET /health` en FastAPI que retorna `{"status": "ok"}`.

---

## 7. Estrategia de Pruebas
- **Unitarias:** `pytest` con `pytest-asyncio`. Mocks para puertos de infraestructura (audio, teclado, red).
- **Cobertura:** Mínimo 85% por archivo (excluyendo DTOs y configuraciones).
- **Integración:** Pruebas del router FastAPI usando `TestClient`.
- **Responsabilidad:** El agente `executor` debe escribir las pruebas unitarias durante la implementación. Si al finalizar la cobertura es menor al 85%, se debe delegar la tarea al agente `test-architect` para completar la cobertura.

---

## 8. Criterios de Aceptación Globales
- [ ] El daemon inicia correctamente y expone el puerto 8765.
- [ ] Presionar SUPER+ALT+C reduce el volumen del sistema e inicia la grabación.
- [ ] Soltar SUPER+ALT+C restaura el volumen y envía el audio a n8n.
- [ ] Recibir un POST en `/play-tts` reduce el volumen, reproduce el audio, actualiza los archivos de estado y restaura el volumen al terminar.
- [ ] La arquitectura respeta los límites de la Arquitectura Hexagonal (Dominio sin dependencias de framework).

---

## 9. Decomposition Contract

### 9.1 Límites de Tareas
Cada tarea atómica debe cumplir:
- **Scope máximo:** Una sola capa arquitectónica por tarea (Dominio, Aplicación o Infraestructura).
- **Tamaño máximo:** ~200-300 líneas de código nuevo por tarea. Si un archivo excede este límite, dividir en múltiples tareas.
- **Responsabilidad única:** Una tarea no puede mezclar lógica de negocio con configuración de infraestructura.

### 9.2 Estructura de Tareas Recomendada
| Tarea | Capa | Dependencias |
|---|---|---|
| T1: Modelos de dominio y puertos | Domain | Ninguna |
| T2: Casos de uso (aplicación) | Application | T1 |
| T3: Router FastAPI (adapters in) | Infrastructure | T2 |
| T4: Adaptadores out (audio, volumen, estado, n8n) | Infrastructure | T1 |
| T5: Punto de entrada y configuración de la app | Infrastructure | T3, T4 |
| T6: Dockerización y systemd | Infrastructure | T5 |
| T7: Tests unitarios e integración | Testing | T1-T5 |

### 9.3 Reglas de Descomposición
- **No mezclar inbound y outbound adapters** en la misma tarea.
- **No mezclar casos de uso** (HandleVoiceCaptureUseCase y PlayTTSUseCase son tareas separadas).
- **Los puertos (interfaces) pertenecen al dominio** y deben definirse antes que los adapters.
- **Cada adapter out debe implementarse en su propia tarea** para mantener independencia.
- **Los tests deben planificarse como tarea final** después de tener todas las implementaciones.

### 9.4 Priorización
1. T1 (Dominio) → T2 (Aplicación) → T3+T4 (Infraestructura) → T5 (App bootstrap) → T6 (Ops) → T7 (Tests)
2. Si hay restricciones de tiempo, priorizar T1+T2+T3 (ruta crítica: poder recibir y responder requests HTTP).
