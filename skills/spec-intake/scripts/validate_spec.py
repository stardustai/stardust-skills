#!/usr/bin/env python3
"""Validate a spec-intake JSON file without third-party dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PMF_SCORE_KEYS = [
    "customer_willingness",
    "market_clarity",
    "technical_value",
    "gtm_repeatability",
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

MEMORY_WRITE_RULE_KEYS = [
    "source_type",
    "write_allowed",
    "requires_human_approval",
    "target_scope",
    "redaction_required",
    "rollback_method",
]

ENGINEERING_DECISIONS = {
    "continue_technical_spec",
    "mark_poc_design_ready",
    "mark_poc_execution_ready",
    "ready_for_engineering",
}

NEXT_STAGE_DECISIONS = {
    "handoff_to_product",
    "request_engineering_gap_review",
    "continue_technical_spec",
    "mark_poc_design_ready",
    "mark_poc_execution_ready",
    "ready_for_engineering",
}

UI_REVIEW_REQUIRED_LABELS = {
    "product_ready",
    "engineering_gap_review_ready",
    "poc_design_ready",
    "poc_execution_ready",
    "engineering_ready",
}

PRODUCT_PROOF_REQUIRED_LABELS = {
    "product_ready",
    "engineering_gap_review_ready",
    "poc_design_ready",
    "poc_execution_ready",
    "engineering_ready",
}

TECHNICAL_DESIGN_REVIEW_TYPES = {"technical_design", "delivery_plan"}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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
    expected_types = [expected] if isinstance(expected, str) else list(expected)
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
        if isinstance(item_schema, dict) and "$ref" not in item_schema:
            for index, item in enumerate(value):
                errors.extend(_validate_schema_subset(item, item_schema, f"{path}[{index}]"))

    return errors


def _is_unknown_or_empty(value: Any) -> bool:
    if value is None:
        return True
    if value in ("", "unknown", "not_applicable"):
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


def _missing_keys(obj: dict[str, Any], keys: list[str], prefix: str) -> list[str]:
    return [f"{prefix}.{key}" for key in keys if key not in obj]


def _score_out_of_range(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (value < 1 or value > 5)
    )


def _stage_readiness(spec: dict[str, Any]) -> str | None:
    stage_gate = spec.get("stage_gate", {})
    return stage_gate.get("readiness_label") if isinstance(stage_gate, dict) else None


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


def _evidence_map(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    opportunity = spec.get("opportunity_assessment", {})
    if not isinstance(opportunity, dict):
        return {}
    registry = opportunity.get("evidence_registry", [])
    if not isinstance(registry, list):
        return {}
    return {
        item["id"]: item
        for item in registry
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _non_assumption_evidence(refs: Any, evidence_by_id: dict[str, dict[str, Any]]) -> bool:
    if not isinstance(refs, list):
        return False
    for ref in refs:
        item = evidence_by_id.get(ref)
        if isinstance(item, dict) and item.get("is_assumption") is False:
            return True
    return False


def _validate_opportunity(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    opportunity = spec.get("opportunity_assessment")
    if not isinstance(opportunity, dict):
        return ["opportunity_assessment must be an object"]

    evidence_by_id = _evidence_map(spec)
    if not evidence_by_id:
        errors.append("opportunity_assessment.evidence_registry must include at least one evidence item")

    pmf = opportunity.get("pmf_validation")
    if isinstance(pmf, dict):
        pain_refs = pmf.get("pain_evidence_refs")
        if not _non_assumption_evidence(pain_refs, evidence_by_id):
            errors.append("opportunity_assessment.pmf_validation.pain_evidence_refs requires at least one non-assumption evidence item")

        scores = pmf.get("four_factor_scores")
        if isinstance(scores, dict):
            for key in PMF_SCORE_KEYS:
                score_item = scores.get(key)
                if not isinstance(score_item, dict):
                    errors.append(f"opportunity_assessment.pmf_validation.four_factor_scores.{key} must be an object")
                    continue
                score = score_item.get("score")
                if _score_out_of_range(score):
                    errors.append(f"opportunity_assessment.pmf_validation.four_factor_scores.{key}.score must be between 1 and 5")
                if isinstance(score, (int, float)) and not isinstance(score, bool) and score >= 3:
                    if not _non_assumption_evidence(score_item.get("evidence_refs"), evidence_by_id):
                        errors.append(
                            f"opportunity_assessment.pmf_validation.four_factor_scores.{key}.evidence_refs "
                            "requires non-assumption evidence when score >= 3"
                        )
        else:
            errors.append("opportunity_assessment.pmf_validation.four_factor_scores must be an object")

        if pmf.get("overall_decision") == "批准 PoC":
            errors.extend(_validate_poc_approval(spec))
        if pmf.get("overall_decision") == "主线候选":
            low_scores: list[str] = []
            scores = pmf.get("four_factor_scores")
            if isinstance(scores, dict):
                for key in PMF_SCORE_KEYS:
                    score_item = scores.get(key)
                    score = score_item.get("score") if isinstance(score_item, dict) else None
                    if not isinstance(score, (int, float)) or isinstance(score, bool) or score < 4:
                        low_scores.append(key)
            if low_scores:
                errors.append("主线候选 requires all PMF four-factor scores >= 4: " + ", ".join(low_scores))
    else:
        errors.append("opportunity_assessment.pmf_validation must be an object")

    priority = opportunity.get("priority_decision")
    if isinstance(priority, dict):
        expected_formula = "机会优先级指数 = 商业价值 * 商业信号清晰度 / 产研投入量"
        if priority.get("formula_name") != "机会优先级指数":
            errors.append("opportunity_assessment.priority_decision.formula_name must be 机会优先级指数")
        if priority.get("formula") != expected_formula:
            errors.append("opportunity_assessment.priority_decision.formula has unexpected value")
        for key in [
            "business_value_score",
            "commercial_signal_clarity_score",
            "product_engineering_effort_score",
        ]:
            if _score_out_of_range(priority.get(key)):
                errors.append(f"opportunity_assessment.priority_decision.{key} must be between 1 and 5")
        effort = priority.get("product_engineering_effort_score")
        if isinstance(effort, (int, float)) and not isinstance(effort, bool) and effort <= 0:
            errors.append("opportunity_assessment.priority_decision.product_engineering_effort_score must be > 0")
        if priority.get("scope_expansion_risk") == "high" and _is_unknown_or_empty(
            priority.get("scope_reduction_recommendation")
        ):
            errors.append("high scope_expansion_risk requires scope_reduction_recommendation")
    else:
        errors.append("opportunity_assessment.priority_decision must be an object")

    competitive = opportunity.get("competitive_research")
    if isinstance(competitive, dict):
        errors.extend(_validate_competitive_research(spec, competitive))
    else:
        errors.append("opportunity_assessment.competitive_research must be an object")

    return errors


def _validate_competitive_research(spec: dict[str, Any], competitive: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    readiness = _stage_readiness(spec)
    research_required = competitive.get("research_required") is True
    status = competitive.get("status")
    matrix = competitive.get("comparison_matrix")

    if research_required and status == "not_started" and readiness in PRODUCT_PROOF_REQUIRED_LABELS:
        errors.append(f"{readiness} requires competitive research to be user_provided, agent_researched, confirmed, or not_applicable")

    if research_required:
        if not isinstance(matrix, list) or not matrix:
            errors.append("opportunity_assessment.competitive_research.comparison_matrix is required when research_required=true")
        else:
            for index, item in enumerate(matrix):
                if not isinstance(item, dict):
                    errors.append(f"opportunity_assessment.competitive_research.comparison_matrix[{index}] must be an object")
                    continue
                for key in ["product_name", "vendor", "source", "core_workflow", "overlap_score", "differentiation_score"]:
                    if _is_unknown_or_empty(item.get(key)):
                        errors.append(f"opportunity_assessment.competitive_research.comparison_matrix[{index}].{key} is required")
                for key in ["overlap_score", "differentiation_score"]:
                    if _score_out_of_range(item.get(key)):
                        errors.append(f"opportunity_assessment.competitive_research.comparison_matrix[{index}].{key} must be between 1 and 5")

        differentiation = competitive.get("differentiation_score")
        if isinstance(differentiation, dict):
            if _score_out_of_range(differentiation.get("score")):
                errors.append("opportunity_assessment.competitive_research.differentiation_score.score must be between 1 and 5")
            for key in ["score", "rationale", "scoring_method"]:
                if _is_unknown_or_empty(differentiation.get(key)):
                    errors.append(f"opportunity_assessment.competitive_research.differentiation_score.{key} is required")
        else:
            errors.append("opportunity_assessment.competitive_research.differentiation_score must be an object")

    if readiness in ("product_ready", "engineering_gap_review_ready", "poc_design_ready", "poc_execution_ready", "engineering_ready"):
        if research_required and competitive.get("user_confirmation") != "confirmed":
            errors.append(f"{readiness} requires opportunity_assessment.competitive_research.user_confirmation=confirmed")

    return errors


def _validate_stage_gate(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_gate = spec.get("stage_gate")
    if not isinstance(stage_gate, dict):
        return ["stage_gate must be an object"]

    opportunity = spec.get("opportunity_assessment", {})
    priority = opportunity.get("priority_decision", {}) if isinstance(opportunity, dict) else {}
    recommendation = priority.get("recommendation") if isinstance(priority, dict) else None
    decision = stage_gate.get("decision")
    current_stage = stage_gate.get("current_stage")

    if recommendation == "needs_more_evidence" and decision in ENGINEERING_DECISIONS:
        errors.append(
            "needs_more_evidence cannot move to technical spec, PoC ready, or engineering ready; "
            "use continue_business_validation, handoff_to_product, continue_product_shape, or request_engineering_gap_review"
        )

    readiness = stage_gate.get("readiness_label")
    if readiness == "engineering_ready" and decision != "ready_for_engineering":
        errors.append("engineering_ready requires stage_gate.decision=ready_for_engineering")

    exit_check = stage_gate.get("stage_exit_check")
    if isinstance(exit_check, dict):
        if decision in NEXT_STAGE_DECISIONS:
            if exit_check.get("status") != "confirmed":
                errors.append(f"{decision} requires stage_gate.stage_exit_check.status=confirmed")
            for key in ["exit_summary", "confirmation_question", "confirmed_by", "next_stage"]:
                if _is_unknown_or_empty(exit_check.get(key)):
                    errors.append(f"{decision} requires stage_gate.stage_exit_check.{key}")
            if current_stage == "business_feasibility" and decision == "handoff_to_product":
                summary_text = " ".join(
                    str(exit_check.get(key) or "")
                    for key in ["exit_summary", "confirmation_question"]
                )
                required_terms = [
                    "target buyer",
                    "acceptance",
                    "alternative",
                    "minimum paid artifact",
                    "evidence",
                    "PMF",
                    "opportunity priority",
                    "competitive",
                    "blocked",
                ]
                missing_terms = [term for term in required_terms if term.lower() not in summary_text.lower()]
                if missing_terms:
                    errors.append(
                        "handoff_to_product requires business stage exit summary to cover: "
                        + ", ".join(missing_terms)
                    )
    else:
        errors.append("stage_gate.stage_exit_check must be an object")

    if readiness in ("poc_execution_ready", "engineering_ready"):
        execution = _readiness_check(spec, "poc_execution_ready")
        if execution and execution.get("status") != "ready":
            errors.append("poc_execution_ready or engineering_ready requires validation_plan.poc_execution_ready.status=ready")

    return errors


def _validate_poc_approval(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    opportunity = spec.get("opportunity_assessment", {})
    pmf = opportunity.get("pmf_validation", {}) if isinstance(opportunity, dict) else {}
    partners = opportunity.get("design_partner_registry", []) if isinstance(opportunity, dict) else []
    minimum_artifact = opportunity.get("minimum_paid_artifact", {}) if isinstance(opportunity, dict) else {}

    confirmed_partner = False
    if isinstance(partners, list):
        for partner in partners:
            if not isinstance(partner, dict):
                continue
            if (
                partner.get("status") == "confirmed"
                and not _is_unknown_or_empty(partner.get("budget_owner"))
                and not _is_unknown_or_empty(partner.get("reviewer"))
                and partner.get("data_available") in ("yes", "partial")
            ):
                confirmed_partner = True
                break
    if not confirmed_partner:
        errors.append("批准 PoC requires a confirmed design partner with budget owner, reviewer, and available data")

    if isinstance(minimum_artifact, dict) and _is_unknown_or_empty(minimum_artifact.get("name")):
        errors.append("批准 PoC requires opportunity_assessment.minimum_paid_artifact.name")

    criteria = pmf.get("poc_entry_criteria") if isinstance(pmf, dict) else None
    if isinstance(criteria, dict):
        missing = [
            key
            for key in [
                "customer_evidence",
                "paid_signal",
                "data_available",
                "baseline_defined",
                "acceptance_method",
                "timebox_and_resource_cap",
            ]
            if _is_unknown_or_empty(criteria.get(key))
        ]
        if missing:
            errors.append("批准 PoC requires complete poc_entry_criteria: " + ", ".join(missing))
    else:
        errors.append("批准 PoC requires opportunity_assessment.pmf_validation.poc_entry_criteria")

    return errors


def _readiness_check(spec: dict[str, Any], key: str) -> dict[str, Any] | None:
    validation = spec.get("validation_plan", {})
    if not isinstance(validation, dict):
        return None
    value = validation.get(key)
    return value if isinstance(value, dict) else None


def _validate_ui(spec: dict[str, Any], spec_path: Path) -> list[str]:
    errors: list[str] = []
    ui = spec.get("ui_requirements")
    if not isinstance(ui, dict):
        return ["ui_requirements must be an object"]

    needs_wireframe = ui.get("has_ui") is True and ui.get("wireframe_required") is True
    if needs_wireframe:
        errors.extend(_svg_wireframe_errors(ui, spec_path))

    stage_gate = spec.get("stage_gate", {})
    readiness = stage_gate.get("readiness_label") if isinstance(stage_gate, dict) else None
    if needs_wireframe and readiness in UI_REVIEW_REQUIRED_LABELS and ui.get("wireframe_status") != "reviewed":
        errors.append(f"{readiness} requires ui_requirements.wireframe_status=reviewed for UI specs")

    return errors


def _validate_product_context(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    product = spec.get("product_context")
    if not isinstance(product, dict):
        return ["product_context must be an object"]

    leadership = product.get("technical_leadership")
    if not isinstance(leadership, dict):
        return ["product_context.technical_leadership must be an object"]

    readiness = _stage_readiness(spec)
    if readiness in PRODUCT_PROOF_REQUIRED_LABELS:
        for key in ["claim", "proof_or_argument", "score_rationale"]:
            if _is_unknown_or_empty(leadership.get(key)):
                errors.append(f"{readiness} requires product_context.technical_leadership.{key}")
        score = leadership.get("spec_agent_score")
        if _is_unknown_or_empty(score):
            errors.append(f"{readiness} requires product_context.technical_leadership.spec_agent_score")
        elif _score_out_of_range(score):
            errors.append("product_context.technical_leadership.spec_agent_score must be between 1 and 5")
        if leadership.get("product_owner_confirmation") != "confirmed":
            errors.append(f"{readiness} requires product_context.technical_leadership.product_owner_confirmation=confirmed")

    return errors


def _validate_workflow(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    workflow = spec.get("workflow")
    if not isinstance(workflow, dict):
        return ["workflow must be an object"]
    steps = workflow.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["workflow.steps must be a non-empty array"]
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"workflow.steps[{index}] must be an object")
            continue
        errors.extend(_missing_keys(step, WORKFLOW_STEP_KEYS, f"workflow.steps[{index}]"))
        if not isinstance(step.get("human_review_required"), bool):
            errors.append(f"workflow.steps[{index}].human_review_required must be boolean")
    return errors


def _validate_friday_object_model(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    product = spec.get("product_context", {})
    build_target = product.get("build_target") if isinstance(product, dict) else None
    spec_type = product.get("spec_type") if isinstance(product, dict) else None
    if build_target != "domain_pack" and spec_type != "domain_pack":
        return errors

    model = spec.get("friday_object_model")
    if not isinstance(model, dict):
        return ["Domain Pack specs require friday_object_model"]

    for key in ["workspace_memory", "tasks", "artifacts", "recipes", "feedback_comments", "rooms"]:
        if _is_unknown_or_empty(model.get(key)):
            errors.append(f"Domain Pack specs require friday_object_model.{key}")

    relationships = model.get("object_relationships")
    if not isinstance(relationships, list):
        errors.append("friday_object_model.object_relationships must be an array")
    else:
        required_terms = ["Task", "Artifact", "Feedback", "Recipe", "Memory"]
        relationship_text = " ".join(str(item) for item in relationships)
        missing_terms = [term for term in required_terms if term not in relationship_text]
        if missing_terms:
            errors.append(
                "friday_object_model.object_relationships must describe Task -> Artifact -> Feedback -> Recipe/Memory loop; missing "
                + ", ".join(missing_terms)
            )

    return errors


def _validate_memory_policy(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = spec.get("knowledge_and_memory_policy")
    if not isinstance(policy, dict):
        return ["knowledge_and_memory_policy must be an object"]

    rules = policy.get("memory_write_rules")
    if not isinstance(rules, list) or not rules:
        errors.append("knowledge_and_memory_policy.memory_write_rules must be a non-empty array")
        return errors

    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"knowledge_and_memory_policy.memory_write_rules[{index}] must be an object")
            continue
        errors.extend(_missing_keys(rule, MEMORY_WRITE_RULE_KEYS, f"knowledge_and_memory_policy.memory_write_rules[{index}]"))
        if rule.get("write_allowed") is True and rule.get("requires_human_approval") is not True:
            errors.append(
                f"knowledge_and_memory_policy.memory_write_rules[{index}] write_allowed=true requires requires_human_approval=true"
            )
        if rule.get("write_allowed") is True and _is_unknown_or_empty(rule.get("rollback_method")):
            errors.append(
                f"knowledge_and_memory_policy.memory_write_rules[{index}] write_allowed=true requires rollback_method"
            )

    return errors


def _validate_validation_plan(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validation = spec.get("validation_plan")
    if not isinstance(validation, dict):
        return ["validation_plan must be an object"]

    stage_gate = spec.get("stage_gate", {})
    readiness = stage_gate.get("readiness_label") if isinstance(stage_gate, dict) else None

    metrics = validation.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        errors.append("validation_plan.metrics must be a non-empty array")
    else:
        for index, metric in enumerate(metrics):
            if not isinstance(metric, dict):
                errors.append(f"validation_plan.metrics[{index}] must be an object")
                continue
            for key in ["metric_id", "definition", "baseline", "target", "measurement_method", "fixture_id", "owner", "pass_fail_rule"]:
                if _is_unknown_or_empty(metric.get(key)):
                    errors.append(f"validation_plan.metrics[{index}].{key} is required")

    assets = validation.get("evaluation_assets")
    if readiness in ("poc_design_ready", "poc_execution_ready", "engineering_ready"):
        if not isinstance(assets, list) or not assets:
            errors.append(f"{readiness} requires validation_plan.evaluation_assets")
        else:
            unavailable = [
                str(asset.get("asset_id"))
                for asset in assets
                if isinstance(asset, dict) and asset.get("status") not in ("available", "approved")
            ]
            if unavailable:
                errors.append(f"{readiness} requires available or approved evaluation assets: " + ", ".join(unavailable))

    poc_design = validation.get("poc_design_ready")
    if readiness in ("poc_design_ready", "poc_execution_ready", "engineering_ready"):
        if not isinstance(poc_design, dict) or poc_design.get("status") != "ready":
            errors.append(f"{readiness} requires validation_plan.poc_design_ready.status=ready")

    return errors


def _validate_engineering_ready(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_gate = spec.get("stage_gate", {})
    readiness = stage_gate.get("readiness_label") if isinstance(stage_gate, dict) else None
    if readiness != "engineering_ready":
        return errors

    owners = spec.get("owners", {})
    if isinstance(owners, dict):
        for key in ["business_owner", "product_owner", "engineering_owner", "qa_owner"]:
            if _is_unknown_or_empty(owners.get(key)):
                errors.append(f"engineering_ready requires owners.{key}")
    else:
        errors.append("engineering_ready requires owners")

    implementation = spec.get("implementation_mapping", {})
    if isinstance(implementation, dict):
        if implementation.get("engineering_review_type") not in ("technical_design", "delivery_plan"):
            errors.append("engineering_ready requires implementation_mapping.engineering_review_type=technical_design or delivery_plan")
        capabilities = implementation.get("capabilities")
        if isinstance(capabilities, list):
            unknown = [
                str(item.get("capability"))
                for item in capabilities
                if isinstance(item, dict) and item.get("support_status") in ("missing", "unknown")
            ]
            if unknown:
                errors.append("engineering_ready cannot include missing or unknown implementation capabilities: " + ", ".join(unknown))
    else:
        errors.append("engineering_ready requires implementation_mapping")

    missing_fields = spec.get("missing_fields")
    if missing_fields:
        errors.append("engineering_ready cannot have missing_fields")

    return errors


def _validate_implementation_mapping(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    implementation = spec.get("implementation_mapping")
    if not isinstance(implementation, dict):
        return ["implementation_mapping must be an object"]

    readiness = _stage_readiness(spec)
    review_type = implementation.get("engineering_review_type")
    requires_design_review = review_type in TECHNICAL_DESIGN_REVIEW_TYPES or readiness == "engineering_ready"

    source_review = implementation.get("source_code_review")
    if isinstance(source_review, dict):
        if requires_design_review:
            if source_review.get("required") is not True:
                errors.append("technical design review requires implementation_mapping.source_code_review.required=true")
            if source_review.get("status") != "completed":
                errors.append("technical design review requires implementation_mapping.source_code_review.status=completed")
            if _is_unknown_or_empty(source_review.get("paths_read")):
                errors.append("technical design review requires implementation_mapping.source_code_review.paths_read")
            if source_review.get("unread_required_paths"):
                errors.append("technical design review cannot have unread_required_paths")
    else:
        errors.append("implementation_mapping.source_code_review must be an object")

    assessment = implementation.get("technical_design_assessment")
    if isinstance(assessment, dict):
        if requires_design_review:
            for key in ["design_summary", "score_rationale"]:
                if _is_unknown_or_empty(assessment.get(key)):
                    errors.append(f"technical design review requires implementation_mapping.technical_design_assessment.{key}")
            if _score_out_of_range(assessment.get("ai_score")) or _is_unknown_or_empty(assessment.get("ai_score")):
                errors.append("implementation_mapping.technical_design_assessment.ai_score must be between 1 and 5")
            dimensions = assessment.get("scoring_dimensions")
            if not isinstance(dimensions, list) or not dimensions:
                errors.append("technical design review requires implementation_mapping.technical_design_assessment.scoring_dimensions")
            else:
                seen: set[str] = set()
                for index, item in enumerate(dimensions):
                    if not isinstance(item, dict):
                        errors.append(f"implementation_mapping.technical_design_assessment.scoring_dimensions[{index}] must be an object")
                        continue
                    dimension = item.get("dimension")
                    if isinstance(dimension, str):
                        seen.add(dimension)
                    if _score_out_of_range(item.get("score")) or _is_unknown_or_empty(item.get("score")):
                        errors.append(f"implementation_mapping.technical_design_assessment.scoring_dimensions[{index}].score must be between 1 and 5")
                    if _is_unknown_or_empty(item.get("rationale")):
                        errors.append(f"implementation_mapping.technical_design_assessment.scoring_dimensions[{index}].rationale is required")
                required_dimensions = {"architecture_fit", "code_reuse", "integration_complexity", "testability", "delivery_risk"}
                missing = sorted(required_dimensions - seen)
                if missing:
                    errors.append("technical design assessment missing scoring dimensions: " + ", ".join(missing))
            if readiness == "engineering_ready" and assessment.get("ai_engineer_confirmation") != "confirmed":
                errors.append("engineering_ready requires implementation_mapping.technical_design_assessment.ai_engineer_confirmation=confirmed")
    else:
        errors.append("implementation_mapping.technical_design_assessment must be an object")

    return errors


def validate(spec_path: Path, schema_path: Path) -> list[str]:
    schema = _load_json(schema_path)
    spec = _load_json(spec_path)
    errors = _validate_schema_subset(spec, schema)

    if not isinstance(spec, dict):
        return errors or ["spec must be a JSON object"]

    errors.extend(_validate_stage_gate(spec))
    errors.extend(_validate_opportunity(spec))
    errors.extend(_validate_product_context(spec))
    errors.extend(_validate_workflow(spec))
    errors.extend(_validate_ui(spec, spec_path))
    errors.extend(_validate_friday_object_model(spec))
    errors.extend(_validate_memory_policy(spec))
    errors.extend(_validate_validation_plan(spec))
    errors.extend(_validate_implementation_mapping(spec))
    errors.extend(_validate_engineering_ready(spec))

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
