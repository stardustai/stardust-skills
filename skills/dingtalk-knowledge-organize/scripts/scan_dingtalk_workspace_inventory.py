#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from collections import deque
from urllib.error import HTTPError, URLError


CONFIG_PATH = os.path.expanduser("~/.dingtalk-skills/config")
OUTPUT_DIR = pathlib.Path.home() / "Documents" / "memory" / "钉钉知识库"


def load_config():
    cfg = {}
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            cfg[key] = value
    required = [
        "DINGTALK_APP_KEY",
        "DINGTALK_APP_SECRET",
        "DINGTALK_OPERATOR_ID",
    ]
    missing = [key for key in required if key not in cfg]
    if missing:
        raise SystemExit(f"Missing config keys: {', '.join(missing)}")
    return cfg


def request_json(url, method="GET", body=None, token=None, retries=3, backoff_seconds=1.5):
    headers = {}
    payload = None
    if token:
        headers["x-acs-dingtalk-access-token"] = token
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method=method,
    )
    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt >= retries:
                raise SystemExit(f"Request failed after {attempt} attempts: {url} :: {exc}") from exc
            time.sleep(backoff_seconds * attempt)


def fetch_access_token(cfg):
    data = request_json(
        "https://api.dingtalk.com/v1.0/oauth2/accessToken",
        method="POST",
        body={
            "appKey": cfg["DINGTALK_APP_KEY"],
            "appSecret": cfg["DINGTALK_APP_SECRET"],
        },
    )
    return data["accessToken"]


def list_workspaces(operator_id, token):
    workspaces = []
    next_token = None
    while True:
        query = {"operatorId": operator_id, "maxResults": 100}
        if next_token:
            query["nextToken"] = next_token
        url = "https://api.dingtalk.com/v2.0/wiki/workspaces?" + urllib.parse.urlencode(query)
        data = request_json(url, token=token)
        workspaces.extend(data.get("workspaces") or [])
        next_token = data.get("nextToken")
        if not next_token:
            return workspaces


def resolve_workspace(workspaces, workspace_name):
    exact = [item for item in workspaces if item.get("name") == workspace_name]
    if exact:
        return exact[0]
    partial = [item for item in workspaces if workspace_name in (item.get("name") or "")]
    if partial:
        return partial[0]
    names = [item.get("name") for item in workspaces]
    raise SystemExit(
        "Workspace not found. Available workspaces: " + ", ".join(name for name in names if name)
    )


def resolve_workspace_by_id(workspaces, workspace_id):
    matched = [item for item in workspaces if item.get("workspaceId") == workspace_id]
    if matched:
        return matched[0]
    raise SystemExit(f"Workspace ID not found: {workspace_id}")


def scan_workspace(workspace, operator_id, token, progress_every=50):
    queue = deque([(workspace["rootNodeId"], "")])
    visited = set()
    files = []
    folders_seen = 0
    api_calls = 0

    while queue:
        parent_id, parent_path = queue.popleft()
        if parent_id in visited:
            continue
        visited.add(parent_id)
        folders_seen += 1
        if progress_every and folders_seen % progress_every == 0:
            print(
                json.dumps(
                    {
                        "event": "scan_progress",
                        "workspace": workspace["name"],
                        "folders_seen": folders_seen,
                        "files_so_far": len(files),
                        "queue_size": len(queue),
                        "api_calls": api_calls,
                    },
                    ensure_ascii=False,
                ),
                file=sys.stderr,
                flush=True,
            )
        next_token = None
        while True:
            query = {
                "parentNodeId": parent_id,
                "operatorId": operator_id,
                "maxResults": 100,
            }
            if next_token:
                query["nextToken"] = next_token
            url = "https://api.dingtalk.com/v2.0/wiki/nodes?" + urllib.parse.urlencode(query)
            data = request_json(url, token=token)
            api_calls += 1
            for node in data.get("nodes") or []:
                name = node.get("name") or ""
                path = f"{parent_path}/{name}" if parent_path else name
                if node.get("type") == "FOLDER":
                    queue.append((node["nodeId"], path))
                    continue
                if node.get("type") != "FILE":
                    continue
                files.append(
                    {
                        "path": path,
                        "name": name,
                        "node_type": node.get("type") or "",
                        "node_category": node.get("category") or "",
                        "extension": (node.get("extension") or "").lower(),
                        "workspace_id": node.get("workspaceId") or "",
                        "modified_time": node.get("modifiedTime") or "",
                        "created_time": node.get("createTime") or "",
                        "url": node.get("url") or "",
                        "node_id": node.get("nodeId") or "",
                    }
                )
            next_token = data.get("nextToken")
            if not next_token:
                break

    files.sort(key=lambda item: item["path"].lower())
    return {
        "workspace": {
            "name": workspace["name"],
            "workspace_id": workspace.get("workspaceId") or "",
            "root_node_id": workspace.get("rootNodeId") or "",
            "url": workspace.get("url") or "",
        },
        "counts": {
            "files": len(files),
            "folders_seen": folders_seen,
            "api_calls": api_calls,
        },
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-name")
    parser.add_argument("--workspace-id")
    parser.add_argument("--output-json")
    parser.add_argument("--progress-every", type=int, default=50)
    args = parser.parse_args()
    if not args.workspace_name and not args.workspace_id:
        raise SystemExit("Provide either --workspace-name or --workspace-id")

    cfg = load_config()
    token = fetch_access_token(cfg)
    workspaces = list_workspaces(cfg["DINGTALK_OPERATOR_ID"], token)
    if args.workspace_id:
        workspace = resolve_workspace_by_id(workspaces, args.workspace_id)
    else:
        workspace = resolve_workspace(workspaces, args.workspace_name)
    inventory = scan_workspace(
        workspace,
        cfg["DINGTALK_OPERATOR_ID"],
        token,
        progress_every=args.progress_every,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.output_json:
        output_path = pathlib.Path(args.output_json)
    else:
        safe_name = workspace["name"].replace("/", " ").strip()
        output_path = OUTPUT_DIR / f"{safe_name}-inventory.json"

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(inventory, handle, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "workspace": inventory["workspace"]["name"],
                "files": inventory["counts"]["files"],
                "folders_seen": inventory["counts"]["folders_seen"],
                "api_calls": inventory["counts"]["api_calls"],
                "output_json": str(output_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
