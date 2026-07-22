#!/usr/bin/env python3
"""Validate a spec-intake JSON file without third-party dependencies."""

from __future__ import annotations

import argparse
import json
from datetime import date
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

PRODUCT_GOAL_KEYS = [
    "goal_id",
    "business_owner_definition",
    "product_refinement",
    "target_user",
    "target_outcome",
    "business_metric_refs",
    "product_metric_refs",
    "loop_engineering_signal",
]

BUSINESS_METRIC_KEYS = [
    "metric_id",
    "business_definition",
    "product_refinement",
    "owner",
    "baseline",
    "target",
    "measurement_method",
    "review_cadence",
    "loop_engineering_use",
]

USER_JOURNEY_KEYS = [
    "journey_id",
    "name",
    "primary_actor",
    "business_goal",
    "entry_point",
    "happy_path",
    "exception_paths",
    "exit_criteria",
    "covered_operation_flow_ids",
]

USER_OPERATION_FLOW_KEYS = [
    "flow_id",
    "journey_id",
    "actor",
    "trigger",
    "preconditions",
    "user_actions",
    "system_responses",
    "expected_result",
    "failure_modes",
    "test_case_seed",
]

VIRTUAL_REVIEW_ROLE_KEYS = [
    "role_id",
    "role_name",
    "role_type",
    "review_focus",
    "challenge_questions",
    "review_findings",
    "decision_impact",
    "status",
]

VIRTUAL_REVIEW_PRODUCT_OWNER_TYPES = {"pm", "owner"}

VIRTUAL_REVIEW_CHALLENGER_TYPES = {
    "algorithm",
    "user",
    "domain_expert",
    "researcher",
    "qa",
    "engineering",
    "compliance",
    "sales_gtm",
}

BUSINESS_SUCCESS_SCENARIO_KEYS = [
    "scenario_id",
    "title",
    "scope_status",
    "priority",
    "business_owner",
    "user_role",
    "business_goal",
    "preconditions",
    "trigger",
    "workflow_step_refs",
    "expected_business_outcome",
    "expected_final_state",
    "success_signals",
    "business_invariants",
    "unacceptable_outcomes",
    "alternate_paths",
    "exception_paths",
    "recovery_expectations",
    "confirmation",
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
    "mark_validation_design_ready",
    "mark_validation_execution_ready",
    "ready_for_engineering",
}

NEXT_STAGE_DECISIONS = {
    "handoff_to_product",
    "request_engineering_gap_review",
    "continue_technical_spec",
    "mark_validation_design_ready",
    "mark_validation_execution_ready",
    "ready_for_engineering",
}

UI_REVIEW_REQUIRED_LABELS = {
    "product_ready",
    "engineering_gap_review_ready",
    "validation_design_ready",
    "validation_execution_ready",
    "engineering_ready",
}

PRODUCT_PROOF_REQUIRED_LABELS = {
    "product_ready",
    "engineering_gap_review_ready",
    "validation_design_ready",
    "validation_execution_ready",
    "engineering_ready",
}

MARKET_SIZING_REQUIRED_LABELS = PRODUCT_PROOF_REQUIRED_LABELS | {"business_ready"}

FIRST_PARTY_CUSTOMER_EVIDENCE_TYPES = {
    "customer_interview",
    "customer_data",
    "paid_signal",
    "usage_data",
    "sales_pipeline",
}

EXTERNAL_MARKET_EVIDENCE_TYPES = {
    "consulting_report",
    "industry_report",
    "market_research",
}

TECHNICAL_DESIGN_REVIEW_TYPES = {"technical_design", "delivery_plan"}

SCENARIO_COVERAGE_REQUIRED_LABELS = {
    "validation_design_ready",
    "validation_execution_ready",
    "engineering_ready",
}

READINESS_STAGE = {
    "business_ready": "business_feasibility",
    "product_ready": "product_shape",
    "engineering_gap_review_ready": "engineering_gap_review",
    "validation_design_ready": "validation_design",
    "validation_execution_ready": "validation_execution",
    "engineering_ready": "engineering_delivery",
}

DECISION_NEXT_STAGE = {
    "handoff_to_product": "product_shape",
    "request_engineering_gap_review": "engineering_gap_review",
    "continue_technical_spec": "technical_spec",
    "mark_validation_design_ready": "validation_design",
    "mark_validation_execution_ready": "validation_execution",
    "ready_for_engineering": "engineering_delivery",
}

RISK_LEVEL = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}

RISK_DIMENSION_FLOORS = {
    "user_exposure": {
        "prototype_only": 0,
        "internal_single_team": 1,
        "internal_multi_team": 1,
        "external_users": 2,
        "customer_facing": 2,
    },
    "data_sensitivity": {
        "synthetic": 0,
        "public": 0,
        "internal": 1,
        "confidential": 2,
        "restricted": 3,
    },
    "write_impact": {
        "none": 0,
        "read_only": 1,
        "reversible_write": 2,
        "irreversible_write": 3,
        "bulk_destructive": 3,
    },
    "integrations_and_permissions": {
        "none": 0,
        "approved_internal": 1,
        "external_or_elevated": 2,
        "production_privileged": 3,
    },
    "reversibility": {
        "easy": 0,
        "moderate": 1,
        "difficult": 2,
        "irreversible": 3,
    },
    "business_impact": {
        "demo": 0,
        "low": 1,
        "medium": 2,
        "high": 2,
        "critical": 3,
    },
}


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


def _resolve_local_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any] | None:
    if not ref.startswith("#/"):
        return None
    current: Any = root_schema
    for part in ref[2:].split("/"):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current if isinstance(current, dict) else None


def _validate_schema_subset(
    value: Any,
    schema: dict[str, Any],
    path: str = "$",
    root_schema: dict[str, Any] | None = None,
) -> list[str]:
    if root_schema is None:
        root_schema = schema
    ref = schema.get("$ref")
    if isinstance(ref, str):
        resolved = _resolve_local_ref(root_schema, ref)
        if resolved is None:
            return [f"unresolved schema reference at {path}: {ref}"]
        schema = resolved

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
                errors.extend(
                    _validate_schema_subset(value[key], child_schema, f"{path}.{key}", root_schema)
                )

    if isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    _validate_schema_subset(item, item_schema, f"{path}[{index}]", root_schema)
                )

    return errors


def _is_unknown_or_empty(value: Any) -> bool:
    if value is None:
        return True
    if value in ("", "unknown", "not_applicable"):
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


def _value_at_path(root: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = root
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _business_handoff_missing_fields(spec: dict[str, Any]) -> list[str]:
    required_paths = [
        ("product_context", "build_target"),
        ("opportunity_assessment", "commercial_context", "target_buyer"),
        ("opportunity_assessment", "market_sizing", "market_attractiveness_score"),
        ("opportunity_assessment", "market_sizing", "market_size_summary"),
        ("opportunity_assessment", "pmf_validation", "current_alternative"),
        ("opportunity_assessment", "minimum_paid_artifact", "name"),
        ("opportunity_assessment", "minimum_paid_artifact", "buyer_value"),
        ("opportunity_assessment", "priority_decision", "recommendation"),
        ("opportunity_assessment", "priority_decision", "opportunity_priority_score"),
    ]

    missing = [
        ".".join(path)
        for path in required_paths
        if _is_unknown_or_empty(_value_at_path(spec, path))
    ]

    acceptance_method = _value_at_path(
        spec,
        ("opportunity_assessment", "pmf_validation", "poc_entry_criteria", "acceptance_method"),
    )
    design_partners = _value_at_path(spec, ("opportunity_assessment", "design_partner_registry"))
    has_reviewer = any(
        isinstance(item, dict) and not _is_unknown_or_empty(item.get("reviewer"))
        for item in design_partners or []
    )
    if _is_unknown_or_empty(acceptance_method) and not has_reviewer:
        missing.append(
            "opportunity_assessment.pmf_validation.poc_entry_criteria.acceptance_method "
            "or opportunity_assessment.design_partner_registry[].reviewer"
        )

    evidence = _value_at_path(spec, ("opportunity_assessment", "evidence_registry"))
    if not isinstance(evidence, list) or not evidence:
        missing.append("opportunity_assessment.evidence_registry")

    scores = _value_at_path(spec, ("opportunity_assessment", "pmf_validation", "four_factor_scores"))
    if not isinstance(scores, dict):
        missing.append("opportunity_assessment.pmf_validation.four_factor_scores")
    else:
        for key in PMF_SCORE_KEYS:
            score_item = scores.get(key)
            score = score_item.get("score") if isinstance(score_item, dict) else None
            if _is_unknown_or_empty(score):
                missing.append(f"opportunity_assessment.pmf_validation.four_factor_scores.{key}.score")

    competitive = _value_at_path(spec, ("opportunity_assessment", "competitive_research"))
    if not isinstance(competitive, dict):
        missing.append("opportunity_assessment.competitive_research")
    else:
        if competitive.get("status") in (None, "", "unknown", "not_started"):
            missing.append("opportunity_assessment.competitive_research.status")
        if not competitive.get("comparison_matrix"):
            missing.append("opportunity_assessment.competitive_research.comparison_matrix")
        score = _value_at_path(competitive, ("differentiation_score", "score"))
        if _is_unknown_or_empty(score):
            missing.append("opportunity_assessment.competitive_research.differentiation_score.score")

    blocked_actions = _value_at_path(spec, ("stage_gate", "blocked_next_actions"))
    if not isinstance(blocked_actions, list) or not blocked_actions:
        missing.append("stage_gate.blocked_next_actions")

    return missing


def _missing_keys(obj: dict[str, Any], keys: list[str], prefix: str) -> list[str]:
    return [f"{prefix}.{key}" for key in keys if key not in obj]


def _score_out_of_range(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (value < 1 or value > 5)
    )


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


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


def _non_assumption_evidence_of_type(
    refs: Any,
    evidence_by_id: dict[str, dict[str, Any]],
    allowed_types: set[str],
) -> bool:
    if not isinstance(refs, list):
        return False
    for ref in refs:
        item = evidence_by_id.get(ref)
        if (
            isinstance(item, dict)
            and item.get("is_assumption") is False
            and item.get("type") in allowed_types
        ):
            return True
    return False


def _unknown_evidence_refs(
    refs: Any,
    evidence_by_id: dict[str, dict[str, Any]],
    prefix: str,
) -> list[str]:
    if not isinstance(refs, list):
        return [f"{prefix} must be an array"]
    return [f"{prefix} references unknown evidence item: {ref}" for ref in refs if ref not in evidence_by_id]


def _validate_opportunity(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    opportunity = spec.get("opportunity_assessment")
    if not isinstance(opportunity, dict):
        return ["opportunity_assessment must be an object"]

    evidence_by_id = _evidence_map(spec)
    if not evidence_by_id:
        errors.append("opportunity_assessment.evidence_registry must include at least one evidence item")

    pmf = opportunity.get("pmf_validation")
    market_sizing = opportunity.get("market_sizing")
    if isinstance(market_sizing, dict):
        errors.extend(_validate_market_sizing(spec, market_sizing, evidence_by_id))
    else:
        errors.append("opportunity_assessment.market_sizing must be an object")

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

        if pmf.get("overall_decision") == "批准客户 PoC":
            errors.extend(_validate_customer_poc_approval(spec))
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


def _validate_market_sizing(
    spec: dict[str, Any],
    market_sizing: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    readiness = _stage_readiness(spec)
    require_complete = readiness in MARKET_SIZING_REQUIRED_LABELS

    for key in [
        "customer_value",
        "customer_payment_willingness",
        "competition_intensity",
    ]:
        item = market_sizing.get(key)
        if not isinstance(item, dict):
            errors.append(f"opportunity_assessment.market_sizing.{key} must be an object")
            continue
        score = item.get("score")
        if _score_out_of_range(score):
            errors.append(f"opportunity_assessment.market_sizing.{key}.score must be between 1 and 5")
        if require_complete:
            for child_key in ["score", "notes"]:
                if _is_unknown_or_empty(item.get(child_key)):
                    errors.append(f"{readiness} requires opportunity_assessment.market_sizing.{key}.{child_key}")
            if not _non_assumption_evidence(item.get("evidence_refs"), evidence_by_id):
                errors.append(
                    f"{readiness} requires non-assumption evidence for opportunity_assessment.market_sizing.{key}"
                )

    for key in ["average_contract_value", "addressable_customer_count"]:
        item = market_sizing.get(key)
        if not isinstance(item, dict):
            errors.append(f"opportunity_assessment.market_sizing.{key} must be an object")
            continue
        if require_complete:
            for child_key in ["estimate", "range", "unit", "notes"]:
                if _is_unknown_or_empty(item.get(child_key)):
                    errors.append(f"{readiness} requires opportunity_assessment.market_sizing.{key}.{child_key}")
            if not _non_assumption_evidence(item.get("evidence_refs"), evidence_by_id):
                errors.append(
                    f"{readiness} requires non-assumption evidence for opportunity_assessment.market_sizing.{key}"
                )

    attractiveness = market_sizing.get("market_attractiveness_score")
    if _score_out_of_range(attractiveness):
        errors.append("opportunity_assessment.market_sizing.market_attractiveness_score must be between 1 and 5")
    if require_complete:
        for key in ["market_size_summary", "market_attractiveness_score", "calculation_note", "confidence"]:
            if _is_unknown_or_empty(market_sizing.get(key)):
                errors.append(f"{readiness} requires opportunity_assessment.market_sizing.{key}")
        if not _non_assumption_evidence(market_sizing.get("evidence_refs"), evidence_by_id):
            errors.append(f"{readiness} requires non-assumption evidence for opportunity_assessment.market_sizing.evidence_refs")

    evidence_quality = market_sizing.get("evidence_quality")
    if isinstance(evidence_quality, dict):
        errors.extend(_validate_market_evidence_quality(spec, evidence_quality, evidence_by_id))
    elif require_complete:
        errors.append(f"{readiness} requires opportunity_assessment.market_sizing.evidence_quality")
    else:
        errors.append("opportunity_assessment.market_sizing.evidence_quality must be an object")

    return errors


def _validate_market_evidence_quality(
    spec: dict[str, Any],
    evidence_quality: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    readiness = _stage_readiness(spec)
    require_complete = readiness in MARKET_SIZING_REQUIRED_LABELS

    for key in [
        "primary_evidence_refs",
        "external_market_evidence_refs",
        "first_party_customer_feedback_refs",
        "internal_estimate_refs",
    ]:
        errors.extend(
            _unknown_evidence_refs(
                evidence_quality.get(key),
                evidence_by_id,
                f"opportunity_assessment.market_sizing.evidence_quality.{key}",
            )
        )

    status = evidence_quality.get("validation_status")
    if require_complete:
        if status in (None, "", "unknown", "not_applicable", "unverified_estimate"):
            errors.append(
                f"{readiness} requires opportunity_assessment.market_sizing.evidence_quality.validation_status="
                "partially_supported, supported, or strongly_supported"
            )
        if _is_unknown_or_empty(evidence_quality.get("confidence_rationale")):
            errors.append(
                f"{readiness} requires opportunity_assessment.market_sizing.evidence_quality.confidence_rationale"
            )
        if not _non_assumption_evidence(evidence_quality.get("primary_evidence_refs"), evidence_by_id):
            errors.append(f"{readiness} requires non-assumption primary evidence for market sizing")
        if not _non_assumption_evidence_of_type(
            evidence_quality.get("first_party_customer_feedback_refs"),
            evidence_by_id,
            FIRST_PARTY_CUSTOMER_EVIDENCE_TYPES,
        ):
            errors.append(
                f"{readiness} requires first-party customer feedback evidence for market sizing"
            )

    market_sizing = _value_at_path(spec, ("opportunity_assessment", "market_sizing"))
    attractiveness = market_sizing.get("market_attractiveness_score") if isinstance(market_sizing, dict) else None
    confidence = market_sizing.get("confidence") if isinstance(market_sizing, dict) else None
    priority = _value_at_path(spec, ("opportunity_assessment", "priority_decision", "recommendation"))
    needs_external = (
        status in {"supported", "strongly_supported"}
        or confidence in {"medium", "high"}
        or priority == "top_8"
        or (isinstance(attractiveness, (int, float)) and not isinstance(attractiveness, bool) and attractiveness >= 4)
    )
    if needs_external and not _non_assumption_evidence_of_type(
        evidence_quality.get("external_market_evidence_refs"),
        evidence_by_id,
        EXTERNAL_MARKET_EVIDENCE_TYPES,
    ):
        errors.append(
            "supported market sizing, medium/high confidence, top_8 priority, or attractiveness >= 4 "
            "requires external market evidence such as consulting_report, industry_report, or market_research"
        )

    if status == "strongly_supported":
        if not _non_assumption_evidence_of_type(
            evidence_quality.get("first_party_customer_feedback_refs"),
            evidence_by_id,
            FIRST_PARTY_CUSTOMER_EVIDENCE_TYPES,
        ) or not _non_assumption_evidence_of_type(
            evidence_quality.get("external_market_evidence_refs"),
            evidence_by_id,
            EXTERNAL_MARKET_EVIDENCE_TYPES,
        ):
            errors.append("strongly_supported market sizing requires both external market evidence and first-party customer feedback")

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

    if readiness in ("product_ready", "engineering_gap_review_ready", "validation_design_ready", "validation_execution_ready", "engineering_ready"):
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
            "needs_more_evidence cannot move to technical spec, validation ready, or engineering ready; "
            "use continue_business_validation, handoff_to_product, continue_product_shape, or request_engineering_gap_review"
        )

    readiness = stage_gate.get("readiness_label")
    if readiness == "engineering_ready" and decision != "ready_for_engineering":
        errors.append("engineering_ready requires stage_gate.decision=ready_for_engineering")

    expected_stage = READINESS_STAGE.get(readiness)
    if expected_stage is not None and current_stage != expected_stage:
        errors.append(f"{readiness} requires stage_gate.current_stage={expected_stage}")

    exit_check = stage_gate.get("stage_exit_check")
    if isinstance(exit_check, dict):
        if decision in NEXT_STAGE_DECISIONS:
            if exit_check.get("status") != "confirmed":
                errors.append(f"{decision} requires stage_gate.stage_exit_check.status=confirmed")
            for key in ["exit_summary", "confirmation_question", "confirmed_by", "next_stage"]:
                if _is_unknown_or_empty(exit_check.get(key)):
                    errors.append(f"{decision} requires stage_gate.stage_exit_check.{key}")
            expected_next_stage = DECISION_NEXT_STAGE.get(decision)
            if expected_next_stage is not None and exit_check.get("next_stage") != expected_next_stage:
                errors.append(
                    f"{decision} requires stage_gate.stage_exit_check.next_stage={expected_next_stage}"
                )
            if current_stage == "business_feasibility" and decision == "handoff_to_product":
                missing_fields = _business_handoff_missing_fields(spec)
                if missing_fields:
                    errors.append(
                        "handoff_to_product requires structured business handoff fields: "
                        + ", ".join(missing_fields)
                    )
    else:
        errors.append("stage_gate.stage_exit_check must be an object")

    if readiness in ("validation_execution_ready", "engineering_ready"):
        execution = _readiness_check(spec, "validation_execution_ready")
        if execution and execution.get("status") != "ready":
            errors.append("validation_execution_ready or engineering_ready requires validation_plan.validation_execution_ready.status=ready")

    return errors


def _validate_customer_poc_approval(spec: dict[str, Any]) -> list[str]:
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
        errors.append("批准客户 PoC requires a confirmed design partner with budget owner, reviewer, and available data")

    if isinstance(minimum_artifact, dict) and _is_unknown_or_empty(minimum_artifact.get("name")):
        errors.append("批准客户 PoC requires opportunity_assessment.minimum_paid_artifact.name")

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
            errors.append("批准客户 PoC requires complete poc_entry_criteria: " + ", ".join(missing))
    else:
        errors.append("批准客户 PoC requires opportunity_assessment.pmf_validation.poc_entry_criteria")

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
    stage_gate = spec.get("stage_gate", {})
    readiness = stage_gate.get("readiness_label") if isinstance(stage_gate, dict) else None
    if needs_wireframe and readiness in UI_REVIEW_REQUIRED_LABELS:
        errors.extend(_svg_wireframe_errors(ui, spec_path))
        if ui.get("wireframe_status") != "reviewed":
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
        errors.extend(_validate_product_goals_and_metrics(spec, product, readiness))
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


def _validate_product_goals_and_metrics(
    spec: dict[str, Any], product: dict[str, Any], readiness: str
) -> list[str]:
    errors: list[str] = []
    goals = product.get("product_goals")
    business_metrics = product.get("business_metrics")

    if not isinstance(goals, list) or not goals:
        errors.append(f"{readiness} requires product_context.product_goals")
        goals = []
    if not isinstance(business_metrics, list) or not business_metrics:
        errors.append(f"{readiness} requires product_context.business_metrics")
        business_metrics = []

    business_metric_ids: set[str] = set()
    for index, metric in enumerate(business_metrics):
        prefix = f"product_context.business_metrics[{index}]"
        if not isinstance(metric, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_missing_keys(metric, BUSINESS_METRIC_KEYS, prefix))
        metric_id = metric.get("metric_id")
        if isinstance(metric_id, str):
            if metric_id in business_metric_ids:
                errors.append(f"product_context.business_metrics has duplicate metric_id: {metric_id}")
            business_metric_ids.add(metric_id)
        for key in BUSINESS_METRIC_KEYS:
            if _is_unknown_or_empty(metric.get(key)):
                errors.append(f"{readiness} requires {prefix}.{key}")

    validation = spec.get("validation_plan", {})
    validation_metrics = validation.get("metrics", []) if isinstance(validation, dict) else []
    product_metric_ids = {
        item.get("metric_id")
        for item in validation_metrics
        if isinstance(item, dict) and isinstance(item.get("metric_id"), str)
    }

    goal_ids: set[str] = set()
    for index, goal in enumerate(goals):
        prefix = f"product_context.product_goals[{index}]"
        if not isinstance(goal, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_missing_keys(goal, PRODUCT_GOAL_KEYS, prefix))
        goal_id = goal.get("goal_id")
        if isinstance(goal_id, str):
            if goal_id in goal_ids:
                errors.append(f"product_context.product_goals has duplicate goal_id: {goal_id}")
            goal_ids.add(goal_id)
        for key in PRODUCT_GOAL_KEYS:
            if _is_unknown_or_empty(goal.get(key)):
                errors.append(f"{readiness} requires {prefix}.{key}")
        for ref in goal.get("business_metric_refs", []):
            if ref not in business_metric_ids:
                errors.append(f"{prefix}.business_metric_refs references unknown business metric: {ref}")
        for ref in goal.get("product_metric_refs", []):
            if ref not in product_metric_ids:
                errors.append(f"{prefix}.product_metric_refs references unknown validation metric: {ref}")

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

    readiness = _stage_readiness(spec)
    journeys = workflow.get("user_journeys")
    operation_flows = workflow.get("user_operation_flows")
    if readiness in PRODUCT_PROOF_REQUIRED_LABELS:
        if not isinstance(journeys, list) or not journeys:
            errors.append(f"{readiness} requires workflow.user_journeys")
            journeys = []
        if not isinstance(operation_flows, list) or not operation_flows:
            errors.append(f"{readiness} requires workflow.user_operation_flows")
            operation_flows = []

    if isinstance(journeys, list) and isinstance(operation_flows, list):
        errors.extend(_validate_user_journeys_and_operation_flows(journeys, operation_flows, readiness))

    return errors


def _validate_user_journeys_and_operation_flows(
    journeys: list[Any], operation_flows: list[Any], readiness: str | None
) -> list[str]:
    errors: list[str] = []
    require_complete = readiness in PRODUCT_PROOF_REQUIRED_LABELS
    journey_ids: set[str] = set()
    flow_ids: set[str] = set()

    for index, journey in enumerate(journeys):
        prefix = f"workflow.user_journeys[{index}]"
        if not isinstance(journey, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_missing_keys(journey, USER_JOURNEY_KEYS, prefix))
        journey_id = journey.get("journey_id")
        if isinstance(journey_id, str):
            if journey_id in journey_ids:
                errors.append(f"workflow.user_journeys has duplicate journey_id: {journey_id}")
            journey_ids.add(journey_id)
        if require_complete:
            for key in USER_JOURNEY_KEYS:
                if _is_unknown_or_empty(journey.get(key)):
                    errors.append(f"{readiness} requires {prefix}.{key}")

    for index, flow in enumerate(operation_flows):
        prefix = f"workflow.user_operation_flows[{index}]"
        if not isinstance(flow, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_missing_keys(flow, USER_OPERATION_FLOW_KEYS, prefix))
        flow_id = flow.get("flow_id")
        if isinstance(flow_id, str):
            if flow_id in flow_ids:
                errors.append(f"workflow.user_operation_flows has duplicate flow_id: {flow_id}")
            flow_ids.add(flow_id)
        journey_id = flow.get("journey_id")
        if isinstance(journey_id, str) and journey_id not in journey_ids:
            errors.append(f"{prefix}.journey_id references unknown journey: {journey_id}")
        if require_complete:
            for key in USER_OPERATION_FLOW_KEYS:
                if _is_unknown_or_empty(flow.get(key)):
                    errors.append(f"{readiness} requires {prefix}.{key}")

    for index, journey in enumerate(journeys):
        if not isinstance(journey, dict):
            continue
        prefix = f"workflow.user_journeys[{index}]"
        for ref in journey.get("covered_operation_flow_ids", []):
            if ref not in flow_ids:
                errors.append(f"{prefix}.covered_operation_flow_ids references unknown operation flow: {ref}")

    return errors


def _needs_virtual_review_panel(spec: dict[str, Any]) -> bool:
    readiness = _stage_readiness(spec)
    if readiness not in PRODUCT_PROOF_REQUIRED_LABELS:
        return False

    product = spec.get("product_context", {})
    if isinstance(product, dict) and product.get("build_target") == "domain_pack":
        return True

    ui = spec.get("ui_requirements", {})
    if isinstance(ui, dict) and ui.get("has_ui") is True:
        return True

    workflow = spec.get("workflow", {})
    if isinstance(workflow, dict):
        journeys = workflow.get("user_journeys")
        operation_flows = workflow.get("user_operation_flows")
        if isinstance(journeys, list) and len(journeys) > 1:
            return True
        if isinstance(operation_flows, list) and len(operation_flows) > 1:
            return True

    scenarios = spec.get("business_success_scenarios")
    if isinstance(scenarios, list) and len(scenarios) > 1:
        return True

    profile = spec.get("delivery_risk_profile", {})
    if isinstance(profile, dict) and profile.get("risk_tier") in {"R2", "R3"}:
        return True

    return False


def _validate_review_gates(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    review_gates = spec.get("review_gates")
    if not isinstance(review_gates, dict):
        return ["review_gates must be an object"]

    panel = review_gates.get("virtual_review_panel")
    if not isinstance(panel, list):
        return ["review_gates.virtual_review_panel must be an array"]

    role_ids: set[str] = set()
    active_role_types: set[str] = set()
    has_product_owner_review = False
    has_challenger_review = False
    completed_count = 0

    for index, role in enumerate(panel):
        prefix = f"review_gates.virtual_review_panel[{index}]"
        if not isinstance(role, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_missing_keys(role, VIRTUAL_REVIEW_ROLE_KEYS, prefix))

        role_id = role.get("role_id")
        if isinstance(role_id, str):
            if role_id in role_ids:
                errors.append(f"review_gates.virtual_review_panel has duplicate role_id: {role_id}")
            role_ids.add(role_id)

        status = role.get("status")
        role_type = role.get("role_type")
        if status != "not_needed" and isinstance(role_type, str):
            active_role_types.add(role_type)
            if role_type in VIRTUAL_REVIEW_PRODUCT_OWNER_TYPES:
                has_product_owner_review = True
            if role_type in VIRTUAL_REVIEW_CHALLENGER_TYPES:
                has_challenger_review = True

        if status in {"proposed", "active", "completed"}:
            for key in ["review_focus", "challenge_questions"]:
                if _is_unknown_or_empty(role.get(key)):
                    errors.append(f"{prefix}.{key} is required for {status} virtual review role")

        if status == "completed":
            completed_count += 1
            for key in ["review_findings", "decision_impact"]:
                if _is_unknown_or_empty(role.get(key)):
                    errors.append(f"{prefix}.{key} is required for completed virtual review role")

    readiness = _stage_readiness(spec)
    if _needs_virtual_review_panel(spec):
        if not panel:
            errors.append(f"{readiness} requires review_gates.virtual_review_panel for complex product design")
        if len(active_role_types) < 2:
            errors.append(f"{readiness} requires at least two virtual review role types")
        if not has_product_owner_review:
            errors.append(f"{readiness} requires a virtual PM or owner review role")
        if not has_challenger_review:
            errors.append(f"{readiness} requires a non-product virtual challenger role")
        if completed_count < 2:
            errors.append(f"{readiness} requires at least two completed virtual review roles")

    return errors


def _validate_business_success_scenarios(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scenarios = spec.get("business_success_scenarios")
    readiness = _stage_readiness(spec)
    if not isinstance(scenarios, list):
        errors.append("business_success_scenarios must be an array")
        if readiness in PRODUCT_PROOF_REQUIRED_LABELS:
            errors.append(f"{readiness} requires business_success_scenarios")
        return errors

    workflow = spec.get("workflow", {})
    workflow_steps = workflow.get("steps", []) if isinstance(workflow, dict) else []
    workflow_step_ids = {
        step.get("step_id")
        for step in workflow_steps
        if isinstance(step, dict) and isinstance(step.get("step_id"), str)
    }

    seen_ids: set[str] = set()
    in_scope_critical = 0
    for index, scenario in enumerate(scenarios):
        prefix = f"business_success_scenarios[{index}]"
        if not isinstance(scenario, dict):
            errors.append(f"{prefix} must be an object")
            continue

        errors.extend(_missing_keys(scenario, BUSINESS_SUCCESS_SCENARIO_KEYS, prefix))
        scenario_id = scenario.get("scenario_id")
        if isinstance(scenario_id, str):
            if scenario_id in seen_ids:
                errors.append(f"business_success_scenarios has duplicate scenario_id: {scenario_id}")
            seen_ids.add(scenario_id)

        for ref in scenario.get("workflow_step_refs", []):
            if ref not in workflow_step_ids:
                errors.append(f"{prefix}.workflow_step_refs references unknown workflow step: {ref}")

        if scenario.get("scope_status") != "in_scope":
            continue
        if scenario.get("priority") == "critical":
            in_scope_critical += 1

        if readiness in PRODUCT_PROOF_REQUIRED_LABELS:
            for key in [
                "scenario_id",
                "title",
                "business_owner",
                "user_role",
                "business_goal",
                "trigger",
                "workflow_step_refs",
                "expected_business_outcome",
                "expected_final_state",
                "success_signals",
                "business_invariants",
                "unacceptable_outcomes",
            ]:
                if _is_unknown_or_empty(scenario.get(key)):
                    errors.append(f"{readiness} requires {prefix}.{key}")

            confirmation = scenario.get("confirmation")
            if not isinstance(confirmation, dict) or confirmation.get("status") != "confirmed":
                errors.append(
                    f"{readiness} requires confirmed critical business success scenario: {scenario_id}"
                    if scenario.get("priority") == "critical"
                    else f"{readiness} requires confirmed in-scope business success scenario: {scenario_id}"
                )
            elif any(
                _is_unknown_or_empty(confirmation.get(key))
                for key in ["confirmer_role", "confirmed_by", "confirmed_at", "confirmed_version"]
            ):
                errors.append(f"{readiness} requires complete confirmation for business success scenario: {scenario_id}")
            else:
                if confirmation.get("confirmer_role") != "business_owner":
                    errors.append(
                        f"{readiness} requires business-owner confirmation for business success scenario: {scenario_id}"
                    )
                if confirmation.get("confirmed_by") != scenario.get("business_owner"):
                    errors.append(
                        f"{readiness} requires confirmed_by to match business_owner for business success scenario: {scenario_id}"
                    )
                owners = spec.get("owners", {})
                if isinstance(owners, dict) and owners.get("business_owner") != scenario.get("business_owner"):
                    errors.append(
                        f"{readiness} requires scenario business_owner to match owners.business_owner: {scenario_id}"
                    )
                if not _is_iso_date(confirmation.get("confirmed_at")):
                    errors.append(
                        f"{readiness} requires a valid ISO confirmation date for business success scenario: {scenario_id}"
                    )
                if confirmation.get("confirmed_version") != spec.get("spec_version"):
                    errors.append(
                        f"{readiness} requires confirmation version {spec.get('spec_version')} "
                        f"for business success scenario: {scenario_id}"
                    )

    if readiness in PRODUCT_PROOF_REQUIRED_LABELS and in_scope_critical == 0:
        errors.append(f"{readiness} requires business_success_scenarios")
    return errors


def _validate_scenario_coverage(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validation = spec.get("validation_plan")
    if not isinstance(validation, dict):
        return errors

    coverage = validation.get("scenario_coverage")
    if not isinstance(coverage, list):
        errors.append("validation_plan.scenario_coverage must be an array")
        readiness = _stage_readiness(spec)
        if readiness in SCENARIO_COVERAGE_REQUIRED_LABELS:
            for scenario in spec.get("business_success_scenarios", []):
                if not isinstance(scenario, dict):
                    continue
                if scenario.get("scope_status") == "in_scope" and scenario.get("priority") == "critical":
                    errors.append(
                        f"{readiness} requires validation_plan.scenario_coverage for critical scenario: "
                        f"{scenario.get('scenario_id')}"
                    )
        return errors

    scenarios = spec.get("business_success_scenarios", [])
    scenario_by_id = {
        scenario.get("scenario_id"): scenario
        for scenario in scenarios
        if isinstance(scenario, dict) and isinstance(scenario.get("scenario_id"), str)
    }
    coverage_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(coverage):
        prefix = f"validation_plan.scenario_coverage[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        scenario_id = item.get("scenario_id")
        if scenario_id not in scenario_by_id:
            errors.append(f"{prefix}.scenario_id references unknown business scenario: {scenario_id}")
            continue
        if scenario_id in coverage_by_id:
            errors.append(f"validation_plan.scenario_coverage has duplicate scenario_id: {scenario_id}")
        coverage_by_id[scenario_id] = item

    readiness = _stage_readiness(spec)
    if readiness not in SCENARIO_COVERAGE_REQUIRED_LABELS:
        return errors

    for scenario_id, scenario in scenario_by_id.items():
        if scenario.get("scope_status") != "in_scope" or scenario.get("priority") != "critical":
            continue
        item = coverage_by_id.get(scenario_id)
        if item is None:
            errors.append(
                f"{readiness} requires validation_plan.scenario_coverage for critical scenario: {scenario_id}"
            )
            continue
        if item.get("qa_status") not in ("drafted", "approved"):
            errors.append(f"{readiness} requires QA coverage design for critical scenario: {scenario_id}")
        if not item.get("qa_case_refs") and not item.get("evaluation_asset_refs"):
            errors.append(f"{readiness} requires QA cases or evaluation assets for critical scenario: {scenario_id}")
        if readiness == "engineering_ready":
            if item.get("qa_status") != "approved":
                errors.append(f"engineering_ready requires approved QA coverage for critical scenario: {scenario_id}")
            requirement = item.get("automation_requirement")
            if requirement == "required" and item.get("automation_plan_status") not in (
                "planned",
                "implemented",
                "verified",
            ):
                errors.append(
                    f"engineering_ready requires an automation plan for critical scenario: {scenario_id}"
                )
    return errors


def _validate_delivery_risk_profile(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    readiness = _stage_readiness(spec)
    profile = spec.get("delivery_risk_profile")
    if not isinstance(profile, dict):
        errors.append("delivery_risk_profile must be an object")
        if readiness in PRODUCT_PROOF_REQUIRED_LABELS:
            errors.append(f"{readiness} requires delivery_risk_profile")
        return errors

    tier = profile.get("risk_tier")
    dimensions = profile.get("dimensions")
    if not isinstance(dimensions, dict):
        return errors

    dimension_floor = 0
    unknown_dimensions: list[str] = []
    for dimension, floor_by_value in RISK_DIMENSION_FLOORS.items():
        value = dimensions.get(dimension)
        if value == "unknown" or value is None:
            unknown_dimensions.append(dimension)
            continue
        floor = floor_by_value.get(value)
        if floor is not None:
            dimension_floor = max(dimension_floor, floor)

    if tier in RISK_LEVEL and RISK_LEVEL[tier] < dimension_floor:
        required_tier = f"R{dimension_floor}"
        errors.append(f"delivery_risk_profile.risk_tier {tier} is below required floor {required_tier}")

    if readiness in PRODUCT_PROOF_REQUIRED_LABELS:
        if tier not in RISK_LEVEL:
            errors.append(f"{readiness} requires delivery_risk_profile.risk_tier R0-R3")
        if unknown_dimensions:
            errors.append(
                f"{readiness} requires resolved delivery risk dimensions: " + ", ".join(unknown_dimensions)
            )
        if _is_unknown_or_empty(profile.get("rationale")):
            errors.append(f"{readiness} requires delivery_risk_profile.rationale")
        if tier in ("R1", "R2", "R3") and _is_unknown_or_empty(profile.get("required_controls")):
            errors.append(f"{readiness} requires delivery_risk_profile.required_controls for {tier}")

        assessment = profile.get("assessment")
        if not isinstance(assessment, dict) or assessment.get("status") != "confirmed":
            errors.append(f"{readiness} requires confirmed delivery_risk_profile.assessment")
        else:
            owners = spec.get("owners", {})
            decision_owner = owners.get("decision_owner") if isinstance(owners, dict) else None
            if assessment.get("confirmed_by") != decision_owner:
                errors.append(
                    f"{readiness} requires delivery risk confirmation by owners.decision_owner"
                )
            if _is_unknown_or_empty(assessment.get("assessed_by")):
                errors.append(f"{readiness} requires delivery_risk_profile.assessment.assessed_by")
            if not _is_iso_date(assessment.get("confirmed_at")):
                errors.append(f"{readiness} requires a valid delivery risk confirmation date")

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
    if readiness in ("validation_design_ready", "validation_execution_ready", "engineering_ready"):
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

    validation_design = validation.get("validation_design_ready")
    if readiness in ("validation_design_ready", "validation_execution_ready", "engineering_ready"):
        if not isinstance(validation_design, dict) or validation_design.get("status") != "ready":
            errors.append(f"{readiness} requires validation_plan.validation_design_ready.status=ready")

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
    errors.extend(_validate_business_success_scenarios(spec))
    errors.extend(_validate_delivery_risk_profile(spec))
    errors.extend(_validate_ui(spec, spec_path))
    errors.extend(_validate_review_gates(spec))
    errors.extend(_validate_friday_object_model(spec))
    errors.extend(_validate_memory_policy(spec))
    errors.extend(_validate_validation_plan(spec))
    errors.extend(_validate_scenario_coverage(spec))
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
