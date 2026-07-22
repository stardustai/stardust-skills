#!/usr/bin/env python3
"""Snapshot, compare, and analyze Dingteam OKR rating archives."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_API_PATH = Path(__file__).resolve().parent / "dingteam_okr_api.py"
_spec = importlib.util.spec_from_file_location("dingteam_okr_api", _API_PATH)
api = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(api)


def archive_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Accept a raw API result, a CLI wrapper, or a saved audit snapshot."""
    if isinstance(payload.get("archive"), dict):
        payload = payload["archive"]
    if payload.get("ok") is True and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("list"), list):
        payload = payload["data"]
    items = payload.get("list")
    if not isinstance(items, list):
        raise ValueError("archive payload does not contain a list")
    return items


def comparison_fields(item: dict[str, Any]) -> dict[str, Any]:
    user = item.get("userInfo") if isinstance(item.get("userInfo"), dict) else {}
    return {
        "ownerId": user.get("id"),
        "owner": user.get("name"),
        "objectiveName": item.get("objectiveName"),
        "objectiveType": item.get("objectiveType"),
        "department": item.get("objectiveDeptName"),
        "score": item.get("score"),
        "progress": item.get("objectiveProgress"),
    }


def index_archive(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        objective_id = item.get("objectiveId")
        if not objective_id:
            raise ValueError(f"rating row lacks objectiveId: {item!r}")
        if objective_id in result:
            raise ValueError(f"duplicate objectiveId in archive: {objective_id}")
        result[str(objective_id)] = comparison_fields(item)
    return result


def compare_archives(
    before_items: list[dict[str, Any]],
    after_items: list[dict[str, Any]],
) -> dict[str, Any]:
    before = index_archive(before_items)
    after = index_archive(after_items)
    added = [
        {"objectiveId": objective_id, **after[objective_id]}
        for objective_id in sorted(after.keys() - before.keys())
    ]
    removed = [
        {"objectiveId": objective_id, **before[objective_id]}
        for objective_id in sorted(before.keys() - after.keys())
    ]
    changed = [
        {
            "objectiveId": objective_id,
            "before": before[objective_id],
            "after": after[objective_id],
        }
        for objective_id in sorted(after.keys() & before.keys())
        if before[objective_id] != after[objective_id]
    ]
    return {
        "baselineCount": len(before),
        "currentCount": len(after),
        "added": added,
        "removed": removed,
        "changed": changed,
        "hasDifferences": bool(added or removed or changed),
    }


def parse_categories(values: list[str]) -> dict[str, str]:
    categories: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"category must be NAME=TEXT: {value}")
        name, text = value.split("=", 1)
        if not name.strip() or not text.strip():
            raise ValueError(f"category must be NAME=TEXT: {value}")
        categories[name.strip()] = text.strip()
    return categories


def analyze_archive(
    items: list[dict[str, Any]],
    categories: dict[str, str],
) -> dict[str, Any]:
    categorized: list[dict[str, Any]] = []
    for item in items:
        name = str(item.get("objectiveName") or "")
        user = item.get("userInfo") if isinstance(item.get("userInfo"), dict) else {}
        for category, marker in categories.items():
            if marker in name:
                categorized.append(
                    {
                        "ownerId": user.get("id"),
                        "owner": user.get("name"),
                        "category": category,
                        "objectiveId": item.get("objectiveId"),
                        "objectiveName": name,
                        "score": item.get("score"),
                        "progress": item.get("objectiveProgress"),
                    }
                )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in categorized:
        grouped.setdefault((str(item["ownerId"]), item["category"]), []).append(item)
    duplicates = [
        {
            "ownerId": owner_id,
            "owner": rows[0]["owner"],
            "category": category,
            "count": len(rows),
            "objectives": rows,
        }
        for (owner_id, category), rows in grouped.items()
        if len(rows) > 1
    ]
    return {
        "totalObjectives": len(items),
        "categorizedObjectives": len(categorized),
        "nullScores": [
            {"objectiveId": item.get("objectiveId"), **comparison_fields(item)}
            for item in items
            if item.get("score") is None
        ],
        "zeroScores": [
            {"objectiveId": item.get("objectiveId"), **comparison_fields(item)}
            for item in items
            if item.get("score") == 0
        ],
        "duplicates": sorted(
            duplicates,
            key=lambda item: (str(item["owner"]), str(item["category"])),
        ),
    }


def snapshot_payload(okr_id: str, archive: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "okrId": okr_id,
        "archive": archive,
    }


def write_json(path: str | None, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path:
        output = Path(path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        print(json.dumps({"output": str(output), "sha256": digest}, ensure_ascii=False))
    else:
        print(text, end="")


def load_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot", help="save a live rating archive")
    snapshot_parser.add_argument("--okr-id", required=True)
    snapshot_parser.add_argument("--user-id", action="append", default=[])
    snapshot_parser.add_argument("--output")

    compare_parser = subparsers.add_parser("compare", help="compare live state to baseline")
    compare_parser.add_argument("--okr-id", required=True)
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--user-id", action="append", default=[])
    compare_parser.add_argument("--output")

    analyze_parser = subparsers.add_parser("analyze", help="scan a saved or live archive")
    source = analyze_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive")
    source.add_argument("--okr-id")
    analyze_parser.add_argument(
        "--category",
        action="append",
        default=[],
        help="repeat NAME=TEXT to classify assessment objectives",
    )
    analyze_parser.add_argument("--output")

    args = parser.parse_args()
    allow_browser = not args.no_browser
    if args.command == "snapshot":
        archive = api.get_rating_list(
            args.okr_id,
            user_ids=args.user_id,
            allow_browser=allow_browser,
        )
        result = snapshot_payload(args.okr_id, archive)
    elif args.command == "compare":
        baseline = archive_items(load_json(args.baseline))
        current = api.get_rating_list(
            args.okr_id,
            user_ids=args.user_id,
            allow_browser=allow_browser,
        )
        result = compare_archives(baseline, current["list"])
    else:
        categories = parse_categories(args.category)
        if args.archive:
            items = archive_items(load_json(args.archive))
        else:
            items = api.get_rating_list(args.okr_id, allow_browser=allow_browser)["list"]
        result = analyze_archive(items, categories)
    write_json(args.output, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
