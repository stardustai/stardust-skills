#!/usr/bin/env python3
import json
import sys

from playwright.sync_api import sync_playwright


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: debug_permission_page.py <storage_state_path> <row_key>", file=sys.stderr)
        return 2

    storage_state_path = sys.argv[1]
    row_key = sys.argv[2]
    url = f"https://shanji.dingtalk.com/app/transcribes/{row_key}"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        payload = page.evaluate(
            """
            () => {
              const simplify = (el) => ({
                tag: el.tagName,
                type: el.getAttribute('type') || '',
                cls: String(el.className || '').slice(0, 200),
                text: ((el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim()).slice(0, 200),
                aria: el.getAttribute('aria-label') || '',
                placeholder: el.getAttribute('placeholder') || '',
                name: el.getAttribute('name') || '',
                disabled: !!el.disabled,
                role: el.getAttribute('role') || '',
              });
              return {
                url: location.href,
                title: document.title,
                body: (document.body.innerText || '').slice(0, 3000),
                elements: Array.from(document.querySelectorAll('button, textarea, input, [role="button"]')).map(simplify),
              };
            }
            """
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
