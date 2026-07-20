#!/usr/bin/env python3
"""Run deterministic package validation for the Vibe Coding Skill."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    schema_ids: dict[str, Path] = {}
    for schema in sorted((skill_root / "assets/schemas").glob("*.json")):
        try:
            payload = json.loads(schema.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON schema {schema}: {exc}", file=sys.stderr)
            return 1
        schema_id = payload.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            print(f"ERROR: JSON schema has no $id: {schema}", file=sys.stderr)
            return 1
        if schema_id in schema_ids:
            print(f"ERROR: duplicate JSON schema $id in {schema_ids[schema_id]} and {schema}", file=sys.stderr)
            return 1
        schema_ids[schema_id] = schema
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(skill_root / "tests"),
            "-p",
            "test_*.py",
        ],
        cwd=skill_root,
        check=False,
        env=environment,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
