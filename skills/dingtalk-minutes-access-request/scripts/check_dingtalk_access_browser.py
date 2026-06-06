#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


DEFAULT_PORT = 19222


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check the dedicated DingTalk access-request browser via CDP.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Remote debugging port.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    endpoint = f"http://127.0.0.1:{args.port}"
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(endpoint)
        contexts = browser.contexts
        pages = []
        for context in contexts:
            for page in context.pages:
                try:
                    pages.append(
                        {
                            "url": page.url,
                            "title": page.title(),
                        }
                    )
                except Exception as exc:
                    pages.append({"url": page.url, "title": "", "error": str(exc)})
        output = {
            "ok": True,
            "endpoint": endpoint,
            "context_count": len(contexts),
            "page_count": len(pages),
            "pages": pages,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
