#!/usr/bin/env python3
"""Inventory a source tree for Dengbao/MLPS-oriented code audit."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


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
    ".idea",
    ".vscode",
    ".turbo",
    ".cache",
    "reports",
    "dengbao-code-audit",
}

SECURITY_PATH_PATTERNS = [
    r"auth",
    r"login",
    r"security",
    r"permission",
    r"role",
    r"rbac",
    r"acl",
    r"audit",
    r"log",
    r"controller",
    r"router",
    r"route",
    r"middleware",
    r"guard",
    r"interceptor",
    r"filter",
    r"upload",
    r"download",
    r"export",
    r"backup",
    r"restore",
    r"docker",
    r"k8s",
    r"kubernetes",
    r"nginx",
    r"deploy",
    r"ci",
    r"workflow",
    r"jenkins",
    r"helm",
    r"values",
]


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".egg")]
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                if path.is_file():
                    yield path
            except OSError:
                continue


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_small_text(path: Path, limit: int = 300_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def detect_package_json(path: Path) -> list[str]:
    tech = []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return tech
    deps = {}
    for key in ("dependencies", "devDependencies"):
        value = data.get(key)
        if isinstance(value, dict):
            deps.update(value)
    mapping = {
        "react": "React",
        "vue": "Vue",
        "next": "Next.js",
        "vite": "Vite",
        "express": "Express",
        "@nestjs/core": "NestJS",
        "koa": "Koa",
        "typeorm": "TypeORM",
        "sequelize": "Sequelize",
        "prisma": "Prisma",
        "mongoose": "Mongoose",
    }
    for dep, name in mapping.items():
        if dep in deps:
            tech.append(name)
    return tech


def detect_text_file(name: str, text: str) -> list[str]:
    tech = []
    lower_name = name.lower()
    lower_text = text.lower()
    if lower_name == "pom.xml" or "spring-boot" in lower_text:
        tech.append("Spring Boot")
    if lower_name in {"build.gradle", "build.gradle.kts"}:
        tech.append("Gradle/Java")
    if lower_name == "requirements.txt":
        tech.append("Python")
    if lower_name == "pyproject.toml":
        tech.append("Python")
    if "django" in lower_text:
        tech.append("Django")
    if "fastapi" in lower_text:
        tech.append("FastAPI")
    if "flask" in lower_text:
        tech.append("Flask")
    if lower_name == "go.mod":
        tech.append("Go")
    if lower_name.startswith("dockerfile") or lower_name == "docker-compose.yml":
        tech.append("Docker")
    if lower_name.endswith((".yaml", ".yml")) and re.search(r"\b(kind|apiVersion):", text):
        tech.append("Kubernetes/YAML")
    if "nginx" in lower_name or "server_name" in lower_text:
        tech.append("Nginx")
    return tech


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Project root to inventory")
    parser.add_argument("--output", "-o", help="Write JSON output to file")
    parser.add_argument("--max-security-files", type=int, default=300)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")

    files = list(iter_files(root))
    ext_counts: Counter[str] = Counter()
    size_total = 0
    tech: set[str] = set()
    security_files: list[str] = []
    doc_files: list[str] = []
    deploy_files: list[str] = []
    package_files: list[str] = []
    top_dirs: Counter[str] = Counter()
    samples_by_ext: dict[str, list[str]] = defaultdict(list)

    security_regex = re.compile("|".join(SECURITY_PATH_PATTERNS), re.IGNORECASE)

    for path in files:
        relative = rel(path, root)
        suffix = path.suffix.lower() or "<none>"
        ext_counts[suffix] += 1
        top_dirs[relative.split("/", 1)[0]] += 1
        try:
            size_total += path.stat().st_size
        except OSError:
            pass
        if len(samples_by_ext[suffix]) < 8:
            samples_by_ext[suffix].append(relative)

        lower = relative.lower()
        name = path.name.lower()
        if name in {"package.json", "pom.xml", "build.gradle", "build.gradle.kts", "requirements.txt", "pyproject.toml", "go.mod"}:
            package_files.append(relative)
        if re.search(r"(^|/)(readme|security|deploy|deployment|operations|architecture|docs?)", lower):
            doc_files.append(relative)
        if any(part in lower for part in ("docker", "k8s", "kubernetes", "nginx", "helm", "compose", "jenkins", ".github/workflows", ".gitlab-ci")):
            deploy_files.append(relative)
        if security_regex.search(lower) and len(security_files) < args.max_security_files:
            security_files.append(relative)

        if name == "package.json":
            tech.update(detect_package_json(path))
        if name in {"package.json", "pom.xml", "build.gradle", "build.gradle.kts", "requirements.txt", "pyproject.toml", "go.mod", "docker-compose.yml"} or suffix in {".yml", ".yaml", ".conf"}:
            tech.update(detect_text_file(name, read_small_text(path)))

    result: dict[str, Any] = {
        "root": str(root),
        "file_count": len(files),
        "total_bytes": size_total,
        "extensions": dict(ext_counts.most_common()),
        "top_level_dirs": dict(top_dirs.most_common(30)),
        "detected_technologies": sorted(tech),
        "package_files": package_files[:100],
        "security_relevant_files": security_files,
        "deployment_files": deploy_files[:200],
        "documentation_files": doc_files[:200],
        "samples_by_extension": dict(samples_by_ext),
        "notes": [
            "Inventory is heuristic. Read relevant files before final conclusions.",
            "Missing documentation files may indicate material gaps for formal Dengbao preparation.",
        ],
    }

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
