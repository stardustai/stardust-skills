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

    readiness = spec.get("readiness_label")
    if readiness == "engineering_ready":
        blockers = []
        owners = spec.get("owners", {})
        if isinstance(owners, dict):
            for key in ["business_owner", "product_owner", "engineering_owner", "qa_owner", "devops_owner"]:
                if owners.get(key) in (None, "", "unknown"):
                    blockers.append(f"owners.{key}")
        if missing_fields:
            blockers.append("missing_fields")
        if blockers:
            errors.append("engineering_ready is invalid while critical fields are unknown: " + ", ".join(blockers))

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
