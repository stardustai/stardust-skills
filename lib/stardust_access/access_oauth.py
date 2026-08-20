#!/usr/bin/env python3
"""Cloudflare Access Managed OAuth client for Stardust internal services.

Standard RFC 8252 native-app flow: dynamic client registration, a loopback
redirect on a random port, authorization code with PKCE, and refresh.  The
skill opens the browser itself, so nothing has to be installed alongside it.

The refresh token is kept in a 0600 file under the user's config directory —
the same trust model `cloudflared` uses for `~/.cloudflared/*-token`.  An
earlier revision required the macOS Keychain and refused to run anywhere else,
which made interactive login impossible on Linux and Windows.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import stat
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


DEFAULT_ACCOUNT = "https://tts-api.preseen.ai"
LOGIN_TIMEOUT_S = 300
# urllib's default "Python-urllib/3.x" is refused by Cloudflare's
# browser-integrity check with 403 "error code: 1010" before Access is ever
# consulted.  Every request this module makes needs an identifiable agent.
USER_AGENT = "stardust-access-client/1.0"
CLIENT_NAME = "Stardust Service Access"


def _origin(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Service base URL must be an absolute HTTP(S) URL")
    return f"{parsed.scheme}://{parsed.netloc}"


# ── Token storage ──────────────────────────────────────────────────────────


def token_path() -> Path:
    """Where the refresh token lives.  Honours an override for tests."""
    override = os.getenv("STARDUST_ACCESS_TOKEN_FILE") or os.getenv(
        "STARDUST_TTS_TOKEN_FILE"
    )
    if override:
        return Path(override)
    if os.name == "nt":
        base = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "stardust-tts" / "oauth.json"


def _read_all() -> dict[str, Any]:
    path = token_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise RuntimeError(f"Could not read {path}: {exc}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Stored Stardust Access credentials at {path} are not valid JSON. "
            "Delete the file and sign in again."
        ) from exc
    return value if isinstance(value, dict) else {}


def _write_all(records: dict[str, Any]) -> None:
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, stat.S_IRWXU)
    except OSError:
        # Best effort: on Windows the POSIX bits do not apply.
        pass
    # Write to a sibling temp file and rename, so a second invocation running
    # at the same time can never observe a half-written credential file.
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    data = json.dumps(records, indent=2, sort_keys=True)
    handle = os.open(
        tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(data)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, path)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def store_record(record: dict[str, Any], account: str = DEFAULT_ACCOUNT) -> None:
    records = _read_all()
    records[account] = record
    _write_all(records)


def load_record(account: str = DEFAULT_ACCOUNT) -> dict[str, Any] | None:
    value = _read_all().get(account)
    return value if isinstance(value, dict) else None


def delete_record(account: str = DEFAULT_ACCOUNT) -> bool:
    records = _read_all()
    if account not in records:
        return False
    del records[account]
    _write_all(records)
    return True


# ── OAuth ──────────────────────────────────────────────────────────────────


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    form: bool = False,
    timeout: float = 30,
) -> dict[str, Any]:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    data = None
    if payload is not None:
        if form:
            data = urllib.parse.urlencode(payload).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OAuth endpoint returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach OAuth endpoint: {exc.reason}") from exc


def discover(base_url: str) -> dict[str, Any]:
    resource_origin = _origin(base_url)
    try:
        protected = request_json(
            resource_origin + "/.well-known/cloudflare-access-protected-resource/"
        )
    except RuntimeError as exc:
        if "HTTP 404" in str(exc):
            raise RuntimeError(
                f"Cloudflare Access metadata is missing for {resource_origin}; "
                "either the service-side Access application/AUD is not configured, "
                "or a local DNS/fake-IP proxy prevented the request from reaching "
                "the correct Cloudflare edge. Check whether DNS resolves to "
                "198.18.x.x before changing the service."
            ) from exc
        raise
    authorization_servers = protected.get("authorization_servers") or []
    if not authorization_servers:
        raise RuntimeError("OAuth resource metadata has no authorization server")
    issuer = str(authorization_servers[0]).rstrip("/")
    metadata = request_json(issuer + "/.well-known/oauth-authorization-server")
    required = ("authorization_endpoint", "token_endpoint", "registration_endpoint")
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise RuntimeError("OAuth server metadata is missing " + ", ".join(missing))
    return {**metadata, "resource": protected.get("resource", resource_origin)}


def _pkce() -> tuple[str, str]:
    while True:
        verifier = base64.urlsafe_b64encode(os.urandom(48)).decode().rstrip("=")
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        if challenge[0].isalnum():
            return verifier, challenge


def _register(metadata: dict[str, Any], redirect_uri: str) -> str:
    response = request_json(
        metadata["registration_endpoint"],
        method="POST",
        payload={
            "client_name": CLIENT_NAME,
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "resource": metadata["resource"],
        },
    )
    client_id = response.get("client_id")
    if not client_id:
        raise RuntimeError("OAuth client registration returned no client_id")
    return str(client_id)


def _interactive_tokens(metadata: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    result: dict[str, str] = {}
    event = threading.Event()

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            values = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            for key in ("code", "state", "error", "error_description"):
                if values.get(key):
                    result[key] = values[key][0]
            message = (
                "Stardust Access authentication complete. You can close this window."
                if result.get("code")
                else "Stardust Access authentication failed. Return to the terminal."
            )
            body = message.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            event.set()

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Callback)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    redirect_uri = f"http://127.0.0.1:{server.server_port}/callback"
    state = secrets.token_urlsafe(32)
    verifier, challenge = _pkce()
    client_id = _register(metadata, redirect_uri)
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "resource": metadata["resource"],
        }
    )
    authorize_url = metadata["authorization_endpoint"] + "?" + query
    try:
        opened = False
        try:
            opened = webbrowser.open(authorize_url)
        except Exception:
            opened = False
        # Over SSH or on a headless box there is no browser to open.  Printing
        # the URL keeps that case usable instead of failing outright; the
        # callback still has to land on this machine's loopback, so the user
        # needs a browser that can reach 127.0.0.1 here.
        print(
            "Sign in with your @stardust.ai address"
            + ("" if opened else " by opening this URL")
            + ":\n  "
            + authorize_url,
            file=sys.stderr,
        )
        if not event.wait(LOGIN_TIMEOUT_S):
            raise RuntimeError(
                f"Timed out after {LOGIN_TIMEOUT_S}s waiting for company login"
            )
    finally:
        server.shutdown()
        server.server_close()
    if result.get("state") != state:
        raise RuntimeError("OAuth callback state did not match")
    if not result.get("code"):
        raise RuntimeError(
            result.get("error_description") or result.get("error") or "OAuth login failed"
        )
    tokens = request_json(
        metadata["token_endpoint"],
        method="POST",
        form=True,
        payload={
            "grant_type": "authorization_code",
            "code": result["code"],
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
            "resource": metadata["resource"],
        },
    )
    return client_id, tokens


def _refresh(metadata: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    return request_json(
        metadata["token_endpoint"],
        method="POST",
        form=True,
        payload={
            "grant_type": "refresh_token",
            "refresh_token": record["refresh_token"],
            "client_id": record["client_id"],
            "resource": metadata["resource"],
        },
    )


def oauth_access_token(base_url: str) -> str:
    account = _origin(base_url)
    metadata = discover(base_url)
    record = load_record(account)
    tokens: dict[str, Any]
    client_id: str
    if record and record.get("client_id") and record.get("refresh_token"):
        client_id = str(record["client_id"])
        try:
            tokens = _refresh(metadata, record)
        except RuntimeError:
            client_id, tokens = _interactive_tokens(metadata)
    else:
        client_id, tokens = _interactive_tokens(metadata)
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token") or (record or {}).get("refresh_token")
    if not access_token or not refresh_token:
        raise RuntimeError("OAuth token response is missing access or refresh token")
    store_record({"client_id": client_id, "refresh_token": str(refresh_token)}, account)
    return str(access_token)


def session_status(base_url: str = DEFAULT_ACCOUNT) -> bool:
    """True when a stored refresh token exists for this origin.

    Returns a bool, not a message: the caller turns it into an exit code.
    """
    record = load_record(_origin(base_url))
    return bool(record and record.get("refresh_token"))


def logout(base_url: str = DEFAULT_ACCOUNT) -> bool:
    return delete_record(_origin(base_url))


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
    return {"Authorization": "Bearer " + oauth_access_token(base_url)}
