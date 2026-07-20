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


class ValidateBusinessSuccessScenarioTests(unittest.TestCase):
    def test_business_ready_allows_scenarios_to_remain_empty(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["readiness_label"] = "business_ready"
        spec_data["business_success_scenarios"] = []
        spec_data["validation_plan"]["scenario_coverage"] = []

        errors = _validate_temp(spec_data)

        self.assertFalse(any("business_success_scenarios" in error for error in errors), errors)

    def test_product_ready_requires_business_success_scenarios(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["readiness_label"] = "product_ready"
        spec_data.pop("business_success_scenarios", None)

        errors = _validate_temp(spec_data)

        self.assertIn(
            "product_ready requires business_success_scenarios",
            errors,
        )

    def test_product_ready_requires_confirmed_critical_scenarios(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["readiness_label"] = "product_ready"
        spec_data["business_success_scenarios"] = [
            {
                "scenario_id": "BIZ-E2E-001",
                "title": "超过 20% 的折扣申请完成审批后允许发送报价",
                "scope_status": "in_scope",
                "business_owner": "销售运营负责人",
                "priority": "critical",
                "user_role": "销售",
                "business_goal": "完成合规折扣审批并向客户发送报价",
                "preconditions": ["销售拥有报价权限"],
                "trigger": "销售提交折扣超过 20% 的报价",
                "workflow_step_refs": ["WF-001", "WF-002"],
                "expected_business_outcome": "合法报价经区域经理批准后可以发给客户",
                "expected_final_state": ["报价状态为 approved", "发送权限为 enabled"],
                "success_signals": ["生成唯一审批记录", "报价发送权限已启用"],
                "business_invariants": ["未批准的报价不能发送"],
                "unacceptable_outcomes": ["未审批报价被发送给客户"],
                "alternate_paths": ["经理拒绝后销售可以修改并重新提交"],
                "exception_paths": [
                    {
                        "condition": "销售重复提交同一报价",
                        "expected_business_response": "复用现有审批并提示正在审批",
                        "expected_final_state": ["只存在一个有效审批单"],
                    }
                ],
                "recovery_expectations": ["审批服务超时时保持报价不可发送"],
                "confirmation": {
                    "status": "pending",
                    "confirmer_role": "business_owner",
                    "confirmed_by": None,
                    "confirmed_at": None,
                    "confirmed_version": None,
                },
            }
        ]

        errors = _validate_temp(spec_data)

        self.assertIn(
            "product_ready requires confirmed critical business success scenario: BIZ-E2E-001",
            errors,
        )

    def test_engineering_ready_requires_coverage_for_each_critical_scenario(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["readiness_label"] = "engineering_ready"
        spec_data["business_success_scenarios"] = [
            {
                "scenario_id": "BIZ-E2E-001",
                "title": "业务成功流程",
                "scope_status": "in_scope",
                "business_owner": "业务 owner",
                "priority": "critical",
                "user_role": "业务用户",
                "business_goal": "完成主业务流程",
                "preconditions": ["前置条件已满足"],
                "trigger": "用户发起主流程",
                "workflow_step_refs": ["WF-001"],
                "expected_business_outcome": "业务目标达成",
                "expected_final_state": ["业务对象进入完成状态"],
                "success_signals": ["业务对象状态可被查询为完成"],
                "business_invariants": ["不得产生重复业务对象"],
                "unacceptable_outcomes": ["界面显示成功但业务对象未完成"],
                "alternate_paths": [],
                "exception_paths": [],
                "recovery_expectations": ["失败后保持可重试状态"],
                "confirmation": {
                    "status": "confirmed",
                    "confirmer_role": "business_owner",
                    "confirmed_by": "业务 owner",
                    "confirmed_at": "2026-07-20",
                    "confirmed_version": "1.5",
                },
            }
        ]
        spec_data["validation_plan"].pop("scenario_coverage", None)

        errors = _validate_temp(spec_data)

        self.assertIn(
            "engineering_ready requires validation_plan.scenario_coverage for critical scenario: BIZ-E2E-001",
            errors,
        )

    def test_duplicate_scenario_id_and_unknown_workflow_step_are_rejected(self) -> None:
        spec_data = _load_example()
        duplicate = json.loads(json.dumps(spec_data["business_success_scenarios"][0]))
        duplicate["workflow_step_refs"] = ["WF-UNKNOWN"]
        spec_data["business_success_scenarios"].append(duplicate)

        errors = _validate_temp(spec_data)

        self.assertIn(
            "business_success_scenarios has duplicate scenario_id: BIZ-E2E-001",
            errors,
        )
        self.assertIn(
            "business_success_scenarios[1].workflow_step_refs references unknown workflow step: WF-UNKNOWN",
            errors,
        )

    def test_unknown_scenario_coverage_reference_is_rejected(self) -> None:
        spec_data = _load_example()
        spec_data["validation_plan"]["scenario_coverage"][0]["scenario_id"] = "BIZ-E2E-UNKNOWN"

        errors = _validate_temp(spec_data)

        self.assertIn(
            "validation_plan.scenario_coverage[0].scenario_id references unknown business scenario: BIZ-E2E-UNKNOWN",
            errors,
        )

    def test_scenario_coverage_cannot_rewrite_business_outcome(self) -> None:
        spec_data = _load_example()
        spec_data["validation_plan"]["scenario_coverage"][0]["expected_business_outcome"] = "QA 改写后的结果"

        errors = _validate_temp(spec_data)

        self.assertIn(
            "unexpected key: $.validation_plan.scenario_coverage[0].expected_business_outcome",
            errors,
        )

    def test_engineering_ready_requires_approved_qa_and_automation_plan(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["readiness_label"] = "engineering_ready"
        coverage = spec_data["validation_plan"]["scenario_coverage"][0]
        coverage["qa_status"] = "drafted"
        coverage["automation_requirement"] = "required"
        coverage["automation_plan_status"] = "not_started"

        errors = _validate_temp(spec_data)

        self.assertIn(
            "engineering_ready requires approved QA coverage for critical scenario: BIZ-E2E-001",
            errors,
        )
        self.assertIn(
            "engineering_ready requires an automation plan for critical scenario: BIZ-E2E-001",
            errors,
        )

    def test_placeholder_business_confirmation_is_rejected(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["readiness_label"] = "engineering_ready"
        scenario = spec_data["business_success_scenarios"][0]
        scenario["business_owner"] = "待确认"
        scenario["confirmation"] = {
            "status": "confirmed",
            "confirmer_role": "business_owner",
            "confirmed_by": "待确认",
            "confirmed_at": "待确认",
            "confirmed_version": "待确认",
        }

        errors = _validate_temp(spec_data)

        self.assertIn(
            "engineering_ready requires a valid ISO confirmation date for business success scenario: BIZ-E2E-001",
            errors,
        )
        self.assertIn(
            "engineering_ready requires confirmation version 1.5 for business success scenario: BIZ-E2E-001",
            errors,
        )

    def test_engineering_ready_rejects_incoherent_stage_gate(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["current_stage"] = "business_feasibility"
        spec_data["stage_gate"]["readiness_label"] = "engineering_ready"
        spec_data["stage_gate"]["decision"] = "ready_for_engineering"
        spec_data["stage_gate"]["stage_exit_check"]["next_stage"] = "product_shape"

        errors = _validate_temp(spec_data)

        self.assertIn(
            "engineering_ready requires stage_gate.current_stage=engineering_delivery",
            errors,
        )
        self.assertIn(
            "ready_for_engineering requires stage_gate.stage_exit_check.next_stage=engineering_delivery",
            errors,
        )

    def test_ai_agent_cannot_confirm_business_success_scenario(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["readiness_label"] = "engineering_ready"
        spec_data["business_success_scenarios"][0]["confirmation"]["confirmed_by"] = "AI agent"

        errors = _validate_temp(spec_data)

        self.assertIn(
            "engineering_ready requires confirmed_by to match business_owner for business success scenario: BIZ-E2E-001",
            errors,
        )


class ValidateDeliveryRiskProfileTests(unittest.TestCase):
    def test_product_ready_requires_confirmed_delivery_risk_profile(self) -> None:
        spec_data = _load_example()
        spec_data["stage_gate"]["current_stage"] = "product_shape"
        spec_data["stage_gate"]["readiness_label"] = "product_ready"
        spec_data.pop("delivery_risk_profile", None)

        errors = _validate_temp(spec_data)

        self.assertIn("product_ready requires delivery_risk_profile", errors)

    def test_risk_tier_cannot_be_lower_than_dimension_floor(self) -> None:
        spec_data = _load_example()
        spec_data["delivery_risk_profile"] = {
            "risk_tier": "R1",
            "rationale": "错误地把受限数据项目评为低风险",
            "dimensions": {
                "user_exposure": "internal_single_team",
                "data_sensitivity": "restricted",
                "write_impact": "read_only",
                "integrations_and_permissions": "approved_internal",
                "reversibility": "easy",
                "business_impact": "low",
            },
            "required_controls": ["restricted data review"],
            "assessment": {
                "status": "confirmed",
                "assessed_by": "spec agent",
                "confirmed_by": "PMF owner",
                "confirmed_at": "2026-07-20",
            },
        }

        errors = _validate_temp(spec_data)

        self.assertIn(
            "delivery_risk_profile.risk_tier R1 is below required floor R3",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
