#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).resolve().parent / "dingteam_okr_audit.py"
SPEC = importlib.util.spec_from_file_location("dingteam_okr_audit_under_test", PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


def row(objective_id: str, owner: str, name: str, score: object) -> dict:
    return {
        "objectiveId": objective_id,
        "objectiveName": name,
        "score": score,
        "objectiveProgress": 100,
        "userInfo": {"id": owner.lower(), "name": owner},
    }


class DingteamOkrAuditTest(unittest.TestCase):
    def test_archive_items_accepts_saved_snapshot_and_cli_wrapper(self) -> None:
        rows = [row("o1", "Mina", "领导力考核", 80)]
        self.assertEqual(audit.archive_items({"archive": {"list": rows}}), rows)
        self.assertEqual(audit.archive_items({"ok": True, "data": {"list": rows}}), rows)

    def test_compare_reports_added_removed_and_changed(self) -> None:
        before = [row("o1", "Mina", "领导力考核", 70), row("o2", "ET", "文化", 80)]
        after = [row("o1", "Mina", "领导力考核", 75), row("o3", "Roy", "文化", 90)]
        result = audit.compare_archives(before, after)
        self.assertEqual([item["objectiveId"] for item in result["added"]], ["o3"])
        self.assertEqual([item["objectiveId"] for item in result["removed"]], ["o2"])
        self.assertEqual([item["objectiveId"] for item in result["changed"]], ["o1"])
        self.assertTrue(result["hasDifferences"])

    def test_analyze_distinguishes_null_zero_and_duplicates(self) -> None:
        rows = [
            row("o1", "ET", "领导力考核", None),
            row("o2", "ET", "领导力补充考核", 0),
            row("o3", "Mina", "文化价值观考核", 80),
        ]
        result = audit.analyze_archive(
            rows, {"leadership": "领导力", "culture": "文化价值观"}
        )
        self.assertEqual(len(result["nullScores"]), 1)
        self.assertEqual(len(result["zeroScores"]), 1)
        self.assertEqual(len(result["duplicates"]), 1)
        self.assertEqual(result["duplicates"][0]["category"], "leadership")

    def test_parse_categories_rejects_missing_separator(self) -> None:
        with self.assertRaisesRegex(ValueError, "NAME=TEXT"):
            audit.parse_categories(["leadership"])


if __name__ == "__main__":
    unittest.main()
