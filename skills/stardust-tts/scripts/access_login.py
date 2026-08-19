#!/usr/bin/env python3
"""Cloudflare Access authentication for the Stardust TTS client.

Two modes, in precedence order:

1. A workload service token (`CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET`).
2. An employee session obtained by `cloudflared access login`.

`cloudflared` owns the employee credential end to end: this module never reads,
writes, or stores a token itself, and there is no plaintext fallback. That also
makes interactive use work anywhere cloudflared runs, rather than macOS only.

Replaced the Managed OAuth + PKCE + Keychain client on 2026-08-19. The Access
application no longer enables Managed OAuth, so that path could not authenticate
at all; `cloudflared access login` performs the same browser one-time-PIN flow
against the same policy with none of the bespoke credential handling.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

DEFAULT_ORIGIN = "https://tts-api.preseen.ai"
# Re-login rather than send a token that expires mid-flight; a cold synthesis
# request can occupy the better part of a minute.
EXPIRY_MARGIN_S = 120
INSTALL_HINT = (
    "cloudflared is required to sign in.\n"
    "  macOS:   brew install cloudflared\n"
    "  Linux:   https://developers.cloudflare.com/cloudflare-one/connections/"
    "connect-networks/downloads/\n"
    "There is no API-key alternative: the service is company-login only."
)


def origin(base_url: str) -> str:
    """The Access application origin for an API base URL."""
    return base_url.split("/v1", 1)[0].rstrip("/") or DEFAULT_ORIGIN


def _cloudflared() -> str:
    path = shutil.which("cloudflared")
    if not path:
        raise RuntimeError(INSTALL_HINT)
    return path


def _looks_like_jwt(value: str) -> bool:
    return value.count(".") == 2 and all(part for part in value.split("."))


def _expiry(token: str) -> float | None:
    """`exp` from the unverified payload, or None if unreadable.

    Only used to decide whether to log in again. The origin verifies the
    signature; nothing here is trusted for authorization.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return float(json.loads(base64.urlsafe_b64decode(payload))["exp"])
    except Exception:
        return None


def cached_token(app: str) -> str | None:
    result = subprocess.run(
        [_cloudflared(), "access", "token", "--app", app],
        capture_output=True,
        text=True,
    )
    token = result.stdout.strip()
    if result.returncode != 0 or not _looks_like_jwt(token):
        return None
    expiry = _expiry(token)
    if expiry is not None and expiry - time.time() < EXPIRY_MARGIN_S:
        return None
    return token


def login(app: str) -> str:
    # No --quiet: on a headless or SSH session cloudflared prints the URL the
    # employee has to open, and suppressing it turns login into a silent hang.
    if subprocess.run([_cloudflared(), "access", "login", "--app", app]).returncode:
        raise RuntimeError("Cloudflare Access login failed or was cancelled")
    token = cached_token(app)
    if token is None:
        raise RuntimeError(
            "Login completed but no usable token was returned. Retry with "
            f"`cloudflared access login --app {app}`"
        )
    return token


def employee_token(base_url: str) -> str:
    app = origin(base_url)
    return cached_token(app) or login(app)


def session_status(base_url: str) -> bool:
    """True when a usable employee session already exists."""
    return cached_token(origin(base_url)) is not None


def logout(base_url: str) -> bool:
    """Remove the cached employee session. True when one was present."""
    app = origin(base_url)
    host = app.split("://", 1)[-1]
    directory = Path.home() / ".cloudflared"
    removed = False
    for path in directory.glob(f"{host}-*token*"):
        path.unlink(missing_ok=True)
        removed = True
    return removed


def auth_headers(base_url: str) -> dict[str, str]:
    client_id = os.getenv("CF_ACCESS_CLIENT_ID") or ""
    client_secret = os.getenv("CF_ACCESS_CLIENT_SECRET") or ""
    if bool(client_id) != bool(client_secret):
        raise ValueError(
            "Set both CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET, or neither"
        )
    if client_id:
        return {
            "CF-Access-Client-Id": client_id,
            "CF-Access-Client-Secret": client_secret,
        }
    token = employee_token(base_url)
    # Both forms are accepted by the edge and each is ignored when the other is
    # used. Sending both removes a failure mode that is expensive to diagnose:
    # if only one were correct and we picked wrong, every call would return the
    # HTML login page, which is indistinguishable from an expired session.
    return {"cf-access-token": token, "Cookie": f"CF_Authorization={token}"}
