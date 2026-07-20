#!/usr/bin/env python3
"""Validate fresh verification evidence against the exact project and remote revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def parse_timestamp(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{field} must be an ISO timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} must be an ISO timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed.astimezone(timezone.utc)


def is_absolute_url(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


def project_artifact(root: Path, value: Any, field: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        errors.append(f"{field} must be a project-relative path")
        return None
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        errors.append(f"{field} must remain inside the project root")
        return None
    if not path.is_file():
        errors.append(f"{field} does not exist: {value}")
        return None
    return path


def pr_matches_origin(pr_url: str, remote_url: Any) -> bool:
    if not isinstance(remote_url, str):
        return False
    remote = urlparse(remote_url)
    if remote.scheme == "file":
        return True
    pr = urlparse(pr_url)
    scp = re.fullmatch(r"[^@\s]+@([^:\s]+):(.+)", remote_url)
    remote_host = scp.group(1).lower() if scp else (remote.hostname or "").lower()
    remote_path = (scp.group(2) if scp else remote.path).removesuffix(".git").strip("/")
    pr_path = pr.path.strip("/")
    if not (remote_host and remote_path and (pr.hostname or "").lower() == remote_host):
        return False
    escaped_repo = re.escape(remote_path)
    if remote_host == "github.com" or remote_host.endswith(".github.com"):
        pattern = rf"{escaped_repo}/pull/[1-9][0-9]*"
    elif "gitlab" in remote_host:
        pattern = rf"{escaped_repo}/-/merge_requests/[1-9][0-9]*"
    elif "bitbucket" in remote_host:
        pattern = rf"{escaped_repo}/pull-requests/[1-9][0-9]*"
    else:
        pattern = rf"{escaped_repo}/(?:pull|pulls|merge_requests|pull-requests)/[1-9][0-9]*"
    return re.fullmatch(pattern, pr_path) is not None


def validate_manifest_check(
    root: Path, reference: Any, expected_sha256: Any, check_name: Any,
    project: dict[str, Any], head: str, field: str, now: datetime,
    max_age_minutes: int, errors: list[str],
) -> tuple[Path | None, datetime | None]:
    path = project_artifact(root, reference, f"{field}.evidence_manifest", errors)
    if path is None:
        return None, None
    actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_sha256 != actual_sha256:
        errors.append(f"{field}.evidence_sha256 must match the referenced evidence manifest")
    manifest = load_object(path, f"{field}.evidence_manifest", errors)
    schema_path = Path(__file__).resolve().parents[1] / "assets/schemas/evidence-manifest.schema.json"
    errors.extend(validate_instance(manifest, schema_path, f"{field}.evidence_manifest"))
    manifest_git = manifest.get("git") if isinstance(manifest.get("git"), dict) else {}
    if manifest_git.get("commit") != head:
        errors.append(f"{field}.evidence_manifest must be bound to current HEAD")
    if manifest.get("project_root") != str(root):
        errors.append(f"{field}.evidence_manifest must be bound to the project root")
    manifest_started = parse_timestamp(manifest.get("started_at"), f"{field}.evidence_manifest.started_at", errors)
    manifest_finished = parse_timestamp(manifest.get("finished_at"), f"{field}.evidence_manifest.finished_at", errors)
    if manifest_started is not None and manifest_finished is not None and manifest_started > manifest_finished:
        errors.append(f"{field}.evidence_manifest.started_at cannot follow finished_at")
    if manifest_finished is not None:
        if manifest_finished > now:
            errors.append(f"{field}.evidence_manifest.finished_at cannot be in the future")
        elif now - manifest_finished > timedelta(minutes=max_age_minutes):
            errors.append(f"{field}.evidence_manifest is stale")
    checks = manifest.get("checks") if isinstance(manifest.get("checks"), list) else []
    matches = [item for item in checks if isinstance(item, dict) and item.get("name") == check_name]
    if len(matches) != 1:
        errors.append(f"{field}.evidence_manifest must contain exactly one {check_name} check")
        return path, manifest_finished
    check = matches[0]
    commands = project.get("commands") if isinstance(project.get("commands"), dict) else {}
    if check.get("command") != commands.get(check_name):
        errors.append(f"{field} must bind to the exact PROJECT.yaml command")
    if check.get("status") != "passed" or check.get("exit_code") != 0:
        errors.append(f"{field} must bind to a passing generated check")
    check_started = parse_timestamp(check.get("started_at"), f"{field}.check.started_at", errors)
    check_finished = parse_timestamp(check.get("finished_at"), f"{field}.check.finished_at", errors)
    if check_started is not None and check_finished is not None and check_started > check_finished:
        errors.append(f"{field}.check.started_at cannot follow finished_at")
    if manifest_started is not None and check_started is not None and check_started < manifest_started:
        errors.append(f"{field}.check.started_at cannot precede the manifest run")
    if manifest_finished is not None and check_finished is not None and check_finished > manifest_finished:
        errors.append(f"{field}.check.finished_at cannot follow the manifest run")
    if check_finished is not None and (check_finished > now or now - check_finished > timedelta(minutes=max_age_minutes)):
        errors.append(f"{field}.check evidence must be fresh")
    return path, manifest_finished


def validate_review_evidence(
    review: dict[str, Any], project: dict[str, Any], root: Path, head: str,
    requires_pr: bool, now: datetime, max_age_minutes: int, primary_evidence_path: Path,
    errors: list[str],
) -> None:
    allowed_fields = {
        "$schema", "schema_version", "commit", "author_agent_id", "status", "reviews",
        "independent_verification", "runtime_evidence", "attestation", "reviewed_at",
        "pull_request_url",
    }
    extras = sorted(set(review) - allowed_fields)
    if extras:
        errors.append("review_evidence contains unsupported fields: " + ", ".join(extras))
    if review.get("$schema") != "skills/vibe-coding/assets/schemas/review-evidence.schema.json":
        errors.append("review_evidence.$schema must reference the published review evidence schema")
    if review.get("schema_version") != "1.0":
        errors.append("review_evidence.schema_version must be 1.0")
    if review.get("commit") != head:
        errors.append("review_evidence.commit must match current HEAD")
    if review.get("status") != "pass":
        errors.append("review_evidence.status must be pass")
    author = review.get("author_agent_id")
    if not isinstance(author, str) or not author:
        errors.append("review_evidence.author_agent_id must identify the implementation agent")

    artifacts = project.get("artifacts") if isinstance(project.get("artifacts"), dict) else {}
    repository = project.get("repository") if isinstance(project.get("repository"), dict) else {}
    required_artifacts = {artifacts.get("spec"), artifacts.get("design"), artifacts.get("plan")}
    required_artifacts.add(f"git:diff:{repository.get('baseline_commit')}..{head}")
    reviews = review.get("reviews")
    by_type: dict[str, dict[str, Any]] = {}
    reviewer_ids: list[str] = []
    contexts: list[str] = []
    if not isinstance(reviews, list):
        errors.append("review_evidence.reviews must be an array")
        reviews = []
    for index, item in enumerate(reviews):
        prefix = f"review_evidence.reviews[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        review_fields = {
            "review_type", "reviewer_id", "execution_context_id", "reviewed_artifacts",
            "status", "findings_count", "blocking_findings", "evidence_uri",
        }
        item_extras = sorted(set(item) - review_fields)
        if item_extras:
            errors.append(f"{prefix} contains unsupported fields: {', '.join(item_extras)}")
        review_type = item.get("review_type")
        if review_type not in {"spec", "code_quality", "independent_test"}:
            errors.append(f"{prefix}.review_type is unsupported")
        elif review_type in by_type:
            errors.append(f"duplicate independent review type: {review_type}")
        else:
            by_type[review_type] = item
        reviewer_id = item.get("reviewer_id")
        context = item.get("execution_context_id")
        if not isinstance(reviewer_id, str) or not reviewer_id or reviewer_id == author:
            errors.append(f"{prefix}.reviewer_id must identify an agent independent from the author")
        else:
            reviewer_ids.append(reviewer_id)
        if not isinstance(context, str) or not context:
            errors.append(f"{prefix}.execution_context_id must identify an independent run")
        else:
            contexts.append(context)
        reviewed = item.get("reviewed_artifacts")
        if not isinstance(reviewed, list) or not required_artifacts.issubset(set(reviewed)):
            errors.append(f"{prefix}.reviewed_artifacts must include Spec, Design, Plan, and exact Git diff")
        if item.get("status") != "pass" or item.get("blocking_findings") != 0:
            errors.append(f"{prefix} must pass with zero blocking findings")
        if not isinstance(item.get("findings_count"), int) or isinstance(item.get("findings_count"), bool) or item["findings_count"] < 0:
            errors.append(f"{prefix}.findings_count must be a non-negative integer")
        project_artifact(root, item.get("evidence_uri"), f"{prefix}.evidence_uri", errors)
    missing_types = sorted({"spec", "code_quality", "independent_test"} - set(by_type))
    if missing_types:
        errors.append("review_evidence.reviews is missing independent review types: " + ", ".join(missing_types))
    if len(reviewer_ids) != len(set(reviewer_ids)):
        errors.append("review_evidence reviewer_id values must be unique")
    if len(contexts) != len(set(contexts)):
        errors.append("review_evidence execution_context_id values must be unique")

    independent = review.get("independent_verification")
    primary_manifest = load_object(primary_evidence_path, "primary evidence manifest", errors)
    primary_run_id = primary_manifest.get("run_id")
    primary_sha256 = hashlib.sha256(primary_evidence_path.read_bytes()).hexdigest()
    if not isinstance(independent, dict):
        errors.append("review_evidence.independent_verification must be an object")
    else:
        independent_extras = sorted(set(independent) - {"commit", "checks"})
        if independent_extras:
            errors.append("review_evidence.independent_verification contains unsupported fields: " + ", ".join(independent_extras))
        if independent.get("commit") != head:
            errors.append("review_evidence.independent_verification.commit must match current HEAD")
        checks = independent.get("checks")
        by_name: dict[str, dict[str, Any]] = {}
        if isinstance(checks, list):
            for index, item in enumerate(checks):
                if not isinstance(item, dict):
                    errors.append(f"review_evidence.independent_verification.checks[{index}] must be an object")
                    continue
                check_extras = sorted(set(item) - {"name", "command", "exit_code", "captured_at", "evidence_manifest", "evidence_sha256"})
                if check_extras:
                    errors.append(f"review_evidence.independent_verification.checks[{index}] contains unsupported fields: {', '.join(check_extras)}")
                name = item.get("name")
                if isinstance(name, str) and name in by_name:
                    errors.append(f"duplicate independent verification check: {name}")
                elif isinstance(name, str):
                    by_name[name] = item
        else:
            errors.append("review_evidence.independent_verification.checks must be an array")
        commands = project.get("commands") if isinstance(project.get("commands"), dict) else {}
        for name in ("test_full", "eval_full"):
            check = by_name.get(name)
            if check is None:
                errors.append(f"review_evidence independent {name} execution is required")
                continue
            if check.get("command") != commands.get(name) or check.get("exit_code") != 0:
                errors.append(f"review_evidence independent {name} must run the exact project command successfully")
            manifest_path, manifest_finished = validate_manifest_check(
                root, check.get("evidence_manifest"), check.get("evidence_sha256"), name,
                project, head, f"review_evidence.independent_verification.{name}", now,
                max_age_minutes, errors,
            )
            if manifest_path == primary_evidence_path:
                errors.append(f"review_evidence independent {name} must use an independent runner manifest")
            if check.get("evidence_sha256") == primary_sha256:
                errors.append(f"review_evidence independent {name} manifest digest must differ from the primary run")
            if manifest_path is not None:
                independent_manifest = load_object(manifest_path, f"review_evidence independent {name} manifest", errors)
                if independent_manifest.get("run_id") == primary_run_id:
                    errors.append(f"review_evidence independent {name} must have a distinct runner run_id")
            captured = parse_timestamp(check.get("captured_at"), f"review_evidence.independent_verification.{name}.captured_at", errors)
            if captured is not None and (captured > now or now - captured > timedelta(minutes=max_age_minutes)):
                errors.append(f"review_evidence independent {name} evidence must be fresh")
            if captured is not None and manifest_finished is not None and not (
                manifest_finished <= captured <= manifest_finished + timedelta(minutes=5)
            ):
                errors.append(f"review_evidence independent {name}.captured_at must closely follow its runner manifest")

    runtime = review.get("runtime_evidence")
    runtime_policy = (project.get("verification") or {}).get("runtime", {})
    required_runtime = runtime_policy.get("required_evidence_fields") if isinstance(runtime_policy, dict) else []
    if not isinstance(runtime, dict):
        errors.append("review_evidence.runtime_evidence must be an object")
    else:
        for field in required_runtime if isinstance(required_runtime, list) else []:
            if field not in runtime or runtime[field] in (None, "", [], {}):
                errors.append(f"review_evidence.runtime_evidence.{field} must contain an observed value")
                continue
            observation = runtime[field]
            if not isinstance(observation, dict):
                errors.append(f"review_evidence.runtime_evidence.{field} must be a generated evidence reference")
                continue
            check_name = observation.get("check_name")
            allowed_runtime_checks = runtime_policy.get("check_names") if isinstance(runtime_policy, dict) else []
            if check_name not in allowed_runtime_checks:
                errors.append(f"review_evidence.runtime_evidence.{field}.check_name must be a configured runtime check")
            if observation.get("observed") in (None, "", [], {}):
                errors.append(f"review_evidence.runtime_evidence.{field}.observed must contain a measured value")
            validate_manifest_check(
                root, observation.get("evidence_manifest"), observation.get("evidence_sha256"),
                check_name, project, head, f"review_evidence.runtime_evidence.{field}", now,
                max_age_minutes, errors,
            )

    attestation = review.get("attestation")
    if not isinstance(attestation, dict):
        errors.append("review_evidence.attestation must be an object")
    else:
        attestation_extras = sorted(set(attestation) - {"provider", "run_id", "artifact_uri"})
        if attestation_extras:
            errors.append("review_evidence.attestation contains unsupported fields: " + ", ".join(attestation_extras))
        for field in ("provider", "run_id"):
            if not isinstance(attestation.get(field), str) or not attestation[field]:
                errors.append(f"review_evidence.attestation.{field} must be a non-empty string")
        project_artifact(root, attestation.get("artifact_uri"), "review_evidence.attestation.artifact_uri", errors)

    reviewed_at = parse_timestamp(review.get("reviewed_at"), "review_evidence.reviewed_at", errors)
    if reviewed_at is not None:
        if reviewed_at > now:
            errors.append("review_evidence.reviewed_at cannot be in the future")
        elif now - reviewed_at > timedelta(minutes=max_age_minutes):
            errors.append("review evidence is stale")
    pr_url = review.get("pull_request_url")
    if requires_pr:
        if not is_absolute_url(pr_url):
            errors.append("review_evidence.pull_request_url must be an absolute URL when PR is required")
        elif not pr_matches_origin(pr_url, repository.get("remote_url")):
            errors.append("review_evidence.pull_request_url must belong to the configured origin repository")
    elif pr_url not in (None, "") and not is_absolute_url(pr_url):
        errors.append("review_evidence.pull_request_url must be null or an absolute URL")


def status_paths(root: Path, ignored_paths: list[Path]) -> list[str]:
    result = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if result.returncode != 0:
        return ["<git-status-failed>"]
    ignored: set[str] = set()
    for path in ignored_paths:
        try:
            ignored.add(str(path.resolve().relative_to(root)))
        except ValueError:
            pass
    paths: list[str] = []
    for line in result.stdout.splitlines():
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        value = value.strip('"')
        if value not in ignored:
            paths.append(value)
    return sorted(paths)


def validate(
    project_path: Path,
    evidence_path: Path,
    review_evidence_path: Path,
    traceability_path: Path,
    environment: str,
    max_age_minutes: int,
) -> list[str]:
    errors: list[str] = []
    project_path = project_path.resolve()
    evidence_path = evidence_path.resolve()
    review_evidence_path = review_evidence_path.resolve()
    traceability_path = traceability_path.resolve()
    root = project_path.parent
    for path, label in (
        (evidence_path, "evidence"),
        (review_evidence_path, "review evidence"),
        (traceability_path, "traceability"),
    ):
        if not path.is_relative_to(root):
            errors.append(f"{label} path must remain inside the project root")
    project = load_object(project_path, "PROJECT.yaml", errors)
    evidence = load_object(evidence_path, "evidence manifest", errors)
    review_evidence = load_object(review_evidence_path, "review evidence", errors)
    if errors:
        return errors

    schema_root = Path(__file__).resolve().parents[1] / "assets/schemas"
    errors.extend(validate_instance(project, schema_root / "project.schema.json", "PROJECT.yaml"))
    errors.extend(validate_instance(evidence, schema_root / "evidence-manifest.schema.json", "evidence manifest"))
    errors.extend(validate_instance(review_evidence, schema_root / "review-evidence.schema.json", "review evidence"))

    project_validator = Path(__file__).resolve().with_name("validate_project.py")
    project_result = subprocess.run(
        [sys.executable, str(project_validator), "--project-root", str(root)], cwd=root,
        capture_output=True, text=True, check=False,
    )
    if project_result.returncode != 0:
        detail = (project_result.stdout + project_result.stderr).strip()
        errors.append(f"project contract validation failed: {detail}")

    if evidence.get("project_root") != str(root):
        errors.append("evidence.project_root must match the PROJECT.yaml directory")
    artifacts = project.get("artifacts") if isinstance(project.get("artifacts"), dict) else {}
    spec_rel = artifacts.get("spec")
    spec_path = (root / spec_rel).resolve() if isinstance(spec_rel, str) else None
    if spec_path is None or not spec_path.is_file() or not spec_path.is_relative_to(root):
        errors.append("PROJECT.yaml artifacts.spec must be a project-confined file")
    elif hashlib.sha256(spec_path.read_bytes()).hexdigest() != artifacts.get("spec_sha256"):
        errors.append("PROJECT.yaml artifacts.spec_sha256 must match the current Spec content")

    if evidence.get("schema_version") != "1.0":
        errors.append("evidence.schema_version must be 1.0")
    if evidence.get("phase") != "full":
        errors.append("evidence.phase must be full")
    started_at = parse_timestamp(evidence.get("started_at"), "evidence.started_at", errors)
    finished_at = parse_timestamp(evidence.get("finished_at"), "evidence.finished_at", errors)
    if started_at is not None and finished_at is not None and started_at > finished_at:
        errors.append("evidence.started_at cannot be after evidence.finished_at")
    now = datetime.now(timezone.utc)
    if finished_at is not None:
        if finished_at > now:
            errors.append("evidence.finished_at cannot be in the future")
        elif now - finished_at > timedelta(minutes=max_age_minutes):
            errors.append(f"evidence is stale: older than {max_age_minutes} minutes")

    commands = project.get("commands") if isinstance(project.get("commands"), dict) else {}
    verification = project.get("verification") if isinstance(project.get("verification"), dict) else {}
    inventory = verification.get("check_inventory")
    if not isinstance(inventory, list):
        errors.append("PROJECT.yaml verification.check_inventory must be an array")
        inventory = []
    for required in ("test_full", "eval_full"):
        if required not in inventory:
            errors.append(f"PROJECT.yaml verification.check_inventory must include {required}")
    checks = evidence.get("checks")
    if not isinstance(checks, list):
        errors.append("evidence.checks must be an array")
        checks = []
    by_name: dict[str, dict[str, Any]] = {}
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("name"), str):
            errors.append("each evidence check must have a name")
            continue
        name = check["name"]
        if name in by_name:
            errors.append(f"duplicate evidence check: {name}")
        by_name[name] = check
    unexpected = sorted(set(by_name) - set(inventory))
    if unexpected:
        errors.append("evidence contains checks outside PROJECT.yaml inventory: " + ", ".join(unexpected))
    for name in inventory:
        check = by_name.get(name)
        if check is None:
            errors.append(f"fresh {name} evidence is required")
            continue
        if check.get("command") != commands.get(name):
            errors.append(f"{name}.command must exactly match PROJECT.yaml commands.{name}")
        if check.get("status") != "passed":
            errors.append(f"{name}.status must be passed")
        timeout = check.get("timeout_seconds")
        expected_timeout = (project.get("command_timeouts_seconds") or {}).get(name)
        if timeout != expected_timeout:
            errors.append(f"{name}.timeout_seconds must match PROJECT.yaml command_timeouts_seconds.{name}")
        for stream in ("stdout", "stderr"):
            summary = check.get(stream)
            if not isinstance(summary, dict):
                errors.append(f"{name}.{stream} must be a bounded output summary object")
            elif (
                not isinstance(summary.get("byte_count"), int)
                or not isinstance(summary.get("sha256"), str)
                or len(summary.get("sha256", "")) != 64
                or not isinstance(summary.get("summary"), str)
            ):
                errors.append(f"{name}.{stream} must contain byte_count, sha256, and summary")
        check_started = parse_timestamp(check.get("started_at"), f"{name}.started_at", errors)
        check_finished = parse_timestamp(check.get("finished_at"), f"{name}.finished_at", errors)
        if check_started is not None and check_finished is not None and check_started > check_finished:
            errors.append(f"{name}.started_at cannot be after {name}.finished_at")
        if check_finished is not None:
            if check_finished > now:
                errors.append(f"{name}.finished_at cannot be in the future")
            elif now - check_finished > timedelta(minutes=max_age_minutes):
                errors.append(f"{name} evidence is stale")
        if started_at is not None and check_started is not None and check_started < started_at:
            errors.append(f"{name}.started_at cannot precede the evidence run")
        if finished_at is not None and check_finished is not None and check_finished > finished_at:
            errors.append(f"{name}.finished_at cannot follow the evidence run")
        if check.get("exit_code") != 0:
            errors.append(f"{name} did not pass")

    branch = git(root, "branch", "--show-current").stdout.strip()
    head_result = git(root, "rev-parse", "HEAD")
    head = head_result.stdout.strip() if head_result.returncode == 0 else ""
    evidence_git = evidence.get("git") if isinstance(evidence.get("git"), dict) else {}
    if evidence_git.get("branch") != branch:
        errors.append("evidence.git.branch must match the current Git branch")
    if evidence_git.get("commit") != head:
        errors.append("evidence.git.commit must match current HEAD")
    if evidence_git.get("clean") is not True:
        errors.append("evidence.git.clean must be true")
    dirty = status_paths(root, [evidence_path, review_evidence_path])
    if dirty:
        errors.append("delivery requires a clean working tree; found: " + ", ".join(dirty))
    origin = git(root, "remote", "get-url", "origin")
    repository = project.get("repository") if isinstance(project.get("repository"), dict) else {}
    if origin.returncode != 0 or origin.stdout.strip() != repository.get("remote_url"):
        errors.append("PROJECT.yaml repository.remote_url must match git origin")
    if branch != repository.get("feature_branch"):
        errors.append("current branch must match PROJECT.yaml repository.feature_branch")
    remote = git(root, "ls-remote", "--exit-code", "origin", f"refs/heads/{branch}")
    remote_revision = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else ""
    if not remote_revision:
        errors.append("delivery branch must exist on origin")
    if remote_revision != head:
        errors.append("remote branch revision and current HEAD must match")

    delivery = project.get("delivery") if isinstance(project.get("delivery"), dict) else {}
    requires_pr = delivery.get("requires_pr")
    if not isinstance(requires_pr, bool):
        errors.append("delivery.requires_pr must be a boolean")
    validate_review_evidence(
        review_evidence, project, root, head, requires_pr, now, max_age_minutes,
        evidence_path, errors,
    )

    trace_validator = Path(__file__).resolve().with_name("validate_traceability.py")
    if spec_path is not None and spec_path.is_file() and traceability_path.is_file():
        trace_result = subprocess.run(
            [
                sys.executable,
                str(trace_validator),
                "--project-root",
                str(root),
                "--spec",
                str(spec_path),
                "--traceability",
                str(traceability_path),
                "--environment",
                environment,
                "--max-age-minutes",
                str(max_age_minutes),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if trace_result.returncode != 0:
            detail = (trace_result.stdout + trace_result.stderr).strip()
            errors.append(f"business traceability validation failed: {detail}")
    elif not traceability_path.is_file():
        errors.append("traceability evidence contract does not exist")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--review-evidence", type=Path, required=True)
    parser.add_argument("--traceability", type=Path, required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--max-age-minutes", type=int, default=60)
    args = parser.parse_args()
    if args.max_age_minutes <= 0:
        print("ERROR: --max-age-minutes must be positive", file=sys.stderr)
        return 2
    errors = validate(
        args.project,
        args.evidence,
        args.review_evidence,
        args.traceability,
        args.environment,
        args.max_age_minutes,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("VALID: evidence is fresh and bound to the exact project, commands, commit, and remote branch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
