#!/usr/bin/env python3
import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import Page


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = SKILL_DIR / "config.json"
DEFAULT_STORAGE_STATE_PATH = Path.home() / "Documents" / "dingtalk-minutes-access-request" / ".storage_state.json"
DEFAULT_PERMISSION_REQUEST_MESSAGE = "用于工作相关会议纪要查看，如内容与工作无关或涉及个人隐私，请拒绝"
PERMISSION_STATE_TIMEOUT_MS = 10000
PERMISSION_STATE_RETRIES = 3
PERMISSION_STATE_RETRY_DELAY_MS = 3000


def emit_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


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


def wait_for_detail_ready(page: Page, timeout_ms: int = 10000) -> dict:
    start = time.time()
    while (time.time() - start) * 1000 < timeout_ms:
        state = page.evaluate(
            """
            () => {
              const body = (document.body.innerText || '').replace(/\\u00a0/g, ' ').trim();
              const contentEl = document.querySelector('[data-overlayscrollbars-contents]');
              const contentText = contentEl ? (contentEl.innerText || '').replace(/\\u00a0/g, ' ').trim() : '';
              return {
                url: location.href,
                title: document.title,
                is_permission: location.pathname.includes('/app/permission/') || body.includes('暂无权限访问'),
                has_content: !!contentEl,
                content_text_len: contentText.length,
                body_head: body.slice(0, 400)
              };
            }
            """
        )
        if state.get("is_permission"):
            return state
        if state.get("has_content") and int(state.get("content_text_len", 0)) >= 40:
            return state
        page.wait_for_timeout(300)

    return page.evaluate(
        """
        () => {
          const body = (document.body.innerText || '').replace(/\\u00a0/g, ' ').trim();
          const contentEl = document.querySelector('[data-overlayscrollbars-contents]');
          const contentText = contentEl ? (contentEl.innerText || '').replace(/\\u00a0/g, ' ').trim() : '';
          return {
            url: location.href,
            title: document.title,
            is_permission: location.pathname.includes('/app/permission/') || body.includes('暂无权限访问'),
            has_content: !!contentEl,
            content_text_len: contentText.length,
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
              const match = body.match(/(?:暂无权限访问|No permission to access)\\s*[\\"“”「]?\\s*([\\s\\S]*?)\\s*[\\"“”」]?\\s*(?:当前账号|Current account|Request permission from)/);
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
