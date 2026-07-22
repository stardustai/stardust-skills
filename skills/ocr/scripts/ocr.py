#!/usr/bin/env python3
"""Call the external Stardust OCR service for local images and PDFs."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml


DEFAULT_BASE_URL = "https://ocr.preseen.ai/v1"
DEFAULT_CONFIG_PATH = Path(
    os.getenv("DOCUMENT_OCR_CONFIG")
    or Path.home() / "Documents/Projects/memory-connector/config/providers.yaml"
)
USER_AGENT = "stardust-ocr-skill/1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract text from local images or PDFs with the external OCR service."
    )
    parser.add_argument("files", nargs="+", type=Path, help="Local image or PDF paths")
    parser.add_argument("--format", choices=("text", "markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, help="Write output to this path")
    parser.add_argument("--pages", help="One-based PDF pages, for example 1,3-5")
    parser.add_argument("--languages", help="Comma-separated language identifiers")
    parser.add_argument("--model", help="OCR model identifier")
    parser.add_argument("--base-url", help="External OCR API base URL")
    parser.add_argument("--profile", default=os.getenv("DOCUMENT_OCR_PROFILE", "rapidocr_gpu4"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--timeout", type=float, default=300.0)
    return parser


def load_profile(config_path: Path, profile_name: str) -> dict[str, Any]:
    if not config_path.is_file():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    profiles = raw.get("document_ocr_providers") or {}
    profile = profiles.get(profile_name)
    if profile is None:
        raise ValueError(
            f"OCR profile {profile_name!r} is not defined in {config_path}"
        )
    if not isinstance(profile, dict):
        raise ValueError(f"OCR profile {profile_name!r} must be a mapping")
    return profile


def parse_pages(raw: str | None) -> list[int] | None:
    if raw is None:
        return None
    pages: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token:
            raise ValueError("Page selection contains an empty item")
        if "-" in token:
            start_raw, end_raw = token.split("-", 1)
            start, end = int(start_raw), int(end_raw)
            if start < 1 or end < start:
                raise ValueError(f"Invalid page range: {token}")
            pages.update(range(start, end + 1))
        else:
            page = int(token)
            if page < 1:
                raise ValueError("Page numbers are one-based and must be positive")
            pages.add(page)
    return sorted(pages)


def detect_mime_type(path: Path) -> str:
    guessed, _encoding = mimetypes.guess_type(path.name)
    mime_type = guessed or ""
    if mime_type.startswith("image/") or mime_type == "application/pdf":
        return mime_type
    raise ValueError(f"Unsupported OCR input type for {path}: {mime_type or 'unknown'}")


def build_payload(
    paths: list[Path],
    *,
    model: str | None,
    languages: list[str] | None,
    page_numbers: list[int] | None,
) -> dict[str, Any]:
    inputs = []
    for index, original_path in enumerate(paths, start=1):
        path = original_path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"OCR input does not exist or is not a file: {path}")
        mime_type = detect_mime_type(path)
        if page_numbers is not None and mime_type != "application/pdf":
            raise ValueError("--pages can only be used when every input is a PDF")
        inputs.append(
            {
                "source_id": f"input-{index}:{path.name}",
                "mime_type": mime_type,
                "data_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
                "page_numbers": page_numbers,
            }
        )
    return {"model": model, "languages": languages, "inputs": inputs}


def call_ocr(
    *, base_url: str, api_key: str, payload: dict[str, Any], timeout: float
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/ocr"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OCR service returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach OCR service at {url}: {exc.reason}") from exc


def render_text(response: dict[str, Any]) -> str:
    return "\n\n".join(
        str(item.get("text") or "").strip()
        for item in response.get("data") or []
        if str(item.get("text") or "").strip()
    )


def render_markdown(response: dict[str, Any]) -> str:
    sections: list[str] = []
    for item in response.get("data") or []:
        source_id = str(item.get("source_id") or "unknown source")
        lines = [f"# {source_id}"]
        confidence = item.get("confidence")
        if confidence is not None:
            lines.append(f"\nConfidence: {confidence}")
        warnings = [str(value) for value in item.get("warnings") or []]
        if warnings:
            lines.append("\nWarnings: " + "; ".join(warnings))
        pages = item.get("pages") or []
        if pages:
            for page in pages:
                lines.append(f"\n## Page {page.get('page_number')}")
                page_confidence = page.get("confidence")
                if page_confidence is not None:
                    lines.append(f"\nConfidence: {page_confidence}")
                page_warnings = [str(value) for value in page.get("warnings") or []]
                if page_warnings:
                    lines.append("\nWarnings: " + "; ".join(page_warnings))
                lines.append("\n" + str(page.get("text") or "").strip())
        else:
            lines.append("\n" + str(item.get("text") or "").strip())
        sections.append("\n".join(lines).rstrip())
    return "\n\n".join(sections) + ("\n" if sections else "")


def render(response: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(response, ensure_ascii=False, indent=2) + "\n"
    if output_format == "text":
        text = render_text(response)
        return text + ("\n" if text else "")
    return render_markdown(response)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = load_profile(args.config, args.profile)
        languages = (
            [value.strip() for value in args.languages.split(",") if value.strip()]
            if args.languages
            else list(profile.get("languages") or ["ch_sim", "en"])
        )
        model = args.model or profile.get("model") or "rapidocr:ch_sim+en"
        api_key = os.getenv("DOCUMENT_OCR_API_KEY") or profile.get("api_key") or ""
        base_url = (
            args.base_url
            or os.getenv("DOCUMENT_OCR_PUBLIC_BASE_URL")
            or DEFAULT_BASE_URL
        )
        payload = build_payload(
            args.files,
            model=str(model),
            languages=languages,
            page_numbers=parse_pages(args.pages),
        )
        response = call_ocr(
            base_url=base_url,
            api_key=str(api_key),
            payload=payload,
            timeout=args.timeout,
        )
        output = render(response, args.format)
        if args.output:
            output_path = args.output.expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
        return 0
    except (OSError, ValueError, RuntimeError, yaml.YAMLError) as exc:
        print(f"ocr: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
