#!/usr/bin/env python3
"""Collect AI PR red-team signals from a repository.

The scanner is intentionally heuristic. It finds review leads; it does not
replace reading the changed code and proving whether each lead is on a
production path.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


IGNORE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

LANGUAGE_EXTENSIONS = {
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".py": "Python",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
}

SOURCE_EXTENSIONS = set(LANGUAGE_EXTENSIONS) | {
    ".json",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".env",
    ".example",
}

TEST_PATH_RE = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|(\.|_)(test|spec)\.")
FAKE_WORD_RE = re.compile(
    r"\b(mock|fake|dummy|sample|stub|placeholder|hardcoded|demo|fallback|temporary|todo|fixme)\b",
    re.IGNORECASE,
)
JS_ENV_RE = re.compile(r"process\.env(?:\.([A-Z][A-Z0-9_]*)|\[['\"]([A-Z][A-Z0-9_]*)['\"]\])")
PY_ENV_RE = re.compile(r"os\.environ(?:\.get)?\(['\"]([A-Z][A-Z0-9_]*)['\"]")


@dataclass
class Signal:
    category: str
    severity: str
    file: str
    line: int
    language: str
    message: str
    evidence: str
    recommendation: str
    owner_role: str
    acceptance_criteria: str


def run_git(root: Path, args: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def is_ignored(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def is_probably_text(path: Path) -> bool:
    return path.suffix in SOURCE_EXTENSIONS or path.name in {
        ".env.example",
        "Dockerfile",
        "Makefile",
        "README.md",
        "package.json",
        "pyproject.toml",
        "go.mod",
        "pom.xml",
    }


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or is_ignored(path.relative_to(root)):
            continue
        if is_probably_text(path):
            files.append(path)
    return sorted(files)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def language_for(path: Path) -> str:
    return LANGUAGE_EXTENSIONS.get(path.suffix, "Unknown")


def is_test_file(path: Path) -> bool:
    return bool(TEST_PATH_RE.search(path.as_posix()))


def detect_changed_files(root: Path, base: str | None, files: list[Path]) -> list[str]:
    if base:
        names = run_git(root, ["diff", "--name-only", f"{base}...HEAD"])
        if names:
            return sorted({name for name in names.splitlines() if name})

    names = "\n".join(
        part
        for part in [
            run_git(root, ["diff", "--name-only"]),
            run_git(root, ["diff", "--cached", "--name-only"]),
        ]
        if part
    )
    if names:
        return sorted({name for name in names.splitlines() if name})

    return [rel(root, path) for path in files]


def language_inventory(root: Path, files: list[Path]) -> dict:
    counts: dict[str, int] = {}
    for path in files:
        language = language_for(path)
        if language != "Unknown":
            counts[language] = counts.get(language, 0) + 1

    manifests = {
        "package.json": (root / "package.json").exists(),
        "pyproject.toml": (root / "pyproject.toml").exists(),
        "go.mod": (root / "go.mod").exists(),
        "pom.xml": (root / "pom.xml").exists(),
    }

    for manifest, exists in manifests.items():
        if not exists:
            continue
        if manifest == "package.json":
            counts["TypeScript/JavaScript"] = counts.get("TypeScript/JavaScript", 0) + 1
        elif manifest == "pyproject.toml":
            counts["Python"] = counts.get("Python", 0) + 1
        elif manifest == "go.mod":
            counts["Go"] = counts.get("Go", 0) + 1
        elif manifest == "pom.xml":
            counts["Java"] = counts.get("Java", 0) + 1

    primary = [
        lang
        for lang, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if lang != "TypeScript/JavaScript"
    ]
    if "TypeScript/JavaScript" in counts and not {"TypeScript", "JavaScript"} & set(primary):
        primary.append("TypeScript/JavaScript")

    return {
        "counts": counts,
        "primary_languages": primary,
        "manifests": {name: exists for name, exists in manifests.items() if exists},
    }


def parse_env_example(root: Path) -> set[str]:
    keys: set[str] = set()
    for name in [".env.example", ".env.sample", "env.example"]:
        path = root / name
        if not path.exists():
            continue
        for line in read_text(path).splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip()
            if key:
                keys.add(key)
    return keys


def add_signal(signals: list[Signal], **kwargs: object) -> None:
    signals.append(Signal(**kwargs))  # type: ignore[arg-type]


def scan_fake_words(root: Path, path: Path, text: str, signals: list[Signal]) -> None:
    if is_test_file(path):
        return
    language = language_for(path)
    for index, line in enumerate(text.splitlines(), start=1):
        if FAKE_WORD_RE.search(line):
            add_signal(
                signals,
                category="fake-fallback",
                severity="HIGH",
                file=rel(root, path),
                line=index,
                language=language,
                message="Production code contains fake/mock/fallback wording that needs path verification",
                evidence=line.strip()[:240],
                recommendation="Trace whether this code is reachable in production. Replace fake data with real integration behavior or document an intentional, observable degradation path.",
                owner_role="Backend/Frontend owner",
                acceptance_criteria="Reviewer can point to the production path decision: removed fake logic, or approved fallback with logs, metrics, tests, and runbook notes.",
            )


def scan_js_ts(root: Path, path: Path, text: str, env_keys: set[str], signals: list[Signal]) -> None:
    relative = rel(root, path)
    lines = text.splitlines()
    language = language_for(path)

    for index, line in enumerate(lines, start=1):
        for match in JS_ENV_RE.finditer(line):
            key = match.group(1) or match.group(2)
            if env_keys and key not in env_keys:
                add_signal(
                    signals,
                    category="env-drift",
                    severity="HIGH",
                    file=relative,
                    line=index,
                    language=language,
                    message="Environment variable is referenced in code but missing from .env.example",
                    evidence=key,
                    recommendation="Add a safe placeholder and usage note to .env.example, and verify the README/local setup path.",
                    owner_role="Service owner",
                    acceptance_criteria=f".env.example documents {key}, and the documented start/test command succeeds without private values.",
                )

        if re.search(r"\b(as\s+any|:\s*any\b|@ts-ignore|@ts-expect-error)\b", line):
            add_signal(
                signals,
                category="engineering-quality",
                severity="MEDIUM",
                file=relative,
                line=index,
                language=language,
                message="TypeScript escape hatch weakens type-driven review",
                evidence=line.strip()[:240],
                recommendation="Replace the escape hatch with typed boundaries, runtime validation, or a narrow adapter that contains the unsafe conversion.",
                owner_role="TypeScript owner",
                acceptance_criteria="The unsafe cast is removed or isolated with a named boundary and test coverage for invalid input.",
            )

    for index, line in enumerate(lines, start=1):
        if re.search(r"\bcatch\s*\(", line):
            window = "\n".join(lines[index : index + 8])
            if re.search(r"return\s+(\[\]|{}|true|false|null|undefined|['\"]|`|\[\s*{)", window):
                add_signal(
                    signals,
                    category="fake-fallback",
                    severity="BLOCKER",
                    file=relative,
                    line=index,
                    language=language,
                    message="JavaScript/TypeScript catch block converts failure into fallback success",
                    evidence=(line.strip() + " " + window.strip()).replace("\n", " ")[:240],
                    recommendation="Do not hide integration or data failures behind default success. Return a typed error, surface degraded mode explicitly, and cover it with tests.",
                    owner_role="Backend/Frontend owner",
                    acceptance_criteria="A failing dependency produces an observable error or approved degraded response with test coverage and operational logging.",
                )

    if path.suffix in {".tsx", ".jsx"} and re.search(r"\b(prisma|sequelize|typeorm|mongoose|knex|node:fs|fs)\b", text):
        add_signal(
            signals,
            category="engineering-quality",
            severity="HIGH",
            file=relative,
            line=first_matching_line(lines, r"\b(prisma|sequelize|typeorm|mongoose|knex|node:fs|fs)\b"),
            language=language,
            message="React UI code should not reach database clients directly",
            evidence="UI layer imports or references persistence/infrastructure APIs.",
            recommendation="Move persistence access behind an API/client or application service. Keep React components focused on rendering, interaction state, and server-state hooks.",
            owner_role="Frontend owner",
            acceptance_criteria="The component depends on a typed client/hook, while database access remains in backend or infrastructure modules with tests.",
        )

    if re.search(r"\.(controller|route|handler)\.tsx?$", relative) and re.search(r"\b(prisma|sequelize|typeorm|mongoose|knex)\b", text):
        add_signal(
            signals,
            category="engineering-quality",
            severity="MEDIUM",
            file=relative,
            line=first_matching_line(lines, r"\b(prisma|sequelize|typeorm|mongoose|knex)\b"),
            language=language,
            message="HTTP boundary contains direct persistence access",
            evidence="Controller/route handler references database client directly.",
            recommendation="Move business rules and persistence access into application/domain services; keep handlers thin and validation-focused.",
            owner_role="Backend owner",
            acceptance_criteria="Handler delegates to a service, and service behavior is covered by unit or integration tests.",
        )

    weak_status_only_test(root, path, lines, signals)
    file_size_quality(root, path, lines, signals)


def weak_status_only_test(root: Path, path: Path, lines: list[str], signals: list[Signal]) -> None:
    if not is_test_file(path):
        return
    text = "\n".join(lines)
    expectation_count = len(re.findall(r"\b(expect|assert)\b", text))
    status_only = re.search(r"\b(status|statusCode)\b.*\b(200|201|204)\b", text)
    trivial = re.search(r"(expect\(true\)\.toBe\(true\)|assert\(?True\)?|assert\.ok\(true\))", text)
    skipped = re.search(r"\b(describe|it|test)\.(skip|only)\b", text)
    if skipped:
        severity = "HIGH" if ".skip" in skipped.group(0) else "MEDIUM"
        message = "Test file contains skipped or focused tests"
    elif trivial:
        severity = "HIGH"
        message = "Test contains a trivial assertion that cannot prove behavior"
    elif status_only and expectation_count <= 1:
        severity = "HIGH"
        message = "Test only checks HTTP status and misses business assertions"
    else:
        return

    add_signal(
        signals,
        category="weak-test",
        severity=severity,
        file=rel(root, path),
        line=first_matching_line(lines, r"(status|statusCode|expect\(true\)|assert\(?True\)?|\.skip|\.only)"),
        language=language_for(path),
        message=message,
        evidence=next_matching_text(lines, r"(status|statusCode|expect\(true\)|assert\(?True\)?|\.skip|\.only)"),
        recommendation="Assert the business result, error path, permission behavior, and data shape that the PR claims to implement.",
        owner_role="QA/Author",
        acceptance_criteria="The test fails when the implementation returns wrong data while still returning a successful status code.",
    )


def scan_python(root: Path, path: Path, text: str, env_keys: set[str], signals: list[Signal]) -> None:
    relative = rel(root, path)
    lines = text.splitlines()

    for index, line in enumerate(lines, start=1):
        for match in PY_ENV_RE.finditer(line):
            key = match.group(1)
            if env_keys and key not in env_keys:
                add_signal(
                    signals,
                    category="env-drift",
                    severity="HIGH",
                    file=relative,
                    line=index,
                    language="Python",
                    message="Python environment variable is referenced but missing from .env.example",
                    evidence=key,
                    recommendation="Document the setting with a safe placeholder and verify the documented run command.",
                    owner_role="Service owner",
                    acceptance_criteria=f".env.example documents {key}, and local tests/startup do not depend on private values.",
                )

        if re.search(r"def\s+\w+\([^)]*=\s*(\[\]|{}|set\()", line):
            add_signal(
                signals,
                category="engineering-quality",
                severity="HIGH",
                file=relative,
                line=index,
                language="Python",
                message="Python functions should not use mutable default arguments",
                evidence=line.strip()[:240],
                recommendation="Use None as the default and initialize a new list/dict/set inside the function.",
                owner_role="Python owner",
                acceptance_criteria="Repeated calls do not share mutable state, covered by a regression test.",
            )

        if re.search(r"\bexcept\s*:\s*$", line):
            add_signal(
                signals,
                category="engineering-quality",
                severity="HIGH",
                file=relative,
                line=index,
                language="Python",
                message="Python bare except catches system-exiting exceptions",
                evidence=line.strip()[:240],
                recommendation="Catch the narrow exception type, preserve context, and let unrecoverable exceptions propagate.",
                owner_role="Python owner",
                acceptance_criteria="Only expected exceptions are caught, and unexpected failures remain visible in tests/logs.",
            )

        if re.search(r"\bexcept\s+Exception\b", line):
            window = "\n".join(lines[index : index + 8])
            if re.search(r"return\s+(\[\]|{}|None|True|False|['\"])", window):
                add_signal(
                    signals,
                    category="fake-fallback",
                    severity="BLOCKER",
                    file=relative,
                    line=index,
                    language="Python",
                    message="Python broad exception fallback hides operational failure",
                    evidence=(line.strip() + " " + window.strip()).replace("\n", " ")[:240],
                    recommendation="Catch narrow exceptions and return a typed error or explicit degraded result instead of silently returning empty/default data.",
                    owner_role="Python owner",
                    acceptance_criteria="A dependency failure is observable to the caller and covered by a negative-path test.",
                )

    weak_status_only_test(root, path, lines, signals)
    file_size_quality(root, path, lines, signals)


def scan_go(root: Path, path: Path, text: str, signals: list[Signal]) -> None:
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if re.search(r"^\s*_\s*=", line):
            add_signal(
                signals,
                category="engineering-quality",
                severity="HIGH",
                file=rel(root, path),
                line=index,
                language="Go",
                message="Go error/value is intentionally ignored",
                evidence=line.strip()[:240],
                recommendation="Handle the returned error/value explicitly. If ignoring is intentional, document why and prove it is safe.",
                owner_role="Go owner",
                acceptance_criteria="The ignored return is handled or justified with a narrow test that proves no failure path is lost.",
            )
        if "panic(" in line:
            add_signal(
                signals,
                category="fake-fallback",
                severity="HIGH",
                file=rel(root, path),
                line=index,
                language="Go",
                message="Go production path panics instead of returning an error",
                evidence=line.strip()[:240],
                recommendation="Return errors through the call boundary and let handlers translate them into explicit responses.",
                owner_role="Go owner",
                acceptance_criteria="The failure path returns an error/response and is covered by tests.",
            )


def scan_java(root: Path, path: Path, text: str, signals: list[Signal]) -> None:
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if re.search(r"catch\s*\([^)]*Exception[^)]*\)\s*\{\s*\}", line):
            add_signal(
                signals,
                category="fake-fallback",
                severity="BLOCKER",
                file=rel(root, path),
                line=index,
                language="Java",
                message="Java empty catch block hides failure",
                evidence=line.strip()[:240],
                recommendation="Catch a narrow exception, preserve context, and return or throw a domain-specific error.",
                owner_role="Java owner",
                acceptance_criteria="The failure path is visible to callers and covered by tests.",
            )


def file_size_quality(root: Path, path: Path, lines: list[str], signals: list[Signal]) -> None:
    if len(lines) <= 400 or is_test_file(path):
        return
    add_signal(
        signals,
        category="engineering-quality",
        severity="MEDIUM",
        file=rel(root, path),
        line=1,
        language=language_for(path),
        message="Large source file may be carrying multiple responsibilities",
        evidence=f"{len(lines)} lines",
        recommendation="Review whether the file mixes UI, orchestration, domain logic, IO, and formatting. Split only along real ownership or testability boundaries.",
        owner_role="Module owner",
        acceptance_criteria="Responsibilities are either justified in the report or split into smaller modules with unchanged behavior tests.",
    )


def first_matching_line(lines: list[str], pattern: str) -> int:
    regex = re.compile(pattern)
    for index, line in enumerate(lines, start=1):
        if regex.search(line):
            return index
    return 1


def next_matching_text(lines: list[str], pattern: str) -> str:
    regex = re.compile(pattern)
    for line in lines:
        if regex.search(line):
            return line.strip()[:240]
    return ""


def scan(root: Path, base: str | None = None) -> dict:
    files = iter_files(root)
    env_keys = parse_env_example(root)
    changed_files = detect_changed_files(root, base, files)
    changed_set = set(changed_files)
    scan_files = [
        path
        for path in files
        if rel(root, path) in changed_set or not run_git(root, ["rev-parse", "--is-inside-work-tree"])
    ]
    if not scan_files:
        scan_files = files

    signals: list[Signal] = []
    for path in scan_files:
        text = read_text(path)
        if not text:
            continue
        scan_fake_words(root, path, text, signals)
        language = language_for(path)
        if language in {"TypeScript", "JavaScript"}:
            scan_js_ts(root, path, text, env_keys, signals)
        elif language == "Python":
            scan_python(root, path, text, env_keys, signals)
        elif language == "Go":
            scan_go(root, path, text, signals)
        elif language == "Java":
            scan_java(root, path, text, signals)

    inventory = language_inventory(root, files)
    return {
        "repo": str(root),
        "git": {
            "status": run_git(root, ["status", "--short", "--branch"]),
            "base": base,
            "changed_files": changed_files,
        },
        "language_inventory": inventory,
        "language_review_guidance": language_review_guidance(inventory["primary_languages"]),
        "signals": [asdict(signal) for signal in sorted(signals, key=signal_sort_key)],
    }


def signal_sort_key(signal: Signal) -> tuple[int, str, int, str]:
    severity_rank = {"BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return (severity_rank.get(signal.severity, 9), signal.file, signal.line, signal.message)


def language_review_guidance(languages: Iterable[str]) -> dict[str, list[str]]:
    guidance: dict[str, list[str]] = {}
    for language in languages:
        if language == "TypeScript":
            guidance[language] = [
                "Use types and runtime validation at IO boundaries instead of any/ts-ignore.",
                "Keep React components UI-focused and move business logic to hooks/services.",
                "Keep Nest/HTTP handlers thin; route through application services and typed DTOs.",
            ]
        elif language == "JavaScript":
            guidance[language] = [
                "Compensate for weak static typing with validation, focused modules, and behavior tests.",
                "Do not turn async failures into default success values unless degraded mode is explicit.",
            ]
        elif language == "Python":
            guidance[language] = [
                "Prefer explicit exceptions, typed return shapes, dependency injection, and small pure functions.",
                "Avoid mutable defaults, bare except, and broad Exception fallbacks that return empty data.",
            ]
        elif language == "Go":
            guidance[language] = [
                "Handle errors explicitly, keep packages small, and pass context through IO boundaries.",
                "Avoid panic in request paths and avoid ignored errors.",
            ]
        elif language == "Java":
            guidance[language] = [
                "Preserve layered boundaries, typed exceptions, transaction scope, and narrow service responsibilities.",
                "Avoid empty catch blocks and controller-heavy business logic.",
            ]
    return guidance


def to_markdown(report: dict) -> str:
    lines = [
        "# AI PR Redteam Scan",
        "",
        f"- Repo: `{report['repo']}`",
        f"- Primary languages: {', '.join(report['language_inventory']['primary_languages']) or 'Unknown'}",
        f"- Changed files: {len(report['git']['changed_files'])}",
        f"- Signals: {len(report['signals'])}",
        "",
    ]
    if report["signals"]:
        lines.extend(
            [
                "| Severity | Category | File | Line | Message | Recommendation |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for signal in report["signals"]:
            lines.append(
                f"| {signal['severity']} | {signal['category']} | `{signal['file']}` | {signal['line']} | "
                f"{escape_pipe(signal['message'])} | {escape_pipe(signal['recommendation'])} |"
            )
    else:
        lines.append("No heuristic signals found. Review still requires reading the PR intent and changed code.")
    return "\n".join(lines) + "\n"


def escape_pipe(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a repository for AI PR red-team review signals.")
    parser.add_argument("repo", help="Repository root to scan")
    parser.add_argument("--base", help="Optional git base ref for PR diff scope")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", help="Optional output file")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"repo does not exist or is not a directory: {root}")

    report = scan(root, args.base)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else to_markdown(report)

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
