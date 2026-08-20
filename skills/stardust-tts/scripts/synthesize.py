#!/usr/bin/env python3
"""Generate MP3 speech with the public Stardust Qwen3-TTS service."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from access_oauth import auth_headers, logout, session_status


DEFAULT_BASE_URL = "https://tts-api.preseen.ai/v1"
DEFAULT_MODEL = "qwen3-tts-1.7b-customvoice"
DEFAULT_VOICE = "Vivian"
MAX_INPUT_CHARS = 3000
USER_AGENT = "stardust-tts-skill/1.0"
VOICES = (
    "Vivian",
    "Serena",
    "Uncle_Fu",
    "Dylan",
    "Eric",
    "Ryan",
    "Aiden",
    "Ono_Anna",
    "Sohee",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate compressed MP3 speech with Stardust Qwen3-TTS."
    )
    parser.add_argument("text", nargs="?", help="Text to synthesize, or '-' for stdin")
    parser.add_argument("--input-file", type=Path, help="Read UTF-8 text from a file")
    parser.add_argument("--output", type=Path, help="Required destination .mp3 path")
    parser.add_argument("--voice", choices=VOICES, default=DEFAULT_VOICE)
    parser.add_argument("--instructions", help="Natural-language delivery instructions")
    parser.add_argument(
        "--base-url",
        default=os.getenv("STARDUST_TTS_BASE_URL", DEFAULT_BASE_URL),
        help="Compatible API base URL",
    )
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--list-voices", action="store_true")
    parser.add_argument("--auth-status", action="store_true")
    parser.add_argument("--logout", action="store_true")
    return parser


def resolve_text(text: str | None, input_file: Path | None) -> str:
    if text is not None and input_file is not None:
        raise ValueError("Provide text or --input-file, not both")
    if input_file is not None:
        path = input_file.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Input file does not exist: {path}")
        value = path.read_text(encoding="utf-8")
    elif text == "-":
        value = sys.stdin.read()
    elif text is not None:
        value = text
    else:
        raise ValueError("Provide text, '-' for stdin, or --input-file")

    value = value.strip()
    if not value:
        raise ValueError("Text must not be empty")
    if len(value) > MAX_INPUT_CHARS:
        raise ValueError(
            f"Text is {len(value)} characters; the service limit is {MAX_INPUT_CHARS}"
        )
    return value


def validate_output_path(output: Path | None) -> Path:
    if output is None:
        raise ValueError("--output is required")
    path = output.expanduser().resolve()
    if path.suffix.lower() != ".mp3":
        raise ValueError("Output path must end in .mp3; WAV output is not supported")
    return path


def resolve_auth_headers(base_url: str) -> dict[str, str]:
    return auth_headers(base_url)


def build_payload(
    text: str,
    *,
    voice: str,
    instructions: str | None,
) -> dict[str, object]:
    if voice not in VOICES:
        raise ValueError(f"Unsupported voice {voice!r}; use --list-voices")
    if not text.strip():
        raise ValueError("Text must not be empty")
    if len(text) > MAX_INPUT_CHARS:
        raise ValueError(
            f"Text is {len(text)} characters; the service limit is {MAX_INPUT_CHARS}"
        )
    payload: dict[str, object] = {
        "model": DEFAULT_MODEL,
        "input": text,
        "voice": voice,
        "response_format": "mp3",
    }
    if instructions and instructions.strip():
        payload["instructions"] = instructions.strip()
    return payload


def is_mp3(data: bytes) -> bool:
    return data.startswith(b"ID3") or (
        len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0
    )


def call_speech(
    *,
    base_url: str,
    auth_headers: dict[str, str],
    payload: dict[str, object],
    timeout: float,
) -> bytes:
    if timeout <= 0:
        raise ValueError("--timeout must be greater than zero")
    url = base_url.rstrip("/") + "/audio/speech"
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
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
            audio = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 403 and "1010" in detail:
            # Cloudflare's browser-integrity check, not Access. Reporting this
            # as an authentication failure sends the user into re-login
            # attempts that cannot help.
            raise RuntimeError(
                "Cloudflare rejected the client signature (error 1010) before "
                "Access saw the request. The sign-in is fine; the User-Agent "
                "was refused. Report this rather than signing in again."
            ) from exc
        raise RuntimeError(
            f"TTS service returned HTTP {exc.code}: {detail or exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach TTS service at {url}: {exc.reason}") from exc

    if content_type != "audio/mpeg":
        raise RuntimeError(
            f"TTS service returned unexpected Content-Type {content_type or 'missing'}"
        )
    if not audio:
        raise RuntimeError("TTS service returned an empty audio response")
    if not is_mp3(audio):
        raise RuntimeError("TTS service returned audio/mpeg but the bytes are not MP3")
    return audio


def write_mp3(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_voices:
        print("\n".join(VOICES))
        return 0
    if args.auth_status:
        service_mode = bool(os.getenv("CF_ACCESS_CLIENT_ID")) and bool(
            os.getenv("CF_ACCESS_CLIENT_SECRET")
        )
        if service_mode:
            print("Authentication: Cloudflare service token configured")
            return 0
        try:
            active = session_status(args.base_url)
        except RuntimeError as exc:
            print(f"stardust-tts: {exc}", file=sys.stderr)
            return 1
        print(
            "Authentication: Cloudflare Access session active"
            if active
            else "Authentication: login required"
        )
        return 0 if active else 1
    if args.logout:
        try:
            removed = logout(args.base_url)
        except RuntimeError as exc:
            print(f"stardust-tts: {exc}", file=sys.stderr)
            return 1
        print(
            "Removed Stardust TTS Access session"
            if removed
            else "No Stardust TTS Access session found"
        )
        return 0
    try:
        text = resolve_text(args.text, args.input_file)
        output = validate_output_path(args.output)
        payload = build_payload(
            text,
            voice=args.voice,
            instructions=args.instructions,
        )
        audio = call_speech(
            base_url=args.base_url,
            auth_headers=resolve_auth_headers(args.base_url),
            payload=payload,
            timeout=args.timeout,
        )
        write_mp3(output, audio)
        print(f"Wrote {len(audio)} bytes to {output}")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"stardust-tts: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
