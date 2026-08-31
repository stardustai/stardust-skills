#!/usr/bin/env python3
"""Collect read-only rescue signals from a software project."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "__pycache__",
    "coverage",
    ".cache",
    ".turbo",
    ".idea",
    ".vscode",
}

TEXT_SUFFIXES = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".py",
    ".go",
    ".java",
    ".kt",
    ".rs",
    ".rb",
    ".php",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".env",
    ".md",
    ".txt",
}

ENV_REFERENCE_PATTERNS = [
    re.compile(r"\bprocess\.env\.([A-Z_][A-Z0-9_]*)\b"),
    re.compile(r"\bimport\.meta\.env\.([A-Z_][A-Z0-9_]*)\b"),
    re.compile(r"\bos\.environ\[['\"]([A-Z_][A-Z0-9_]*)['\"]\]"),
    re.compile(r"\bos\.getenv\(['\"]([A-Z_][A-Z0-9_]*)['\"]"),
    re.compile(r"\bgetenv\(['\"]([A-Z_][A-Z0-9_]*)['\"]"),
]

SENSITIVE_ENV_RE = re.compile(r"(SECRET|TOKEN|PASSWORD|PASS|KEY|PRIVATE|CREDENTIAL|DATABASE_URL)", re.IGNORECASE)
COMMON_ENV = {"NODE_ENV", "PATH", "HOME", "PWD", "SHELL", "CI"}
COMMAND_START_RE = re.compile(
    r"^(?:\$?\s*)("
    r"npm|pnpm|yarn|bun|npx|node|python|python3|pip|pip3|poetry|uv|pytest|"
    r"go|cargo|mvn|gradle|make|docker|docker-compose|kubectl"
    r")\b(.+)?$"
)


def read_text(path: Path, max_bytes: int = 400_000) -> str:
    try:
        if path.stat().st_size > max_bytes:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in IGNORE_DIRS and not name.startswith(".egg")]
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                if path.is_file():
                    yield path
            except OSError:
                continue


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def git_info(root: Path) -> dict[str, Any]:
    def run_git(args: list[str]) -> tuple[int, str]:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return 1, ""
        return result.returncode, result.stdout.strip()

    inside_code, inside = run_git(["rev-parse", "--is-inside-work-tree"])
    if inside_code != 0 or inside != "true":
        return {"inside_work_tree": False}

    _, branch = run_git(["branch", "--show-current"])
    _, status = run_git(["status", "--short", "--branch"])
    _, remote = run_git(["remote", "-v"])
    return {
        "inside_work_tree": True,
        "branch": branch,
        "has_uncommitted_changes": bool("\n".join(status.splitlines()[1:]).strip()),
        "status_short": status.splitlines(),
        "remotes": sorted(set(line for line in remote.splitlines() if line.strip())),
    }


def package_json_files(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    packages: list[tuple[Path, dict[str, Any]]] = []
    for path in iter_files(root):
        if path.name == "package.json":
            packages.append((path, load_json(path)))
    return sorted(packages, key=lambda item: rel(item[0], root))


def detect_package_managers(root: Path, packages: list[tuple[Path, dict[str, Any]]]) -> list[str]:
    managers: set[str] = set()
    if (root / "pnpm-lock.yaml").exists():
        managers.add("pnpm")
    if (root / "package-lock.json").exists():
        managers.add("npm")
    if (root / "yarn.lock").exists():
        managers.add("yarn")
    if (root / "bun.lockb").exists() or (root / "bun.lock").exists():
        managers.add("bun")
    if (root / "poetry.lock").exists():
        managers.add("poetry")
    if (root / "uv.lock").exists():
        managers.add("uv")
    if (root / "requirements.txt").exists():
        managers.add("pip")

    for _, package in packages:
        package_manager = package.get("packageManager")
        if isinstance(package_manager, str):
            managers.add(package_manager.split("@", 1)[0])

    return ordered(managers, ["pnpm", "npm", "yarn", "bun", "poetry", "uv", "pip"])


def dependencies(packages: list[tuple[Path, dict[str, Any]]]) -> set[str]:
    deps: set[str] = set()
    for _, package in packages:
        for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            value = package.get(key)
            if isinstance(value, dict):
                deps.update(value)
    return deps


def ordered(values: Iterable[str], preferred: list[str]) -> list[str]:
    value_set = set(values)
    result = [value for value in preferred if value in value_set]
    result.extend(sorted(value_set.difference(result)))
    return result


def detect_frameworks(root: Path, deps: set[str], files: list[Path]) -> dict[str, list[str]]:
    deployment: set[str] = set()
    names = {rel(path, root).lower() for path in files}
    if any(name.endswith("dockerfile") or "dockerfile" in name or "docker-compose" in name for name in names):
        deployment.add("Docker")
    if any("k8s/" in name or "kubernetes/" in name or "helm/" in name for name in names):
        deployment.add("Kubernetes")
    if any(name.startswith(".github/workflows/") for name in names):
        deployment.add("GitHub Actions")
    if ".gitlab-ci.yml" in names:
        deployment.add("GitLab CI")

    return {
        "frontend": ordered(
            {
                label
                for dep, label in {
                    "react": "React",
                    "vite": "Vite",
                    "next": "Next.js",
                    "vue": "Vue",
                    "@angular/core": "Angular",
                    "svelte": "Svelte",
                }.items()
                if dep in deps
            },
            ["React", "Vite", "Next.js", "Vue", "Angular", "Svelte"],
        ),
        "backend": ordered(
            {
                label
                for dep, label in {
                    "@nestjs/core": "NestJS",
                    "express": "Express",
                    "fastapi": "FastAPI",
                    "django": "Django",
                    "flask": "Flask",
                }.items()
                if dep in deps
            },
            ["NestJS", "Express", "FastAPI", "Django", "Flask"],
        ),
        "test": ordered(
            {
                label
                for dep, label in {
                    "vitest": "Vitest",
                    "jest": "Jest",
                    "@playwright/test": "Playwright",
                    "cypress": "Cypress",
                    "pytest": "Pytest",
                }.items()
                if dep in deps
            },
            ["Vitest", "Jest", "Playwright", "Cypress", "Pytest"],
        ),
        "database": ordered(
            {
                label
                for dep, label in {
                    "prisma": "Prisma",
                    "@prisma/client": "Prisma",
                    "drizzle-orm": "Drizzle",
                    "typeorm": "TypeORM",
                    "sequelize": "Sequelize",
                    "pg": "PostgreSQL Client",
                }.items()
                if dep in deps
            },
            ["Prisma", "Drizzle", "TypeORM", "Sequelize", "PostgreSQL Client"],
        ),
        "deployment": ordered(deployment, ["Docker", "Kubernetes", "GitHub Actions", "GitLab CI"]),
    }


def lockfiles(root: Path) -> list[str]:
    names = ["pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lock", "bun.lockb", "poetry.lock", "uv.lock"]
    return [name for name in names if (root / name).exists()]


def readme_commands(root: Path) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for path in sorted(root.glob("README*.md")):
        text = read_text(path)
        in_fence = False
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence:
                continue
            cleaned = stripped.removeprefix("$").strip()
            if COMMAND_START_RE.match(cleaned):
                commands.append({"path": rel(path, root), "line": lineno, "command": cleaned})
    return commands[:200]


def parse_env_example(path: Path) -> set[str]:
    names: set[str] = set()
    for line in read_text(path, max_bytes=100_000).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name = stripped.split("=", 1)[0].strip()
        if re.fullmatch(r"[A-Z_][A-Z0-9_]*", name):
            names.add(name)
    return names


def env_inventory(root: Path, files: list[Path]) -> dict[str, Any]:
    example_files: list[str] = []
    actual_env_files: list[str] = []
    example_vars: set[str] = set()
    referenced: dict[tuple[str, str], dict[str, Any]] = {}

    for path in files:
        relative = rel(path, root)
        name = path.name
        lower = name.lower()
        if lower in {".env", ".env.local", ".env.production", ".env.development", ".env.test"}:
            actual_env_files.append(relative)
            continue
        if lower.endswith((".env.example", ".env.sample")) or lower in {".env.example", "env.example"}:
            example_files.append(relative)
            example_vars.update(parse_env_example(path))
            continue

        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = read_text(path)
        if not text:
            continue
        for pattern in ENV_REFERENCE_PATTERNS:
            for match in pattern.finditer(text):
                name = match.group(1)
                key = (name, relative)
                if key not in referenced:
                    line = text.count("\n", 0, match.start()) + 1
                    referenced[key] = {"name": name, "path": relative, "line": line}

    referenced_values = sorted(referenced.values(), key=lambda item: (item["name"], item["path"], item["line"]))
    sensitive_names = sorted({item["name"] for item in referenced_values if SENSITIVE_ENV_RE.search(item["name"])})
    missing_examples = sorted(
        {
            item["name"]
            for item in referenced_values
            if item["name"] not in example_vars and item["name"] not in COMMON_ENV
        }
    )
    return {
        "example_files": sorted(example_files),
        "actual_env_files": sorted(actual_env_files),
        "example_variables": sorted(example_vars),
        "referenced_variables": referenced_values,
        "referenced_without_example": missing_examples,
        "sensitive_names_referenced": sensitive_names,
    }


def package_scripts(root: Path, packages: list[tuple[Path, dict[str, Any]]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path, package in packages:
        scripts = package.get("scripts")
        if isinstance(scripts, dict):
            clean_scripts = {str(key): str(value) for key, value in sorted(scripts.items())}
        else:
            clean_scripts = {}
        result.append({"path": rel(path, root), "scripts": clean_scripts})
    return result


def risk_signals(
    root: Path,
    packages: list[tuple[Path, dict[str, Any]]],
    managers: list[str],
    locks: list[str],
    env: dict[str, Any],
    commands: list[dict[str, Any]],
) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    if not list(root.glob("README*.md")):
        signals.append({"code": "missing-readme", "message": "No README file found at project root."})
    if packages and not locks:
        signals.append({"code": "missing-lockfile", "message": "package.json exists but no common JS lockfile is present."})
    if len(managers) > 1:
        signals.append({"code": "multiple-package-managers", "message": f"Multiple package managers detected: {', '.join(managers)}."})
    if not any(item["scripts"].get("test") for item in package_scripts(root, packages)):
        signals.append({"code": "missing-test-script", "message": "No package.json test script detected."})
    if packages and not any(item["scripts"].get("build") for item in package_scripts(root, packages)):
        signals.append({"code": "missing-build-script", "message": "No package.json build script detected."})
    if env["actual_env_files"]:
        signals.append({"code": "actual-env-file-present", "message": "Actual .env-style files are present; do not copy values into reports."})
    if env["referenced_without_example"]:
        signals.append(
            {
                "code": "env-referenced-without-example",
                "message": "Env vars referenced in code but absent from env examples: "
                + ", ".join(env["referenced_without_example"]),
            }
        )
    if env["sensitive_names_referenced"]:
        signals.append(
            {
                "code": "sensitive-env-name-referenced",
                "message": "Sensitive-looking env names are referenced; report names only, never values.",
            }
        )
    if commands and packages:
        script_names = set()
        for item in package_scripts(root, packages):
            script_names.update(item["scripts"].keys())
        missing_script_commands = []
        for command in commands:
            words = command["command"].split()
            if len(words) >= 3 and words[0] in {"npm", "pnpm", "yarn", "bun"} and words[1] == "run":
                if words[2] not in script_names:
                    missing_script_commands.append(command["command"])
            elif len(words) >= 2 and words[0] in {"pnpm", "yarn", "bun"}:
                subcommand = words[1]
                if subcommand not in {"install", "add", "remove", "dlx", "exec"} and subcommand not in script_names:
                    missing_script_commands.append(command["command"])
        if missing_script_commands:
            signals.append(
                {
                    "code": "readme-command-missing-script",
                    "message": "README references package commands without matching scripts: "
                    + ", ".join(sorted(set(missing_script_commands))),
                }
            )
    return signals


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect read-only rescue context from a project")
    parser.add_argument("root", help="Project root")
    parser.add_argument("--output", "-o", help="Write JSON output to this path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Project root does not exist or is not a directory: {root}")

    files = sorted(iter_files(root), key=lambda path: rel(path, root))
    packages = package_json_files(root)
    deps = dependencies(packages)
    managers = detect_package_managers(root, packages)
    locks = lockfiles(root)
    env = env_inventory(root, files)
    commands = readme_commands(root)
    ext_counts = Counter(path.suffix.lower() or "<none>" for path in files)

    result: dict[str, Any] = {
        "root": root.as_posix(),
        "file_count": len(files),
        "extensions": dict(sorted(ext_counts.items())),
        "git": git_info(root),
        "manifests": [rel(path, root) for path, _ in packages],
        "lockfiles": locks,
        "package_managers": managers,
        "package_scripts": package_scripts(root, packages),
        "frameworks": detect_frameworks(root, deps, files),
        "readme_commands": commands,
        "env": env,
        "risk_signals": risk_signals(root, packages, managers, locks, env, commands),
    }

    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
