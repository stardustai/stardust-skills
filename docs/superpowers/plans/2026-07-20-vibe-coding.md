# Vibe Coding Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a company-level `vibe-coding` orchestration Skill that converts an approved `spec-intake` v1.5 Spec into stable, tested, evaluated, reviewable, and deliverable code.

**Architecture:** Keep `SKILL.md` as the stage-gated orchestrator and move detailed policy into focused references. Consume, rather than duplicate, the `spec-intake` contract; enforce repository readiness, risk-adaptive controls, business-scenario traceability, loop-engineering feedback, and delivery evidence through standard-library Python validators and versioned templates.

**Tech Stack:** Agent Skills Markdown, JSON Schema-compatible contracts, Python 3 standard library, Bash repository tests, Git/GitHub delivery.

---

## File map

- `skills/vibe-coding/SKILL.md`: trigger contract and ten-stage automatic orchestration.
- `skills/vibe-coding/README.md`: operator-facing capability, inputs, outputs, and verification commands.
- `skills/vibe-coding/references/*.md`: detailed company standards loaded only at the relevant stage.
- `skills/vibe-coding/assets/schemas/*.json`: machine-readable project, feedback, traceability, and evidence contracts.
- `skills/vibe-coding/assets/templates/*.tpl`: project documentation and delivery templates.
- `skills/vibe-coding/scripts/*.py`: project/readiness/traceability/check/delivery validators and pre-commit installer.
- `skills/vibe-coding/tests/*.py`: unit tests for deterministic controls.
- `skills/vibe-coding/evals/evals.json`: positive, negative, boundary, and adversarial Skill behavior evals.
- `skills/spec-intake/**`: publish the already validated v1.5 business-success and delivery-risk input contract.
- `tests/vibe-coding.test.sh`: repository-level structure and behavior smoke test.
- `README.md`: list and explain the new Skill.

### Task 1: Publish the approved design baseline

**Files:**
- Create: `docs/superpowers/specs/2026-07-20-vibe-coding-design.md`
- Create: `docs/superpowers/specs/company-vibe-coding/*.md`

- [x] Copy the approved rolling design and companion standards into this repository.
- [x] Mark the repository copy as the implementation baseline and retain the confirmed responsibility model: business defines success flows, Skill structures them, QA expands coverage, engineering automates evidence.
- [x] Verify no Graphify requirement is introduced.

### Task 2: Synchronize `spec-intake` v1.5

**Files:**
- Modify: `skills/spec-intake/**`

- [x] Mirror the validated local `spec-intake` Skill into the repository with checksums.
- [x] Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/spec-intake/scripts/test_validate_spec.py` and expect 16 passing tests.
- [x] Validate `skills/spec-intake/examples/insurance-broker-proposal.spec.json` and expect `VALID`.
- [x] Commit the complete v1.5 input-contract change independently.

### Task 3: Write failing `vibe-coding` contract tests

**Files:**
- Create: `skills/vibe-coding/tests/test_validate_project.py`
- Create: `skills/vibe-coding/tests/test_validate_traceability.py`
- Create: `skills/vibe-coding/tests/test_run_project_checks.py`
- Create: `skills/vibe-coding/tests/test_validate_delivery.py`
- Create: `tests/vibe-coding.test.sh`

- [x] Add tests proving formal development rejects non-`engineering_ready` Specs, missing remote URLs, missing mandatory documentation, unapproved technical-debt paths, and incomplete critical-scenario mappings.
- [x] Add tests proving configured checks execute without `shell=True`, fresh evidence is recorded, and failed commands block delivery.
- [x] Add tests proving successful full test plus Eval evidence can pass delivery validation.
- [x] Run the tests before implementation and confirm they fail because validators do not exist.

### Task 4: Implement deterministic contracts and validators

**Files:**
- Create: `skills/vibe-coding/assets/schemas/*.json`
- Create: `skills/vibe-coding/scripts/validate_project.py`
- Create: `skills/vibe-coding/scripts/validate_traceability.py`
- Create: `skills/vibe-coding/scripts/run_project_checks.py`
- Create: `skills/vibe-coding/scripts/install_pre_commit.py`
- Create: `skills/vibe-coding/scripts/validate_delivery.py`
- Create: `skills/vibe-coding/scripts/self_test.py`

- [x] Implement strict JSON-compatible `PROJECT.yaml` parsing with actionable field-level failures.
- [x] Validate the `spec-intake` stage gate, remote repository, required/conditional artifacts, risk tier, owners, commands, pre-commit policy, and selected technical-debt strategy.
- [x] Validate every in-scope critical business-success scenario is mapped to QA and executable verification evidence.
- [x] Execute command arrays sequentially, capture timestamps/stdout/stderr/exit status, and write an evidence manifest.
- [x] Install a versioned pre-commit hook that runs the configured full test suite.
- [x] Reject delivery unless full tests and Eval passed with fresh evidence and the configured push/PR policy is satisfied.
- [x] Run all unit tests and expect success.

### Task 5: Implement the orchestration Skill and standards

**Files:**
- Create: `skills/vibe-coding/SKILL.md`
- Create: `skills/vibe-coding/README.md`
- Create: `skills/vibe-coding/references/*.md`
- Create: `skills/vibe-coding/assets/templates/*.tpl`

- [x] Define the ten-stage path: intake, repository inspection, initialization/debt choice, architecture and planning, feedback contract, TDD implementation, traceable QA/Eval, independent review, Git delivery, optional deployment.
- [x] Require user multiple-choice confirmation for product behavior, business goals, architecture/data/risk/permission changes, and plan-external refactoring.
- [x] Encode the two allowed technical-debt choices: full remediation or minimum safe remediation with the affected debt excluded from the current implementation path.
- [x] Reference Superpowers development Skills, `qa-generated-test-case`, and optional `production-devops-sre` by Skill name.
- [x] Prefer subagents for complex separable work while preserving an independent spec/code/test review when subagents are unavailable.
- [x] Add complete project, architecture, algorithm, business goal/metrics, runtime, testing, Eval, traceability, runbook, PR, evidence, and rule-audit templates.

### Task 6: Add behavior evals and repository integration

**Files:**
- Create: `skills/vibe-coding/evals/evals.json`
- Modify: `README.md`

- [x] Add evals for new projects, existing-project initialization, unit-test-only false completion, multi-person small direct-push policy, large-feature PR policy, discovered refactoring, business/spec conflict, and optional deployment.
- [x] Assert the Skill never accepts self-reported success without fresh business-observable evidence.
- [x] Add the Skill to repository documentation, usage, permission, and directory sections.

### Task 7: Verify, independently review, and publish

**Files:**
- Modify only files required by review findings.

- [x] Run Skill quick validation, all Python tests, all repository shell tests, JSON parsing, secret scan, and `git diff --check`.
- [x] Dispatch independent spec-compliance and code-quality reviewers; fix all verified findings and rerun checks.
- [x] Commit the `vibe-coding` feature with a detailed message.
- [x] Push `codex/vibe-coding` to `origin`.
- [x] Create a ready PR containing summary, risk, validation evidence, deployment impact, and review policy.
