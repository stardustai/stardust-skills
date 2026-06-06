#!/usr/bin/env python3
import argparse
import csv
import json
import pathlib
import subprocess
import sys
from collections import Counter


REPORT_DIR = pathlib.Path("/Users/derek/Documents/memory/钉钉知识库")


def run_dws(args, execute):
    cmd = ["dws", *args, "--format", "json"]
    if execute:
        cmd.append("--yes")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "dws command failed")
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {"raw": result.stdout}


def load_inventory(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    by_path = {item["path"].lstrip(): item for item in data["files"]}
    return data, by_path


def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def normalize_folder_path(path):
    return (path or "").strip().strip("/")


def parse_action(row):
    decision = (row.get("admin_decision") or "").strip()
    return decision or None


def extract_nodes(payload):
    if isinstance(payload, dict):
        if "nodes" in payload and isinstance(payload["nodes"], list):
            return payload["nodes"]
        if "items" in payload and isinstance(payload["items"], list):
            return payload["items"]
        if "data" in payload:
            return extract_nodes(payload["data"])
    if isinstance(payload, list):
        return payload
    return []


def extract_node_id(node):
    for key in ("nodeId", "id"):
        value = node.get(key)
        if value:
            return value
    return ""


def extract_node_name(node):
    for key in ("name", "title"):
        value = node.get(key)
        if value:
            return value
    return ""


def list_children(workspace_id=None, folder_id=None):
    args = ["doc", "list"]
    if folder_id:
        args.extend(["--folder", folder_id])
    elif workspace_id:
        args.extend(["--workspace", workspace_id])
    payload = run_dws(args, execute=False)
    return extract_nodes(payload)


def create_folder(name, workspace_id=None, parent_folder_id=None, execute=False):
    args = ["doc", "folder", "create", "--name", name]
    if parent_folder_id:
        args.extend(["--folder", parent_folder_id])
    elif workspace_id:
        args.extend(["--workspace", workspace_id])
    payload = run_dws(args, execute=execute)
    if isinstance(payload, dict):
        if payload.get("nodeId"):
            return payload["nodeId"]
        data = payload.get("data") or {}
        if isinstance(data, dict) and data.get("nodeId"):
            return data["nodeId"]
    raise RuntimeError(f"Failed to extract folder nodeId for folder {name}")


def resolve_folder_path(target_path, workspace_id, cache, execute=False):
    normalized = normalize_folder_path(target_path)
    if not normalized:
        return None
    if normalized in cache:
        return cache[normalized]

    parts = normalized.split("/")
    current_workspace = workspace_id
    current_folder = None
    prefix_parts = []

    for part in parts:
        prefix_parts.append(part)
        prefix = "/".join(prefix_parts)
        if prefix in cache:
            current_folder = cache[prefix]
            current_workspace = None
            continue

        children = list_children(workspace_id=current_workspace, folder_id=current_folder)
        matched = None
        for child in children:
            name = extract_node_name(child)
            node_id = extract_node_id(child)
            if name == part and node_id:
                matched = node_id
                break
        if not matched:
            matched = create_folder(
                part,
                workspace_id=current_workspace,
                parent_folder_id=current_folder,
                execute=execute,
            )
        cache[prefix] = matched
        current_folder = matched
        current_workspace = None

    return current_folder


def execute_row(row, inventory_item, workspace_id, folder_cache, execute):
    action = parse_action(row)
    if not action:
        return {"status": "skipped", "reason": "missing_admin_decision"}

    node_id = inventory_item.get("node_id") or inventory_item.get("nodeId") or ""
    if not node_id:
        return {"status": "failed", "reason": "missing_node_id"}

    performed = []
    target_folder = None
    move_to = (row.get("move_to") or "").strip()
    rename_to = (row.get("rename_to") or "").strip()

    if action == "move_to_待归档" and not move_to:
        move_to = "待归档"

    if action in {"move", "move_and_rename", "move_to_待归档"}:
        if not move_to:
            return {"status": "failed", "reason": "missing_move_to"}
        target_folder = resolve_folder_path(move_to, workspace_id, folder_cache, execute=execute)
        run_dws(["doc", "move", "--node", node_id, "--folder", target_folder], execute=execute)
        performed.append("move")

    if action in {"rename", "move_and_rename"}:
        if not rename_to:
            return {"status": "failed", "reason": "missing_rename_to"}
        run_dws(["doc", "rename", "--node", node_id, "--name", rename_to], execute=execute)
        performed.append("rename")

    if action == "keep":
        return {"status": "skipped", "reason": "keep"}
    if action == "duplicate_candidate":
        return {"status": "skipped", "reason": "duplicate_candidate"}

    return {"status": "executed", "performed": performed, "target_folder": target_folder or ""}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-json", required=True)
    parser.add_argument("--csv-path", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--report-path")
    args = parser.parse_args()

    inventory, inventory_by_path = load_inventory(args.inventory_json)
    rows = load_rows(args.csv_path)
    workspace_id = inventory["workspace"]["workspace_id"]
    workspace_name = inventory["workspace"]["name"]
    folder_cache = {}
    counters = Counter()
    report_rows = []

    for row in rows:
        file_path = row["file_path"]
        inventory_item = inventory_by_path.get(file_path)
        if not inventory_item:
            counters["missing_inventory_item"] += 1
            report_rows.append(
                {"file_path": file_path, "status": "failed", "reason": "inventory_item_not_found"}
            )
            continue

        action = parse_action(row)
        if args.dry_run:
            status = "ready" if action else "skipped"
            reason = action or "missing_admin_decision"
            counters[status] += 1
            report_rows.append(
                {
                    "file_path": file_path,
                    "status": status,
                    "reason": reason,
                    "move_to": row.get("move_to") or "",
                    "rename_to": row.get("rename_to") or "",
                }
            )
            continue

        try:
            outcome = execute_row(row, inventory_item, workspace_id, folder_cache, execute=True)
        except Exception as exc:
            counters["failed"] += 1
            report_rows.append({"file_path": file_path, "status": "failed", "reason": str(exc)})
            continue

        counters[outcome["status"]] += 1
        report_rows.append({"file_path": file_path, **outcome})

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if args.report_path:
        report_path = pathlib.Path(args.report_path)
    else:
        suffix = "dry-run" if args.dry_run else "executed"
        safe_name = workspace_name.replace("/", " ").strip()
        report_path = REPORT_DIR / f"{safe_name}-remediation-{suffix}-report.json"

    report = {
        "workspace_name": workspace_name,
        "mode": "dry-run" if args.dry_run else "execute",
        "summary": dict(counters),
        "report_rows": report_rows,
    }
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "workspace_name": workspace_name,
                "mode": report["mode"],
                "summary": report["summary"],
                "report_path": str(report_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
