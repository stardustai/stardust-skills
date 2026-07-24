# Vibe Coding

`vibe-coding` is Stardust's company-level engineering orchestration Skill. It consumes an approved Spec that passes the installed authoritative `spec-intake` validator and drives the repository through initialization, risk-adaptive architecture and technical-debt controls, planning, TDD, business-scenario E2E/Eval traceability, independent review, Git delivery, and optional SRE deployment.

## Input

- A JSON document accepted by the installed authoritative `spec-intake` validator with an `engineering_ready` / `ready_for_engineering` stage gate.
- Business-owner-confirmed `business_success_scenarios`.
- QA-approved scenario coverage and a confirmed delivery risk profile.
- A local repository plus an approved remote repository URL.

When the project is new, the Skill creates the standard contract. For an existing repository with a different coherent layout, it offers two organization choices: convert to the standard structure, or adapt in place by mapping actual document paths in `PROJECT.yaml` and README. Missing content is completed under the chosen organization. It separately offers only two safe technical-debt paths: full remediation or minimum safe remediation that excludes defective paths from the current feature.

## Output

- Root `README.md` and JSON-compatible `PROJECT.yaml`.
- Specs and plans under `docs/superpowers/`.
- A standard or adapted document organization, explicitly mapped in `PROJECT.yaml`; adapted layouts are also explained in README.
- Architecture, optional algorithm design, business goals/metrics, runtime constraints, QA normalized Spec/test design/test cases, tests, Evals, traceability, feedback contracts, evidence, runbook, and rollback records.
- An independent documentation-content review that binds every mapped responsibility and required topic to an exact locator and current file SHA-256.
- Small green commits, a pushed branch or PR, and optional deployment evidence.

## Responsibility model

Business defines the successful end-to-end flow. The Skill structures it and enforces gates. QA adds professional coverage. Engineering automates the checks and evidence. Later stages cannot silently rewrite the business outcome.

## Deterministic tools

From the Skill directory:

```bash
python3 scripts/validate_project.py --project-root /path/to/project
python3 scripts/validate_traceability.py --project-root /path/to/project --spec /path/to/spec.json --traceability /path/to/traceability.json --environment test
python3 scripts/validate_feedback.py --project-root /path/to/project --feedback /path/to/task-feedback.json --environment test
python3 scripts/run_project_checks.py --project-root /path/to/project --phase full --evidence /path/to/project/docs/evidence/full-latest.json
python3 scripts/validate_delivery.py --project /path/to/project/PROJECT.yaml --evidence /path/to/project/docs/evidence/full-latest.json --review-evidence /path/to/project/docs/evidence/review-latest.json --traceability /path/to/project/docs/traceability.json --environment test
python3 scripts/install_pre_commit.py --project-root /path/to/project
python3 scripts/self_test.py
```

The scripts use the Python standard library. `PROJECT.yaml` intentionally uses JSON syntax so it remains YAML-compatible without requiring an external parser.

## Referenced Skills

The orchestrator automatically selects Superpowers planning, TDD, debugging, review, worktree, subagent, and verification Skills. It uses `qa-generated-test-case` for QA coverage and optionally uses `production-devops-sre` when deployment is in scope.

Graphify is not a company-level Vibe Coding gate. A project follows it only if the project's own applicable agent rules require it.
