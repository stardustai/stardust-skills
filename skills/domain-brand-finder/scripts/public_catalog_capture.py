#!/usr/bin/env python3
"""Capture paginated npm text-search responses without making clearance claims."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import requests
from requests.adapters import HTTPAdapter


ENDPOINT = "https://registry.npmjs.org/-/v1/search"
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 100
MAX_ALLOWED_PAGES = 100
CONTROL_QUERY = "react"
CONTROL_PACKAGE = "react"
TIMEOUT_SECONDS = 30


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _header_pairs(response: object) -> list[list[str]]:
    raw = getattr(getattr(response, "raw", None), "headers", None)
    if raw is not None and callable(getattr(raw, "iteritems", None)):
        pairs = list(raw.iteritems())
    else:
        headers = getattr(response, "headers", {})
        pairs = list(headers.items()) if hasattr(headers, "items") else []
    return [[str(name), str(value)] for name, value in pairs]


def _body_bytes(response: object) -> bytes:
    body = getattr(response, "content", b"")
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8")
    return b""


def _header_value(header_pairs: list[list[str]], wanted: str) -> str | None:
    for name, value in header_pairs:
        if name.casefold() == wanted.casefold():
            return value
    return None


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _save_receipt(output_dir: Path, receipt: dict) -> None:
    _write_json(output_dir / "receipt.json", receipt)


def _save_response(output_dir: Path, prefix: str, response: object) -> dict:
    body_file = f"{prefix}.body"
    headers_file = f"{prefix}.headers.json"
    (output_dir / body_file).write_bytes(_body_bytes(response))
    headers = _header_pairs(response)
    _write_json(output_dir / headers_file, headers)
    return {
        "http_status": getattr(response, "status_code", None),
        "checked_at": stamp(),
        "url": getattr(response, "url", None),
        "body_file": body_file,
        "headers_file": headers_file,
        "retry_after": _header_value(headers, "Retry-After"),
    }


def _parse_npm_page(response: object) -> tuple[int, list[str]]:
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("response JSON must be an object")
    total = payload.get("total")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError("response total must be a non-negative integer")
    objects = payload.get("objects")
    if not isinstance(objects, list):
        raise ValueError("response objects must be a list")
    names = []
    for index, item in enumerate(objects):
        package = item.get("package") if isinstance(item, dict) else None
        name = package.get("name") if isinstance(package, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"objects[{index}].package.name must be a non-empty string")
        names.append(name)
    return total, names


def _request(session: object, query: str, page_size: int, offset: int) -> object:
    return session.get(
        ENDPOINT,
        params={"text": query, "size": page_size, "from": offset},
        timeout=TIMEOUT_SECONDS,
        allow_redirects=False,
    )


def capture_query(
    session: object,
    query: str,
    output_dir: str | Path,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> dict:
    """Capture one exact npm search query, then its fixed React positive control.

    The query string is validated but never stripped, case-normalized, or otherwise
    rewritten before it is passed as the API's `text` parameter. No retry or sleep
    occurs. A failed, malformed, unstable, duplicate, or capped result stops the
    candidate sequence before any subsequent page or control query.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 100:
        raise ValueError("page_size must be an integer from 1 through 100")
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= MAX_ALLOWED_PAGES:
        raise ValueError(f"max_pages must be an integer from 1 through {MAX_ALLOWED_PAGES}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)
    receipt = {
        "schema_version": 1,
        "capture_kind": "npm_text_search_receipt",
        "endpoint": ENDPOINT,
        "query": query,
        "page_size": page_size,
        "max_pages": max_pages,
        "created_at": stamp(),
        "pagination_status": "UNKNOWN",
        "control_status": "NOT_RUN",
        "capture_status": "INCOMPLETE",
        "reported_total": None,
        "returned_rows": 0,
        "unique_names": 0,
        "package_names": [],
        "pages": [],
        "control": None,
        "error": None,
        "scope_note": "API response capture only; not public-use clearance, legal review, or a conclusion that a name is available.",
    }
    _save_receipt(out, receipt)

    seen_names: set[str] = set()
    offset = 0
    expected_total: int | None = None

    while True:
        params = {"text": query, "size": page_size, "from": offset}
        page_index = len(receipt["pages"])
        page_receipt = {
            "offset": offset,
            "query": query,
            "page_size": page_size,
            "request_params": params,
        }
        try:
            response = _request(session, query, page_size, offset)
        except requests.RequestException as exc:
            page_receipt.update(
                http_status=None,
                checked_at=stamp(),
                body_file=None,
                headers_file=None,
                error=f"{type(exc).__name__}: {exc}",
            )
            receipt["pages"].append(page_receipt)
            receipt.update(pagination_status="UNKNOWN", error=page_receipt["error"])
            _save_receipt(out, receipt)
            return receipt

        prefix = f"candidate-page-{page_index:03d}-from-{offset}"
        saved = _save_response(out, prefix, response)
        page_receipt.update(saved)
        receipt["pages"].append(page_receipt)

        if saved["http_status"] != 200:
            receipt.update(
                pagination_status="INCOMPLETE",
                error=f"HTTP {saved['http_status']} at offset {offset}; stopped without retry, another page, or control query",
            )
            _save_receipt(out, receipt)
            return receipt

        try:
            total, names = _parse_npm_page(response)
        except (ValueError, TypeError) as exc:
            receipt.update(pagination_status="INCOMPLETE", error=f"invalid page at offset {offset}: {exc}")
            _save_receipt(out, receipt)
            return receipt

        page_receipt.update(reported_total=total, returned_rows=len(names))

        if expected_total is not None and total != expected_total:
            receipt.update(
                pagination_status="INCOMPLETE",
                error=f"reported total changed from {expected_total} to {total} at offset {offset}",
            )
            _save_receipt(out, receipt)
            return receipt
        if expected_total is None:
            expected_total = total
            receipt["reported_total"] = total

        expected_rows = max(0, min(page_size, total - offset))
        if len(names) != expected_rows:
            receipt.update(
                pagination_status="INCOMPLETE",
                error=f"page at offset {offset} returned {len(names)} rows; expected {expected_rows}",
            )
            _save_receipt(out, receipt)
            return receipt

        page_seen: set[str] = set()
        duplicates = []
        for name in names:
            key = name.casefold()
            if key in seen_names or key in page_seen:
                duplicates.append(name)
            page_seen.add(key)
        if duplicates:
            receipt.update(
                pagination_status="INCOMPLETE",
                error=f"duplicate package name(s) across captured pages: {', '.join(sorted(set(duplicates)))}",
            )
            _save_receipt(out, receipt)
            return receipt

        seen_names.update(page_seen)
        receipt["package_names"].extend(names)
        receipt["returned_rows"] += len(names)
        receipt["unique_names"] = len(seen_names)

        if receipt["returned_rows"] == expected_total:
            if receipt["unique_names"] != expected_total:
                receipt.update(pagination_status="INCOMPLETE", error="unique package-name count does not equal reported total")
                _save_receipt(out, receipt)
                return receipt
            receipt["pagination_status"] = "COMPLETE"
            _save_receipt(out, receipt)
            break

        if len(receipt["pages"]) >= max_pages:
            receipt.update(
                pagination_status="INCOMPLETE",
                error=f"configured page cap {max_pages} reached before reported total {expected_total}",
            )
            _save_receipt(out, receipt)
            return receipt

        offset += page_size
        _save_receipt(out, receipt)

    try:
        response = _request(session, CONTROL_QUERY, page_size, 0)
    except requests.RequestException as exc:
        receipt.update(control_status="UNKNOWN", error=f"positive-control request failed: {type(exc).__name__}: {exc}")
        _save_receipt(out, receipt)
        return receipt

    saved = _save_response(out, "control-react-from-0", response)
    receipt["control"] = {
        "query": CONTROL_QUERY,
        "expected_package": CONTROL_PACKAGE,
        "request_params": {"text": CONTROL_QUERY, "size": page_size, "from": 0},
        **saved,
    }
    if saved["http_status"] != 200:
        receipt.update(control_status="UNKNOWN", error=f"positive-control HTTP {saved['http_status']}; no retry")
        _save_receipt(out, receipt)
        return receipt

    try:
        control_total, control_names = _parse_npm_page(response)
    except (ValueError, TypeError) as exc:
        receipt.update(control_status="UNKNOWN", error=f"invalid positive-control response: {exc}")
        _save_receipt(out, receipt)
        return receipt
    receipt["control"].update(reported_total=control_total, returned_rows=len(control_names), package_names=control_names)

    expected_control_rows = min(page_size, control_total)
    if len(control_names) != expected_control_rows:
        receipt.update(
            control_status="UNKNOWN",
            error=f"positive-control first page returned {len(control_names)} rows; expected {expected_control_rows}",
        )
        _save_receipt(out, receipt)
        return receipt

    normalized_control_names = [name.casefold() for name in control_names]
    if len(set(normalized_control_names)) != len(normalized_control_names):
        receipt.update(control_status="UNKNOWN", error="positive-control first page contains duplicate package names")
        _save_receipt(out, receipt)
        return receipt

    if CONTROL_PACKAGE.casefold() not in {name.casefold() for name in control_names}:
        receipt.update(control_status="NOT_CONFIRMED", error="positive-control identity was not present on its first page")
        _save_receipt(out, receipt)
        return receipt

    receipt.update(control_status="MATCHED", capture_status="RECEIPT_CAPTURED")
    _save_receipt(out, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Exact npm text query; preserved without normalization")
    parser.add_argument("--output-dir", required=True, help="New, non-existing directory for raw pages and receipt")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                        help="Maximum candidate pages; no control runs if reached")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=0))
    try:
        receipt = capture_query(
            session,
            args.query,
            args.output_dir,
            page_size=args.page_size,
            max_pages=args.max_pages,
        )
    except (OSError, ValueError) as exc:
        print(f"capture failed before completion: {exc}", file=sys.stderr)
        return 2
    finally:
        session.close()
    print(json.dumps({"output_dir": str(Path(args.output_dir)), "pagination_status": receipt["pagination_status"],
                      "control_status": receipt["control_status"], "capture_status": receipt["capture_status"]}))
    return 0 if receipt["capture_status"] == "RECEIPT_CAPTURED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
