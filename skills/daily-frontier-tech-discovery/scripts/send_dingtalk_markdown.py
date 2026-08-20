#!/usr/bin/env python3
"""Send a Markdown report to the skill-scoped DingTalk robot."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import stat
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "config.json"


def _sign(secret: str, timestamp: str) -> str:
    payload = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return urllib.parse.quote_plus(base64.b64encode(digest).decode("utf-8"))


def _signed_url(webhook: str, secret: str) -> str:
    timestamp = str(round(time.time() * 1000))
    sign = _sign(secret, timestamp)
    joiner = "&" if "?" in webhook else "?"
    return f"{webhook}{joiner}timestamp={timestamp}&sign={sign}"


def _read_text(text: str | None, text_file: str | None) -> str:
    if text is not None:
        return text
    if text_file:
        with open(text_file, "r", encoding="utf-8") as handle:
            return handle.read()
    return sys.stdin.read()


def _validate(title: str, text: str) -> None:
    if not title.strip():
        raise ValueError("title is required")
    if not text.strip():
        raise ValueError("markdown text is empty")
    if "http://" not in text and "https://" not in text:
        raise ValueError("markdown text must contain at least one URL")


def _read_config(config_path: str | None) -> tuple[str, str]:
    path = Path(config_path).expanduser() if config_path else DEFAULT_CONFIG
    if not path.exists():
        raise RuntimeError(f"DingTalk config file not found: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o600:
        raise RuntimeError(f"DingTalk config must have mode 600: {path}")
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    webhook = str(config.get("webhook", "")).strip()
    secret = str(config.get("secret", "")).strip()
    if not webhook or not secret:
        raise RuntimeError(f"DingTalk config is missing webhook or secret: {path}")
    return webhook, secret


def _validate_response(response_text: str) -> dict[str, object]:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("DingTalk returned a non-JSON response") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("DingTalk returned an invalid response object")
    errcode = payload.get("errcode")
    if errcode != 0:
        errmsg = str(payload.get("errmsg") or "unknown error")
        raise RuntimeError(f"DingTalk send failed: errcode={errcode}, errmsg={errmsg}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default="每日前沿技术洞察")
    parser.add_argument("--text")
    parser.add_argument("--text-file")
    parser.add_argument("--config", help="Path to skill-scoped DingTalk config JSON")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    text = _read_text(args.text, args.text_file)
    _validate(args.title, text)

    body = {
        "msgtype": "markdown",
        "markdown": {
            "title": args.title,
            "text": text,
        },
    }

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "payload": body}, ensure_ascii=False))
        return 0

    try:
        webhook, secret = _read_config(args.config)
        request = urllib.request.Request(
            _signed_url(webhook, secret),
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            response_text = response.read().decode("utf-8")
        payload = _validate_response(response_text)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"send_dingtalk_markdown: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
