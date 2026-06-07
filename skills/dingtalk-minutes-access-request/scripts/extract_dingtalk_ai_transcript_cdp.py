#!/usr/bin/env python3
import argparse
import json
import time

from playwright.sync_api import Page, sync_playwright


DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:19222"
DEFAULT_URL_SUBSTRING = "shanji.dingtalk.com/app/transcribes/"
DEFAULT_TRANSCRIPT_TIMEOUT_S = 240.0
DEFAULT_AI_SUMMARY_TIMEOUT_S = 8.0


GET_PAGE_META_JS = """
() => ({
  title: document.title,
  url: location.href
})
"""


GET_TRANSCRIPT_STATE_JS = """
() => {
  const contents =
    document.querySelector('.fm-transcribe-text__variable-size-list > div') ||
    document.querySelector('[data-overlayscrollbars-contents]');
  if (!contents) return { found: false };
  let scroller = contents;
  let cur = contents;
  while (cur) {
    if (cur.scrollHeight > cur.clientHeight + 5) {
      scroller = cur;
      break;
    }
    cur = cur.parentElement;
  }
  const text = (contents.innerText || '').replace(/\\u00a0/g, ' ');
  return {
    found: true,
    scrollTop: scroller.scrollTop,
    scrollHeight: scroller.scrollHeight,
    clientHeight: scroller.clientHeight,
    text
  };
}
"""


GET_AI_SUMMARY_JS = """
() => {
  const el =
    document.querySelector('.fm-full-text-summary__content') ||
    document.querySelector('.fm-full-text-summary') ||
    document.querySelector('.fm-tiptap-md-editor');
  if (!el) return { found: false };
  const text = (el.innerText || '').replace(/\\u00a0/g, ' ').trim();
  return {
    found: true,
    className: String(el.className || ''),
    charCount: text.length,
    text
  };
}
"""


SET_TRANSCRIPT_SCROLL_JS = """
(value) => {
  const contents =
    document.querySelector('.fm-transcribe-text__variable-size-list > div') ||
    document.querySelector('[data-overlayscrollbars-contents]');
  if (!contents) return { found: false };
  let scroller = contents;
  let cur = contents;
  while (cur) {
    if (cur.scrollHeight > cur.clientHeight + 5) {
      scroller = cur;
      break;
    }
    cur = cur.parentElement;
  }
  scroller.scrollTop = value;
  scroller.dispatchEvent(new Event('scroll', { bubbles: true }));
  return {
    found: true,
    scrollTop: scroller.scrollTop,
    scrollHeight: scroller.scrollHeight,
    clientHeight: scroller.clientHeight
  };
}
"""


STEP_TRANSCRIPT_SCROLL_JS = """
() => {
  const contents =
    document.querySelector('.fm-transcribe-text__variable-size-list > div') ||
    document.querySelector('[data-overlayscrollbars-contents]');
  if (!contents) return { found: false };
  let scroller = contents;
  let cur = contents;
  while (cur) {
    if (cur.scrollHeight > cur.clientHeight + 5) {
      scroller = cur;
      break;
    }
    cur = cur.parentElement;
  }
  const step = Math.max(260, Math.floor(scroller.clientHeight * 0.8));
  scroller.scrollTop = Math.min(scroller.scrollTop + step, scroller.scrollHeight);
  scroller.dispatchEvent(new Event('scroll', { bubbles: true }));
  return {
    found: true,
    scrollTop: scroller.scrollTop,
    scrollHeight: scroller.scrollHeight,
    clientHeight: scroller.clientHeight
  };
}
"""


ENSURE_TRANSCRIPT_TAB_JS = """
() => {
  const normalize = (value) => ((value || '').replace(/\\s+/g, ' ')).trim();
  const candidates = Array.from(document.querySelectorAll('div,span,button')).filter((el) => {
    const text = normalize(el.innerText || el.textContent);
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && (text === '转写' || text === 'Transcribe');
  });
  const target = candidates[0] || null;
  if (!target) return { clicked: false };
  target.click();
  return { clicked: true, text: normalize(target.innerText || target.textContent) };
}
"""


ENSURE_AI_SUMMARY_TAB_JS = """
() => {
  const normalize = (value) => ((value || '').replace(/\\s+/g, ' ')).trim();
  const candidates = Array.from(document.querySelectorAll('div,span,button')).filter((el) => {
    const text = normalize(el.innerText || el.textContent);
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && (text === 'AI纪要' || text === 'AI Summary');
  });
  const target = candidates[0] || null;
  if (!target) return { clicked: false };
  target.click();
  return { clicked: true, text: normalize(target.innerText || target.textContent) };
}
"""


def normalize_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def merge_snapshot_lines(snapshots: list[str]) -> list[str]:
    merged: list[str] = []
    for snapshot in snapshots:
        lines = normalize_lines(snapshot)
        if not lines:
            continue
        if not merged:
            merged = lines[:]
            continue

        max_overlap = min(len(merged), len(lines), 400)
        overlap = 0
        for width in range(max_overlap, 0, -1):
            if merged[-width:] == lines[:width]:
                overlap = width
                break

        if overlap:
            merged.extend(lines[overlap:])
            continue

        joined_existing = "\n".join(merged)
        joined_new = "\n".join(lines)
        if joined_new not in joined_existing:
            merged.extend(lines)

    deduped: list[str] = []
    for line in merged:
        if deduped and deduped[-1] == line:
            continue
        deduped.append(line)
    return deduped


def _wait_for_found_state(page: Page, state_js: str, timeout_s: float, poll_s: float = 0.2) -> dict:
    """Poll a page state function until it returns `found`, or the timeout expires."""
    deadline = time.monotonic() + timeout_s
    last_state: dict = {"found": False}
    while time.monotonic() < deadline:
        last_state = page.evaluate(state_js)
        if last_state.get("found"):
            return last_state
        time.sleep(poll_s)
    return last_state


def find_target_page(endpoint: str, url_substring: str) -> Page:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(endpoint)
        try:
            for context in browser.contexts:
                for page in context.pages:
                    if url_substring in page.url:
                        return page
        finally:
            pass
    raise RuntimeError(f"No page found for substring: {url_substring}")


def extract_transcript(
    page: Page,
    delay_s: float = 0.2,
    max_steps: int = 800,
    timeout_s: float = DEFAULT_TRANSCRIPT_TIMEOUT_S,
) -> tuple[str, dict]:
    page.evaluate(ENSURE_TRANSCRIPT_TAB_JS)
    page.wait_for_timeout(600)
    original_state = _wait_for_found_state(page, GET_TRANSCRIPT_STATE_JS, timeout_s=min(timeout_s, 4.0))
    if not original_state or not original_state.get("found"):
        raise RuntimeError("Transcript container '[data-overlayscrollbars-contents]' was not found.")

    original_scroll_top = int(original_state["scrollTop"])
    snapshots: list[str] = []
    last_signature = None
    stable_at_bottom = 0
    deadline = time.monotonic() + timeout_s

    try:
        page.evaluate(SET_TRANSCRIPT_SCROLL_JS, 0)
        time.sleep(0.8)

        for _ in range(max_steps):
            if time.monotonic() >= deadline:
                break
            state = page.evaluate(GET_TRANSCRIPT_STATE_JS)
            if not state.get("found"):
                time.sleep(0.2)
                continue

            text = state.get("text", "").strip()
            if text:
                signature = (
                    int(state["scrollTop"]),
                    len(text),
                    text[:120],
                    text[-120:],
                )
                if signature != last_signature:
                    snapshots.append(text)
                    last_signature = signature

            scroll_top = int(state["scrollTop"])
            scroll_height = int(state["scrollHeight"])
            client_height = int(state["clientHeight"])
            if scroll_top + client_height >= scroll_height - 5:
                stable_at_bottom += 1
                if stable_at_bottom >= 2:
                    break
            else:
                stable_at_bottom = 0

            page.evaluate(STEP_TRANSCRIPT_SCROLL_JS)
            remaining_s = deadline - time.monotonic()
            if remaining_s <= 0:
                break
            time.sleep(min(delay_s, remaining_s))
    finally:
        page.evaluate(SET_TRANSCRIPT_SCROLL_JS, original_scroll_top)

    merged_lines = merge_snapshot_lines(snapshots)
    transcript = "\n".join(merged_lines).strip()
    return transcript, {
        "snapshot_count": len(snapshots),
        "line_count": len(merged_lines),
        "char_count": len(transcript),
    }


def extract_ai_summary(page: Page, timeout_s: float = DEFAULT_AI_SUMMARY_TIMEOUT_S) -> tuple[str, dict]:
    page.evaluate(ENSURE_AI_SUMMARY_TAB_JS)
    page.wait_for_timeout(600)
    state = _wait_for_found_state(page, GET_AI_SUMMARY_JS, timeout_s=timeout_s)
    if not state.get("found"):
        raise RuntimeError("AI summary container was not found.")
    text = state.get("text", "").strip()
    return text, {"char_count": len(text), "class_name": state.get("className", "")}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract DingTalk AI transcript content from the dedicated CDP browser.")
    parser.add_argument("--cdp-endpoint", default=DEFAULT_CDP_ENDPOINT, help="Chrome CDP HTTP endpoint.")
    parser.add_argument("--url-substring", default=DEFAULT_URL_SUBSTRING, help="Substring used to find the target page.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(args.cdp_endpoint)
        try:
            target_page = None
            for context in browser.contexts:
                for page in context.pages:
                    if args.url_substring in page.url:
                        target_page = page
                        break
                if target_page:
                    break
            if target_page is None:
                raise RuntimeError(f"No page found for substring: {args.url_substring}")

            page_meta = target_page.evaluate(GET_PAGE_META_JS)
            transcript, transcript_meta = extract_transcript(target_page)
            ai_summary, ai_summary_meta = extract_ai_summary(target_page)
            output = {
                "title": page_meta.get("title", ""),
                "url": page_meta.get("url", ""),
                "transcript": transcript,
                "ai_summary": ai_summary,
                "transcript_meta": transcript_meta,
                "ai_summary_meta": ai_summary_meta,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
