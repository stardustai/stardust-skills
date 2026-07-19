#!/usr/bin/env python3
"""检查应用仓库并生成待人工确认的 deploy-inputs.json。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SKIP_DIRS = {".git", ".idea", ".vscode", "node_modules", "vendor", "dist", "build", "target", "deploy"}
RUNTIME_FILES = {
    "go.mod": "go",
    "package.json": "node",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "Cargo.toml": "rust",
}


def safe_name(value: str) -> str:
    value = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    value = re.sub(r"-+", "-", value)
    return value[:63] or "application"


def discover_modules(root: Path) -> list[tuple[Path, str]]:
    found: dict[Path, str] = {}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        runtime = RUNTIME_FILES.get(path.name)
        if runtime:
            found.setdefault(path.parent, runtime)
    if not found:
        return [(root, "unknown")]
    shallow = []
    for path, runtime in sorted(found.items()):
        if not any(parent in found for parent in path.parents if parent != path):
            shallow.append((path, runtime))
    return shallow or sorted(found.items())


def port_candidate(module: Path) -> int:
    patterns = [
        re.compile(r"(?:PORT|port)\s*[:=]\s*[\"']?(\d{2,5})"),
        re.compile(r"(?:listen|ListenAndServe)\s*\([^\n]{0,80}[:\"](\d{2,5})"),
    ]
    for path in module.rglob("*"):
        try:
            is_candidate = path.is_file() and path.stat().st_size <= 512_000
        except OSError:
            continue
        if not is_candidate or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in {".go", ".js", ".ts", ".json", ".yaml", ".yml", ".properties", ".py", ".rs"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in patterns:
            match = pattern.search(text)
            if match and 1 <= int(match.group(1)) <= 65535:
                return int(match.group(1))
    return 8080


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd(), help="项目根目录")
    parser.add_argument("--output", type=Path, default=Path("deploy-inputs.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    project = safe_name(root.name)
    modules = discover_modules(root)
    services = []
    used = set()
    for module, runtime in modules:
        relative = module.relative_to(root)
        name = project if relative == Path(".") else safe_name(module.name)
        if name in used:
            name = safe_name(f"{name}-{len(used) + 1}")
        used.add(name)
        detected_port = port_candidate(module)
        services.append({
            "name": name,
            "module": "." if relative == Path(".") else str(relative),
            "workload": "stateless",
            "runtime": runtime,
            "image": "<IMAGE_DIGEST_REQUIRED>",
            "port": detected_port,
            "health_path": "/healthz",
            "ready_path": "/readyz",
            "compose_healthcheck": ["CMD", "wget", "-q", "--spider", f"http://127.0.0.1:{detected_port}/healthz"],
            "expose": False,
            "ingress_path": "/",
            "uid": 10000,
            "gid": 10000,
            "data_path": None,
            "storage_size": None,
            "requires_confirmation": ["workload", "image", "port", "health_path", "ready_path", "compose_healthcheck", "expose", "uid", "gid"],
        })
    result = {
        "schema_version": 1,
        "project": project,
        "namespace": project,
        "domain": "<DOMAIN_PENDING_APPROVAL>",
        "change_ticket": "<CHANGE_TICKET_REQUIRED>",
        "domain_request": "<DOMAIN_REQUEST_REQUIRED>",
        "first_cicd_approved": False,
        "services": services,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 {args.output}；所有 requires_confirmation 字段必须由项目组确认。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
