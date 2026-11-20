"""Text-to-speech through the gpu4 LiteLLM gateway (Qwen3-TTS CustomVoice).

The gateway serves `POST /v1/audio/speech` and always returns MP3, whatever
`response_format` asks for, so this module requests and reports MP3 only.
"""

from __future__ import annotations

import base64

import httpx

from ai_services.backends import BackendError, backend_request
from ai_services.config import Settings
from ai_services.schemas import TtsRequest, TtsResponse

MEDIA_TYPE = "audio/mpeg"


def synthesize_speech(
    request: TtsRequest,
    settings: Settings,
    *,
    transport: httpx.BaseTransport | None = None,
) -> tuple[bytes, TtsResponse]:
    model = request.model or settings.tts_model
    voice = request.voice or settings.tts_voice

    payload: dict = {
        "model": model,
        "input": request.text,
        "voice": voice,
        "response_format": "mp3",
    }
    if request.instructions:
        payload["instructions"] = request.instructions

    response = backend_request(
        "TTS",
        "POST",
        settings.tts_base_url.rstrip("/") + "/audio/speech",
        api_key=settings.tts_api_key,
        timeout_seconds=settings.tts_timeout_seconds,
        transport=transport,
        json=payload,
    )
    audio = response.content
    if not audio:
        raise BackendError("TTS", "returned empty audio")
    return audio, TtsResponse(
        model=model,
        voice=voice,
        format="mp3",
        media_type=MEDIA_TYPE,
        size_bytes=len(audio),
        audio_base64=base64.b64encode(audio).decode("ascii"),
    )


def tts_runtime_status(settings: Settings) -> dict:
    return {"base_url": settings.tts_base_url, "model": settings.tts_model, "voice": settings.tts_voice}
