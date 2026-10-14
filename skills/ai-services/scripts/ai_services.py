#!/usr/bin/env python3
"""Call the Stardust AI Services endpoint: OCR, ASR and TTS."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
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
        f"ai-services: shared Access client not found at {_SHARED}. "
        "Re-run ./install.sh from the stardust-skills checkout."
    )
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
from access_oauth import auth_headers, logout, session_status  # noqa: E402

DEFAULT_BASE_URL = "https://ai-services.preseen.ai"
USER_AGENT = "stardust-ai-services-skill/1.0"
TTS_MAX_CHARS = 3000
TTS_VOICES = (
    "Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee",
)
OCR_ENGINES = ("rapidocr", "qwen")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stardust AI Services: OCR, ASR and TTS.")
    parser.add_argument("--base-url", default=os.getenv("AI_SERVICES_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--auth-status", action="store_true", help="Check the stored login")
    parser.add_argument("--logout", action="store_true", help="Remove this service's login")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("health", help="Show the configured OCR/ASR/TTS backends")

    ocr = sub.add_parser("ocr", help="Extract text from an image or PDF")
    ocr.add_argument("file", type=Path)
    ocr.add_argument(
        "--engine", choices=OCR_ENGINES, default="rapidocr",
        help="rapidocr (default, fast plain text) or qwen (tables / complex layouts, Markdown)",
    )
    ocr.add_argument("--pages", help="One-based PDF pages, for example 1,3-5")
    ocr.add_argument("--languages", help="Comma-separated languages (rapidocr only)")
    ocr.add_argument("--format", choices=("text", "markdown", "json"), default="markdown")
    ocr.add_argument("--output", type=Path)
    ocr.add_argument("--timeout", type=float, default=600.0)

    asr = sub.add_parser("asr", help="Transcribe an audio file")
    asr.add_argument("file", type=Path)
    asr.add_argument("--language", help="Language code such as zh or en; auto-detected if omitted")
    asr.add_argument("--format", choices=("text", "json"), default="text")
    asr.add_argument("--output", type=Path)
    asr.add_argument("--timeout", type=float, default=1800.0)

    tts = sub.add_parser("tts", help="Synthesize speech to an MP3")
    tts.add_argument("text", nargs="?", help="Text to speak (max 3000 characters)")
    tts.add_argument("--input-file", type=Path, help="Read the text from this UTF-8 file")
    tts.add_argument("--output", type=Path, required=True, help="Destination .mp3 path")
    tts.add_argument("--voice", choices=TTS_VOICES)
    tts.add_argument("--instructions", help="Tone, emotion and pacing in plain language")
    tts.add_argument("--timeout", type=float, default=300.0)
    return parser


def parse_pages(spec: str | None) -> list[int] | None:
    """Expand '1,3-5' into [1, 3, 4, 5]; one-based."""
    if not spec:
        return None
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        low, _, high = part.partition("-")
        try:
            start, end = int(low), int(high or low)
        except ValueError as exc:
            raise ValueError(f"invalid page spec {part!r}") from exc
        if start < 1 or end < start:
            raise ValueError(f"invalid page range {part!r}")
        pages.extend(range(start, end + 1))
    return pages or None


def resolve_text(text: str | None, input_file: Path | None) -> str:
    if bool(text) == bool(input_file):
        raise ValueError("pass exactly one of TEXT or --input-file")
    value = (input_file.read_text(encoding="utf-8") if input_file else text or "").strip()
    if not value:
        raise ValueError("text is empty")
    if len(value) > TTS_MAX_CHARS:
        raise ValueError(
            f"text is {len(value)} characters; the limit is {TTS_MAX_CHARS} per request"
        )
    return value


def validate_mp3_path(path: Path) -> Path:
    if path.suffix.lower() != ".mp3":
        raise ValueError("--output must end in .mp3 (the service only returns MP3)")
    return path


def encode_multipart(
    fields: dict[str, str], file_field: str, path: Path
) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
            f'filename="{path.name}"\r\nContent-Type: {content_type}\r\n\r\n'
        ).encode()
        + path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def request(
    base_url: str,
    method: str,
    route: str,
    *,
    body: bytes | None = None,
    content_type: str | None = None,
    timeout: float = 300.0,
    retry_gateway_timeout: bool = False,
) -> bytes:
    url = base_url.rstrip("/") + route
    headers = {"User-Agent": USER_AGENT, **auth_headers(base_url)}
    if content_type:
        headers["Content-Type"] = content_type
    attempts = 2 if retry_gateway_timeout else 1
    for attempt in range(attempts):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if exc.code == 524 and attempt + 1 < attempts:
                time.sleep(5)  # cold model start can exceed Cloudflare's ~100 s limit
                continue
            if exc.code == 403 and "1010" in detail:
                raise RuntimeError(
                    "HTTP 403 (Cloudflare error 1010: browser-integrity check, not a login "
                    "problem). See stardust_access/README.md."
                ) from exc
            raise RuntimeError(f"HTTP {exc.code} from {route}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"cannot reach {url}: {exc.reason}") from exc
    raise RuntimeError("unreachable")


def format_ocr(result: dict[str, Any], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    if fmt == "text":
        return result.get("text", "")
    lines = [f"# {result.get('filename', 'document')}", ""]
    meta = f"engine: {result.get('engine')} · model: {result.get('model')}"
    if result.get("confidence") is not None:
        meta += f" · confidence: {result['confidence']:.3f}"
    lines += [meta, ""]
    pages = result.get("pages") or []
    if pages:
        for page in pages:
            lines += [f"## Page {page['page_number']}", "", page.get("text", ""), ""]
    else:
        lines += [result.get("text", ""), ""]
    for warning in result.get("warnings") or []:
        lines.append(f"> warning: {warning}")
    return "\n".join(lines).rstrip() + "\n"


def write_or_print(content: str, output: Path | None) -> None:
    if output:
        output.write_text(content, encoding="utf-8")
        print(f"wrote {output.resolve()}")
    else:
        sys.stdout.write(content if content.endswith("\n") else content + "\n")


def run(args: argparse.Namespace) -> int:
    base = args.base_url
    if args.command == "health":
        print(request(base, "GET", "/health").decode("utf-8"))
        return 0

    if args.command == "ocr":
        fields = {"engine": args.engine}
        pages = parse_pages(args.pages)
        if pages:
            fields["page_numbers"] = ",".join(str(p) for p in pages)
        if args.languages:
            fields["languages"] = args.languages
        body, ctype = encode_multipart(fields, "file", args.file)
        raw = request(base, "POST", "/ocr", body=body, content_type=ctype, timeout=args.timeout)
        write_or_print(format_ocr(json.loads(raw), args.format), args.output)
        return 0

    if args.command == "asr":
        fields = {"language": args.language} if args.language else {}
        body, ctype = encode_multipart(fields, "file", args.file)
        raw = request(base, "POST", "/asr", body=body, content_type=ctype, timeout=args.timeout)
        result = json.loads(raw)
        content = json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else result["text"]
        write_or_print(content, args.output)
        return 0

    if args.command == "tts":
        text = resolve_text(args.text, args.input_file)
        output = validate_mp3_path(args.output)
        payload = {"text": text}
        if args.voice:
            payload["voice"] = args.voice
        if args.instructions:
            payload["instructions"] = args.instructions
        audio = request(
            base, "POST", "/tts", body=json.dumps(payload).encode(),
            content_type="application/json", timeout=args.timeout, retry_gateway_timeout=True,
        )
        if not audio:
            raise RuntimeError("the service returned empty audio")
        output.write_bytes(audio)
        print(f"wrote {output.resolve()} ({len(audio)} bytes)")
        return 0

    raise ValueError("choose a command: health, ocr, asr or tts")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.auth_status:
            print("signed in" if session_status(args.base_url) else "sign-in required")
            return 0
        if args.logout:
            print("removed session" if logout(args.base_url) else "no stored session")
            return 0
        if not args.command:
            parser.print_help()
            return 2
        return run(args)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ai-services: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
