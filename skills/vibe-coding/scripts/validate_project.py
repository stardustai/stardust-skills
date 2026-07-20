#!/usr/bin/env python3
"""Validate a Vibe Coding project contract and its engineering-ready inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from schema_runtime import validate_instance


REQUIRED_DOCUMENT_KEYS = (
    "business_goal", "system_architecture", "runtime_constraints", "test_plan",
    "traceability", "eval_plan", "runbook", "technical_debt_register",
    "agent_rules_audit", "qa_normalized_spec", "qa_test_design", "qa_test_cases",
)
DOCUMENT_TOPICS = {
    "business_goal": ("problem_and_users", "business_goal", "success_metrics", "business_success_scenarios"),
    "system_architecture": ("system_context", "boundaries", "components", "data_flow", "authorization", "observability", "failure_recovery"),
    "runtime_constraints": ("environments", "versions", "commands", "configuration", "resources", "dependencies", "observability", "recovery"),
    "test_plan": ("scope", "traceability", "test_layers", "commands", "test_data", "pass_fail_rules", "evidence"),
    "traceability": ("requirements", "business_scenarios", "qa_cases", "automated_checks", "evidence"),
    "eval_plan": ("acceptance_cases", "datasets", "metrics", "thresholds", "commands", "evidence"),
    "runbook": ("start_stop", "health", "monitoring", "incidents", "rollback", "ownership"),
    "technical_debt_register": ("definition", "evidence", "strategy", "scope", "verification"),
    "agent_rules_audit": ("sources", "scope", "compliance", "evidence", "exceptions"),
    "qa_normalized_spec": ("scope", "requirements", "business_rules", "success_scenarios", "risks"),
    "qa_test_design": ("coverage_strategy", "positive", "negative", "permissions", "recovery"),
    "qa_test_cases": ("case_ids", "preconditions", "steps", "expected_results", "traceability"),
    "algorithm_design": ("problem", "inputs_outputs", "algorithm", "constraints", "evaluation", "failure_modes"),
    "ui_spec": ("user_flows", "screens", "states", "validation", "accessibility", "permissions"),
}
COMMAND_NAMES = (
    "install", "start", "stop", "build", "pre_commit_full", "test_full",
    "eval_full", "smoke", "health_check",
)
CHANGE_DIMENSIONS = (
    "architecture", "public_api", "data_schema", "permissions",
    "dependency_or_integration", "migration_or_bulk_write",
    "technical_debt_or_refactor", "material_spec_or_plan", "critical_runtime",
)
OWNER_MAPPING = {
    "business": "business_owner", "product": "product_owner",
    "engineering": "engineering_owner", "qa": "qa_owner", "decision": "decision_owner",
}
DEPLOYMENT_STATES = {
    "not_started", "blocked", "non_production_deployed", "production_rollout",
    "production_deployed", "rolled_back",
}
APPLICABILITY_CATEGORIES = (
    "format_static_type", "unit", "integration", "business_e2e", "permissions",
    "ui_accessibility", "performance_cost", "recovery_rollback", "eval",
)
PLACEHOLDER_PATTERN = re.compile(r"__[A-Z0-9_]+__|\b(?:TODO|TBD)\b", re.IGNORECASE)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{label} does not exist: {path}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"{label} must be JSON-compatible YAML: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} must contain an object")
        return {}
    return value


def required_object(parent: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def required_string(parent: dict[str, Any], key: str, field: str, errors: list[str]) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty string")
        return ""
    return value


def project_path(root: Path, value: str, field: str, errors: list[str]) -> Path | None:
    if not value:
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{field} must be a normalized project-relative path")
        return None
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        errors.append(f"{field} must remain inside the project root")
        return None
    return path


def validate_url(value: str, errors: list[str]) -> None:
    parsed = urlparse(value)
    if parsed.scheme == "file" and Path(parsed.path).is_absolute():
        return
    if re.fullmatch(r"[^@\s]+@[^:\s]+:.+", value):
        return
    if not parsed.scheme or not parsed.netloc:
        errors.append("repository.remote_url must be an absolute repository URL")


def validate_command(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value or any(not isinstance(arg, str) or not arg for arg in value):
        errors.append(f"{field} must be a non-empty array of non-empty command arguments")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_document(path: Path, label: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"required document is missing: {label}")
        return
    content = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(content) < 40:
        errors.append(f"required document is an incomplete placeholder: {label}")
    if PLACEHOLDER_PATTERN.search(content):
        errors.append(f"required document contains unresolved placeholders: {label}")


def reviewed_section(content: str, locator: str) -> str | None:
    lines = content.splitlines()
    matches = [index for index, line in enumerate(lines) if line.strip() == locator]
    if len(matches) != 1:
        return None
    start = matches[0] + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].lstrip().startswith("#"):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def validate_documentation(
    root: Path,
    project: dict[str, Any],
    artifact_paths: dict[str, Path],
    errors: list[str],
) -> dict[str, Path]:
    readme = root / "README.md"
    validate_document(readme, "README.md", errors)
    readme_content = readme.read_text(encoding="utf-8", errors="replace") if readme.is_file() else ""
    documentation = required_object(project, "documentation", errors)
    organization = documentation.get("organization")
    if organization not in {"standard", "adapt_existing"}:
        errors.append("documentation.organization must be standard or adapt_existing")
    paths = documentation.get("paths")
    if not isinstance(paths, dict):
        errors.append("documentation.paths must map every required document responsibility")
        paths = {}
    conditional = documentation.get("conditional_paths")
    if not isinstance(conditional, dict):
        errors.append("documentation.conditional_paths must map algorithm_design and ui_spec")
        conditional = {}

    resolved: dict[str, Path] = {}
    for key in REQUIRED_DOCUMENT_KEYS:
        value = paths.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"documentation.paths.{key} must be a non-empty project path")
            continue
        path = project_path(root, value, f"documentation.paths.{key}", errors)
        if path is not None:
            resolved[key] = path
            validate_document(path, value, errors)
    for key in ("algorithm_design", "ui_spec"):
        value = conditional.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            errors.append(f"documentation.conditional_paths.{key} must be a project path or null")
            continue
        path = project_path(root, value, f"documentation.conditional_paths.{key}", errors)
        if path is not None:
            resolved[key] = path
            validate_document(path, value, errors)

    if organization == "standard":
        canonical_conditional = {
            "algorithm_design": "docs/algorithm-design.md",
            "ui_spec": "docs/ui-spec.md",
        }
        for key, value in conditional.items():
            if value is not None and value != canonical_conditional.get(key):
                errors.append(
                    f"documentation.conditional_paths.{key} must use {canonical_conditional[key]} in standard structure"
                )

    readme_entries = {"organization": organization}
    readme_entries.update({key: value for key, value in paths.items() if isinstance(value, str)})
    readme_entries.update({key: value for key, value in conditional.items() if isinstance(value, str)})
    for key, path in artifact_paths.items():
        if path.is_relative_to(root):
            readme_entries[key] = str(path.relative_to(root))
    content_review_value = documentation.get("content_review")
    if isinstance(content_review_value, str):
        readme_entries["content_review"] = content_review_value
    readme_lines = {line.strip() for line in readme_content.splitlines()}
    missing_from_readme = sorted(
        key for key, value in readme_entries.items()
        if f"- `{key}`: `{value}`" not in readme_lines
    )
    if missing_from_readme:
        errors.append(
            "README documentation map must contain exact responsibility-to-path entries for: "
            + ", ".join(missing_from_readme)
        )

    review_value = required_string(documentation, "content_review", "documentation.content_review", errors)
    review_path = project_path(root, review_value, "documentation.content_review", errors)
    if review_path is None:
        return resolved
    review = load_json(review_path, "documentation content review", errors)
    if not review:
        return resolved
    errors.extend(validate_instance(
        review,
        Path(__file__).resolve().parents[1] / "assets/schemas/documentation-review.schema.json",
        "documentation content review",
    ))
    if review.get("status") != "pass":
        errors.append("documentation content review status must be pass")
    reviewer_id = review.get("reviewer_id")
    author_id = review.get("author_agent_id")
    if isinstance(reviewer_id, str) and isinstance(author_id, str) and reviewer_id.strip().casefold() == author_id.strip().casefold():
        errors.append("documentation content review reviewer must differ from the document author agent")
    if review.get("execution_context_id") == review.get("author_execution_context_id"):
        errors.append("documentation content review must run in an independent execution context")
    documents = review.get("documents")
    if not isinstance(documents, list):
        errors.append("documentation content review documents must be an array")
        return resolved
    by_responsibility: dict[str, dict[str, Any]] = {}
    for item in documents:
        if not isinstance(item, dict) or not isinstance(item.get("responsibility"), str):
            continue
        responsibility = item["responsibility"]
        if responsibility in by_responsibility:
            errors.append(f"documentation content review contains duplicate responsibility: {responsibility}")
        by_responsibility[responsibility] = item
    if set(by_responsibility) != set(resolved):
        missing = sorted(set(resolved) - set(by_responsibility))
        extra = sorted(set(by_responsibility) - set(resolved))
        if missing:
            errors.append("documentation content review is missing responsibilities: " + ", ".join(missing))
        if extra:
            errors.append("documentation content review contains unmapped responsibilities: " + ", ".join(extra))
    for responsibility, path in resolved.items():
        item = by_responsibility.get(responsibility)
        if not isinstance(item, dict) or not path.is_file():
            continue
        expected_relative = str(path.relative_to(root))
        if item.get("path") != expected_relative:
            errors.append(f"documentation content review path mismatch for {responsibility}")
        if item.get("sha256") != sha256(path):
            errors.append(f"documentation content review checksum mismatch for {responsibility}")
        coverage = item.get("coverage")
        if not isinstance(coverage, list):
            errors.append(f"documentation content review coverage must be an array for {responsibility}")
            continue
        covered: dict[str, dict[str, str]] = {}
        used_locators: set[str] = set()
        for entry in coverage:
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("topic"), str)
                and isinstance(entry.get("locator"), str)
                and isinstance(entry.get("section_sha256"), str)
            ):
                if entry["topic"] in covered:
                    errors.append(f"documentation content review contains duplicate topic for {responsibility}: {entry['topic']}")
                if entry["locator"] in used_locators:
                    errors.append(
                        f"documentation content review requires a unique full-line locator for every topic in {responsibility}"
                    )
                used_locators.add(entry["locator"])
                covered[entry["topic"]] = entry
        expected_topics = set(DOCUMENT_TOPICS[responsibility])
        if set(covered) != expected_topics:
            errors.append(f"documentation content review topics are incomplete for {responsibility}")
        content = path.read_text(encoding="utf-8", errors="replace")
        for topic, entry in covered.items():
            locator = entry["locator"]
            section = reviewed_section(content, locator)
            if section is None:
                errors.append(
                    f"documentation content review requires a unique full-line locator for {responsibility}.{topic}"
                )
                continue
            if len(section) < 40 or PLACEHOLDER_PATTERN.search(section):
                errors.append(f"documentation content review section is incomplete for {responsibility}.{topic}")
                continue
            section_hash = hashlib.sha256(section.encode("utf-8")).hexdigest()
            if entry["section_sha256"] != section_hash:
                errors.append(f"documentation content review section checksum mismatch for {responsibility}.{topic}")
    return resolved


def validate_spec_with_authority(spec_path: Path, errors: list[str]) -> dict[str, Any]:
    validator = Path(__file__).resolve().parents[2] / "spec-intake" / "scripts" / "validate_spec.py"
    if not validator.is_file():
        errors.append(f"authoritative spec-intake validator is missing: {validator}")
        return {}
    result = subprocess.run(
        [sys.executable, str(validator), str(spec_path)], cwd=spec_path.parent,
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        errors.append(f"authoritative spec-intake validation failed: {detail}")
        return {}
    return load_json(spec_path, "artifacts.spec", errors)


def validate_spec_alignment(project: dict[str, Any], spec: dict[str, Any], errors: list[str]) -> None:
    if spec.get("spec_version") != "1.5":
        errors.append("spec.spec_version must be 1.5")
    stage = spec.get("stage_gate") if isinstance(spec.get("stage_gate"), dict) else {}
    if stage.get("readiness_label") != "engineering_ready" or stage.get("decision") != "ready_for_engineering":
        errors.append("spec must be engineering_ready with decision ready_for_engineering")
    profile = spec.get("delivery_risk_profile") if isinstance(spec.get("delivery_risk_profile"), dict) else {}
    risk = project.get("risk") if isinstance(project.get("risk"), dict) else {}
    if risk.get("tier") != profile.get("risk_tier"):
        errors.append("risk.tier must match spec.delivery_risk_profile.risk_tier")
    project_owners = project.get("owners") if isinstance(project.get("owners"), dict) else {}
    spec_owners = spec.get("owners") if isinstance(spec.get("owners"), dict) else {}
    for project_key, spec_key in OWNER_MAPPING.items():
        if project_owners.get(project_key) != spec_owners.get(spec_key):
            errors.append(f"owners.{project_key} must match spec.owners.{spec_key}")


def porcelain_paths(root: Path) -> list[str]:
    result = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if result.returncode != 0:
        return []
    paths: list[str] = []
    for line in result.stdout.splitlines():
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.append(value.strip('"'))
    return sorted(paths)


def validate_git_state(root: Path, repository: dict[str, Any], errors: list[str]) -> None:
    inside = git(root, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        errors.append("project root must be a Git working tree")
        return
    origin = git(root, "remote", "get-url", "origin")
    if origin.returncode != 0:
        errors.append("git origin must exist and be readable")
    elif origin.stdout.strip() != repository.get("remote_url"):
        errors.append("repository.remote_url must match the configured git origin")
    branch = git(root, "branch", "--show-current").stdout.strip()
    if not branch:
        errors.append("Git HEAD must not be detached")
    elif branch != repository.get("feature_branch"):
        errors.append("repository.feature_branch must match the current Git branch")
    head = git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        errors.append("Git HEAD must resolve to a commit")
        return
    for field in ("baseline_commit", "last_green_commit"):
        commit = repository.get(field)
        exists = git(root, "cat-file", "-e", f"{commit}^{{commit}}") if isinstance(commit, str) else None
        if exists is None or exists.returncode != 0:
            errors.append(f"repository.{field} must resolve to a Git commit")
        elif git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode != 0:
            errors.append(f"repository.{field} must be an ancestor of current HEAD")
    remote_url = repository.get("remote_url")
    default_branch = repository.get("default_branch")
    if isinstance(remote_url, str) and isinstance(default_branch, str):
        remote_default = git(root, "ls-remote", "--exit-code", "origin", f"refs/heads/{default_branch}")
        if remote_default.returncode != 0:
            errors.append("repository.default_branch must exist on origin")
    actual_dirty = porcelain_paths(root)
    state = repository.get("working_tree")
    known = repository.get("known_dirty_paths")
    if state == "clean":
        if actual_dirty:
            errors.append(f"repository declares a clean working tree but found: {', '.join(actual_dirty)}")
        if known != []:
            errors.append("clean repository state requires empty repository.known_dirty_paths")
    elif state == "known_dirty":
        if not isinstance(known, list) or not known or sorted(known) != actual_dirty:
            errors.append("repository.known_dirty_paths must exactly match the current working tree changes")
    else:
        errors.append("repository.working_tree must be clean or known_dirty")


def derive_requires_pr(risk_tier: Any, delivery: dict[str, Any]) -> bool:
    dimensions = delivery.get("change_dimensions") if isinstance(delivery.get("change_dimensions"), dict) else {}
    return bool(
        risk_tier in {"R2", "R3"}
        or delivery.get("explicit_pr_required") is True
        or delivery.get("direct_push_permitted") is not True
        or (delivery.get("collaboration") == "multi_person" and delivery.get("change_size") == "large")
        or any(dimensions.get(name) is True for name in CHANGE_DIMENSIONS)
    )


def validate_verification(root: Path, project: dict[str, Any], errors: list[str]) -> None:
    commands = required_object(project, "commands", errors)
    for name in COMMAND_NAMES:
        validate_command(commands.get(name), f"commands.{name}", errors)
    for name, value in commands.items():
        validate_command(value, f"commands.{name}", errors)
    timeouts = required_object(project, "command_timeouts_seconds", errors)
    default_timeout = timeouts.get("default")
    if not isinstance(default_timeout, (int, float)) or isinstance(default_timeout, bool) or default_timeout <= 0:
        errors.append("command_timeouts_seconds.default must be a positive number")
    for name in commands:
        timeout = timeouts.get(name)
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
            errors.append(f"command_timeouts_seconds.{name} must be a positive number")
    extras = sorted(set(timeouts) - set(commands) - {"default"})
    if extras:
        errors.append("command_timeouts_seconds contains unknown commands: " + ", ".join(extras))
    verification = required_object(project, "verification", errors)
    inventory = verification.get("check_inventory")
    if not isinstance(inventory, list) or not inventory or any(name not in commands for name in inventory):
        errors.append("verification.check_inventory must name configured commands")
        inventory = []
    for required in ("pre_commit_full", "test_full", "eval_full"):
        if required not in inventory:
            errors.append(f"verification.check_inventory must include {required}")
    for section_name in ("runtime", "business"):
        section = verification.get(section_name)
        if not isinstance(section, dict):
            errors.append(f"verification.{section_name} must be an object")
            continue
        names = section.get("check_names")
        if not isinstance(names, list) or not names or any(name not in inventory for name in names):
            errors.append(f"verification.{section_name}.check_names must be non-empty and included in check_inventory")
        fields = section.get("required_evidence_fields")
        if not isinstance(fields, list) or not fields or any(not isinstance(field, str) or not field for field in fields):
            errors.append(f"verification.{section_name}.required_evidence_fields must be non-empty strings")
    applicability = verification.get("applicability")
    if not isinstance(applicability, dict):
        errors.append("verification.applicability must define every verification category")
        return
    owners = project.get("owners") if isinstance(project.get("owners"), dict) else {}
    allowed_approvers = {owners.get("qa"), owners.get("decision")}
    unknown = sorted(set(applicability) - set(APPLICABILITY_CATEGORIES))
    missing = sorted(set(APPLICABILITY_CATEGORIES) - set(applicability))
    if unknown:
        errors.append("verification.applicability contains unknown categories: " + ", ".join(unknown))
    if missing:
        errors.append("verification.applicability is missing categories: " + ", ".join(missing))
    risk = project.get("risk") if isinstance(project.get("risk"), dict) else {}
    features = project.get("features") if isinstance(project.get("features"), dict) else {}
    always_required = {"business_e2e", "eval"}
    if features.get("business_ui") is True:
        always_required.add("ui_accessibility")
    if risk.get("tier") in {"R2", "R3"}:
        always_required.update({"permissions", "recovery_rollback"})
    for category in APPLICABILITY_CATEGORIES:
        field = f"verification.applicability.{category}"
        policy = applicability.get(category)
        if not isinstance(policy, dict):
            errors.append(f"{field} must be an object")
            continue
        status = policy.get("status")
        if status not in {"required", "not_applicable"}:
            errors.append(f"{field}.status must be required or not_applicable")
        for key in ("reason", "evidence", "approved_by"):
            if not isinstance(policy.get(key), str) or not policy[key].strip():
                errors.append(f"{field}.{key} must be a non-empty string")
        evidence_path = project_path(root, policy.get("evidence", ""), f"{field}.evidence", errors)
        if evidence_path is not None and not evidence_path.is_file():
            errors.append(f"{field}.evidence must reference an existing project file")
        if status == "not_applicable" and policy.get("approved_by") not in allowed_approvers:
            errors.append(f"{field}.approved_by must be the QA or decision owner for an exemption")
        if category in always_required and status != "required":
            errors.append(f"{field} is required for this project and cannot be exempted")


def validate_project(root: Path) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    project = load_json(root / "PROJECT.yaml", "PROJECT.yaml", errors)
    if not project:
        return errors
    errors.extend(validate_instance(
        project, Path(__file__).resolve().parents[1] / "assets/schemas/project.schema.json", "PROJECT.yaml"
    ))
    for key in ("schema_version", "project_id", "name", "status"):
        required_string(project, key, key, errors)
    if project.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")

    repository = required_object(project, "repository", errors)
    remote_url = required_string(repository, "remote_url", "repository.remote_url", errors)
    if remote_url:
        validate_url(remote_url, errors)
    for key in ("default_branch", "feature_branch", "baseline_commit", "last_green_commit"):
        required_string(repository, key, f"repository.{key}", errors)
    if not isinstance(repository.get("known_dirty_paths"), list):
        errors.append("repository.known_dirty_paths must be an array")

    artifacts = required_object(project, "artifacts", errors)
    artifact_paths: dict[str, Path] = {}
    for key in ("spec", "design", "plan"):
        value = required_string(artifacts, key, f"artifacts.{key}", errors)
        expected_prefix = "docs/superpowers/plans/" if key == "plan" else "docs/superpowers/specs/"
        if value and not value.startswith(expected_prefix):
            errors.append(f"artifacts.{key} must use the Superpowers path prefix {expected_prefix}")
        path = project_path(root, value, f"artifacts.{key}", errors)
        if path is not None:
            artifact_paths[key] = path
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"artifacts.{key} does not reference a non-empty file: {value}")
            elif key in {"design", "plan"}:
                validate_document(path, value, errors)
    expected_checksum = required_string(artifacts, "spec_sha256", "artifacts.spec_sha256", errors)
    if "spec" in artifact_paths and artifact_paths["spec"].is_file() and sha256(artifact_paths["spec"]) != expected_checksum:
        errors.append("artifacts.spec_sha256 does not match the pinned Spec content")
    document_paths = validate_documentation(root, project, artifact_paths, errors)

    risk = required_object(project, "risk", errors)
    if risk.get("tier") not in {"R0", "R1", "R2", "R3"}:
        errors.append("risk.tier must be R0, R1, R2, or R3")
    if risk.get("source") not in {artifacts.get("spec"), f"{artifacts.get('spec')}#/delivery_risk_profile"}:
        errors.append("risk.source must point to artifacts.spec delivery_risk_profile")
    owners = required_object(project, "owners", errors)
    for key in OWNER_MAPPING:
        required_string(owners, key, f"owners.{key}", errors)
    validate_verification(root, project, errors)

    features = required_object(project, "features", errors)
    for key in ("algorithmic", "business_ui"):
        if not isinstance(features.get(key), bool):
            errors.append(f"features.{key} must be a boolean")
    debt = required_object(project, "technical_debt", errors)
    strategy = debt.get("strategy")
    if strategy not in {"full_remediation", "minimum_safe"}:
        errors.append("technical_debt.strategy must be full_remediation or minimum_safe")
    required_string(debt, "approved_by", "technical_debt.approved_by", errors)
    decision = required_string(debt, "decision_record", "technical_debt.decision_record", errors)
    decision_path = project_path(root, decision, "technical_debt.decision_record", errors)
    if decision_path is not None and (not decision_path.is_file() or decision_path.stat().st_size == 0):
        errors.append("technical_debt.decision_record must reference a non-empty file")
    debt_document = document_paths.get("technical_debt_register")
    if decision_path is not None and debt_document is not None and decision_path != debt_document:
        errors.append("technical_debt.decision_record must match documentation.paths.technical_debt_register")
    excluded_ids, excluded_paths = debt.get("excluded_debt_ids"), debt.get("excluded_paths")
    if not isinstance(excluded_ids, list) or any(not isinstance(v, str) or not v for v in excluded_ids):
        errors.append("technical_debt.excluded_debt_ids must be an array of non-empty IDs")
        excluded_ids = []
    if not isinstance(excluded_paths, list) or any(not isinstance(v, str) or not v for v in excluded_paths):
        errors.append("technical_debt.excluded_paths must be an array of non-empty project paths")
        excluded_paths = []
    else:
        for index, value in enumerate(excluded_paths):
            project_path(root, value, f"technical_debt.excluded_paths[{index}]", errors)
    if strategy == "minimum_safe" and (not excluded_ids or not excluded_paths):
        errors.append("minimum_safe requires excluded debt IDs and paths")
    if strategy == "full_remediation" and (excluded_ids or excluded_paths):
        errors.append("full_remediation cannot leave excluded debt IDs or paths")

    pre_commit = required_object(project, "pre_commit", errors)
    if pre_commit.get("hook_path") != ".githooks/pre-commit" or pre_commit.get("full_suite") is not True:
        errors.append("pre_commit must use .githooks/pre-commit with full_suite=true")
    delivery = required_object(project, "delivery", errors)
    if delivery.get("collaboration") not in {"single_owner", "multi_person"}:
        errors.append("delivery.collaboration must be single_owner or multi_person")
    if delivery.get("change_size") not in {"small", "large"}:
        errors.append("delivery.change_size must be small or large")
    for key in ("direct_push_permitted", "explicit_pr_required", "requires_pr"):
        if not isinstance(delivery.get(key), bool):
            errors.append(f"delivery.{key} must be a boolean")
    dimensions = delivery.get("change_dimensions")
    if not isinstance(dimensions, dict) or any(not isinstance(dimensions.get(name), bool) for name in CHANGE_DIMENSIONS):
        errors.append("delivery.change_dimensions must define every structural trigger as a boolean")
    derived_pr = derive_requires_pr(risk.get("tier"), delivery)
    expected_mode = "pull_request" if derived_pr else "direct_push"
    if delivery.get("requires_pr") is not derived_pr or delivery.get("mode") != expected_mode:
        errors.append(f"delivery must match derived PR policy: requires_pr={str(derived_pr).lower()}, mode={expected_mode}")

    deployment = required_object(project, "deployment", errors)
    if not isinstance(deployment.get("required"), bool):
        errors.append("deployment.required must be a boolean")
    if deployment.get("sre_skill") != "production-devops-sre":
        errors.append("deployment.sre_skill must be production-devops-sre")
    if deployment.get("lifecycle_status") not in DEPLOYMENT_STATES:
        errors.append("deployment.lifecycle_status must be a supported lifecycle status")
    if deployment.get("required") and not isinstance(deployment.get("target_environment"), str):
        errors.append("deployment.target_environment must be set when deployment.required=true")

    for enabled, key in ((features.get("algorithmic"), "algorithm_design"), (features.get("business_ui"), "ui_spec")):
        if enabled and key not in document_paths:
            errors.append(f"required conditional document is missing or empty: documentation.conditional_paths.{key}")

    if "spec" in artifact_paths and artifact_paths["spec"].is_file():
        spec = validate_spec_with_authority(artifact_paths["spec"], errors)
        if spec:
            validate_spec_alignment(project, spec, errors)
            ui_requirements = spec.get("ui_requirements")
            if isinstance(ui_requirements, dict) and isinstance(ui_requirements.get("has_ui"), bool):
                if features.get("business_ui") is not ui_requirements.get("has_ui"):
                    errors.append("features.business_ui must match spec.ui_requirements.has_ui")
    validate_git_state(root, repository, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate_project(args.project_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("VALID: project contract, authoritative Spec, Git, and delivery policy gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
