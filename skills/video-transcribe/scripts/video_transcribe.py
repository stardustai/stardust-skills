#!/usr/bin/env python3
"""Transcribe YouTube or Bilibili videos through Stardust Video Transcribe."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
_SHARED = SCRIPT_DIR.parents[2] / "lib" / "stardust_access"
if not _SHARED.is_dir():
    _SHARED = (
        Path(os.getenv("STARDUST_AGENTS_HOME", Path.home() / ".agents"))
        / "lib"
        / "stardust_access"
    )
if not _SHARED.is_dir():
    raise SystemExit(
        f"video-transcribe: shared Access client not found at {_SHARED}. "
        "Re-run ./install.sh from the stardust-skills checkout."
    )
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
from access_oauth import auth_headers, logout, session_status


DEFAULT_BASE_URL = "https://video-transcribe.preseen.ai"
DEFAULT_LANGS = ("zh.*", "en.*")
USER_AGENT = "stardust-video-transcribe-skill/1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe a YouTube or Bilibili URL with Stardust Video Transcribe."
    )
    parser.add_argument("video_url", nargs="?", help="YouTube or Bilibili HTTP(S) URL")
    parser.add_argument(
        "--base-url",
        default=os.getenv("VIDEO_TRANSCRIBE_BASE_URL", DEFAULT_BASE_URL),
        help="Stardust Video Transcribe service base URL",
    )
    parser.add_argument(
        "--prefer-subtitles",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Prefer platform subtitles before server-side ASR",
    )
    parser.add_argument(
        "--lang",
        action="append",
        dest="langs",
        help="Subtitle language regex in preference order; repeat as needed",
    )
    parser.add_argument("--combine-subtitles", action="store_true")
    parser.add_argument("--keep-workdir", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path, help="Write output to this path")
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--auth-status", action="store_true")
    parser.add_argument("--logout", action="store_true")
    return parser


def validate_video_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Video URL must be an absolute HTTP(S) URL")
    return value


def build_payload(
    video_url: str,
    *,
    prefer_subtitles: bool,
    langs: list[str],
    combine_subtitles: bool,
    keep_workdir: bool,
) -> dict[str, Any]:
    return {
        "url": validate_video_url(video_url),
        "prefer_subtitles": prefer_subtitles,
        "langs": langs,
        "combine_subtitles": combine_subtitles,
        "keep_workdir": keep_workdir,
    }


def resolve_auth_headers(base_url: str) -> dict[str, str]:
    return auth_headers(base_url)


def service_token_configured() -> bool:
    client_id = os.getenv("CF_ACCESS_CLIENT_ID") or ""
    client_secret = os.getenv("CF_ACCESS_CLIENT_SECRET") or ""
    if bool(client_id) != bool(client_secret):
        raise ValueError(
            "Set both CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET, or neither"
        )
    return bool(client_id)


def call_transcribe(
    *,
    base_url: str,
    auth_headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("--timeout must be greater than zero")
    url = base_url.rstrip("/") + "/transcribe"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            **auth_headers,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 403 and "1010" in detail:
            raise RuntimeError(
                "Cloudflare rejected the client signature (error 1010) before "
                "Access saw the request. The sign-in is fine; report this as a "
                "service-host configuration or client-network issue."
            ) from exc
        raise RuntimeError(
            f"Video Transcribe service returned HTTP {exc.code}: "
            f"{exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Video Transcribe service at {url}: {exc.reason}"
        ) from exc
    if not isinstance(value, dict):
        raise RuntimeError("Video Transcribe service returned a non-object JSON response")
    return value


def render(response: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(response, ensure_ascii=False, indent=2) + "\n"
    text = response.get("text")
    if not isinstance(text, str):
        raise ValueError("Video Transcribe response is missing the text field")
    return text + ("\n" if text and not text.endswith("\n") else "")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.auth_status:
            if service_token_configured():
                print("Authentication: Cloudflare service token configured")
                return 0
            active = session_status(args.base_url)
            print(
                "Authentication: Cloudflare Access session active"
                if active
                else "Authentication: login required"
            )
            return 0 if active else 1
        if args.logout:
            removed = logout(args.base_url)
            print(
                "Removed Stardust Video Transcribe Access session"
                if removed
                else "No Stardust Video Transcribe Access session found"
            )
            return 0
        if not args.video_url:
            raise ValueError("Provide a YouTube or Bilibili video URL")
        payload = build_payload(
            args.video_url,
            prefer_subtitles=args.prefer_subtitles,
            langs=args.langs or list(DEFAULT_LANGS),
            combine_subtitles=args.combine_subtitles,
            keep_workdir=args.keep_workdir,
        )
        response = call_transcribe(
            base_url=args.base_url,
            auth_headers=resolve_auth_headers(args.base_url),
            payload=payload,
            timeout=args.timeout,
        )
        output = render(response, args.format)
        if args.output:
            path = args.output.expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output, encoding="utf-8")
            print(f"Wrote {path}")
        else:
            sys.stdout.write(output)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"video-transcribe: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
