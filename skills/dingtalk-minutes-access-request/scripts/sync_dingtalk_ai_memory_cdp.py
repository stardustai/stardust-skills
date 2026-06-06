#!/usr/bin/env python3
import argparse
import calendar
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from extract_dingtalk_ai_transcript_cdp import (
    GET_AI_SUMMARY_JS,
    GET_PAGE_META_JS,
    GET_TRANSCRIPT_STATE_JS,
    extract_ai_summary,
    extract_transcript,
)


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = SKILL_DIR / "config.json"
DEFAULT_BASE_MEMORY_DIR = Path.home() / "Documents" / "dingtalk-minutes-access-request" / "captures"
DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:19222"
DEFAULT_STORAGE_STATE_PATH = Path.home() / "Documents" / "dingtalk-minutes-access-request" / ".storage_state.json"
DEFAULT_CHROME_PROFILE_DIR = Path.home() / "Documents" / "dingtalk-minutes-access-request" / ".chrome-profile"
MAIN_CHROME_USER_DATA_DIR = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
TRANSCRIBE_URL_TEMPLATE = "https://shanji.dingtalk.com/app/transcribes/{row_key}"
HISTORY_URL = "https://shanji-admin.dingtalk.com/history"
DEFAULT_PERMISSION_REQUEST_MESSAGE = "AI自动抓取，用于会议纪要整理，如和工作内容无关或者涉及个人隐私，请拒绝"
DEFAULT_LOOKBACK_MONTHS = 3
PERMISSION_STATE_TIMEOUT_MS = 10000
PERMISSION_STATE_RETRIES = 3
PERMISSION_STATE_RETRY_DELAY_MS = 1500


def sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned or "untitled"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_config(config_path: Path) -> dict:
    config = read_json(config_path)
    return config if isinstance(config, dict) else {}


def pid_is_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_lock_info(lock_path: Path) -> dict:
    payload = read_json(lock_path)
    return payload if isinstance(payload, dict) else {}


def coerce_path(value: str | None, default: Path) -> Path:
    if not value:
        return default.expanduser()
    return Path(value).expanduser()


def resolve_settings(args: argparse.Namespace) -> dict:
    config_path = Path(args.config).expanduser()
    config = load_config(config_path)
    base_dir = coerce_path(args.base_dir or config.get("base_dir"), DEFAULT_BASE_MEMORY_DIR)
    lock_path = coerce_path(args.lock_path or config.get("lock_path"), base_dir / ".sync.lock")
    permission_request_message = str(
        args.permission_request_message
        or config.get("permission_request_message")
        or DEFAULT_PERMISSION_REQUEST_MESSAGE
    ).strip()
    cdp_endpoint = str(args.cdp_endpoint or config.get("cdp_endpoint") or DEFAULT_CDP_ENDPOINT).strip()
    storage_state_path = coerce_path(args.storage_state or config.get("storage_state_path"), DEFAULT_STORAGE_STATE_PATH)
    lookback_months = int(args.lookback_months or config.get("lookback_months") or DEFAULT_LOOKBACK_MONTHS)
    stop_before_date = str(args.stop_before_date or config.get("stop_before_date") or "").strip()
    refresh_storage_state_from_cdp = bool(
        config.get("refresh_storage_state_from_cdp", False)
        if args.refresh_storage_state_from_cdp is None
        else args.refresh_storage_state_from_cdp
    )
    refresh_storage_state_from_main_chrome_profile = bool(
        config.get("refresh_storage_state_from_main_chrome_profile", False)
        if args.refresh_storage_state_from_main_chrome_profile is None
        else args.refresh_storage_state_from_main_chrome_profile
    )
    return {
        "config_path": config_path,
        "base_dir": base_dir,
        "lock_path": lock_path,
        "permission_request_message": permission_request_message,
        "cdp_endpoint": cdp_endpoint,
        "storage_state_path": storage_state_path,
        "lookback_months": lookback_months,
        "stop_before_date": stop_before_date,
        "refresh_storage_state_from_cdp": refresh_storage_state_from_cdp,
        "refresh_storage_state_from_main_chrome_profile": refresh_storage_state_from_main_chrome_profile,
    }


def acquire_run_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_lock_info(lock_path)
    existing_pid = existing.get("pid")
    if existing and not pid_is_alive(int(existing_pid) if str(existing_pid).isdigit() else None):
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        current = read_lock_info(lock_path)
        handle.close()
        current_pid = current.get("pid")
        raise RuntimeError(
            f"Another sync run is already active: {lock_path}"
            + (f" (pid={current_pid})" if current_pid else "")
        )
    handle.seek(0)
    handle.truncate()
    handle.write(json.dumps({"pid": os.getpid(), "started_at": time.time()}, ensure_ascii=False) + "\n")
    handle.flush()
    return handle


def release_run_lock(handle) -> None:
    if handle is None:
        return
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def emit_progress(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)


def glob_capture_exists(base_dir: Path, row_key: str) -> bool:
    row_key_marker = f"<!-- row_key: {row_key} -->"
    for markdown_path in base_dir.glob("*/*.md"):
        try:
            head = markdown_path.read_text(encoding="utf-8")[:512]
        except Exception:
            continue
        if row_key_marker in head:
            return True
    return False


def cleanup_undownloaded_dirs(base_dir: Path) -> int:
    removed = 0
    for permission_path in sorted(base_dir.glob("*/*/permission.json")):
        row_dir = permission_path.parent
        row_key = row_dir.name
        if glob_capture_exists(base_dir, row_key):
            continue
        permission_path.unlink()
        if row_dir.exists() and not any(row_dir.iterdir()):
            row_dir.rmdir()
            parent_dir = row_dir.parent
            if parent_dir.exists() and not any(parent_dir.iterdir()):
                parent_dir.rmdir()
        removed += 1
    return removed


def parse_history_last_active(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def build_summary_markdown(row_key: str, payload: dict) -> str:
    ai_summary = (payload.get("ai_summary") or "").rstrip()
    transcript = (payload.get("transcript") or "").rstrip()
    if not ai_summary:
        ai_summary = "(empty ai_summary)"
    if not transcript:
        transcript = "(empty transcript)"
    return "\n".join(
        [
            f"<!-- row_key: {row_key} -->",
            f"<!-- source_url: {payload.get('url', '')} -->",
            "",
            "# AI Summary",
            "",
            ai_summary,
            "",
            "# Transcript",
            "",
            transcript,
            "",
        ]
    )


def build_markdown_filename(title: str, timestamp: datetime) -> str:
    """Return the persisted markdown filename for a transcript capture."""
    return f"{sanitize_name(title)} {timestamp.strftime('%Y-%m-%d %H:%M')}.md"


def target_path_for_capture(meeting_dir: Path, title: str, timestamp: datetime, row_key: str) -> Path:
    """Return a non-colliding path for a row-keyed transcript capture."""
    target_path = meeting_dir / build_markdown_filename(title, timestamp)
    if not target_path.exists():
        return target_path

    head = target_path.read_text(encoding="utf-8", errors="ignore")[:512]
    if f"<!-- row_key: {row_key} -->" in head:
        return target_path

    suffix = row_key[-8:]
    return meeting_dir / f"{sanitize_name(title)} {timestamp.strftime('%Y-%m-%d %H:%M')} {suffix}.md"


def save_capture(base_dir: Path, row_key: str, title: str, payload: dict) -> Path:
    sanitized_title = sanitize_name(title)
    meeting_dir = base_dir / sanitized_title
    meeting_dir.mkdir(parents=True, exist_ok=True)

    history_row = payload.get("history_row") or {}
    timestamp = parse_history_last_active(str(history_row.get("last_active") or ""))
    if timestamp is None:
        timestamp = datetime.now()
    target_path = target_path_for_capture(meeting_dir, sanitized_title, timestamp, row_key)
    write_text(target_path, build_summary_markdown(row_key, payload))
    return target_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch sync DingTalk AI transcript history via CDP.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to JSON config.")
    parser.add_argument("--base-dir", help="Base output directory. Overrides config.")
    parser.add_argument("--lock-path", help="Path to the run-lock file. Overrides config.")
    parser.add_argument("--cdp-endpoint", help="CDP HTTP endpoint. Overrides config.")
    parser.add_argument("--storage-state", help="Playwright storage_state.json for headless runs.")
    parser.add_argument("--use-storage-state", action="store_true", help="Launch a headless browser using storage_state instead of CDP.")
    parser.add_argument("--permission-request-message", help="Reason text to fill before clicking '发送申请'.")
    parser.add_argument("--lookback-months", type=int, help="Default lookback window in calendar months when stop-before-date is not provided.")
    parser.add_argument("--stop-before-date", help="Stop when history rows are older than this local timestamp, format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS.")
    parser.add_argument("--max-pages", type=int, help="Optional page limit.")
    parser.add_argument("--max-items", type=int, help="Optional item limit.")
    parser.add_argument("--no-request-permissions", action="store_true", help="Do not click '发送申请'.")
    parser.add_argument(
        "--refresh-storage-state-from-cdp",
        dest="refresh_storage_state_from_cdp",
        action="store_true",
        default=None,
        help="Before a storage-state run, export a fresh storage_state.json from the live CDP browser if available.",
    )
    parser.add_argument(
        "--no-refresh-storage-state-from-cdp",
        dest="refresh_storage_state_from_cdp",
        action="store_false",
        help="Do not refresh storage_state.json from the live CDP browser before running.",
    )
    parser.add_argument(
        "--refresh-storage-state-from-main-chrome-profile",
        dest="refresh_storage_state_from_main_chrome_profile",
        action="store_true",
        default=None,
        help="Before a storage-state run, export a fresh storage_state.json from a copied main Chrome Default profile.",
    )
    parser.add_argument(
        "--no-refresh-storage-state-from-main-chrome-profile",
        dest="refresh_storage_state_from_main_chrome_profile",
        action="store_false",
        help="Do not refresh storage_state.json from a copied main Chrome Default profile before running.",
    )
    parser.add_argument(
        "--use-main-chrome-session",
        action="store_true",
        help="Debug mode: launch a visible Chrome window from a copied main Chrome Default profile instead of headless storage_state mode.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def subtract_calendar_months(value: datetime, months: int) -> datetime:
    year = value.year
    month = value.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day, hour=0, minute=0, second=0, microsecond=0)


def parse_local_timestamp(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            if fmt == "%Y-%m-%d":
                parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
            return parsed
        except ValueError:
            continue
    return None


def wait_for_history_ready(page: Page, timeout_ms: int = 15000) -> None:
    page.goto(HISTORY_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        pass
    login_state = page.evaluate(
        """
        () => {
          const body = (document.body.innerText || '').replace(/\\u00a0/g, ' ').trim();
          const title = document.title || '';
          const url = location.href;
          const looksLoggedOut =
            /登录|登入|login|sign in|扫码|scan/i.test(title) ||
            /登录|登入|login|sign in|扫码登录|账号登录|手机号登录|短信验证码|Scan|QR code/i.test(body);
          return {
            url,
            title,
            body_head: body.slice(0, 500),
            looks_logged_out: looksLoggedOut,
          };
        }
        """
    )
    if login_state.get("looks_logged_out"):
        raise RuntimeError(
            "Login required before history is accessible: "
            + json.dumps(login_state, ensure_ascii=False)
        )
    page.wait_for_function(
        """
        () => {
          if (location.pathname !== '/history') return false;
          if (document.querySelector('tr[data-row-key]')) return true;
          const body = (document.body.innerText || '').replace(/\\u00a0/g, ' ');
          return (
            body.includes('历史记录') ||
            body.includes('History') ||
            body.includes('Historical AI Minutes records') ||
            body.includes('No content')
          );
        }
        """,
        timeout=timeout_ms,
    )


def apply_history_start_date_filter(page: Page, start_dt: datetime, timeout_ms: int = 15000) -> dict:
    start_title = start_dt.strftime("%Y-%m-%d")
    start_value = start_dt.strftime("%Y-%m-%d 00:00:00")

    picker_input = page.locator("div.dtd-picker-input").first
    picker_input.click()
    page.wait_for_timeout(300)

    target_cell = page.locator(f'td.dtd-picker-cell[title="{start_title}"] .dtd-picker-cell-inner').first
    for _ in range(24):
        if target_cell.count():
            break
        page.locator("button.dtd-picker-header-prev-btn").click()
        page.wait_for_timeout(200)
    else:
        raise RuntimeError(f"Could not find history start date cell for {start_title}")

    target_cell.click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name=re.compile(r"^OK$", re.I)).click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name=re.compile(r"^Search$", re.I)).click()

    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        pass
    page.wait_for_timeout(4000)

    return page.evaluate(
        """
        () => ({
          start: document.querySelector('input[placeholder="Start date"]')?.value || '',
          end: document.querySelector('input[placeholder="End date"]')?.value || '',
          row_count: document.querySelectorAll('tr[data-row-key]').length,
          body_head: (document.body.innerText || '').slice(0, 800),
        })
        """
    )


def get_history_page(page: Page) -> dict:
    return page.evaluate(
        """
        () => {
          const rows = Array.from(document.querySelectorAll('tr[data-row-key]')).map((tr) => {
            const tds = Array.from(tr.querySelectorAll('td'));
            const button = tr.querySelector('button');
            return {
              row_key: tr.getAttribute('data-row-key') || '',
              masked_title: button ? (button.innerText || '').trim() : '',
              role: tds[2] ? (tds[2].innerText || '').trim() : '',
              initiator: tds[3] ? (tds[3].innerText || '').trim() : '',
              size: tds[4] ? (tds[4].innerText || '').trim() : '',
              last_active: tds[5] ? (tds[5].innerText || '').trim() : ''
            };
          });
          const currentPage = parseInt(document.querySelector('li.dtd-pagination-item-active')?.getAttribute('title') || '1', 10);
          const nextEnabled = !!document.querySelector('li.dtd-pagination-next[aria-disabled="false"] button');
          const totalPages = parseInt(Array.from(document.querySelectorAll('li.dtd-pagination-item')).slice(-1)[0]?.getAttribute('title') || String(currentPage), 10);
          return {
            current_page: currentPage,
            total_pages: totalPages,
            next_enabled: nextEnabled,
            rows
          };
        }
        """
    )


def go_to_next_page(page: Page, expected_next_page: int, previous_first_row_key: str = "") -> bool:
    clicked = page.evaluate(
        """
        () => {
          const btn = document.querySelector('li.dtd-pagination-next[aria-disabled="false"] button');
          if (!btn) return false;
          btn.click();
          return true;
        }
        """
    )
    if not clicked:
        return False
    page.wait_for_function(
        """
        ({ expectedPage, previousFirstRowKey }) => {
          const active = document.querySelector('li.dtd-pagination-item-active');
          const currentPage = parseInt(active?.getAttribute('title') || '0', 10);
          if (currentPage !== expectedPage) return false;
          const firstRowKey = document.querySelector('tr[data-row-key]')?.getAttribute('data-row-key') || '';
          if (!previousFirstRowKey) return !!firstRowKey;
          return !!firstRowKey && firstRowKey !== previousFirstRowKey;
        }
        """,
        arg={"expectedPage": expected_next_page, "previousFirstRowKey": previous_first_row_key},
        timeout=10000,
    )
    return True


def wait_for_detail_ready(page: Page, timeout_ms: int = 10000) -> dict:
    start = time.time()
    while (time.time() - start) * 1000 < timeout_ms:
        state = page.evaluate(
            """
            () => {
              const body = (document.body.innerText || '').replace(/\\u00a0/g, ' ').trim();
              const transcriptEl = document.querySelector('[data-overlayscrollbars-contents]');
              const transcriptText = transcriptEl ? (transcriptEl.innerText || '').replace(/\\u00a0/g, ' ').trim() : '';
              return {
                url: location.href,
                title: document.title,
                is_permission: location.pathname.includes('/app/permission/') || body.includes('暂无权限访问'),
                has_transcript: !!transcriptEl,
                transcript_text_len: transcriptText.length,
                has_ai_summary: !!(
                  document.querySelector('.fm-full-text-summary__content') ||
                  document.querySelector('.fm-full-text-summary') ||
                  document.querySelector('.fm-tiptap-md-editor')
                ),
                body_head: body.slice(0, 400)
              };
            }
            """
        )
        if state.get("is_permission"):
            return state
        if state.get("has_transcript") and int(state.get("transcript_text_len", 0)) >= 40:
            return state
        if state.get("has_ai_summary") and state.get("body_head"):
            return state
        page.wait_for_timeout(300)

    return page.evaluate(
        """
        () => {
          const body = (document.body.innerText || '').replace(/\\u00a0/g, ' ').trim();
          const transcriptEl = document.querySelector('[data-overlayscrollbars-contents]');
          const transcriptText = transcriptEl ? (transcriptEl.innerText || '').replace(/\\u00a0/g, ' ').trim() : '';
          return {
            url: location.href,
            title: document.title,
            is_permission: location.pathname.includes('/app/permission/') || body.includes('暂无权限访问'),
            has_transcript: !!transcriptEl,
            transcript_text_len: transcriptText.length,
            has_ai_summary: !!(
              document.querySelector('.fm-full-text-summary__content') ||
              document.querySelector('.fm-full-text-summary') ||
              document.querySelector('.fm-tiptap-md-editor')
            ),
            body_head: body.slice(0, 400)
          };
        }
        """
    )


def get_permission_state(page: Page, timeout_ms: int = PERMISSION_STATE_TIMEOUT_MS) -> dict:
    deadline = time.time() + timeout_ms / 1000
    last_state = {
        "title": "",
        "body": "",
        "can_request": False,
        "request_button_text": "",
        "request_button_disabled": False,
        "request_target_unresolved": False,
        "already_requested": False,
    }
    while time.time() < deadline:
        state = page.evaluate(
            """
            () => {
              const normalize = (value) => ((value || '').replace(/\\s+/g, ' ')).trim();
              const directButton = Array.from(document.querySelectorAll('button')).find((el) => {
                const text = normalize(el.innerText || el.textContent);
                return /^(发送申请|Send Application)$/i.test(text);
              });
              const body = (document.body.innerText || '').replace(/\\u00a0/g, ' ').trim();
              const match = body.match(/(?:暂无权限访问|No permission to access)\\s*[\"“”「]?\\s*([\\s\\S]*?)\\s*[\"“”」]?\\s*(?:当前账号|Current account|Request permission from)/);
              return {
                title: match ? match[1].replace(/\\s+/g, ' ').trim() : '',
                body,
                can_request: !!directButton,
                request_button_text: directButton ? normalize(directButton.innerText || directButton.textContent) : '',
                request_button_disabled: !!(directButton && directButton.disabled),
                request_target_unresolved: /(?:Request permission from|向谁申请|申请给)\\s*Please select|请选择/i.test(body),
                already_requested: /已发送|申请已发送|等待审批|审批中|已向|Applied to|Reapply|Refresh Page/.test(body)
              };
            }
            """
        )
        last_state = state
        body_text = str(state.get("body") or "").strip()
        body_is_placeholder = body_text.lower() in {"loading", "loading..."} or body_text in {"加载中", "加载中..."}
        if (body_text and not body_is_placeholder) or state.get("can_request") or state.get("already_requested"):
            return state
        page.wait_for_timeout(250)
    return last_state


def click_send_request(page: Page, request_message: str) -> bool:
    textarea = page.locator("textarea").first
    if textarea.count():
        textarea.fill(request_message or "")

    send_button = page.get_by_role("button", name=re.compile(r"^(发送申请|Send Application)$", re.I)).first
    if not send_button.count():
        return False

    if send_button.is_disabled():
        # Some DingTalk permission pages render the button first, then hydrate the approver target later.
        page.wait_for_timeout(1500)

    if send_button.is_disabled():
        picker = page.get_by_text(re.compile(r"^(Please select|请选择)$", re.I)).first
        if picker.count():
            picker.click(force=True)
            page.wait_for_timeout(800)

    if send_button.is_disabled():
        return False

    send_button.click()
    return True


def resolve_permission_page(page: Page, topic: str, request_permissions: bool, request_message: str) -> tuple[str, dict, int]:
    last_state = {}
    requested = False
    for attempt in range(1, PERMISSION_STATE_RETRIES + 1):
        state = get_permission_state(page)
        last_state = state

        if state.get("already_requested"):
            return ("permission_requested" if requested else "permission_pending", state, attempt)

        if request_permissions and state.get("can_request"):
            requested = click_send_request(page, request_message)
            if requested:
                emit_progress(f"Clicked 发送申请 for {topic}; waiting 3s")
                page.wait_for_timeout(3000)
                state = get_permission_state(page)
                return ("permission_requested", state, attempt)

        if attempt >= PERMISSION_STATE_RETRIES:
            break

        emit_progress(
            f"Permission page unresolved for {topic}; retry {attempt + 1}/{PERMISSION_STATE_RETRIES} after {PERMISSION_STATE_RETRY_DELAY_MS}ms"
        )
        page.wait_for_timeout(PERMISSION_STATE_RETRY_DELAY_MS)
        page.reload(wait_until="domcontentloaded")
        wait_for_detail_ready(page)

    if last_state.get("can_request"):
        if last_state.get("request_target_unresolved") or last_state.get("request_button_disabled"):
            return ("permission_pending", last_state, PERMISSION_STATE_RETRIES)

    return ("failed", last_state, PERMISSION_STATE_RETRIES)


def refresh_storage_state_from_cdp(pw, cdp_endpoint: str, storage_state_path: Path) -> dict:
    browser = pw.chromium.connect_over_cdp(cdp_endpoint)
    try:
        if not browser.contexts:
            raise RuntimeError(f"No browser contexts found for {cdp_endpoint}")
        context = browser.contexts[0]
        result = persist_refreshed_storage_state(context, storage_state_path, "live_cdp_browser")
        result.update({
            "cdp_endpoint": cdp_endpoint,
        })
        return result
    finally:
        browser.close()


def prepare_main_chrome_profile_copy() -> Path:
    source_root = MAIN_CHROME_USER_DATA_DIR
    source_profile = source_root / "Default"
    source_local_state = source_root / "Local State"
    if not source_profile.exists():
        raise RuntimeError(f"Main Chrome profile not found: {source_profile}")
    if not source_local_state.exists():
        raise RuntimeError(f"Main Chrome Local State not found: {source_local_state}")

    temp_root = Path(tempfile.mkdtemp(prefix="chrome-main-profile-copy-"))
    target_profile = temp_root / "Default"
    rsync_cmd = [
        "rsync",
        "-a",
        "--delete",
        "--exclude=*/Cache/*",
        "--exclude=*/GPUCache/*",
        "--exclude=*/Code Cache/*",
        "--exclude=*/Service Worker/CacheStorage/*",
        "--exclude=*/Blob Storage/*",
        f"{str(source_profile)}/",
        str(target_profile),
    ]
    subprocess.run(rsync_cmd, check=True)
    shutil.copy2(source_local_state, temp_root / "Local State")
    return temp_root


def load_storage_state_payload(storage_state_path: Path) -> dict:
    if not storage_state_path.exists():
        return {"cookies": [], "origins": []}
    return json.loads(storage_state_path.read_text(encoding="utf-8"))


def storage_state_counts(payload: dict) -> tuple[int, int]:
    return (len(payload.get("cookies", [])), len(payload.get("origins", [])))


def persist_refreshed_storage_state(context, storage_state_path: Path, source_label: str) -> dict:
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)
    previous_payload = load_storage_state_payload(storage_state_path)
    previous_cookie_count, previous_origin_count = storage_state_counts(previous_payload)

    with tempfile.NamedTemporaryFile(
        prefix=f"{storage_state_path.stem}.tmp-",
        suffix=storage_state_path.suffix,
        dir=str(storage_state_path.parent),
        delete=False,
    ) as handle:
        temp_storage_state_path = Path(handle.name)

    try:
        context.storage_state(path=str(temp_storage_state_path))
        refreshed_payload = load_storage_state_payload(temp_storage_state_path)
        cookie_count, origin_count = storage_state_counts(refreshed_payload)
        if (cookie_count == 0 and origin_count == 0) and (
            previous_cookie_count > 0 or previous_origin_count > 0
        ):
            return {
                "ok": False,
                "preserved_existing": True,
                "source": source_label,
                "output": str(storage_state_path),
                "cookie_count": cookie_count,
                "origin_count": origin_count,
                "previous_cookie_count": previous_cookie_count,
                "previous_origin_count": previous_origin_count,
            }

        temp_storage_state_path.replace(storage_state_path)
        return {
            "ok": True,
            "source": source_label,
            "output": str(storage_state_path),
            "cookie_count": cookie_count,
            "origin_count": origin_count,
            "previous_cookie_count": previous_cookie_count,
            "previous_origin_count": previous_origin_count,
        }
    finally:
        try:
            temp_storage_state_path.unlink()
        except FileNotFoundError:
            pass


def refresh_storage_state_from_main_chrome_profile(pw, storage_state_path: Path) -> dict:
    temp_main_profile_dir = prepare_main_chrome_profile_copy()
    context = None
    try:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(temp_main_profile_dir),
            channel="chrome",
            headless=True,
            args=["--profile-directory=Default"],
        )
        result = persist_refreshed_storage_state(context, storage_state_path, "main_chrome_profile_copy")
        result["profile_dir"] = str(temp_main_profile_dir)
        return result
    finally:
        if context is not None:
            context.close()
        shutil.rmtree(temp_main_profile_dir, ignore_errors=True)


def process_row(detail_page: Page, base_dir: Path, row: dict, request_permissions: bool, request_message: str) -> dict:
    row_key = row["row_key"]
    label = row.get("masked_title") or row_key
    emit_progress(f"Processing {label} ({row_key})")
    if glob_capture_exists(base_dir, row_key):
        emit_progress(f"Skipped existing {label}")
        return {"row_key": row_key, "status": "skipped_existing", "topic": row.get("masked_title", "")}

    detail_page.goto(TRANSCRIBE_URL_TEMPLATE.format(row_key=row_key), wait_until="domcontentloaded")
    ready = wait_for_detail_ready(detail_page)
    url = ready.get("url", detail_page.url)

    if ready.get("is_permission") or "/app/permission/" in url:
        state = get_permission_state(detail_page)
        topic = str(state.get("title") or "").strip() or row.get("masked_title") or row_key
        status, state, attempts = resolve_permission_page(detail_page, topic, request_permissions, request_message)
        payload = {
            "ok": False,
            "status": status,
            "row_key": row_key,
            "topic": topic,
            "source_url": url,
            "history_row": row,
            "page_state": state,
            "permission_attempts": attempts,
            "last_checked_at": time.time(),
        }
        emit_progress(f"{payload['status']} {topic}")
        return payload

    if "/app/transcribes/" in url and ready.get("has_transcript"):
        page_meta = detail_page.evaluate(GET_PAGE_META_JS)
        transcript, transcript_meta = extract_transcript(detail_page)
        ai_summary, ai_summary_meta = extract_ai_summary(detail_page)
        title = page_meta.get("title") or row.get("masked_title") or row_key
        payload = {
            "ok": True,
            "status": "downloaded",
            "row_key": row_key,
            "title": title,
            "url": page_meta.get("url", url),
            "history_row": row,
            "transcript": transcript,
            "ai_summary": ai_summary,
            "transcript_meta": transcript_meta,
            "ai_summary_meta": ai_summary_meta,
        }
        saved_path = save_capture(base_dir, row_key, title, payload)
        payload["saved_path"] = str(saved_path)
        payload["saved_dir"] = str(saved_path.parent)
        emit_progress(f"Downloaded {title}")
        return payload

    topic = row.get("masked_title") or row_key
    payload = {
        "ok": False,
        "status": "unexpected_page",
        "row_key": row_key,
        "topic": topic,
        "source_url": url,
        "history_row": row,
        "detail_state": ready,
        "last_checked_at": time.time(),
    }
    emit_progress(f"Unexpected page for {topic}")
    return payload


def main() -> int:
    args = parse_args()
    settings = resolve_settings(args)
    base_dir = settings["base_dir"]
    lock_path = settings["lock_path"]
    cdp_endpoint = settings["cdp_endpoint"]
    storage_state_path = settings["storage_state_path"]
    permission_request_message = settings["permission_request_message"]
    stop_before_date_text = settings["stop_before_date"]
    lookback_months = settings["lookback_months"]
    refresh_state = settings["refresh_storage_state_from_cdp"]
    refresh_state_from_main_profile = settings["refresh_storage_state_from_main_chrome_profile"]
    base_dir.mkdir(parents=True, exist_ok=True)
    lock_handle = None
    explicit_cutoff = parse_local_timestamp(stop_before_date_text) if stop_before_date_text else None
    cutoff_dt = explicit_cutoff or subtract_calendar_months(datetime.now(), lookback_months)

    try:
        lock_handle = acquire_run_lock(lock_path)
        emit_progress(f"Acquired run lock {lock_path}")
        emit_progress(f"History cutoff: stop before {cutoff_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "lock_path": str(lock_path)}, ensure_ascii=False), file=sys.stderr)
        return 1

    try:
        removed = cleanup_undownloaded_dirs(base_dir)
        if removed:
            emit_progress(f"Removed {removed} undownloaded directories")

        with sync_playwright() as pw:
            launched_browser = None
            temp_main_profile_dir = None
            if args.use_main_chrome_session:
                temp_main_profile_dir = prepare_main_chrome_profile_copy()
                emit_progress(f"Using copied main Chrome profile for visible debugging: {temp_main_profile_dir}")
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=str(temp_main_profile_dir),
                    channel="chrome",
                    headless=False,
                    args=["--profile-directory=Default"],
                )
                browser = context.browser
            elif args.use_storage_state:
                if refresh_state_from_main_profile:
                    try:
                        refresh_result = refresh_storage_state_from_main_chrome_profile(pw, storage_state_path)
                        if refresh_result.get("preserved_existing"):
                            emit_progress(
                                "Copied main Chrome profile produced empty storage_state; preserved existing "
                                f"state ({refresh_result['previous_cookie_count']} cookies, "
                                f"{refresh_result['previous_origin_count']} origins)"
                            )
                        else:
                            emit_progress(
                                "Refreshed storage_state.json from copied main Chrome profile "
                                f"({refresh_result['cookie_count']} cookies, {refresh_result['origin_count']} origins)"
                            )
                    except Exception as exc:
                        emit_progress(f"Main Chrome profile storage_state refresh skipped: {exc}")
                elif refresh_state:
                    try:
                        refresh_result = refresh_storage_state_from_cdp(pw, cdp_endpoint, storage_state_path)
                        if refresh_result.get("preserved_existing"):
                            emit_progress(
                                "Live CDP browser produced empty storage_state; preserved existing "
                                f"state ({refresh_result['previous_cookie_count']} cookies, "
                                f"{refresh_result['previous_origin_count']} origins)"
                            )
                        else:
                            emit_progress(
                                "Refreshed storage_state.json from live CDP browser "
                                f"({refresh_result['cookie_count']} cookies, {refresh_result['origin_count']} origins)"
                            )
                    except Exception as exc:
                        emit_progress(f"Live CDP storage_state refresh skipped: {exc}")
                try:
                    launched_browser = pw.chromium.launch(channel="chrome", headless=True)
                except Exception as exc:
                    emit_progress(f"Chrome launch failed; falling back to bundled Chromium: {exc}")
                    launched_browser = pw.chromium.launch(headless=True)
                context = launched_browser.new_context(storage_state=str(storage_state_path))
                browser = launched_browser
            else:
                browser = pw.chromium.connect_over_cdp(cdp_endpoint)
            try:
                if args.use_storage_state or args.use_main_chrome_session:
                    pass
                else:
                    if not browser.contexts:
                        raise RuntimeError(f"No browser contexts found for {cdp_endpoint}")
                    context = browser.contexts[0]
                history_page = context.pages[0] if context.pages else context.new_page()
                detail_page = context.new_page()
                emit_progress("Opening DingTalk AI history")
                wait_for_history_ready(history_page)
                history_filter_state = apply_history_start_date_filter(history_page, cutoff_dt)
                emit_progress(
                    "Applied history start date filter: "
                    f"{history_filter_state.get('start', '')} -> {history_filter_state.get('end', '')}; "
                    f"rows={history_filter_state.get('row_count', 0)}"
                )
                emit_progress("History ready; scratch tab opened")

                results = []
                seen_row_keys: set[str] = set()
                processed_count = 0
                page_limit = args.max_pages if args.max_pages and args.max_pages > 0 else None
                item_limit = args.max_items if args.max_items and args.max_items > 0 else None
                stop_due_to_cutoff = False

                while True:
                    page_state = get_history_page(history_page)
                    current_page = int(page_state.get("current_page", 1))
                    rows = page_state.get("rows", [])
                    emit_progress(f"History page {current_page}: {len(rows)} rows")
                    if not rows:
                        break

                    for row in rows:
                        row_key = row.get("row_key")
                        if not row_key or row_key in seen_row_keys:
                            continue
                        row_last_active = parse_local_timestamp(str(row.get("last_active") or ""))
                        if row_last_active and row_last_active < cutoff_dt:
                            emit_progress(
                                f"Stopping at {row.get('masked_title') or row_key}: "
                                f"{row_last_active.strftime('%Y-%m-%d %H:%M:%S')} is older than cutoff {cutoff_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                            stop_due_to_cutoff = True
                            break
                        seen_row_keys.add(row_key)
                        try:
                            result = process_row(
                                detail_page,
                                base_dir,
                                row,
                                request_permissions=not args.no_request_permissions,
                                request_message=permission_request_message,
                            )
                        except Exception as exc:
                            topic = row.get("masked_title") or row_key
                            result = {
                                "ok": False,
                                "status": "failed",
                                "row_key": row_key,
                                "topic": topic,
                                "history_row": row,
                                "error": str(exc),
                                "last_checked_at": time.time(),
                            }
                            emit_progress(f"Failed {topic}: {exc}")
                        results.append(result)
                        processed_count += 1
                        if item_limit and processed_count >= item_limit:
                            raise StopIteration

                    if stop_due_to_cutoff:
                        break

                    if page_limit and current_page >= page_limit:
                        break
                    if not page_state.get("next_enabled"):
                        break
                    emit_progress(f"Advancing to history page {current_page + 1}")
                    previous_first_row_key = rows[0].get("row_key", "") if rows else ""
                    if not go_to_next_page(history_page, current_page + 1, previous_first_row_key):
                        break
                detail_page.close()
            except StopIteration:
                pass
            finally:
                if args.use_main_chrome_session:
                    context.close()
                    if temp_main_profile_dir:
                        shutil.rmtree(temp_main_profile_dir, ignore_errors=True)
                else:
                    browser.close()

        summary = {
            "ok": True,
            "config_path": str(settings["config_path"]),
            "base_dir": str(base_dir),
            "lock_path": str(lock_path),
            "cdp_endpoint": cdp_endpoint,
            "storage_state_path": str(storage_state_path),
            "use_storage_state": bool(args.use_storage_state),
            "use_main_chrome_session": bool(args.use_main_chrome_session),
            "refresh_storage_state_from_cdp": bool(refresh_state),
            "refresh_storage_state_from_main_chrome_profile": bool(refresh_state_from_main_profile),
            "cutoff_before": cutoff_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "processed": len(results),
            "downloaded": sum(1 for item in results if item.get("status") == "downloaded"),
            "skipped_existing": sum(1 for item in results if item.get("status") == "skipped_existing"),
            "permission_requested": sum(1 for item in results if item.get("status") == "permission_requested"),
            "permission_pending": sum(1 for item in results if item.get("status") == "permission_pending"),
            "unexpected_page": sum(1 for item in results if item.get("status") == "unexpected_page"),
            "failed": sum(1 for item in results if item.get("status") == "failed"),
            "results": results,
        }
        emit_progress(
            f"Done: processed={summary['processed']} downloaded={summary['downloaded']} "
            f"skipped={summary['skipped_existing']} permission_requested={summary['permission_requested']} "
            f"permission_pending={summary['permission_pending']} failed={summary['failed']}"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0
    finally:
        release_run_lock(lock_handle)


if __name__ == "__main__":
    raise SystemExit(main())
