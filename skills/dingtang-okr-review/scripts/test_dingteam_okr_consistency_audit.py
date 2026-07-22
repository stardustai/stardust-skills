#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).resolve().parent / "dingteam_okr_consistency_audit.py"
SPEC = importlib.util.spec_from_file_location("dingteam_okr_consistency_under_test", PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


class DingteamOkrConsistencyAuditTest(unittest.TestCase):
    def test_normalized_label_removes_assessment_prefix(self) -> None:
        self.assertEqual(audit.normalized_label("领导力：战略能力\n说明"), "战略能力\n说明")
        self.assertEqual(audit.normalized_label("文化:I Can I Up"), "I Can I Up")

    def test_matching_label_uses_manifest_dimensions(self) -> None:
        dimensions = {"战略能力", "团队赋能能力"}
        self.assertEqual(
            audit.matching_label("领导力：团队赋能能力\n证据", dimensions),
            "团队赋能能力",
        )
        self.assertEqual(audit.matching_label("业务KR", dimensions), "")

    def test_same_value_accepts_sheet_rounding_only(self) -> None:
        self.assertTrue(audit.same_value("81.67", 81.669))
        self.assertFalse(audit.same_value("81.67", 81.60))

    def test_complete_evaluators_ignores_unfinished_rows(self) -> None:
        kr = {
            "roleUsers": [
                {
                    "users": [
                        {"name": "Derek", "status": "complete"},
                        {"name": "Mina", "status": "wait"},
                    ]
                }
            ]
        }
        self.assertEqual(
            [item["name"] for item in audit.complete_evaluators(kr)], ["Derek"]
        )


if __name__ == "__main__":
    unittest.main()
