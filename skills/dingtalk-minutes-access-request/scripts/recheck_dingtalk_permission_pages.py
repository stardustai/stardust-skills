#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from sync_dingtalk_ai_memory_cdp import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_PERMISSION_REQUEST_MESSAGE,
    DEFAULT_STORAGE_STATE_PATH,
    load_config,
    resolve_permission_page,
    wait_for_detail_ready,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recheck a saved set of DingTalk permission pages one by one.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to JSON config.")
    parser.add_argument("--storage-state", help="Playwright storage_state.json for headless runs.")
    parser.add_argument("--source-json", help="Prior sync JSON file to extract target pages from.")
    parser.add_argument(
        "--status",
        default="failed",
        help="Comma-separated statuses to select from source-json. Default: failed",
    )
    parser.add_argument("--url", action="append", default=[], help="Explicit permission page URL to recheck. Repeatable.")
    parser.add_argument("--request-permissions", action="store_true", help="Click 发送申请 when possible.")
    parser.add_argument(
        "--permission-request-message",
        default=DEFAULT_PERMISSION_REQUEST_MESSAGE,
        help="Reason text to fill before clicking 发送申请.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def load_targets(source_json_path: Path | None, statuses: set[str], urls: list[str]) -> list[dict]:
    targets: list[dict] = []
    seen: set[str] = set()

    for url in urls:
        text = str(url).strip()
        if text and text not in seen:
            targets.append({"source": "cli", "url": text})
            seen.add(text)

    if not source_json_path:
        return targets

    data = json.loads(source_json_path.read_text(encoding="utf-8"))
    for item in data.get("results", []):
        status = str(item.get("status") or "").strip()
        url = str(item.get("source_url") or item.get("url") or "").strip()
        if status not in statuses or not url or url in seen:
            continue
        targets.append(
            {
                "source": str(source_json_path),
                "row_key": item.get("row_key"),
                "topic": item.get("topic") or item.get("title") or "",
                "previous_status": status,
                "url": url,
            }
        )
        seen.add(url)
    return targets


def recheck_page(page, target: dict, request_permissions: bool, request_message: str) -> dict:
    url = target["url"]
    page.goto(url, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PlaywrightTimeoutError:
        pass

    ready = wait_for_detail_ready(page)
    current_url = ready.get("url", page.url)
    title = page.title()
    status, state, attempts = resolve_permission_page(page, target.get("topic") or target.get("row_key") or url, request_permissions, request_message)
    if status == "failed" and state.get("can_request"):
        status = "requestable"

    return {
        "ok": status in {"permission_requested", "permission_pending", "requestable"},
        "status": status,
        "source_url": url,
        "final_url": current_url,
        "title": title,
        "topic": str(state.get("title") or "").strip() or target.get("topic") or "",
        "previous_status": target.get("previous_status", ""),
        "row_key": target.get("row_key", ""),
        "page_state": state,
        "permission_attempts": attempts,
        "last_checked_at": time.time(),
    }


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config).expanduser())
    storage_state_path = (
        Path(args.storage_state).expanduser()
        if args.storage_state
        else Path(config.get("storage_state_path") or DEFAULT_STORAGE_STATE_PATH).expanduser()
    )
    source_json_path = Path(args.source_json).expanduser() if args.source_json else None
    statuses = {part.strip() for part in str(args.status or "").split(",") if part.strip()}
    targets = load_targets(source_json_path, statuses, args.url)

    if not targets:
        print(json.dumps({"ok": True, "targets": 0, "results": []}, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0

    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(storage_state=str(storage_state_path))
        page = context.new_page()
        for target in targets:
            results.append(
                recheck_page(
                    page=page,
                    target=target,
                    request_permissions=bool(args.request_permissions),
                    request_message=str(args.permission_request_message or "").strip(),
                )
            )
        context.close()
        browser.close()

    summary = {
        "ok": True,
        "source_json": str(source_json_path) if source_json_path else "",
        "storage_state_path": str(storage_state_path),
        "targets": len(targets),
        "requestable": sum(1 for item in results if item.get("status") == "requestable"),
        "permission_requested": sum(1 for item in results if item.get("status") == "permission_requested"),
        "permission_pending": sum(1 for item in results if item.get("status") == "permission_pending"),
        "failed": sum(1 for item in results if item.get("status") == "failed"),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
