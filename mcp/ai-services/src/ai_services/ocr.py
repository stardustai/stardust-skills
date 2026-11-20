"""OCR through the ocr-provider service (`POST /v1/ocr`)."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import httpx

from ai_services.backends import BackendError, backend_request
from ai_services.config import Settings
from ai_services.ocr_qwen import ocr_with_qwen
from ai_services.schemas import OcrPage, OcrResponse

ENGINES = ("rapidocr", "qwen")

SUPPORTED_MIME_PREFIXES = ("image/",)
SUPPORTED_MIME_TYPES = {"application/pdf"}


def guess_mime_type(filename: str, mime_type: str | None = None) -> str:
    resolved = mime_type or mimetypes.guess_type(filename)[0] or ""
    if not (resolved.startswith(SUPPORTED_MIME_PREFIXES) or resolved in SUPPORTED_MIME_TYPES):
        raise ValueError(
            f"unsupported OCR input type {resolved or 'unknown'!r}; send an image or a PDF"
        )
    return resolved


def ocr_document(
    filename: str,
    data: bytes,
    settings: Settings,
    *,
    mime_type: str | None = None,
    page_numbers: list[int] | None = None,
    languages: list[str] | None = None,
    engine: str = "rapidocr",
    transport: httpx.BaseTransport | None = None,
) -> OcrResponse:
    if engine not in ENGINES:
        raise ValueError(f"unsupported OCR engine {engine!r}; use one of {list(ENGINES)}")
    name = Path(filename or "document").name
    if engine == "qwen":
        return ocr_with_qwen(
            name, data, guess_mime_type(name, mime_type), settings,
            page_numbers=page_numbers, transport=transport,
        )
    payload: dict = {
        "inputs": [
            {
                "source_id": name,
                "mime_type": guess_mime_type(name, mime_type),
                "data_base64": base64.b64encode(data).decode("ascii"),
                **({"page_numbers": page_numbers} if page_numbers else {}),
            }
        ]
    }
    if settings.ocr_model:
        payload["model"] = settings.ocr_model
    if languages:
        payload["languages"] = languages

    response = backend_request(
        "OCR",
        "POST",
        settings.ocr_base_url.rstrip("/") + "/ocr",
        api_key=settings.ocr_api_key,
        timeout_seconds=settings.ocr_timeout_seconds,
        transport=transport,
        json=payload,
    )
    try:
        body = response.json()
        item = body["data"][0]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise BackendError("OCR", "returned an unexpected response") from exc
    return OcrResponse(
        filename=name,
        engine="rapidocr",
        model=str(body.get("model") or settings.ocr_model or ""),
        text=str(item.get("text") or ""),
        confidence=item.get("confidence"),
        warnings=[str(w) for w in item.get("warnings") or []],
        pages=[OcrPage(**page) for page in item.get("pages") or []],
    )


def ocr_runtime_status(settings: Settings) -> dict:
    return {
        "rapidocr": {"base_url": settings.ocr_base_url, "model": settings.ocr_model},
        "qwen": {"base_url": settings.ocr_qwen_base_url, "model": settings.ocr_qwen_model},
    }
