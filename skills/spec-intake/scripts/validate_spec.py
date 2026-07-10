#!/usr/bin/env python3
"""Validate a spec-intake JSON file without third-party dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BOUNDARY_KEYS = [
    "memory_layer",
    "agent_or_recipe_layer",
    "product_ui_layer",
    "external_business_systems",
    "human_or_compliance_review",
    "explicitly_not_owned",
]

EVIDENCE_KEYS = [
    "must_trace",
    "source_granularity",
    "unknown_or_uncertain_handling",
]

DATA_GOVERNANCE_KEYS = [
    "sensitivity",
    "permission_model",
    "versioning",
    "retention",
    "audit_log",
]

COMMERCIAL_CONTEXT_KEYS = [
    "customer_segment",
    "pack_level",
    "l2_scenario",
    "l3_aggregation_logic",
    "target_buyer",
    "deliverable",
    "why_customer_will_pay",
    "market_or_customer_pool",
    "design_partners",
    "poc_path",
    "cooperation_model",
    "pricing_hypothesis",
    "biggest_delivery_risk",
    "next_sales_action",
    "pmf_confidence",
]

PMF_VALIDATION_KEYS = [
    "use_case_id",
    "source_entry",
    "current_state",
    "target_icp",
    "workflow",
    "pain_evidence",
    "current_alternative",
    "buyer_language",
    "competitive_gap",
    "decision_chain",
    "paid_signal",
    "four_factor_scores",
    "overall_decision",
    "next_action",
    "owner",
    "evidence_links",
    "last_reviewed",
    "poc_entry_criteria",
]

PMF_SCORE_KEYS = [
    "customer_willingness",
    "market_clarity",
    "technical_value",
    "gtm_repeatability",
]

POC_ENTRY_CRITERIA_KEYS = [
    "customer_evidence",
    "paid_signal",
    "data_available",
    "baseline_defined",
    "acceptance_method",
    "timebox_and_resource_cap",
]

HANDOFF_OPTION_KEYS = [
    "current_gate",
    "available_next_actions",
    "selected_next_action",
    "handoff_target",
    "handoff_notes",
]

PRIORITY_DECISION_KEYS = [
    "candidate_rank",
    "recommendation",
    "business_value_score",
    "commercial_signal_clarity_score",
    "product_engineering_effort_score",
    "opportunity_priority_score",
    "formula_name",
    "formula",
    "scope_expansion_risk",
    "scope_reduction_recommendation",
    "reason",
    "missing_evidence",
    "decision_owner",
]

DOMAIN_PACK_KEYS = [
    "applicable",
    "pack_definition",
    "target_industry_or_scene",
    "pack_goal",
    "commercial_or_delivery_unit",
    "domain_workflow",
    "memory_assets",
    "recipe_assets",
    "connector_assets",
    "interface_configuration",
    "permission_scope",
    "non_memory_boundaries",
    "workspace_instance_policy",
    "first_recipe",
    "iteration_loop",
    "self_learning_policy",
    "versioning_policy",
    "evaluation_assets",
    "marketplace_or_delivery",
    "workspace_design",
]

WORKSPACE_INSTANCE_KEYS = [
    "workspace_created_by",
    "workspace_lifecycle",
    "room_granularity",
    "artifact_types",
    "local_changes_policy",
    "master_pack_update_policy",
]

FIRST_RECIPE_KEYS = [
    "name",
    "goal",
    "input",
    "output",
    "execution_logic",
    "constraints",
    "required_evidence",
    "human_review",
    "owner",
]

VERSIONING_KEYS = [
    "domain_pack_versioned",
    "recipe_versioned",
    "workspace_versioned",
    "memory_backup_or_rollback",
    "release_policy",
    "upgrade_policy",
    "rollback_policy",
]

EVALUATION_ASSET_KEYS = [
    "golden_tasks",
    "rubrics",
    "failure_cases",
    "acceptance_checklist",
    "regression_set",
]

WORKFLOW_STEP_KEYS = [
    "step_id",
    "phase",
    "actor",
    "input",
    "action",
    "output",
    "human_review_required",
    "failure_handling",
]


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _missing_keys(obj: dict[str, Any], keys: list[str], prefix: str) -> list[str]:
    return [f"{prefix}.{key}" for key in keys if key not in obj]


def _is_unknown_or_empty(value: Any) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    if value == "unknown":
        return True
    if value == "not_applicable":
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


def _svg_wireframe_errors(ui_requirements: dict[str, Any], spec_path: Path) -> list[str]:
    artifacts = ui_requirements.get("wireframe_artifacts")
    if not isinstance(artifacts, list):
        return ["ui_requirements.wireframe_artifacts must be an array"]

    svg_artifacts = [item for item in artifacts if isinstance(item, str) and item.lower().endswith(".svg")]
    if not svg_artifacts:
        return ["ui_requirements.wireframe_artifacts must include a produced .svg wireframe for UI specs"]

    errors: list[str] = []
    for artifact in svg_artifacts:
        if artifact.startswith(("http://", "https://")):
            continue
        artifact_path = Path(artifact)
        if not artifact_path.is_absolute():
            artifact_path = spec_path.parent / artifact_path
        if not artifact_path.exists():
            errors.append(f"ui_requirements.wireframe_artifacts SVG does not exist: {artifact}")
    return errors


def _commercial_blockers(spec: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    commercial = spec.get("commercial_context")
    if not isinstance(commercial, dict):
        return ["commercial_context"]

    for key in [
        "customer_segment",
        "pack_level",
        "target_buyer",
        "deliverable",
        "why_customer_will_pay",
        "poc_path",
        "biggest_delivery_risk",
        "next_sales_action",
        "pmf_confidence",
    ]:
        if _is_unknown_or_empty(commercial.get(key)):
            blockers.append(f"commercial_context.{key}")
    return blockers


def _score_out_of_range(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (value < 1 or value > 5)
    )


def _pmf_blockers(spec: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    pmf = spec.get("pmf_validation")
    if not isinstance(pmf, dict):
        return ["pmf_validation"]

    for key in [
        "source_entry",
        "current_state",
        "target_icp",
        "workflow",
        "pain_evidence",
        "current_alternative",
        "buyer_language",
        "decision_chain",
        "paid_signal",
        "overall_decision",
        "next_action",
        "owner",
        "evidence_links",
    ]:
        if _is_unknown_or_empty(pmf.get(key)):
            blockers.append(f"pmf_validation.{key}")

    scores = pmf.get("four_factor_scores")
    if not isinstance(scores, dict):
        blockers.append("pmf_validation.four_factor_scores")
    else:
        for key in PMF_SCORE_KEYS:
            score_item = scores.get(key)
            if not isinstance(score_item, dict):
                blockers.append(f"pmf_validation.four_factor_scores.{key}")
                continue
            score = score_item.get("score")
            if _is_unknown_or_empty(score):
                blockers.append(f"pmf_validation.four_factor_scores.{key}.score")
            elif _score_out_of_range(score):
                blockers.append(f"pmf_validation.four_factor_scores.{key}.score")
            if _is_unknown_or_empty(score_item.get("evidence")):
                blockers.append(f"pmf_validation.four_factor_scores.{key}.evidence")

    return blockers


def _priority_blockers(spec: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    priority = spec.get("priority_decision")
    if not isinstance(priority, dict):
        return ["priority_decision"]

    expected_formula = "机会优先级指数 = 商业价值 * 商业信号清晰度 / 产研投入量"
    if priority.get("formula_name") != "机会优先级指数":
        blockers.append("priority_decision.formula_name")
    if priority.get("formula") != expected_formula:
        blockers.append("priority_decision.formula")

    for key in [
        "business_value_score",
        "commercial_signal_clarity_score",
        "product_engineering_effort_score",
        "opportunity_priority_score",
        "scope_expansion_risk",
        "reason",
        "decision_owner",
    ]:
        if _is_unknown_or_empty(priority.get(key)):
            blockers.append(f"priority_decision.{key}")

    for key in [
        "business_value_score",
        "commercial_signal_clarity_score",
        "product_engineering_effort_score",
    ]:
        if _score_out_of_range(priority.get(key)):
            blockers.append(f"priority_decision.{key}")

    effort = priority.get("product_engineering_effort_score")
    if isinstance(effort, (int, float)) and not isinstance(effort, bool) and effort <= 0:
        blockers.append("priority_decision.product_engineering_effort_score")

    if priority.get("scope_expansion_risk") == "high" and _is_unknown_or_empty(
        priority.get("scope_reduction_recommendation")
    ):
        blockers.append("priority_decision.scope_reduction_recommendation")

    return blockers


def _product_shape_blockers(spec: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    product_context = spec.get("product_context")
    if not isinstance(product_context, dict):
        blockers.append("product_context")
    elif _is_unknown_or_empty(product_context.get("build_target")):
        blockers.append("product_context.build_target")

    if _is_unknown_or_empty(spec.get("spec_type")):
        blockers.append("spec_type")

    business_context = spec.get("business_context")
    if isinstance(business_context, dict):
        user_scenario = business_context.get("user_scenario")
        target_outcome = business_context.get("target_outcome")
        if not isinstance(user_scenario, dict) or _is_unknown_or_empty(user_scenario.get("user_role")):
            blockers.append("business_context.user_scenario.user_role")
        if not isinstance(target_outcome, dict) or _is_unknown_or_empty(target_outcome.get("user_success_result")):
            blockers.append("business_context.target_outcome.user_success_result")
    else:
        blockers.append("business_context")

    business_objects = spec.get("business_objects")
    if isinstance(business_objects, dict):
        if _is_unknown_or_empty(business_objects.get("durable_assets")) and _is_unknown_or_empty(
            business_objects.get("generated_artifacts")
        ):
            blockers.append("business_objects")
    else:
        blockers.append("business_objects")

    scope = spec.get("scope")
    if isinstance(scope, dict):
        for key in ["in_scope", "out_of_scope", "delivery_boundary"]:
            if _is_unknown_or_empty(scope.get(key)):
                blockers.append(f"scope.{key}")
    else:
        blockers.append("scope")

    ui_requirements = spec.get("ui_requirements")
    if isinstance(ui_requirements, dict):
        if ui_requirements.get("has_ui") is None or ui_requirements.get("wireframe_required") is None:
            blockers.append("ui_requirements")
    else:
        blockers.append("ui_requirements")

    domain_pack = spec.get("domain_pack_context")
    if (
        isinstance(product_context, dict)
        and product_context.get("build_target") == "domain_pack"
        or spec.get("spec_type") == "domain_pack"
    ):
        if isinstance(domain_pack, dict):
            for key in ["pack_definition", "commercial_or_delivery_unit", "target_industry_or_scene", "pack_goal"]:
                if _is_unknown_or_empty(domain_pack.get(key)):
                    blockers.append(f"domain_pack_context.{key}")
        else:
            blockers.append("domain_pack_context")

    return blockers


def _type_matches(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "null":
        return value is None
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    return True


def _schema_type_errors(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    expected = schema.get("type")
    if expected is None:
        return []
    if isinstance(expected, str):
        expected_types = [expected]
    else:
        expected_types = list(expected)
    if not any(_type_matches(value, expected_type) for expected_type in expected_types):
        return [f"{path} must be type {'|'.join(expected_types)}"]
    return []


def _validate_schema_subset(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    errors.extend(_schema_type_errors(value, schema, path))
    if errors:
        return errors

    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(map(str, schema["enum"]))
        errors.append(f"{path} must be one of: {allowed}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"missing required key: {path}.{key}")

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            for key in extra:
                errors.append(f"unexpected key: {path}.{key}")

        for key, child_schema in properties.items():
            if key in value and isinstance(child_schema, dict):
                errors.extend(_validate_schema_subset(value[key], child_schema, f"{path}.{key}"))

    if isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_validate_schema_subset(item, item_schema, f"{path}[{index}]"))

    return errors


def validate(spec_path: Path, schema_path: Path) -> list[str]:
    schema = _load_json(schema_path)
    spec = _load_json(spec_path)
    errors = _validate_schema_subset(spec, schema)

    if not isinstance(spec, dict):
        return errors or ["spec must be a JSON object"]

    workflow = spec.get("workflow")
    if isinstance(workflow, dict):
        steps = workflow.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append("workflow.steps must be a non-empty array")
        elif any(not isinstance(step, dict) for step in steps):
            errors.append("workflow.steps must contain only objects")
        else:
            for index, step in enumerate(steps):
                errors.extend(_missing_keys(step, WORKFLOW_STEP_KEYS, f"workflow.steps[{index}]"))
                if not isinstance(step.get("human_review_required"), bool):
                    errors.append(f"workflow.steps[{index}].human_review_required must be boolean")
    else:
        errors.append("workflow must be an object")

    boundaries = spec.get("capability_boundaries")
    if isinstance(boundaries, dict):
        errors.extend(_missing_keys(boundaries, BOUNDARY_KEYS, "capability_boundaries"))
    else:
        errors.append("capability_boundaries must be an object")

    evidence = spec.get("evidence_requirements")
    if isinstance(evidence, dict):
        errors.extend(_missing_keys(evidence, EVIDENCE_KEYS, "evidence_requirements"))
    else:
        errors.append("evidence_requirements must be an object")

    governance = spec.get("data_governance")
    if isinstance(governance, dict):
        errors.extend(_missing_keys(governance, DATA_GOVERNANCE_KEYS, "data_governance"))
    else:
        errors.append("data_governance must be an object")

    commercial = spec.get("commercial_context")
    if isinstance(commercial, dict):
        errors.extend(_missing_keys(commercial, COMMERCIAL_CONTEXT_KEYS, "commercial_context"))
    else:
        errors.append("commercial_context must be an object")

    pmf_validation = spec.get("pmf_validation")
    if isinstance(pmf_validation, dict):
        errors.extend(_missing_keys(pmf_validation, PMF_VALIDATION_KEYS, "pmf_validation"))
        scores = pmf_validation.get("four_factor_scores")
        if isinstance(scores, dict):
            errors.extend(_missing_keys(scores, PMF_SCORE_KEYS, "pmf_validation.four_factor_scores"))
            for key in PMF_SCORE_KEYS:
                value = scores.get(key)
                if isinstance(value, dict):
                    errors.extend(
                        _missing_keys(value, ["score", "evidence", "notes"], f"pmf_validation.four_factor_scores.{key}")
                    )
                elif key in scores:
                    errors.append(f"pmf_validation.four_factor_scores.{key} must be an object")
        elif "four_factor_scores" in pmf_validation:
            errors.append("pmf_validation.four_factor_scores must be an object")

        poc_entry = pmf_validation.get("poc_entry_criteria")
        if isinstance(poc_entry, dict):
            errors.extend(_missing_keys(poc_entry, POC_ENTRY_CRITERIA_KEYS, "pmf_validation.poc_entry_criteria"))
        elif "poc_entry_criteria" in pmf_validation:
            errors.append("pmf_validation.poc_entry_criteria must be an object")
    else:
        errors.append("pmf_validation must be an object")

    handoff_options = spec.get("handoff_options")
    if isinstance(handoff_options, dict):
        errors.extend(_missing_keys(handoff_options, HANDOFF_OPTION_KEYS, "handoff_options"))
    else:
        errors.append("handoff_options must be an object")

    priority_decision = spec.get("priority_decision")
    if isinstance(priority_decision, dict):
        errors.extend(_missing_keys(priority_decision, PRIORITY_DECISION_KEYS, "priority_decision"))
    else:
        errors.append("priority_decision must be an object")

    domain_pack = spec.get("domain_pack_context")
    if isinstance(domain_pack, dict):
        errors.extend(_missing_keys(domain_pack, DOMAIN_PACK_KEYS, "domain_pack_context"))
        if domain_pack.get("applicable") is True or spec.get("spec_type") == "domain_pack":
            nested_checks = [
                ("workspace_instance_policy", WORKSPACE_INSTANCE_KEYS),
                ("first_recipe", FIRST_RECIPE_KEYS),
                ("versioning_policy", VERSIONING_KEYS),
                ("evaluation_assets", EVALUATION_ASSET_KEYS),
            ]
            for key, required_keys in nested_checks:
                value = domain_pack.get(key)
                if isinstance(value, dict):
                    errors.extend(_missing_keys(value, required_keys, f"domain_pack_context.{key}"))
                else:
                    errors.append(f"domain_pack_context.{key} must be an object")
    else:
        errors.append("domain_pack_context must be an object")

    missing_fields = spec.get("missing_fields")
    if missing_fields is not None:
        if not isinstance(missing_fields, list):
            errors.append("missing_fields must be an array")
        else:
            for index, item in enumerate(missing_fields):
                if not isinstance(item, dict):
                    errors.append(f"missing_fields[{index}] must be an object")
                    continue
                errors.extend(_missing_keys(item, ["field", "status", "note"], f"missing_fields[{index}]"))

    ui_requirements = spec.get("ui_requirements")
    ui_needs_wireframe = False
    if isinstance(ui_requirements, dict):
        ui_needs_wireframe = (
            ui_requirements.get("has_ui") is True
            and ui_requirements.get("wireframe_required") is True
        )
        if ui_needs_wireframe:
            errors.extend(_svg_wireframe_errors(ui_requirements, spec_path))
    else:
        errors.append("ui_requirements must be an object")

    readiness = spec.get("readiness_label")
    if readiness == "business_ready":
        blockers = _commercial_blockers(spec) + _pmf_blockers(spec) + _priority_blockers(spec)
        if missing_fields:
            missing_business_fields = [
                str(item.get("field"))
                for item in missing_fields
                if isinstance(item, dict)
                and item.get("field") is not None
                and str(item.get("field", "")).startswith(
                    ("commercial_context.", "pmf_validation.", "priority_decision.")
                )
            ]
            blockers.extend(missing_business_fields)
        if blockers:
            errors.append("business_ready is invalid while business validation fields are unknown: " + ", ".join(blockers))

    if readiness == "product_ready":
        blockers = _commercial_blockers(spec) + _pmf_blockers(spec) + _priority_blockers(spec) + _product_shape_blockers(spec)
        if missing_fields:
            missing_product_fields = [
                str(item.get("field"))
                for item in missing_fields
                if isinstance(item, dict)
                and item.get("field") is not None
                and str(item.get("field", "")).startswith(
                    (
                        "commercial_context.",
                        "pmf_validation.",
                        "priority_decision.",
                        "product_context.",
                        "business_context.",
                        "business_objects.",
                        "scope.",
                        "domain_pack_context.",
                        "ui_requirements.",
                    )
                )
            ]
            blockers.extend(missing_product_fields)
        if blockers:
            errors.append("product_ready is invalid while product-shape fields are unknown: " + ", ".join(blockers))

    if readiness == "engineering_ready":
        blockers = _commercial_blockers(spec) + _pmf_blockers(spec) + _priority_blockers(spec) + _product_shape_blockers(spec)
        product_context = spec.get("product_context", {})
        if isinstance(product_context, dict):
            if product_context.get("build_target") in (None, "", "unknown"):
                blockers.append("product_context.build_target")
        owners = spec.get("owners", {})
        if isinstance(owners, dict):
            for key in ["business_owner", "product_owner", "engineering_owner", "qa_owner", "devops_owner"]:
                if owners.get(key) in (None, "", "unknown"):
                    blockers.append(f"owners.{key}")
        if isinstance(domain_pack, dict) and (
            domain_pack.get("applicable") is True
            or spec.get("spec_type") == "domain_pack"
            or (isinstance(product_context, dict) and product_context.get("build_target") == "domain_pack")
        ):
            required_domain_values = [
                "pack_definition",
                "target_industry_or_scene",
                "pack_goal",
                "commercial_or_delivery_unit",
                "domain_workflow",
                "memory_assets",
                "recipe_assets",
                "non_memory_boundaries",
                "iteration_loop",
                "self_learning_policy",
            ]
            for key in required_domain_values:
                if _is_unknown_or_empty(domain_pack.get(key)):
                    blockers.append(f"domain_pack_context.{key}")

            for nested_key, nested_required in [
                ("workspace_instance_policy", WORKSPACE_INSTANCE_KEYS),
                ("first_recipe", FIRST_RECIPE_KEYS),
                ("versioning_policy", VERSIONING_KEYS),
                ("evaluation_assets", EVALUATION_ASSET_KEYS),
            ]:
                nested_value = domain_pack.get(nested_key)
                if isinstance(nested_value, dict):
                    for key in nested_required:
                        if _is_unknown_or_empty(nested_value.get(key)):
                            blockers.append(f"domain_pack_context.{nested_key}.{key}")
                else:
                    blockers.append(f"domain_pack_context.{nested_key}")

        if isinstance(ui_requirements, dict):
            if ui_needs_wireframe:
                if ui_requirements.get("wireframe_status") != "reviewed":
                    blockers.append("ui_requirements.wireframe_status")
        if missing_fields:
            blockers.append("missing_fields")
        if blockers:
            errors.append("engineering_ready is invalid while critical fields are unknown: " + ", ".join(blockers))

    if isinstance(pmf_validation, dict):
        decision = pmf_validation.get("overall_decision")
        evidence_links = pmf_validation.get("evidence_links")
        if decision in ("批准 PoC", "主线候选") and _is_unknown_or_empty(evidence_links):
            errors.append(f"pmf_validation.overall_decision={decision} requires evidence_links")
        if decision == "批准 PoC":
            poc_entry = pmf_validation.get("poc_entry_criteria")
            if isinstance(poc_entry, dict):
                missing_poc = [
                    key for key in POC_ENTRY_CRITERIA_KEYS if _is_unknown_or_empty(poc_entry.get(key))
                ]
                if missing_poc:
                    errors.append(
                        "批准 PoC requires complete poc_entry_criteria: "
                        + ", ".join(f"pmf_validation.poc_entry_criteria.{key}" for key in missing_poc)
                    )
            else:
                errors.append("批准 PoC requires pmf_validation.poc_entry_criteria")
        if decision == "主线候选":
            scores = pmf_validation.get("four_factor_scores")
            if isinstance(scores, dict):
                low_scores: list[str] = []
                for key in PMF_SCORE_KEYS:
                    value = scores.get(key)
                    score = value.get("score") if isinstance(value, dict) else None
                    if not isinstance(score, (int, float)) or isinstance(score, bool) or score < 4:
                        low_scores.append(f"pmf_validation.four_factor_scores.{key}.score")
                if low_scores:
                    errors.append("主线候选 requires all PMF four-factor scores >= 4: " + ", ".join(low_scores))
            else:
                errors.append("主线候选 requires pmf_validation.four_factor_scores")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a spec-intake JSON file.")
    parser.add_argument("spec", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references" / "spec-schema.json",
    )
    args = parser.parse_args()

    errors = validate(args.spec, args.schema)
    if errors:
        print("spec-intake validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("spec-intake validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
