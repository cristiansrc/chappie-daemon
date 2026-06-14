# chappie-daemon

**Servicio de captura de voz, control de audio y reproducción TTS**

---

## Responsabilidad

- Grabación de audio del micrófono (modo walkie-talkie)
- Control de volumen adaptativo (volume ducking) durante grabación y reproducción
- Transcripción de voz a texto (STT) via Gemini API
- Reproducción de audio TTS generado
- API HTTP para comunicación con chappie-notification
- Script de control (START/STOP/TOGGLE_TEXT)

## Estado

**Pendiente** - Será implementado en Fase 1

## Estructura Esperada

```
chappie-daemon/
├── src/
│   ├── daemon.py              # Daemon principal (asyncio + Unix socket)
│   ├── audio_capture.py       # Grabación y control de volumen
│   ├── stt_client.py          # Cliente STT (Gemini, Whisper fallback)
│   ├── tts_player.py          # Reproductor TTS con volume ducking
│   ├── n8n_client.py          # Cliente HTTP para n8n webhooks
│   └── client.sh              # Script de control (START/STOP/TOGGLE_TEXT)
├── config/
│   ├── config.yaml            # Configuración general
│   ├── tts-config.yaml        # Configuración de TTS y volume ducking
│   └── commands-whitelist.yaml # Comandos permitidos
├── requirements.txt
└── README.md
```

## Dependencias

- Python 3.12+
- sounddevice (grabación de audio)
- numpy (procesamiento de audio)
- requests (HTTP client)
- python-dotenv (variables de entorno)
- PyYAML (configuración)

## Puertos

- 8765: HTTP API (play-tts, status)

## Archivos de Estado

- `/tmp/chappie_state.txt` - Estado del daemon (idle/listening/thinking/working/speaking)
- `/tmp/chappie_tts_text.txt` - Texto TTS actual
- `/tmp/chappie_tts_state.txt` - Estado TTS (speaking/idle)
- `/tmp/chappie_text_enabled.txt` - Toggle de texto (true/false)
- `/tmp/chappie_capture.wav` - Audio capturado temporal

## Integraciones

- **n8n:** POST a webhook de voice capture
- **chappie-notification:** Recibe audio TTS para reproducción
- **chappie-quickshell:** Provee archivos de estado

---

*Proyecto parte del workspace chappie-workspace*
