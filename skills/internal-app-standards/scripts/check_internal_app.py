#!/usr/bin/env python3
"""Lightweight repository checker for the internal-app-standards skill."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Check:
    status: str
    category: str
    message: str
    path: str | None = None


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def exists(root: Path, relative: str) -> bool:
    return (root / relative).exists()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def package_jsons(root: Path) -> list[tuple[Path, dict]]:
    results: list[tuple[Path, dict]] = []
    for path in root.rglob("package.json"):
        if "node_modules" in path.parts or ".next" in path.parts or "dist" in path.parts:
            continue
        try:
            results.append((path, json.loads(read_text(path))))
        except json.JSONDecodeError:
            results.append((path, {}))
    return results


def dependencies(packages: Iterable[tuple[Path, dict]]) -> set[str]:
    deps: set[str] = set()
    for _, package in packages:
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            value = package.get(key)
            if isinstance(value, dict):
                deps.update(value.keys())
    return deps


def any_file(root: Path, patterns: Iterable[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        found.extend(path for path in root.glob(pattern) if path.is_file())
    return found


def add_path_check(checks: list[Check], root: Path, relative: str, category: str, label: str) -> None:
    status = "PASS" if exists(root, relative) else "FAIL"
    checks.append(Check(status, category, label, relative))


def check_repo(root: Path) -> list[Check]:
    checks: list[Check] = []
    packages = package_jsons(root)
    deps = dependencies(packages)

    for relative, label in [
        ("pnpm-workspace.yaml", "pnpm workspace is present"),
        ("apps/web", "standard frontend app directory exists"),
        ("apps/api", "standard backend app directory exists"),
        ("packages/shared", "shared contracts package exists"),
        ("db", "database directory exists"),
        ("infra/k8s", "Kubernetes manifest directory exists"),
        ("scripts", "deployment/maintenance scripts directory exists"),
    ]:
        add_path_check(checks, root, relative, "structure", label)

    checks.append(Check("PASS" if "react" in deps else "FAIL", "frontend", "React dependency found"))
    checks.append(Check("PASS" if "antd" in deps else "FAIL", "frontend", "Ant Design dependency found"))
    checks.append(Check("PASS" if "typescript" in deps else "FAIL", "engineering", "TypeScript dependency found"))
    checks.append(Check("PASS" if "@nestjs/core" in deps else "FAIL", "backend", "NestJS dependency found"))

    pg_deps = {"pg", "prisma", "@prisma/client", "drizzle-orm", "kysely"}
    checks.append(
        Check(
            "PASS" if deps.intersection(pg_deps) else "FAIL",
            "database",
            "PostgreSQL data-access/migration dependency found",
        )
    )

    migration_files = any_file(root, ["db/migrations/**/*", "apps/api/prisma/migrations/**/*"])
    checks.append(
        Check(
            "PASS" if migration_files else "FAIL",
            "database",
            "committed database migrations found",
            rel(migration_files[0], root) if migration_files else None,
        )
    )

    dockerfiles = any_file(root, ["apps/*/Dockerfile", "infra/docker/**/Dockerfile", "Dockerfile"])
    checks.append(
        Check(
            "PASS" if dockerfiles else "FAIL",
            "deployment",
            "Dockerfile found for buildable runtime image",
            rel(dockerfiles[0], root) if dockerfiles else None,
        )
    )

    k8s_files = any_file(root, ["infra/k8s/**/*.yaml", "infra/k8s/**/*.yml", "k8s/**/*.yaml", "k8s/**/*.yml"])
    k8s_text = "\n".join(read_text(path) for path in k8s_files)
    checks.append(Check("PASS" if k8s_files else "FAIL", "deployment", "Kubernetes YAML files found"))
    checks.append(Check("PASS" if "readinessProbe" in k8s_text else "WARN", "deployment", "readinessProbe configured"))
    checks.append(Check("PASS" if "livenessProbe" in k8s_text else "WARN", "deployment", "livenessProbe configured"))
    checks.append(Check("PASS" if "resources:" in k8s_text else "WARN", "deployment", "CPU/memory resources configured"))

    for script in ("build.sh", "test.sh", "migrate.sh", "deploy.sh", "rollback.sh"):
        path = root / "scripts" / script
        checks.append(
            Check(
                "PASS" if path.exists() else "WARN",
                "scripts",
                f"{script} present",
                rel(path, root),
            )
        )

    env_examples = any_file(root, ["**/.env.example"])
    checks.append(
        Check(
            "PASS" if env_examples else "WARN",
            "configuration",
            ".env.example found for safe configuration documentation",
            rel(env_examples[0], root) if env_examples else None,
        )
    )

    return checks


def render_markdown(root: Path, checks: list[Check]) -> str:
    counts = {status: sum(1 for check in checks if check.status == status) for status in ("PASS", "WARN", "FAIL")}
    lines = [
        "# Internal App Standards Check",
        "",
        f"Repository: `{root}`",
        f"Summary: {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail",
        "",
    ]
    for status in ("FAIL", "WARN", "PASS"):
        group = [check for check in checks if check.status == status]
        if not group:
            continue
        lines.append(f"## {status}")
        lines.append("")
        for check in group:
            suffix = f" (`{check.path}`)" if check.path else ""
            lines.append(f"- **{check.category}**: {check.message}{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a repository against internal app standards.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository path to check")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    args = parser.parse_args()

    root = Path(args.repo).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Repository path does not exist: {root}")

    checks = check_repo(root)
    if args.json:
        print(json.dumps([check.__dict__ for check in checks], ensure_ascii=False, indent=2))
    else:
        print(render_markdown(root, checks))

    return 1 if any(check.status == "FAIL" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
