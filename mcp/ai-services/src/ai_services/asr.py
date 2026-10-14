"""Speech-to-text through an OpenAI-compatible `/audio/transcriptions` gateway."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from ai_services.backends import BackendError, backend_request
from ai_services.config import Settings
from ai_services.schemas import AsrResponse, Segment

# The gateway accepts at most 100 MiB per upload; larger audio is re-encoded to a
# 48 kbps mono mp3 (~21 MB per hour) when ffmpeg is available.
DIRECT_UPLOAD_MAX_BYTES = 24 * 1024 * 1024
UPLOAD_MAX_BYTES = 95 * 1024 * 1024


def parse_transcription(payload: Any) -> tuple[str, list[Segment]]:
    if not isinstance(payload, dict):
        raise BackendError("ASR", "returned a non-object response")
    text = str(payload.get("text") or "").strip()
    segments: list[Segment] = []
    for item in payload.get("segments") or []:
        if not isinstance(item, dict):
            continue
        segment_text = str(item.get("text") or "").strip()
        if not segment_text:
            continue
        start, end = item.get("start"), item.get("end")
        segments.append(
            Segment(
                start=float(start) if isinstance(start, (int, float)) else None,
                end=float(end) if isinstance(end, (int, float)) else None,
                text=segment_text,
            )
        )
    if not segments and text:
        segments.append(Segment(text=text))
    return text, segments


def _compact_for_upload(source: Path, workdir: Path) -> Path:
    if source.stat().st_size <= DIRECT_UPLOAD_MAX_BYTES or not shutil.which("ffmpeg"):
        return source
    compact = workdir / "upload.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-vn",
            "-ac", "1", "-ar", "16000", "-codec:a", "libmp3lame", "-b:a", "48k", str(compact),
        ],
        check=True,
    )
    return compact


def transcribe_audio(
    filename: str,
    data: bytes,
    settings: Settings,
    *,
    language: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> AsrResponse:
    name = Path(filename or "audio").name
    with tempfile.TemporaryDirectory(prefix="ai-services-asr-") as tmp:
        workdir = Path(tmp)
        source = workdir / ("input" + (Path(name).suffix or ".bin"))
        source.write_bytes(data)
        upload = _compact_for_upload(source, workdir)
        size = upload.stat().st_size
        if size > UPLOAD_MAX_BYTES:
            raise BackendError(
                "ASR", f"audio is {size} bytes after compression; the upload limit is {UPLOAD_MAX_BYTES}"
            )

        form = {"model": settings.asr_model, "response_format": "verbose_json"}
        if language or settings.asr_language:
            form["language"] = language or settings.asr_language
        with upload.open("rb") as handle:
            response = backend_request(
                "ASR",
                "POST",
                settings.asr_base_url.rstrip("/") + "/audio/transcriptions",
                api_key=settings.asr_api_key,
                timeout_seconds=settings.asr_timeout_seconds,
                transport=transport,
                data=form,
                files={"file": (upload.name, handle, "application/octet-stream")},
            )
    try:
        payload = response.json()
    except ValueError as exc:
        raise BackendError("ASR", "returned invalid JSON") from exc
    text, segments = parse_transcription(payload)
    return AsrResponse(filename=name, model=settings.asr_model, text=text, segments=segments)


def asr_runtime_status(settings: Settings) -> dict:
    return {"base_url": settings.asr_base_url, "model": settings.asr_model}
