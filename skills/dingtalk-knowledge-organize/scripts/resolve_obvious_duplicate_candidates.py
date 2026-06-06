#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict


def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def write_rows(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_personal(path):
    return path.startswith("11. Personal/")


def is_archive_like(path):
    lowered = path.lower()
    return any(token in lowered for token in ["/archive", "副本", "backup", "备份", "reimbursed", "报销"])


def preferred_nonpersonal_bucket(path):
    if path.startswith("8. Projects/"):
        return 0
    if path.startswith("4. Management/"):
        return 1
    if path.startswith("6. Channels/"):
        return 2
    if path.startswith("3. Training/"):
        return 3
    if path.startswith("1. Onboarding/"):
        return 4
    return 10


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-path", required=True)
    args = parser.parse_args()

    fieldnames, rows = load_rows(args.csv_path)
    groups = defaultdict(list)
    for idx, row in enumerate(rows):
        gid = (row.get("duplicate_group") or "").strip()
        if gid:
            groups[gid].append((idx, row))

    updated = 0
    for gid, items in groups.items():
        personal = [(idx, row) for idx, row in items if is_personal(row["file_path"])]
        nonpersonal = [(idx, row) for idx, row in items if not is_personal(row["file_path"])]
        if not personal or not nonpersonal:
            continue

        # Keep the strongest non-personal path as the canonical retained copy.
        nonpersonal.sort(key=lambda x: (preferred_nonpersonal_bucket(x[1]["file_path"]), x[1]["file_path"]))

        for idx, row in personal:
            if row.get("needs_content_review") == "yes":
                continue
            row["proposed_action"] = "move_to_待归档"
            row["move_to"] = "待归档"
            row["notes"] = (row.get("notes") or "").strip()
            audit = f"自动归档重复副本：{gid}，保留非个人目录主件"
            row["notes"] = f"{row['notes']} | {audit}".strip(" |")
            updated += 1

    # Archive obvious archive-like duplicates even if they are not in Personal.
    for row in rows:
        if row.get("proposed_action") != "duplicate_candidate":
            continue
        if row.get("needs_content_review") == "yes":
            continue
        if is_archive_like(row["file_path"]):
            row["proposed_action"] = "move_to_待归档"
            row["move_to"] = "待归档"
            row["notes"] = ((row.get("notes") or "").strip() + " | 自动归档疑似归档/报销/副本路径").strip(" |")
            updated += 1

    write_rows(args.csv_path, fieldnames, rows)
    print({"updated_rows": updated, "csv_path": args.csv_path})


if __name__ == "__main__":
    main()
