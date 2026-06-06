#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path.home() / "output" / "doc"
OPENCLAW = "openclaw"
DEFAULT_PROFILE_CANDIDATES = ("chrome", "chrome-relay", "user", "openclaw")
SUPPORTED_FORMATS = {
    "docx": {
        "menu_text": "Word(.docx)",
        "wait_pattern": "queryExportJobInfo",
        "extension": ".docx",
    },
    "pdf": {
        "menu_text": "PDF(.pdf)",
        "wait_pattern": "queryExportJobInfo",
        "extension": ".pdf",
    },
    "md": {
        "menu_text": "Markdown(.md)",
        "wait_pattern": "queryExportJobInfo",
        "extension": ".md",
    },
}


def choose_browser_profile(explicit_profile=None):
    if explicit_profile:
        return explicit_profile

    env_profile = os.environ.get("OPENCLAW_BROWSER_PROFILE")
    if env_profile:
        return env_profile

    result = subprocess.run(
        [OPENCLAW, "browser", "profiles", "--json"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Failed to list OpenClaw browser profiles.")

    data = json.loads(result.stdout)
    profiles = data.get("profiles") or []
    by_name = {profile.get("name"): profile for profile in profiles}

    for name in DEFAULT_PROFILE_CANDIDATES:
        profile = by_name.get(name)
        if profile and profile.get("running"):
            return name

    for name in DEFAULT_PROFILE_CANDIDATES:
        if name in by_name:
            return name

    available = ", ".join(sorted(name for name in by_name if name)) or "(none)"
    raise RuntimeError(f"No supported OpenClaw browser profile found. Available profiles: {available}")


def run_openclaw(args, browser_profile, check=True, timeout=45):
    cmd = [OPENCLAW, "browser", "--browser-profile", browser_profile] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "openclaw command failed")
    return result


def get_active_tab(browser_profile):
    result = run_openclaw(["tabs", "--json"], browser_profile=browser_profile, timeout=20)
    data = json.loads(result.stdout)
    tabs = data.get("tabs") or []
    if not tabs:
        raise RuntimeError("No Chrome tabs reported by OpenClaw.")
    tab = tabs[0]
    url = tab.get("url", "")
    if "alidocs.dingtalk.com/i/nodes/" not in url:
        raise RuntimeError(f"Active Chrome tab is not a DingTalk document: {url}")
    return tab


def json_string(value):
    return json.dumps(value, ensure_ascii=False)


def build_trigger_js(menu_text):
    return f"""
async () => {{
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const iframe = document.querySelector("iframe");
  if (!iframe || !iframe.contentDocument) {{
    throw new Error("No same-origin editor iframe found.");
  }}
  const d = iframe.contentDocument;
  const w = iframe.contentWindow;

  if (!w.__codexDownloadBlockerInstalled) {{
    w.__codexBlockedDownloads = [];
    const isExportDownload = (url) => {{
      if (!url) return false;
      const text = String(url);
      return text.includes("alidocs-body.oss-") ||
        text.includes("/export/tempres/") ||
        /\\.(docx|pdf|md)(\\?|$)/i.test(text);
    }};

    const originalOpen = w.open ? w.open.bind(w) : null;
    if (originalOpen) {{
      w.open = function(url, ...rest) {{
        if (isExportDownload(url)) {{
          w.__codexBlockedDownloads.push({{ kind: "window.open", url: String(url), ts: Date.now() }});
          return null;
        }}
        return originalOpen(url, ...rest);
      }};
    }}

    const originalAnchorClick = w.HTMLAnchorElement && w.HTMLAnchorElement.prototype.click;
    if (originalAnchorClick) {{
      w.HTMLAnchorElement.prototype.click = function(...args) {{
        const href = this.href || this.getAttribute("href") || "";
        if (isExportDownload(href)) {{
          w.__codexBlockedDownloads.push({{ kind: "anchor.click", url: String(href), ts: Date.now() }});
          return;
        }}
        return originalAnchorClick.apply(this, args);
      }};
    }}

    d.addEventListener("click", (event) => {{
      const anchor = event.target && event.target.closest ? event.target.closest("a[href]") : null;
      const href = anchor && (anchor.href || anchor.getAttribute("href"));
      if (isExportDownload(href)) {{
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        w.__codexBlockedDownloads.push({{ kind: "capture.click", url: String(href), ts: Date.now() }});
      }}
    }}, true);

    w.__codexDownloadBlockerInstalled = true;
  }}

  const visibleTextExists = (text) =>
    Array.from(d.querySelectorAll("div,span,button"))
      .some((el) => (el.innerText || "").trim() === text);

  const clickHeaderMenu = async () => {{
    const candidates = Array.from(d.querySelectorAll("button"))
      .map((btn, index) => {{
        const r = btn.getBoundingClientRect();
        return {{ btn, index, text: (btn.innerText || "").trim(), x: r.x, y: r.y, w: r.width, h: r.height }};
      }})
      .filter((item) =>
        item.w > 0 &&
        item.h > 0 &&
        item.y >= 0 &&
        item.y < 120 &&
        item.x > 1100 &&
        !item.text
      );

    for (const item of candidates) {{
      item.btn.click();
      await sleep(250);
      if (visibleTextExists("下载到本地")) {{
        return true;
      }}
    }}
    return false;
  }};

  if (!visibleTextExists("下载到本地")) {{
    const opened = await clickHeaderMenu();
    if (!opened) {{
      throw new Error("Could not open DingTalk header menu.");
    }}
  }}

  const downloadItem = Array.from(d.querySelectorAll("div"))
    .find((el) =>
      (el.innerText || "").trim() === "下载到本地" &&
      String(el.className).includes("wd3-listitem")
    );
  if (!downloadItem) {{
    throw new Error("Could not find '下载到本地' menu item.");
  }}

  for (const eventType of ["mouseover", "mouseenter", "pointerenter"]) {{
    downloadItem.dispatchEvent(new MouseEvent(eventType, {{
      bubbles: true,
      cancelable: true,
      view: window
    }}));
  }}
  await sleep(500);

  const formatItem = Array.from(d.querySelectorAll("div"))
    .find((el) =>
      (el.innerText || "").trim() === {json_string(menu_text)} &&
      String(el.className).includes("wd3-listitem")
    );
  if (!formatItem) {{
    throw new Error("Could not find export option: " + {json_string(menu_text)});
  }}

  formatItem.click();
  await sleep(200);

  const headingTitle = Array.from(d.querySelectorAll("h1, h2, h3, h4"))
    .map((el) => (el.innerText || "").trim())
    .find((text) => text && !["菜单", "插入", "AI 创作"].includes(text));
  const editableTitle = Array.from(d.querySelectorAll('textarea, input, [contenteditable="true"]'))
    .map((el) => ("value" in el ? el.value : el.innerText || "").trim())
    .find((text) => text && text.length < 200);
  const title = headingTitle || editableTitle || document.title;

  return {{
    ok: true,
    title,
    url: location.href
  }};
}}
"""


def wait_for_export_response(pattern, browser_profile, timeout_ms=30000):
    cmd = [
        OPENCLAW,
        "browser",
        "--browser-profile",
        browser_profile,
        "responsebody",
        pattern,
        "--timeout-ms",
        str(timeout_ms),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc


def trigger_export(menu_text, browser_profile):
    result = run_openclaw(["evaluate", "--fn", build_trigger_js(menu_text)], browser_profile=browser_profile, timeout=30)
    return json.loads(result.stdout)


def parse_export_response(stdout):
    data = json.loads(stdout)
    if not data.get("isSuccess"):
      raise RuntimeError(f"Export job did not succeed: {data}")
    payload = data.get("data") or {}
    oss_url = payload.get("ossUrl")
    status = payload.get("status")
    if status != "success" or not oss_url:
        raise RuntimeError(f"Export job did not produce a downloadable file: {data}")
    return payload


def sanitize_title(name):
    cleaned = "".join(ch for ch in name if ch not in '/\\:*?"<>|').strip()
    return cleaned or "dingtalk-export"


def derive_filename(oss_url, fallback_title, extension):
    parsed = urllib.parse.urlparse(oss_url)
    path_name = urllib.parse.unquote(Path(parsed.path).name)
    if path_name:
        return path_name
    return sanitize_title(fallback_title) + extension


def unique_path(path):
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not allocate unique filename for {path}")


def download_file(url, destination):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp, open(destination, "wb") as out:
        out.write(resp.read())


def verify_file(path, fmt):
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"Downloaded file is missing or empty: {path}")
    if fmt == "docx" and not zipfile.is_zipfile(path):
        raise RuntimeError(f"Downloaded DOCX is not a valid zip container: {path}")


def main():
    parser = argparse.ArgumentParser(description="Export the current DingTalk document from Chrome without using the save dialog.")
    parser.add_argument("--format", choices=sorted(SUPPORTED_FORMATS.keys()), default="docx")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--browser-profile", help="OpenClaw browser profile to use. Defaults to OPENCLAW_BROWSER_PROFILE or auto-detected running relay profile.")
    args = parser.parse_args()

    output_dir = Path(os.path.expanduser(args.output_dir)).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    browser_profile = choose_browser_profile(args.browser_profile)

    format_config = SUPPORTED_FORMATS[args.format]
    tab = get_active_tab(browser_profile)

    waiter = wait_for_export_response(format_config["wait_pattern"], browser_profile=browser_profile, timeout_ms=args.timeout_ms)
    try:
        trigger_info = trigger_export(format_config["menu_text"], browser_profile)
        stdout, stderr = waiter.communicate(timeout=(args.timeout_ms / 1000) + 5)
    except Exception:
        waiter.kill()
        waiter.communicate()
        raise

    if waiter.returncode != 0:
        raise RuntimeError(stderr.strip() or stdout.strip() or "Timed out waiting for export response.")

    payload = parse_export_response(stdout)
    title = sanitize_title(trigger_info.get("title") or tab.get("title") or "dingtalk-export")
    oss_url = payload["ossUrl"]
    filename = derive_filename(oss_url, title, format_config["extension"])
    destination = unique_path(output_dir / filename)

    download_file(oss_url, destination)
    verify_file(destination, args.format)

    result = {
        "title": title,
        "format": args.format,
        "source_url": tab.get("url"),
        "saved_path": str(destination),
        "job_id": payload.get("jobId"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
