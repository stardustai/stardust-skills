#!/usr/bin/env python3
import argparse
import csv
import os
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-path", required=True)
    args = parser.parse_args()

    fieldnames, rows = load_rows(args.csv_path)
    groups = defaultdict(list)
    for idx, row in enumerate(rows):
        gid = (row.get("duplicate_group") or "").strip()
        if gid and row.get("proposed_action") == "duplicate_candidate":
            groups[gid].append((idx, row))

    updated = 0
    for gid, items in groups.items():
        exts = [item["file_type"] for _, item in items]
        parents = {os.path.dirname(item["file_path"]) for _, item in items}
        if len(parents) == 1 and len(exts) == len(set(exts)) and len(exts) > 1:
            for _, row in items:
                row["proposed_action"] = "keep"
                row["notes"] = ((row.get("notes") or "").strip() + " | 同目录跨格式成套文件，降级为保留").strip(" |")
                updated += 1

    write_rows(args.csv_path, fieldnames, rows)
    print({"updated_rows": updated, "csv_path": args.csv_path})


if __name__ == "__main__":
    main()
