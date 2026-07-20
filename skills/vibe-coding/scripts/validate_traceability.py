#!/usr/bin/env python3
"""Validate approved scenario mappings and fresh business-outcome evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from schema_runtime import validate_instance


def load_object(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{label} does not exist: {path}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is invalid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} must contain an object")
        return {}
    return value


def has_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        stripped = value.strip()
        return len(stripped) >= 4 and stripped.startswith("__") and stripped.endswith("__")
    if isinstance(value, list):
        return any(has_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(has_placeholder(item) for item in value.values())
    return False


def string_list(value: Any) -> list[str] | None:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
        or len(set(value)) != len(value)
    ):
        return None
    return value


def valid_commands(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(
            isinstance(command, list)
            and bool(command)
            and all(isinstance(argument, str) and argument for argument in command)
            for command in value
        )
    )


def evaluate_rule(operator: Any, observed: Any, expected: Any) -> bool | None:
    try:
        if operator == "equals": return observed == expected
        if operator == "not_equals": return observed != expected
        if operator == "less_than": return observed < expected
        if operator == "less_than_or_equal": return observed <= expected
        if operator == "greater_than": return observed > expected
        if operator == "greater_than_or_equal": return observed >= expected
        if operator == "contains": return expected in observed
    except (TypeError, ValueError):
        return None
    return None


def current_commit(root: Path, errors: list[str]) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode:
        errors.append("project_root must be a Git repository with a current commit")
        return None
    return result.stdout.strip()


def parse_timestamp(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{field} must be an ISO timestamp with timezone")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} must be an ISO timestamp with timezone")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must be an ISO timestamp with timezone")
        return None
    return parsed.astimezone(timezone.utc)


def project_file(root: Path, value: Any, field: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{field} must be a project-relative path")
        return None
    path = Path(value)
    if path.is_absolute():
        errors.append(f"{field} must be a project-relative path")
        return None
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        errors.append(f"{field} must be a project-relative path confined to {root}")
        return None
    return resolved


def validate_evidence(
    path: Path,
    *,
    root: Path,
    label: str,
    scenario_id: str,
    signal_refs: list[str],
    signal_rules: dict[str, dict[str, Any]],
    expected_business_outcome: Any,
    expected_final_state: Any,
    commit: str | None,
    environment: str,
    max_age_minutes: int,
    allowed_commands: list[list[str]],
    errors: list[str],
) -> None:
    evidence = load_object(path, label, errors)
    if not evidence:
        return
    schema_root = Path(__file__).resolve().parents[1] / "assets/schemas"
    errors.extend(validate_instance(evidence, schema_root / "business-evidence.schema.json", label))
    if has_placeholder(evidence):
        errors.append(f"{label} contains an unresolved __PLACEHOLDER__ value")
    if evidence.get("scenario_id") != scenario_id:
        errors.append(f"{label}.scenario_id must be {scenario_id}")
    if evidence.get("expected_business_outcome") != expected_business_outcome:
        errors.append(f"{label}.expected_business_outcome must match the Business Owner-confirmed Spec")
    if evidence.get("expected_final_state") != expected_final_state:
        errors.append(f"{label}.expected_final_state must match the Business Owner-confirmed Spec")
    if evidence.get("commit") != commit:
        errors.append(f"{label}.commit must match the current commit")
    if evidence.get("environment") != environment:
        errors.append(f"{label}.environment must be {environment}")
    captured_at = parse_timestamp(evidence.get("captured_at"), f"{label}.captured_at", errors)
    if captured_at is not None:
        now = datetime.now(timezone.utc)
        if captured_at > now:
            errors.append(f"{label}.captured_at cannot be in the future")
        elif now - captured_at > timedelta(minutes=max_age_minutes):
            errors.append(f"{label} is stale: older than {max_age_minutes} minutes")
    if evidence.get("status") != "pass":
        errors.append(f"{label}.status must be pass")
    manifest_path = project_file(root, evidence.get("evidence_manifest"), f"{label}.evidence_manifest", errors)
    if manifest_path is not None:
        if not manifest_path.is_file():
            errors.append(f"{label}.evidence_manifest does not exist")
        else:
            actual_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            if evidence.get("evidence_sha256") != actual_sha:
                errors.append(f"{label}.evidence_sha256 must match the generated runner manifest")
            manifest = load_object(manifest_path, f"{label}.evidence_manifest", errors)
            errors.extend(validate_instance(manifest, schema_root / "evidence-manifest.schema.json", f"{label}.evidence_manifest"))
            manifest_git = manifest.get("git") if isinstance(manifest.get("git"), dict) else {}
            if manifest_git.get("commit") != commit or manifest.get("project_root") != str(root):
                errors.append(f"{label}.evidence_manifest must bind current commit and project root")
            manifest_started = parse_timestamp(manifest.get("started_at"), f"{label}.evidence_manifest.started_at", errors)
            manifest_finished = parse_timestamp(manifest.get("finished_at"), f"{label}.evidence_manifest.finished_at", errors)
            now = datetime.now(timezone.utc)
            if manifest_started is not None and manifest_finished is not None and manifest_started > manifest_finished:
                errors.append(f"{label}.evidence_manifest.started_at cannot follow finished_at")
            if manifest_finished is not None:
                if manifest_finished > now:
                    errors.append(f"{label}.evidence_manifest.finished_at cannot be in the future")
                elif now - manifest_finished > timedelta(minutes=max_age_minutes):
                    errors.append(f"{label}.evidence_manifest is stale")
                if captured_at is not None and not (
                    manifest_finished <= captured_at <= manifest_finished + timedelta(minutes=5)
                ):
                    errors.append(f"{label}.captured_at must closely follow the runner manifest")
            check_name = evidence.get("runner_check_name")
            checks = manifest.get("checks") if isinstance(manifest.get("checks"), list) else []
            matches = [item for item in checks if isinstance(item, dict) and item.get("name") == check_name]
            if len(matches) != 1:
                errors.append(f"{label}.evidence_manifest must contain exactly one declared runner check")
            else:
                check = matches[0]
                if check.get("command") not in allowed_commands:
                    errors.append(f"{label} runner check must match a contracted verification command")
                if check.get("status") != "passed" or check.get("exit_code") != 0:
                    errors.append(f"{label} runner check must have generated passing evidence")
                check_started = parse_timestamp(check.get("started_at"), f"{label}.runner_check.started_at", errors)
                check_finished = parse_timestamp(check.get("finished_at"), f"{label}.runner_check.finished_at", errors)
                if check_started is not None and check_finished is not None and check_started > check_finished:
                    errors.append(f"{label}.runner_check.started_at cannot follow finished_at")
                if manifest_started is not None and check_started is not None and check_started < manifest_started:
                    errors.append(f"{label}.runner_check.started_at cannot precede the manifest run")
                if manifest_finished is not None and check_finished is not None and check_finished > manifest_finished:
                    errors.append(f"{label}.runner_check.finished_at cannot follow the manifest run")
                if check_finished is not None and (check_finished > now or now - check_finished > timedelta(minutes=max_age_minutes)):
                    errors.append(f"{label}.runner_check evidence must be fresh")

    observations = evidence.get("business_observations")
    if not isinstance(observations, list) or not observations:
        errors.append(f"{label}.business_observations must contain measured business signals")
        return
    by_signal: dict[str, dict[str, Any]] = {}
    computed_results: list[bool] = []
    for index, observation in enumerate(observations):
        prefix = f"{label}.business_observations[{index}]"
        if not isinstance(observation, dict):
            errors.append(f"{prefix} must be an object")
            continue
        signal_id = observation.get("signal_id")
        if not isinstance(signal_id, str) or not signal_id:
            errors.append(f"{prefix}.signal_id must be a non-empty string")
            continue
        for field in ("source", "expected", "observed"):
            if field not in observation or observation[field] in (None, ""):
                errors.append(f"{prefix}.{field} must contain an observed business value")
        rule = signal_rules.get(signal_id)
        if rule is None:
            errors.append(f"{prefix}.signal_id has no Business Owner-approved measurement rule")
            continue
        if observation.get("source") != rule.get("source"):
            errors.append(f"{prefix}.source must match the approved measurement rule")
        if observation.get("expected") != rule.get("expected"):
            errors.append(f"{prefix}.expected must match the approved measurement rule")
        computed = evaluate_rule(rule.get("operator"), observation.get("observed"), rule.get("expected"))
        computed_passed = computed is True
        if computed is None:
            errors.append(f"{prefix} cannot evaluate the approved measurement rule")
        claimed_passed = observation.get("passed")
        if not isinstance(claimed_passed, bool):
            errors.append(f"{prefix}.passed must be a boolean")
        elif claimed_passed is not computed_passed:
            errors.append(f"{prefix}.passed must equal the validator-computed result")
        if not computed_passed:
            errors.append(f"{prefix} must pass because observed must equal expected")
        computed_results.append(computed_passed)
        if signal_id not in signal_refs:
            errors.append(f"{prefix}.signal_id must reference business_signal_refs")
            continue
        by_signal[signal_id] = observation
    missing = sorted(set(signal_refs) - set(by_signal))
    if missing:
        errors.append(f"{label}.business_observations must cover business_signal_refs: {', '.join(missing)}")
    computed_business_passed = bool(computed_results) and all(computed_results) and not missing
    if evidence.get("business_passed") is not computed_business_passed:
        errors.append(f"{label}.business_passed must equal the validator-computed business result")
    if not computed_business_passed:
        errors.append(f"{label}.business_passed must be true")


def validate(
    project_root: Path,
    spec_path: Path,
    traceability_path: Path,
    environment: str,
    max_age_minutes: int,
) -> list[str]:
    errors: list[str] = []
    root = project_root.resolve()
    commit = current_commit(root, errors)
    spec = load_object(spec_path, "spec", errors)
    traceability = load_object(traceability_path, "traceability", errors)
    if not spec or not traceability:
        return errors
    errors.extend(validate_instance(
        traceability,
        Path(__file__).resolve().parents[1] / "assets/schemas/traceability.schema.json",
        "traceability",
    ))
    if has_placeholder(traceability):
        errors.append("traceability contains an unresolved __PLACEHOLDER__ value")

    scenarios = spec.get("business_success_scenarios")
    if not isinstance(scenarios, list):
        errors.append("spec.business_success_scenarios must be an array")
        return errors
    critical_scenarios = {
        scenario.get("scenario_id"): scenario
        for scenario in scenarios
        if isinstance(scenario, dict)
        and scenario.get("scope_status") == "in_scope"
        and scenario.get("priority") == "critical"
        and isinstance(scenario.get("scenario_id"), str)
        and scenario.get("scenario_id")
    }

    validation_plan = spec.get("validation_plan")
    coverage_items = validation_plan.get("scenario_coverage") if isinstance(validation_plan, dict) else None
    if not isinstance(coverage_items, list):
        errors.append("spec.validation_plan.scenario_coverage must be an array")
        return errors
    coverage_by_id: dict[str, dict[str, Any]] = {}
    for index, coverage in enumerate(coverage_items):
        if not isinstance(coverage, dict) or not isinstance(coverage.get("scenario_id"), str):
            errors.append(f"spec.validation_plan.scenario_coverage[{index}] must identify a scenario")
            continue
        scenario_id = coverage["scenario_id"]
        if scenario_id in coverage_by_id:
            errors.append(f"duplicate authoritative scenario coverage for {scenario_id}")
        coverage_by_id[scenario_id] = coverage

    mappings = traceability.get("mappings")
    if not isinstance(mappings, list):
        errors.append("traceability.mappings must be an array")
        return errors
    mapping_by_id: dict[str, dict[str, Any]] = {}
    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            errors.append(f"traceability.mappings[{index}] must be an object")
            continue
        scenario_id = mapping.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id:
            errors.append(f"traceability.mappings[{index}].scenario_id must be a non-empty string")
            continue
        if scenario_id in mapping_by_id:
            errors.append(f"duplicate traceability mapping for {scenario_id}")
        mapping_by_id[scenario_id] = mapping

    for scenario_id in sorted(critical_scenarios):
        scenario = critical_scenarios[scenario_id]
        coverage = coverage_by_id.get(scenario_id)
        mapping = mapping_by_id.get(scenario_id)
        if coverage is None:
            errors.append(f"critical business scenario {scenario_id} has no authoritative scenario_coverage")
            continue
        if mapping is None:
            errors.append(f"critical business scenario {scenario_id} has no traceability mapping")
            continue
        if coverage.get("qa_status") != "approved":
            errors.append(f"{scenario_id} authoritative qa_status must be approved")
        if coverage.get("automation_requirement") == "required" and coverage.get("automation_plan_status") != "verified":
            errors.append(f"{scenario_id} authoritative automation_plan_status must be verified")
        for field in ("qa_case_refs", "automated_test_refs", "evaluation_asset_refs"):
            authoritative = string_list(coverage.get(field))
            mapped = string_list(mapping.get(field))
            if authoritative is None:
                errors.append(f"{scenario_id} authoritative {field} must contain at least one reference")
            elif mapped is None or set(mapped) != set(authoritative):
                errors.append(f"{scenario_id}.{field} must match authoritative spec scenario_coverage")
        signal_refs = string_list(mapping.get("business_signal_refs"))
        if signal_refs is None:
            errors.append(f"{scenario_id}.business_signal_refs must contain at least one observable business signal")
            signal_refs = []
        authoritative_signals = string_list(scenario.get("success_signals"))
        if authoritative_signals is None:
            errors.append(f"{scenario_id} authoritative success_signals must contain at least one business signal")
        elif set(signal_refs) != set(authoritative_signals):
            errors.append(f"{scenario_id}.business_signal_refs must match business-owned spec success_signals")
        rule_items = mapping.get("business_signal_rules")
        signal_rules: dict[str, dict[str, Any]] = {}
        if not isinstance(rule_items, list):
            errors.append(f"{scenario_id}.business_signal_rules must contain measurable rules")
        else:
            for rule_index, rule in enumerate(rule_items):
                if not isinstance(rule, dict) or not isinstance(rule.get("signal_id"), str):
                    errors.append(f"{scenario_id}.business_signal_rules[{rule_index}] must identify a signal")
                    continue
                if rule["signal_id"] in signal_rules:
                    errors.append(f"duplicate business signal rule for {rule['signal_id']}")
                signal_rules[rule["signal_id"]] = rule
            if set(signal_rules) != set(signal_refs):
                errors.append(f"{scenario_id}.business_signal_rules must exactly cover business_signal_refs")
        approval = mapping.get("business_owner_approval")
        confirmation = scenario.get("confirmation") if isinstance(scenario.get("confirmation"), dict) else {}
        if not isinstance(approval, dict) or approval.get("approved_by") != scenario.get("business_owner") or approval.get("confirmed_version") != confirmation.get("confirmed_version"):
            errors.append(f"{scenario_id}.business_owner_approval must match the confirmed Business Owner and Spec version")
        verification_commands = mapping.get("verification_commands")
        if not valid_commands(verification_commands):
            errors.append(f"{scenario_id}.verification_commands must contain executable argument arrays")
            verification_commands = []
        evidence_paths = string_list(mapping.get("evidence_paths"))
        if evidence_paths is None:
            errors.append(f"{scenario_id}.evidence_paths must contain at least one evidence path")
            continue
        for index, path_value in enumerate(evidence_paths):
            label = f"{scenario_id}.evidence[{index}]"
            path = project_file(root, path_value, f"{scenario_id}.evidence_paths[{index}]", errors)
            if path is not None:
                validate_evidence(
                    path,
                    root=root,
                    label=label,
                    scenario_id=scenario_id,
                    signal_refs=signal_refs,
                    signal_rules=signal_rules,
                    expected_business_outcome=scenario.get("expected_business_outcome"),
                    expected_final_state=scenario.get("expected_final_state"),
                    commit=commit,
                    environment=environment,
                    max_age_minutes=max_age_minutes,
                    allowed_commands=verification_commands,
                    errors=errors,
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--traceability", type=Path, required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--max-age-minutes", type=int, default=60)
    args = parser.parse_args()
    if args.max_age_minutes <= 0:
        print("ERROR: --max-age-minutes must be positive", file=sys.stderr)
        return 2
    errors = validate(
        args.project_root, args.spec, args.traceability, args.environment, args.max_age_minutes
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("VALID: approved scenario coverage is backed by fresh business evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
