#!/usr/bin/env python3
"""Retry existing Codex sessions whose latest completion is a capacity error."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


CAPACITY_RE = re.compile(
    r"selected model is at capacity|model at capacity|server_overloaded|"
    r"too many requests|(?<![0-9])429(?![0-9])",
    re.IGNORECASE,
)
DESKTOP_WRITER_RE = re.compile(
    r"thread-store conflict|already has an active writer",
    re.IGNORECASE,
)
TAIL_BYTES = 1_048_576


@dataclass(frozen=True)
class CapacityFailure:
    session_id: str
    path: Path
    signature: str
    message: str


def parse_args() -> argparse.Namespace:
    home = Path.home()
    parser = argparse.ArgumentParser(
        description="Scan existing Codex session files and resume capacity-failed sessions."
    )
    parser.add_argument(
        "--session-root",
        type=Path,
        default=Path(os.environ.get("CODEX_SESSION_ROOT", home / ".codex/sessions")),
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path(
            os.environ.get(
                "CODEX_CAPACITY_RETRY_STATE",
                home / ".codex/codex-capacity-retry-state.json",
            )
        ),
    )
    parser.add_argument("--codex-bin", default=os.environ.get("CODEX_BIN", "codex"))
    parser.add_argument(
        "--queue-bin",
        default=os.environ.get("CODEX_QUEUE_BIN", os.environ.get("CODEX_BIN", "codex")),
        help="Codex executable used for same-thread Desktop queue fallback",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=float(os.environ.get("CODEX_RETRY_DELAY_SECONDS", "5")),
    )
    parser.add_argument(
        "--scan-interval-seconds",
        type=float,
        default=float(os.environ.get("CODEX_RETRY_SCAN_INTERVAL_SECONDS", "5")),
    )
    parser.add_argument(
        "--max-age-seconds",
        type=float,
        default=float(os.environ.get("CODEX_RETRY_MAX_AGE_SECONDS", "21600")),
        help="Ignore session files not modified within this window; 0 means no age limit",
    )
    parser.add_argument(
        "--resume-prompt",
        default="Please retry the interrupted turn exactly as-is.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Detach from the invoking terminal and keep the watcher alive",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path(
            os.environ.get("CODEX_RETRY_LOG_FILE", home / ".codex/codex-capacity-retry.log")
        ),
    )
    parser.add_argument(
        "--pid-file",
        type=Path,
        default=Path(
            os.environ.get("CODEX_RETRY_PID_FILE", home / ".codex/codex-capacity-retry.pid")
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--watch", action="store_true", help="Keep scanning until interrupted")
    mode.add_argument("--once", action="store_true", help="Scan and retry once, then exit")
    return parser.parse_args()


def read_json_lines(path: Path) -> list[dict]:
    try:
        with path.open("rb") as stream:
            size = path.stat().st_size
            stream.seek(max(0, size - TAIL_BYTES))
            data = stream.read().decode("utf-8", errors="replace")
    except (OSError, ValueError):
        return []

    records: list[dict] = []
    for line in data.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def read_session_id(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8") as stream:
            record = json.loads(stream.readline())
    except (OSError, json.JSONDecodeError):
        return None

    payload = record.get("payload", {})
    if not isinstance(payload, dict):
        return None
    for key in ("id", "session_id", "thread_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def latest_capacity_failure(path: Path) -> CapacityFailure | None:
    session_id = read_session_id(path)
    if not session_id:
        return None

    latest_completion: dict | None = None
    for record in read_json_lines(path):
        if record.get("type") != "event_msg":
            continue
        payload = record.get("payload", {})
        if isinstance(payload, dict) and payload.get("type") == "task_complete":
            latest_completion = record

    if latest_completion is None:
        return None

    payload = latest_completion.get("payload", {})
    if not isinstance(payload, dict):
        return None
    error = payload.get("error", {})
    if not isinstance(error, dict):
        error = {}
    message_parts = [
        str(payload.get("message", "")),
        str(payload.get("codex_error_info", "")),
        str(payload.get("last_agent_message", "")),
        str(error.get("message", "")),
        str(error.get("codex_error_info", "")),
    ]
    message = " ".join(part for part in message_parts if part)
    if not CAPACITY_RE.search(message):
        return None

    signature = "|".join(
        [
            str(latest_completion.get("timestamp", "")),
            str(latest_completion.get("ordinal", "")),
            str(payload.get("message", "")),
            str(payload.get("codex_error_info", "")),
            str(error.get("message", "")),
            str(error.get("codex_error_info", "")),
        ]
    )
    return CapacityFailure(session_id, path, signature, message)


def load_state(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"sessions": {}}
    if not isinstance(value, dict) or not isinstance(value.get("sessions"), dict):
        return {"sessions": {}}
    return value


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def candidate_failures(root: Path, max_age_seconds: float) -> list[CapacityFailure]:
    if not root.is_dir():
        return []
    cutoff = time.time() - max_age_seconds if max_age_seconds > 0 else 0
    candidates: list[CapacityFailure] = []
    for path in root.rglob("rollout-*.jsonl"):
        try:
            if cutoff and path.stat().st_mtime < cutoff:
                continue
        except OSError:
            continue
        failure = latest_capacity_failure(path)
        if failure:
            candidates.append(failure)
    return sorted(candidates, key=lambda item: item.path.stat().st_mtime)


def run_command(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    output = f"{result.stdout}\n{result.stderr}"
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode, output


def resume_session(
    codex_bin: str,
    queue_bin: str,
    failure: CapacityFailure,
    resume_prompt: str,
) -> int:
    status, output = run_command(
        [
            codex_bin,
            "exec",
            "resume",
            "--json",
            "--skip-git-repo-check",
            failure.session_id,
            resume_prompt,
        ]
    )
    if status == 0:
        return 0
    if not DESKTOP_WRITER_RE.search(output):
        return status

    print(
        f"Session {failure.session_id} is Desktop-owned; queueing the same prompt to that thread.",
        flush=True,
    )
    queue_status, _ = run_command(
        [queue_bin, "queue", "--thread", failure.session_id, "--message", resume_prompt]
    )
    return queue_status


def scan_once(args: argparse.Namespace, state: dict) -> int:
    retry_count = 0
    for failure in candidate_failures(args.session_root, args.max_age_seconds):
        if state["sessions"].get(failure.session_id) == failure.signature:
            continue

        retry_count += 1
        print(
            f"Found capacity failure in existing session {failure.session_id}; "
            f"retrying after {args.retry_delay_seconds:g}s.",
            flush=True,
        )
        time.sleep(args.retry_delay_seconds)
        status = resume_session(args.codex_bin, args.queue_bin, failure, args.resume_prompt)
        if status == 0:
            state["sessions"][failure.session_id] = failure.signature
        else:
            # Leave the signature unrecorded so the next watch cycle retries it again.
            state["sessions"].pop(failure.session_id, None)
        save_state(args.state_file, state)
        print(
            f"Retried existing session {failure.session_id} with exit code {status}.",
            flush=True,
        )
    return retry_count


def detach_from_terminal(log_file: Path, pid_file: Path) -> bool:
    """Detach the watcher and redirect its standard streams to a log file.

    The first process returns to the invoking shell. The grandchild owns the
    lock and continues independently of the terminal or PTY that launched it.
    """
    try:
        if os.fork() > 0:
            return False
        os.setsid()
        if os.fork() > 0:
            os._exit(0)
    except OSError as error:
        print(f"could not detach watcher: {error}", file=sys.stderr)
        raise

    os.umask(0o027)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")

    with log_file.open("a", encoding="utf-8", buffering=1) as log_stream:
        with open(os.devnull, "r", encoding="utf-8") as devnull:
            os.dup2(devnull.fileno(), sys.stdin.fileno())
        os.dup2(log_stream.fileno(), sys.stdout.fileno())
        os.dup2(log_stream.fileno(), sys.stderr.fileno())
    print(f"daemon started pid={os.getpid()}", flush=True)
    return True


def remove_pid_file(pid_file: Path, pid: int) -> None:
    try:
        if pid_file.read_text(encoding="utf-8").strip() == str(pid):
            pid_file.unlink()
    except (FileNotFoundError, OSError):
        pass


def main() -> int:
    args = parse_args()
    if args.retry_delay_seconds < 0 or args.scan_interval_seconds < 0 or args.max_age_seconds < 0:
        print("retry delay, scan interval, and max age must be non-negative", file=sys.stderr)
        return 64

    for path_name in ("session_root", "state_file", "log_file", "pid_file"):
        path = getattr(args, path_name)
        setattr(args, path_name, path.expanduser().resolve())

    daemon_pid: int | None = None
    if args.daemon:
        if not detach_from_terminal(args.log_file, args.pid_file):
            return 0
        daemon_pid = os.getpid()

    try:
        lock_path = args.state_file.with_name(f".{args.state_file.name}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("w", encoding="utf-8") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print("another session scanner is already running", file=sys.stderr)
                return 0

            state = load_state(args.state_file)
            while True:
                scan_once(args, state)
                if args.once:
                    return 0
                time.sleep(args.scan_interval_seconds)
    finally:
        if daemon_pid is not None:
            remove_pid_file(args.pid_file, daemon_pid)


if __name__ == "__main__":
    raise SystemExit(main())
