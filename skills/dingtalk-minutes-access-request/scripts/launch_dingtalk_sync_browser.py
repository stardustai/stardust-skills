#!/usr/bin/env python3
import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = SKILL_DIR / "config.json"
DEFAULT_CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_PORT = 19222
DEFAULT_PROFILE_DIR = Path.home() / "Documents" / "dingtalk-minutes-access-request" / ".chrome-profile"
DEFAULT_START_URL = "https://shanji-admin.dingtalk.com/history"


def port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def fetch_json(url: str, timeout: float = 1.5) -> dict | list:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def cdp_ready(port: int) -> bool:
    try:
        version = fetch_json(f"http://127.0.0.1:{port}/json/version")
        return bool(version.get("Browser"))
    except Exception:
        return False


def port_pids(port: int) -> list[int]:
    result = subprocess.run(
        ["lsof", "-ti", f"tcp:{port}"],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        return []
    return [int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()]


def terminate_port_processes(port: int) -> list[int]:
    pids = port_pids(port)
    for pid in pids:
        try:
            os.kill(pid, 15)
        except ProcessLookupError:
            continue
    return pids


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def launch_browser(chrome_bin: str, profile_dir: Path, port: int, start_url: str, headless: bool) -> subprocess.Popen:
    profile_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome_bin,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={str(profile_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if headless:
        cmd.extend(["--headless=new", "--disable-gpu"])
    cmd.append(start_url)
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch a dedicated Chrome profile for DingTalk AI sync over CDP.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to JSON config.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Remote debugging port.")
    parser.add_argument("--profile-dir", default="", help="Dedicated Chrome user-data-dir. Overrides config.")
    parser.add_argument("--chrome-bin", default="", help="Chrome binary path. Overrides config.")
    parser.add_argument("--start-url", default=DEFAULT_START_URL, help="URL to open after launch.")
    parser.add_argument("--timeout", type=float, default=15.0, help="How long to wait for CDP readiness.")
    parser.add_argument("--headless", action="store_true", help="Launch the dedicated browser in headless mode.")
    parser.add_argument("--restart", action="store_true", help="Restart the browser on the target port before launching.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(Path(args.config).expanduser())
    profile_dir = Path(args.profile_dir or config.get("chrome_profile_dir") or DEFAULT_PROFILE_DIR).expanduser()
    chrome_bin = str(args.chrome_bin or config.get("chrome_bin") or os.getenv("DINGTALK_MEETING_CHROME_BIN") or DEFAULT_CHROME_BIN).strip()
    port = args.port

    restarted_pids = []
    if args.restart:
        restarted_pids = terminate_port_processes(port)
        deadline = time.time() + 10.0
        while time.time() < deadline and port_open("127.0.0.1", port):
            time.sleep(0.2)

    already_running = cdp_ready(port)
    process = None
    if not already_running:
        if port_open("127.0.0.1", port) and not cdp_ready(port):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"Port {port} is already in use by a non-CDP process.",
                        "port": port,
                        "restarted_pids": restarted_pids,
                    },
                    ensure_ascii=False,
                    indent=2 if args.pretty else None,
                )
            )
            return 1
        process = launch_browser(chrome_bin, profile_dir, port, args.start_url, args.headless)

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if cdp_ready(port):
            version = fetch_json(f"http://127.0.0.1:{port}/json/version")
            output = {
                "ok": True,
                "already_running": already_running,
                "port": port,
                "profile_dir": str(profile_dir),
                "chrome_bin": chrome_bin,
                "ws_endpoint": version.get("webSocketDebuggerUrl"),
                "browser": version.get("Browser"),
                "start_url": args.start_url,
                "headless": args.headless,
                "pid": process.pid if process else None,
                "restarted_pids": restarted_pids,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))
            return 0
        time.sleep(0.25)

    print(
        json.dumps(
            {
                "ok": False,
                "error": f"Timed out waiting for Chrome CDP on port {port}.",
                "port": port,
                "profile_dir": str(profile_dir),
                "chrome_bin": chrome_bin,
                "headless": args.headless,
                "pid": process.pid if process else None,
                "restarted_pids": restarted_pids,
            },
            ensure_ascii=False,
            indent=2 if args.pretty else None,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
