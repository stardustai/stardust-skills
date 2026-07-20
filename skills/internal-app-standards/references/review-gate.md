# Review Gate

## Contents

- Review process
- Severity levels
- Required checks
- Production decision

## Review Process

For code review, inspect the diff and enough surrounding code to understand behavior. Review against these categories:

- Stack consistency.
- Engineering structure and module boundaries.
- Frontend UX quality and Ant Design usage.
- Backend validation, authorization, error handling, and observability.
- PostgreSQL schema quality and migration safety.
- Docker/Kubernetes/deploy readiness.
- Tests and operational runbook.

## Severity Levels

- `BLOCKER`: must fix before merge or production. Examples: auth bypass, secret leak, destructive migration without plan, no production deployment path, data corruption risk.
- `HIGH`: should fix before production unless explicitly accepted. Examples: missing RBAC on sensitive API, missing migration for schema change, no readiness probe, critical path untested.
- `MEDIUM`: valid risk or maintainability issue that can be scheduled if production risk is bounded.
- `LOW`: style, naming, minor consistency, or documentation improvement.

## Required Checks

Production-bound systems should pass or have documented exceptions for:

- Repo follows standard structure or has an agreed migration path.
- Frontend uses React + Ant Design with non-demo layout and complete states.
- Backend uses TypeScript modules with clear controller/service/repository separation.
- API validates inputs and enforces backend authorization.
- PostgreSQL changes are migration-first and indexed for expected queries.
- Secrets and environment config are externalized.
- Docker images build without local-only assumptions.
- K8s manifests include probes, resources, config/secret references, and rollback path.
- Critical user flows have tests.
- Logs and metrics are sufficient for first-line incident diagnosis.

## Production Decision

Use one of:

- `pass`: no blocker/high issues, production checks passed.
- `pass with follow-ups`: only bounded medium/low risks remain, and follow-ups are explicit.
- `block`: any blocker remains, or high risks are not consciously accepted by the owner.

Never return a vague approval. Include evidence: files inspected, tests run, and assumptions.
