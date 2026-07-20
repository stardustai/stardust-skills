#!/usr/bin/env python3
"""Validate a task feedback contract against fresh measured evidence."""

from __future__ import annotations

import argparse
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


def current_commit(root: Path, errors: list[str]) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode:
        errors.append("project_root must be a Git repository with a current commit")
        return None
    return result.stdout.strip()


def project_file(root: Path, value: Any, field: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        errors.append(f"{field} must be a project-relative path")
        return None
    resolved = (root / value).resolve()
    if not resolved.is_relative_to(root):
        errors.append(f"{field} must be a project-relative path confined to {root}")
        return None
    return resolved


def string_list(value: Any) -> list[str] | None:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
        or len(set(value)) != len(value)
    ):
        return None
    return value


def evaluate_rule(operator: Any, observed: Any, expected: Any) -> bool | None:
    """Evaluate one declared pass/fail rule without trusting a claimed result."""
    try:
        if operator == "equals":
            return observed == expected
        if operator == "not_equals":
            return observed != expected
        if operator == "less_than":
            return observed < expected
        if operator == "less_than_or_equal":
            return observed <= expected
        if operator == "greater_than":
            return observed > expected
        if operator == "greater_than_or_equal":
            return observed >= expected
        if operator == "contains":
            return expected in observed
    except (TypeError, ValueError):
        return None
    return None


def validate_evidence(
    path: Path,
    *,
    label: str,
    phase: str,
    task_id: str,
    signals: dict[str, dict[str, Any]],
    rules_by_signal: dict[str, list[dict[str, Any]]],
    commit: str | None,
    environment: str,
    max_age_minutes: int,
    allowed_commands: list[list[str]] | None,
    errors: list[str],
) -> None:
    evidence = load_object(path, label, errors)
    if not evidence:
        return
    if has_placeholder(evidence):
        errors.append(f"{label} contains an unresolved __PLACEHOLDER__ value")
    if evidence.get("task_id") != task_id:
        errors.append(f"{label}.task_id must be {task_id}")
    if evidence.get("phase") != phase:
        errors.append(f"{label}.phase must be {phase}")
    if evidence.get("commit") != commit:
        errors.append(f"{label}.commit must match the contracted {phase} commit")
    if evidence.get("environment") != environment:
        errors.append(f"{label}.environment must be {environment}")
    captured_at = parse_timestamp(evidence.get("captured_at"), f"{label}.captured_at", errors)
    if captured_at is not None:
        now = datetime.now(timezone.utc)
        if captured_at > now:
            errors.append(f"{label}.captured_at cannot be in the future")
        elif now - captured_at > timedelta(minutes=max_age_minutes):
            errors.append(f"{label} is stale: older than {max_age_minutes} minutes")
    status = evidence.get("status")
    if phase == "result" and status != "pass":
        errors.append(f"{label}.status must be pass")
    if phase == "baseline" and status not in {"pass", "expected_fail"}:
        errors.append(f"{label}.status must be pass or expected_fail")
    verification = evidence.get("verification")
    if not isinstance(verification, dict):
        errors.append(f"{label}.verification must record the executed command and exit code")
    else:
        command = verification.get("command")
        if not (
            isinstance(command, list)
            and command
            and all(isinstance(argument, str) and argument for argument in command)
        ):
            errors.append(f"{label}.verification.command must be an executable argument array")
        elif allowed_commands is not None and command not in allowed_commands:
            errors.append(f"{label}.verification.command must match a contracted verification command")
        exit_code = verification.get("exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            errors.append(f"{label}.verification.exit_code must be an integer")
        elif phase == "result" and exit_code != 0:
            errors.append(f"{label}.verification.exit_code must be 0")
        elif phase == "baseline" and status == "expected_fail" and exit_code == 0:
            errors.append(f"{label}.verification.exit_code must be non-zero for expected_fail")
        elif phase == "baseline" and status == "pass" and exit_code != 0:
            errors.append(f"{label}.verification.exit_code must be 0 for pass")
    observations = evidence.get("observations")
    if not isinstance(observations, list) or not observations:
        errors.append(f"{label}.observations must contain measured signal results")
        return
    observed_ids: set[str] = set()
    for index, observation in enumerate(observations):
        prefix = f"{label}.observations[{index}]"
        if not isinstance(observation, dict):
            errors.append(f"{prefix} must be an object")
            continue
        signal_id = observation.get("signal_id")
        if not isinstance(signal_id, str) or signal_id not in signals:
            errors.append(f"{prefix}.signal_id must reference an observable signal")
            continue
        observed_ids.add(signal_id)
        signal = signals[signal_id]
        if observation.get("source") != signal.get("source"):
            errors.append(f"{prefix}.source must match the feedback contract")
        if observation.get("expected") != signal.get("expected"):
            errors.append(f"{prefix}.expected must match the feedback contract")
        if observation.get("observed") in (None, ""):
            errors.append(f"{prefix}.observed must contain a measured value")
        claimed_passed = observation.get("passed")
        if not isinstance(claimed_passed, bool):
            errors.append(f"{prefix}.passed must be a boolean")
            continue
        rules = rules_by_signal.get(signal_id, [])
        computed_results = [
            evaluate_rule(rule.get("operator"), observation.get("observed"), rule.get("expected"))
            for rule in rules
        ]
        if any(result is None for result in computed_results):
            errors.append(f"{prefix} cannot evaluate the contracted pass/fail rule against observed value")
            continue
        computed_passed = bool(computed_results) and all(computed_results)
        if claimed_passed is not computed_passed:
            errors.append(f"{prefix}.passed must equal the validator-computed result")
        if phase == "result" and not computed_passed:
            errors.append(f"{prefix} must pass the contracted rule")
    missing = sorted(set(signals) - observed_ids)
    if missing:
        errors.append(f"{label}.observations must cover signals: {', '.join(missing)}")


def validate(root: Path, feedback_path: Path, environment: str, max_age_minutes: int) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    commit = current_commit(root, errors)
    feedback = load_object(feedback_path, "feedback", errors)
    if not feedback:
        return errors
    errors.extend(validate_instance(
        feedback, Path(__file__).resolve().parents[1] / "assets/schemas/task-feedback.schema.json", "feedback"
    ))
    if has_placeholder(feedback):
        errors.append("feedback contains an unresolved __PLACEHOLDER__ value")
    task_id = feedback.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        errors.append("feedback.task_id must be a non-empty string")
        task_id = "<invalid-task>"
    if feedback.get("current_commit") != commit:
        errors.append("feedback.current_commit must match the current commit")
    if feedback.get("environment") != environment:
        errors.append(f"feedback.environment must be {environment}")
    if string_list(feedback.get("business_goal_refs")) is None:
        errors.append("feedback.business_goal_refs must contain at least one reference")
    if not isinstance(feedback.get("target"), str) or not feedback["target"]:
        errors.append("feedback.target must be a non-empty observable target")

    signal_items = feedback.get("observable_signals")
    signals: dict[str, dict[str, Any]] = {}
    if not isinstance(signal_items, list) or not signal_items:
        errors.append("feedback.observable_signals must contain at least one signal")
    else:
        for index, signal in enumerate(signal_items):
            prefix = f"feedback.observable_signals[{index}]"
            if not isinstance(signal, dict):
                errors.append(f"{prefix} must be an object")
                continue
            signal_id = signal.get("signal_id")
            if not isinstance(signal_id, str) or not signal_id:
                errors.append(f"{prefix}.signal_id must be a non-empty string")
                continue
            if signal_id in signals:
                errors.append(f"duplicate observable signal: {signal_id}")
            signals[signal_id] = signal
            for field in ("source", "expected"):
                if field not in signal or signal[field] in (None, ""):
                    errors.append(f"{prefix}.{field} must be observable")

    rules = feedback.get("pass_fail_rules")
    covered_signals: set[str] = set()
    rules_by_signal: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(rules, list) or not rules:
        errors.append("feedback.pass_fail_rules must contain at least one rule")
    else:
        for index, rule in enumerate(rules):
            prefix = f"feedback.pass_fail_rules[{index}]"
            if not isinstance(rule, dict):
                errors.append(f"{prefix} must be an object")
                continue
            signal_id = rule.get("signal_id")
            if signal_id not in signals:
                errors.append(f"{prefix}.signal_id references an unknown observable signal")
            elif isinstance(signal_id, str):
                covered_signals.add(signal_id)
                rules_by_signal.setdefault(signal_id, []).append(rule)
            for field in ("rule_id", "operator", "expected"):
                if field not in rule or rule[field] in (None, ""):
                    errors.append(f"{prefix}.{field} is required")
    for signal_id in sorted(set(signals) - covered_signals):
        errors.append(f"observable signal {signal_id} has no pass/fail rule")

    commands = feedback.get("verification_commands")
    commands_valid = (
        isinstance(commands, list)
        and commands
        and all(
            isinstance(command, list)
            and command
            and all(isinstance(argument, str) and argument for argument in command)
            for command in commands
        )
    )
    if not commands_valid:
        errors.append("feedback.verification_commands must contain executable argument arrays")
        commands = []
    rollback = feedback.get("rollback_method")
    if not isinstance(rollback, str) or not rollback or has_placeholder(rollback):
        errors.append("feedback.rollback_method must be concrete and contain no placeholder")

    baseline = feedback.get("baseline")
    if not isinstance(baseline, dict):
        errors.append("feedback.baseline must be an object")
    else:
        measured_at = parse_timestamp(
            baseline.get("measured_at"), "feedback.baseline.measured_at", errors
        )
        if measured_at is not None:
            now = datetime.now(timezone.utc)
            if measured_at > now:
                errors.append("feedback.baseline.measured_at cannot be in the future")
            elif now - measured_at > timedelta(minutes=max_age_minutes):
                errors.append(
                    f"feedback.baseline.measured_at is stale: older than {max_age_minutes} minutes"
                )
        baseline_commit = baseline.get("commit")
        if not isinstance(baseline_commit, str) or not baseline_commit:
            errors.append("baseline.commit must be a non-empty Git commit")
        else:
            exists = subprocess.run(
                ["git", "cat-file", "-e", f"{baseline_commit}^{{commit}}"], cwd=root,
                capture_output=True, text=True, check=False,
            )
            if exists.returncode != 0:
                errors.append("baseline.commit must resolve to a Git commit")
            elif commit is not None and subprocess.run(
                ["git", "merge-base", "--is-ancestor", baseline_commit, commit], cwd=root,
                capture_output=True, text=True, check=False,
            ).returncode != 0:
                errors.append("baseline.commit must be an ancestor of the current commit")
        if baseline.get("environment") != environment:
            errors.append(f"baseline.environment must be {environment}")
        paths = string_list(baseline.get("evidence_paths"))
        if paths is None:
            errors.append("feedback.baseline.evidence_paths must contain at least one path")
        else:
            for index, value in enumerate(paths):
                path = project_file(root, value, f"feedback.baseline.evidence_paths[{index}]", errors)
                if path is not None:
                    validate_evidence(
                        path,
                        label=f"baseline evidence[{index}]",
                        phase="baseline",
                        task_id=task_id,
                        signals=signals,
                        rules_by_signal=rules_by_signal,
                        commit=baseline_commit if isinstance(baseline_commit, str) else None,
                        environment=environment,
                        max_age_minutes=max_age_minutes,
                        allowed_commands=None,
                        errors=errors,
                    )

    evidence_paths = string_list(feedback.get("evidence_paths"))
    if evidence_paths is None:
        errors.append("feedback.evidence_paths must contain at least one path")
    else:
        for index, value in enumerate(evidence_paths):
            path = project_file(root, value, f"feedback.evidence_paths[{index}]", errors)
            if path is not None:
                validate_evidence(
                    path,
                    label=f"result evidence[{index}]",
                    phase="result",
                    task_id=task_id,
                    signals=signals,
                    rules_by_signal=rules_by_signal,
                    commit=commit,
                    environment=environment,
                    max_age_minutes=max_age_minutes,
                    allowed_commands=commands,
                    errors=errors,
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--feedback", type=Path, required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--max-age-minutes", type=int, default=60)
    args = parser.parse_args()
    if args.max_age_minutes <= 0:
        print("ERROR: --max-age-minutes must be positive", file=sys.stderr)
        return 2
    errors = validate(args.project_root, args.feedback, args.environment, args.max_age_minutes)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("VALID: task feedback is bound to fresh measured evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
