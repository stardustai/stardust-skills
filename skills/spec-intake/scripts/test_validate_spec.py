#!/usr/bin/env python3
"""Focused tests for the spec-intake validator."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = SKILL_DIR / "scripts" / "validate_spec.py"
EXAMPLE_SPEC = SKILL_DIR / "examples" / "insurance-broker-proposal.spec.json"


def _load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("validate_spec", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _load_example() -> dict[str, Any]:
    with EXAMPLE_SPEC.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_temp(spec_data: dict[str, Any]) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "spec.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(spec_data, f, ensure_ascii=False, indent=2)
        return validator.validate(path, SKILL_DIR / "references" / "spec-schema.json")


class ValidateSpecUiWireframeTests(unittest.TestCase):
    def test_business_handoff_accepts_chinese_exit_summary(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["current_stage"] = "business_feasibility"
        spec_data["stage_gate"]["readiness_label"] = "business_ready"
        spec_data["stage_gate"]["decision"] = "handoff_to_product"
        spec_data["stage_gate"]["stage_exit_check"] = {
            "status": "confirmed",
            "exit_summary": (
                "已确认产品形态、主买方、验收方式、当前替代方案、最小可付费产物、"
                "证据等级、PMF 四因子、机会优先级、竞品调研和禁止进入工程的事项。"
            ),
            "confirmation_question": "是否确认结束业务验证并交给产品收敛形态？",
            "confirmed_by": "业务 owner",
            "confirmed_at": "2026-07-10",
            "next_stage": "product_shape",
        }
        spec_data["ui_requirements"]["wireframe_status"] = "needed"
        spec_data["ui_requirements"]["wireframe_artifacts"] = []

        errors = _validate_temp(spec_data)

        self.assertFalse(
            any("handoff_to_product requires structured business handoff fields" in error for error in errors),
            errors,
        )

    def test_business_handoff_does_not_require_svg_wireframe(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["current_stage"] = "business_feasibility"
        spec_data["stage_gate"]["readiness_label"] = "business_ready"
        spec_data["stage_gate"]["decision"] = "handoff_to_product"
        spec_data["stage_gate"]["stage_exit_check"]["next_stage"] = "product_shape"
        spec_data["ui_requirements"]["wireframe_status"] = "needed"
        spec_data["ui_requirements"]["wireframe_artifacts"] = []

        errors = _validate_temp(spec_data)

        self.assertNotIn(
            "ui_requirements.wireframe_artifacts must include a produced .svg wireframe for UI specs",
            errors,
        )

    def test_product_ready_requires_reviewed_svg_wireframe(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["readiness_label"] = "product_ready"
        spec_data["ui_requirements"]["wireframe_status"] = "needed"
        spec_data["ui_requirements"]["wireframe_artifacts"] = []

        errors = _validate_temp(spec_data)

        self.assertIn(
            "ui_requirements.wireframe_artifacts must include a produced .svg wireframe for UI specs",
            errors,
        )
        self.assertIn(
            "product_ready requires ui_requirements.wireframe_status=reviewed for UI specs",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
