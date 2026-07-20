#!/usr/bin/env python3
"""Install a portable, repository-local Vibe Coding pre-commit runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


HOOK_VERSION = "2.0"
HOOK_PATH = Path(".githooks/pre-commit")
RUNNER_PATH = Path("scripts/vibe-coding/run_project_checks.py")


def load_project(root: Path) -> dict:
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


def run_git(root: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def verify_git_root(root: Path) -> None:
    result = run_git(root, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        raise ValueError(f"project root is not a git repository: {root}")
    if Path(result.stdout.strip()).resolve() != root:
        raise ValueError(f"project root must be the git worktree root: {root}")


def hook_content() -> str:
    return (
        "#!/bin/sh\n"
        f"# vibe-coding-pre-commit version {HOOK_VERSION}\n"
        "set -eu\n"
        "repo_root=$(git rev-parse --show-toplevel)\n"
        "python_command=${PYTHON:-}\n"
        "if [ -z \"$python_command\" ]; then\n"
        "  python_command=$(command -v python3)\n"
        "fi\n"
        "exec \"$python_command\" \"$repo_root/scripts/vibe-coding/run_project_checks.py\" \\\n"
        "  --project-root \"$repo_root\" \\\n"
        "  --checks pre_commit_full \\\n"
        "  --phase pre_commit \\\n"
        "  --evidence \"$repo_root/docs/evidence/pre-commit-latest.json\"\n"
    )


def ensure_writable_target(path: Path, expected: bytes, label: str) -> None:
    if path.exists() and path.read_bytes() != expected:
        raise ValueError(f"refusing to overwrite conflicting existing {label}: {path}")


def configure_worktree_hook_path(root: Path) -> None:
    current = run_git(root, ["config", "--get", "core.hooksPath"])
    if current.returncode == 0 and current.stdout.strip() not in ("", ".githooks"):
        raise ValueError(f"refusing to replace existing core.hooksPath: {current.stdout.strip()}")
    extension = run_git(root, ["config", "extensions.worktreeConfig", "true"])
    if extension.returncode != 0:
        raise ValueError(f"failed to enable worktree-local git config: {extension.stderr.strip()}")
    configured = run_git(root, ["config", "--worktree", "core.hooksPath", ".githooks"])
    if configured.returncode != 0:
        raise ValueError(f"failed to configure worktree-local core.hooksPath: {configured.stderr.strip()}")


def install(root: Path) -> Path:
    root = root.resolve()
    project = load_project(root)
    pre_commit = project.get("pre_commit") if isinstance(project.get("pre_commit"), dict) else {}
    if pre_commit.get("full_suite") is not True:
        raise ValueError("pre_commit.full_suite must be true before installing the hook")
    if pre_commit.get("hook_path") != str(HOOK_PATH):
        raise ValueError("pre_commit.hook_path must be .githooks/pre-commit")
    command = project.get("commands", {}).get("pre_commit_full") if isinstance(project.get("commands"), dict) else None
    if not isinstance(command, list) or not command or any(not isinstance(arg, str) or not arg for arg in command):
        raise ValueError("commands.pre_commit_full must be a non-empty argument array")
    verify_git_root(root)

    source_runner = Path(__file__).resolve().with_name("run_project_checks.py")
    runner_bytes = source_runner.read_bytes()
    generated_hook = hook_content().encode()
    runner = root / RUNNER_PATH
    hook = root / HOOK_PATH
    ensure_writable_target(hook, generated_hook, "pre-commit hook")
    ensure_writable_target(runner, runner_bytes, "project runner")

    configure_worktree_hook_path(root)
    runner.parent.mkdir(parents=True, exist_ok=True)
    hook.parent.mkdir(parents=True, exist_ok=True)
    if not runner.exists():
        runner.write_bytes(runner_bytes)
    if not hook.exists():
        hook.write_bytes(generated_hook)
    runner.chmod(0o755)
    hook.chmod(0o755)
    return hook


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        path = install(args.project_root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"INSTALLED: version {HOOK_VERSION} pre-commit hook at {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
