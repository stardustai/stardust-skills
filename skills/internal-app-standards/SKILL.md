---
name: internal-app-standards
description: Standardize, design, generate, refactor, and review enterprise internal web systems built through AI coding. Use when Codex needs to create, modify, or review internal admin tools or business systems using React.js + Ant Design frontend, TypeScript backend, PostgreSQL database, Kubernetes deployment, monorepo engineering structure, database migrations, deploy scripts, production readiness checks, or code review against company technical standards.
---

# Internal App Standards

Use this skill to keep AI-coded internal systems consistent enough to run in production. Prefer concise, enforceable engineering decisions over broad architecture essays.

## Default Stack

Use these defaults for new internal systems unless the user explicitly overrides them or an existing repository has a stronger established standard:

- Monorepo: `pnpm` workspaces.
- Frontend: React.js + TypeScript + Vite + Ant Design.
- Backend: TypeScript + NestJS.
- API contract: REST JSON, typed request/response contracts, OpenAPI when exposed across teams.
- Database: PostgreSQL, migration-first schema management, committed migrations.
- Data access: Prisma by default for new systems; preserve the existing repository's data layer when standardizing.
- Deployment: Docker images + Kubernetes manifests using Kustomize-style `base` and environment overlays.

## Workflow

1. Classify the task:
   - New system: produce the standard structure, core modules, DB migrations, Docker/K8s files, and scripts.
   - Existing system: inspect first, then migrate incrementally without breaking working behavior.
   - Review only: read the diff and nearby code, then judge against the release gate.
2. Inspect the repository before changing it. Read package manifests, directory layout, DB migrations/schema, Dockerfiles, K8s manifests, CI scripts, and representative frontend/backend modules.
3. Load only the reference files needed for the current task:
   - `references/stack-standard.md` for repo layout, boundaries, contracts, and shared engineering rules.
   - `references/frontend-standard.md` for React + Ant Design UI implementation.
   - `references/backend-db-standard.md` for TypeScript backend and PostgreSQL design.
   - `references/deployment-standard.md` for Docker, Kubernetes, deploy scripts, and release safety.
   - `references/review-gate.md` for code review and production-readiness decisions.
4. For existing repositories, run:

   ```bash
   python3 <skill-directory>/scripts/check_internal_app.py <repo-path>
   ```

   Use the report as input, not as a substitute for reading the code.
5. Implement or review with small, coherent changes. Keep unrelated refactors out of scope.
6. Finish with the exact validation performed and any remaining production risks.

## Hard Rules

- Do not introduce Vue, Angular, Next.js, Express-only services, MongoDB, MySQL, serverless-only deployment, or ad hoc shell deployment for new systems unless the user explicitly asks.
- Do not build demo-style internal UIs. Internal tools should be dense, calm, table/form/detail oriented, and usable for repeated operational work.
- Do not put business logic in React components, NestJS controllers, SQL strings scattered through handlers, or deployment scripts.
- Do not hardcode secrets, database URLs, tokens, personal accounts, or environment-specific hostnames.
- Do not change database schema without a migration and rollback/compatibility notes.
- Do not mark a system production-ready without auth/RBAC assumptions, observability, resource limits, probes, deploy/rollback instructions, and critical-path tests.

## Expected Output

For design or generation tasks, output:

- Standard repo structure.
- Frontend page/module design.
- Backend module and API design.
- PostgreSQL schema and migration plan.
- Docker/K8s/deploy script plan.
- Key risks and validation plan.

For review tasks, output:

- Findings first, ordered by severity: `BLOCKER`, `HIGH`, `MEDIUM`, `LOW`.
- File and line references when available.
- Production decision: `pass`, `pass with follow-ups`, or `block`.
- Tests and checks actually run.
