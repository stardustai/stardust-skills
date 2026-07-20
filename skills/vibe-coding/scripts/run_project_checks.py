#!/usr/bin/env python3
"""Run bounded project checks and save reproducible, secret-safe evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO


BUILTIN_TIMEOUT_SECONDS = 300.0
TIMEOUT_EXIT_CODE = 124
START_FAILURE_EXIT_CODE = 127


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_project(root: Path) -> dict[str, Any]:
    path = root / "PROJECT.yaml"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"PROJECT.yaml does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"PROJECT.yaml must be JSON-compatible YAML: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("PROJECT.yaml must contain an object")
    return value


def command_for(project: dict[str, Any], name: str) -> list[str]:
    commands = project.get("commands")
    if not isinstance(commands, dict):
        raise ValueError("PROJECT.yaml commands must be an object")
    command = commands.get(name)
    if not isinstance(command, list) or not command or any(not isinstance(arg, str) or not arg for arg in command):
        raise ValueError(f"commands.{name} must be a non-empty argument array")
    return command


def verification_inventory(project: dict[str, Any]) -> list[str]:
    verification = project.get("verification")
    inventory = verification.get("check_inventory") if isinstance(verification, dict) else None
    if not isinstance(inventory, list) or not inventory or any(not isinstance(name, str) or not name for name in inventory):
        raise ValueError("verification.check_inventory must be a non-empty array of command names")
    for name in inventory:
        command_for(project, name)
    return inventory


def positive_seconds(value: Any, location: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{location} must be a positive number")
    seconds = float(value)
    if seconds <= 0 or not math.isfinite(seconds):
        raise ValueError(f"{location} must be a positive finite number")
    return seconds


def project_timeouts(project: dict[str, Any]) -> dict[str, float]:
    configured = project.get("command_timeouts_seconds", {})
    if not isinstance(configured, dict):
        raise ValueError("command_timeouts_seconds must be an object")
    return {str(name): positive_seconds(value, f"command_timeouts_seconds.{name}") for name, value in configured.items()}


def parse_timeout_overrides(values: list[str], names: list[str]) -> dict[str, float]:
    overrides: dict[str, float] = {}
    for value in values:
        name, separator, raw_seconds = value.partition("=")
        if not separator or not name or not raw_seconds:
            raise ValueError("--timeout must use CHECK=SECONDS")
        if name not in names:
            raise ValueError(f"timeout override {name!r} is not one of the requested checks")
        try:
            numeric = float(raw_seconds)
        except ValueError as exc:
            raise ValueError(f"timeout override for {name} must be numeric") from exc
        overrides[name] = positive_seconds(numeric, f"timeout override for {name}")
    return overrides


def timeout_for(
    name: str,
    configured: dict[str, float],
    overrides: dict[str, float],
    cli_default: float | None,
) -> float:
    if name in overrides:
        return overrides[name]
    if name in configured:
        return configured[name]
    if cli_default is not None:
        return cli_default
    if "default" in configured:
        return configured["default"]
    return BUILTIN_TIMEOUT_SECONDS


def confined_evidence_path(root: Path, evidence_path: Path) -> Path:
    candidate = evidence_path if evidence_path.is_absolute() else root / evidence_path
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("evidence path must resolve inside the project root")
    if resolved == root:
        raise ValueError("evidence path must be a file inside the project root")
    return resolved


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def consume_output(stream: BinaryIO, evidence: dict[str, Any]) -> None:
    digest = hashlib.sha256()
    byte_count = 0
    try:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            byte_count += len(chunk)
    finally:
        stream.close()
    evidence.update(
        byte_count=byte_count,
        sha256=digest.hexdigest(),
        summary="[redacted: non-empty output]" if byte_count else "[no output]",
    )


def git_text(root: Path, arguments: list[str]) -> str | None:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def git_clean(root: Path) -> bool | None:
    process = subprocess.Popen(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdout is not None
    first_byte = process.stdout.read(1)
    process.stdout.close()
    if process.poll() is None:
        process.terminate()
    return_code = process.wait()
    if not first_byte and return_code != 0:
        return None
    return not first_byte


def git_context(root: Path) -> dict[str, Any]:
    return {
        "commit": git_text(root, ["rev-parse", "HEAD"]),
        "branch": git_text(root, ["symbolic-ref", "--quiet", "--short", "HEAD"]),
        "clean": git_clean(root),
    }


def stop_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=0.1)
    except subprocess.TimeoutExpired:
        pass
    time.sleep(0.1)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        process.wait()
        return
    process.wait()


def execute_check(root: Path, name: str, command: list[str], timeout_seconds: float) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": name,
        "command": command,
        "timeout_seconds": timeout_seconds,
        "started_at": timestamp(),
        "finished_at": None,
        "status": None,
        "exit_code": None,
    }
    stdout_evidence: dict[str, Any] = {}
    stderr_evidence: dict[str, Any] = {}
    deadline = time.monotonic() + timeout_seconds
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        record.update(
            status="start_failed",
            exit_code=START_FAILURE_EXIT_CODE,
            error_type=type(exc).__name__,
        )
        empty_digest = hashlib.sha256(b"").hexdigest()
        stdout_evidence.update(byte_count=0, sha256=empty_digest, summary="[no output]")
        stderr_evidence.update(byte_count=0, sha256=empty_digest, summary="[no output]")
    else:
        assert process.stdout is not None and process.stderr is not None
        readers = (
            threading.Thread(target=consume_output, args=(process.stdout, stdout_evidence), daemon=True),
            threading.Thread(target=consume_output, args=(process.stderr, stderr_evidence), daemon=True),
        )
        for reader in readers:
            reader.start()
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            stop_process_group(process)
            record.update(status="timed_out", exit_code=TIMEOUT_EXIT_CODE)
        else:
            for reader in readers:
                reader.join(timeout=max(0, deadline - time.monotonic()))
            if any(reader.is_alive() for reader in readers):
                stop_process_group(process)
                record.update(status="timed_out", exit_code=TIMEOUT_EXIT_CODE)
            else:
                record["exit_code"] = process.returncode
                record["status"] = "passed" if process.returncode == 0 else "failed"
        for reader in readers:
            reader.join(timeout=1)
        if any(reader.is_alive() for reader in readers):
            raise RuntimeError("command output streams did not close after process-group termination")
    record["stdout"] = stdout_evidence
    record["stderr"] = stderr_evidence
    record["finished_at"] = timestamp()
    return record


def run_checks(
    root: Path,
    names: list[str],
    evidence_path: Path,
    phase: str,
    *,
    cli_default_timeout: float | None = None,
    timeout_overrides: dict[str, float] | None = None,
) -> int:
    root = root.resolve()
    evidence_path = confined_evidence_path(root, evidence_path)
    project = load_project(root)
    configured_timeouts = project_timeouts(project)
    overrides = timeout_overrides or {}
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": str(uuid.uuid4()),
        "phase": phase,
        "project_root": str(root),
        "git": git_context(root),
        "started_at": timestamp(),
        "finished_at": None,
        "checks": [],
    }
    exit_code = 0
    try:
        for name in names:
            command = command_for(project, name)
            record = execute_check(
                root,
                name,
                command,
                timeout_for(name, configured_timeouts, overrides, cli_default_timeout),
            )
            manifest["checks"].append(record)
            if record["exit_code"] != 0:
                exit_code = int(record["exit_code"] or 1)
                break
    finally:
        manifest["finished_at"] = timestamp()
        write_manifest(evidence_path, manifest)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--checks", nargs="+", help="checks to run; defaults to verification.check_inventory")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--phase", choices=("pre_commit", "full"))
    parser.add_argument("--default-timeout", type=float)
    parser.add_argument("--timeout", action="append", default=[], metavar="CHECK=SECONDS")
    args = parser.parse_args()
    try:
        names = args.checks or verification_inventory(load_project(args.project_root.resolve()))
        phase = args.phase or ("full" if "eval_full" in names else "pre_commit")
        cli_default = None if args.default_timeout is None else positive_seconds(args.default_timeout, "--default-timeout")
        overrides = parse_timeout_overrides(args.timeout, names)
        result = run_checks(
            args.project_root,
            names,
            args.evidence,
            phase,
            cli_default_timeout=cli_default,
            timeout_overrides=overrides,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if result:
        print(f"ERROR: project check failed; evidence written to {args.evidence}", file=sys.stderr)
    else:
        print(f"PASS: project checks completed; evidence written to {args.evidence}")
    return result if 0 <= result <= 125 else 1


if __name__ == "__main__":
    raise SystemExit(main())
