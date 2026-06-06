#!/usr/bin/env python3
import argparse
import importlib.util
import json
import os
import socket
from pathlib import Path
import shutil


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = SKILL_DIR / "config.json"
DEFAULT_STORAGE_STATE_PATH = Path.home() / "Documents" / "dingtalk-minutes-access-request" / ".storage_state.json"
DEFAULT_CHROME_PROFILE_DIR = Path.home() / "Documents" / "dingtalk-minutes-access-request" / ".chrome-profile"
DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:19222"
DEFAULT_CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def check_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local prerequisites for dingtalk-minutes-access-request.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to JSON config.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser()
    config = load_json(config_path)

    storage_state_path = Path(config.get("storage_state_path") or DEFAULT_STORAGE_STATE_PATH).expanduser()
    chrome_profile_dir = Path(config.get("chrome_profile_dir") or DEFAULT_CHROME_PROFILE_DIR).expanduser()
    cdp_endpoint = str(config.get("cdp_endpoint") or DEFAULT_CDP_ENDPOINT).strip()
    chrome_bin = str(config.get("chrome_bin") or os.getenv("DINGTALK_MEETING_CHROME_BIN") or DEFAULT_CHROME_BIN).strip()

    try:
        port = int(cdp_endpoint.rsplit(":", 1)[1])
    except Exception:
        port = 19222

    checks = {
        "python": {
            "ok": True,
            "required": True,
            "executable": shutil.which("python3") or shutil.which("python") or "",
        },
        "playwright": {
            "ok": importlib.util.find_spec("playwright") is not None,
            "required": True,
        },
        "chrome_bin": {
            "ok": Path(chrome_bin).exists(),
            "required": True,
            "path": chrome_bin,
        },
        "lsof": {
            "ok": shutil.which("lsof") is not None,
            "required": True,
            "path": shutil.which("lsof") or "",
        },
        "storage_state": {
            "ok": storage_state_path.exists(),
            "required": False,
            "path": str(storage_state_path),
        },
        "chrome_profile_dir": {
            "ok": chrome_profile_dir.exists(),
            "required": False,
            "path": str(chrome_profile_dir),
        },
        "cdp_port": {
            "ok": check_port_open("127.0.0.1", port),
            "required": False,
            "endpoint": cdp_endpoint,
        },
    }

    result = {
        "ok": True,
        "config_path": str(config_path),
        "checks": checks,
    }

    result["ok"] = all(item.get("ok", False) for item in checks.values() if item.get("required"))
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
