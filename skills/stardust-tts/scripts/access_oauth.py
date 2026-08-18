#!/usr/bin/env python3
"""Cloudflare Access Managed OAuth client with macOS Keychain persistence."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import secrets
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


KEYCHAIN_SERVICE = "ai.stardust.tts.oauth"
DEFAULT_ACCOUNT = "https://tts-api.preseen.ai"


def _origin(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("TTS base URL must be an absolute HTTP(S) URL")
    return f"{parsed.scheme}://{parsed.netloc}"


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    form: bool = False,
    timeout: float = 30,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
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
    protected = request_json(
        resource_origin + "/.well-known/cloudflare-access-protected-resource/"
    )
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


def _require_keychain() -> None:
    if platform.system() != "Darwin":
        raise RuntimeError(
            "Interactive login requires macOS Keychain; use a Cloudflare service "
            "token on headless or non-macOS systems"
        )


def keychain_store(record: dict[str, Any], account: str = DEFAULT_ACCOUNT) -> None:
    _require_keychain()
    secret = json.dumps(record, separators=(",", ":"))
    result = subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-a",
            account,
            "-s",
            KEYCHAIN_SERVICE,
            "-w",
        ],
        input=secret,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Could not save OAuth refresh token in macOS Keychain")


def keychain_load(account: str = DEFAULT_ACCOUNT) -> dict[str, Any] | None:
    _require_keychain()
    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-a",
            account,
            "-s",
            KEYCHAIN_SERVICE,
            "-w",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return None
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Stored Stardust TTS OAuth record is invalid") from exc
    return value if isinstance(value, dict) else None


def keychain_delete(account: str = DEFAULT_ACCOUNT) -> bool:
    _require_keychain()
    result = subprocess.run(
        [
            "security",
            "delete-generic-password",
            "-a",
            account,
            "-s",
            KEYCHAIN_SERVICE,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


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
            "client_name": "Stardust TTS Skill",
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
                "Stardust TTS authentication complete. You can close this window."
                if result.get("code")
                else "Stardust TTS authentication failed. Return to the terminal."
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
    try:
        if not webbrowser.open(metadata["authorization_endpoint"] + "?" + query):
            raise RuntimeError("Could not open a browser for company login")
        if not event.wait(300):
            raise RuntimeError("Timed out waiting for company login")
    finally:
        server.shutdown()
        server.server_close()
    if result.get("state") != state:
        raise RuntimeError("OAuth callback state did not match")
    if not result.get("code"):
        raise RuntimeError(result.get("error_description") or result.get("error") or "OAuth login failed")
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
    record = keychain_load(account)
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
    keychain_store(
        {"client_id": client_id, "refresh_token": str(refresh_token)}, account
    )
    return str(access_token)


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
