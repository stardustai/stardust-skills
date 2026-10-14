"""Shared HTTP plumbing for the OCR, ASR and TTS backends."""

from __future__ import annotations

import httpx


class BackendError(RuntimeError):
    """A backend rejected the request or could not be reached."""

    def __init__(self, backend: str, message: str, status_code: int | None = None) -> None:
        super().__init__(f"{backend} backend: {message}")
        self.backend = backend
        self.status_code = status_code


def auth_headers(api_key: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def backend_request(
    backend: str,
    method: str,
    url: str,
    *,
    api_key: str | None,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None = None,
    **kwargs,
) -> httpx.Response:
    timeout = httpx.Timeout(timeout_seconds, connect=10.0)
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.request(method, url, headers=auth_headers(api_key), **kwargs)
    except httpx.HTTPError as exc:
        raise BackendError(backend, f"request failed: {type(exc).__name__}: {exc}") from exc
    if response.status_code != 200:
        raise BackendError(
            backend, f"HTTP {response.status_code}: {response.text[:200]}", response.status_code
        )
    return response
