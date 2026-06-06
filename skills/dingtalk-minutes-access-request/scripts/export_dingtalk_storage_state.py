#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = SKILL_DIR / "config.json"
DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:19222"
DEFAULT_OUTPUT = Path.home() / "Documents" / "dingtalk-minutes-access-request" / ".storage_state.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export DingTalk storage state from the dedicated CDP browser.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to JSON config.")
    parser.add_argument("--cdp-endpoint", default="", help="Chrome CDP HTTP endpoint. Overrides config.")
    parser.add_argument("--output", default="", help="Output path for Playwright storage_state.json. Overrides config.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(Path(args.config).expanduser())
    output_path = Path(args.output or config.get("storage_state_path") or DEFAULT_OUTPUT).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cdp_endpoint = str(args.cdp_endpoint or config.get("cdp_endpoint") or DEFAULT_CDP_ENDPOINT).strip()

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(cdp_endpoint)
        try:
            if not browser.contexts:
                raise RuntimeError(f"No browser contexts found for {cdp_endpoint}")
            context = browser.contexts[0]
            context.storage_state(path=str(output_path))
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            result = {
                "ok": True,
                "cdp_endpoint": cdp_endpoint,
                "output": str(output_path),
                "cookie_count": len(payload.get("cookies", [])),
                "origin_count": len(payload.get("origins", [])),
            }
            print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
