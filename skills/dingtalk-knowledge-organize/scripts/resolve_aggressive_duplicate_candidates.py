#!/usr/bin/env python3
import argparse
import csv
import os
import re
from collections import Counter, defaultdict


VARIANT_RE = re.compile(r"(\(\d+\)|副本|copy|backup|备份)", re.IGNORECASE)


def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def write_rows(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def top_level(path):
    return path.split("/", 1)[0] if "/" in path else "(root)"


def is_personal(path):
    return path.startswith("11. Personal/")


def has_variant_marker(path):
    basename = os.path.basename(path)
    return bool(VARIANT_RE.search(basename))


def parent_dir(path):
    return os.path.dirname(path)


def note(row, text):
    row["notes"] = ((row.get("notes") or "").strip() + " | " + text).strip(" |")


def mark_archive(row, reason):
    if row.get("needs_content_review") == "yes":
        return False
    row["proposed_action"] = "move_to_待归档"
    row["move_to"] = "待归档"
    note(row, reason)
    return True


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
        paths = [row["file_path"] for _, row in items]
        counts = Counter(paths)

        # Exact same path repeated: archive all but first.
        if any(v > 1 for v in counts.values()):
            seen = set()
            for _, row in items:
                path = row["file_path"]
                if path not in seen:
                    seen.add(path)
                    continue
                if mark_archive(row, f"自动归档完全重复节点：{gid}"):
                    updated += 1
            continue

        # Personal vs business duplicate: archive personal copies.
        has_personal = any(is_personal(path) for path in paths)
        has_nonpersonal = any(not is_personal(path) for path in paths)
        if has_personal and has_nonpersonal:
            for _, row in items:
                if is_personal(row["file_path"]):
                    if mark_archive(row, f"自动归档个人目录重复副本：{gid}"):
                        updated += 1
            continue

        # Root vs non-root duplicate: archive root copy.
        has_root = any(top_level(path) == "(root)" for path in paths)
        has_nonroot = any(top_level(path) != "(root)" for path in paths)
        if has_root and has_nonroot:
            for _, row in items:
                if top_level(row["file_path"]) == "(root)":
                    if mark_archive(row, f"自动归档根目录重复副本：{gid}"):
                        updated += 1
            continue

        # Same parent folder with variant markers: archive marked variants.
        parents = {parent_dir(path) for path in paths}
        if len(parents) == 1:
            marked = [row for _, row in items if has_variant_marker(row["file_path"])]
            if marked:
                for row in marked:
                    if mark_archive(row, f"自动归档同目录版本副本：{gid}"):
                        updated += 1
                continue

        # Same top-level and same extension with variant markers: archive marked variants.
        tops = {top_level(path) for path in paths}
        exts = {row["file_type"] for _, row in items}
        if len(tops) == 1 and len(exts) == 1:
            marked = [row for _, row in items if has_variant_marker(row["file_path"])]
            for row in marked:
                if mark_archive(row, f"自动归档同类版本副本：{gid}"):
                    updated += 1

    write_rows(args.csv_path, fieldnames, rows)
    print({"updated_rows": updated, "csv_path": args.csv_path})


if __name__ == "__main__":
    main()
