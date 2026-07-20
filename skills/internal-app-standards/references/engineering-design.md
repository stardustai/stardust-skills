# Engineering Design Standard

## Contents

- Design workflow
- Architecture defaults
- Module boundaries
- API design
- Data design
- Workflow and integration design
- Frontend design
- Operational design
- Design output template

## Design Workflow

For a new system or substantial feature, design before generating code. Keep the design concise, but make every production-critical decision explicit:

1. Define users, roles, permissions, and core workflows.
2. Identify bounded business capabilities and map them to modules.
3. Define API contracts, request/response types, error shapes, and idempotency rules.
4. Define PostgreSQL tables, relationships, constraints, indexes, audit columns, and migration order.
5. Define frontend routes, pages, tables, forms, detail/edit surfaces, and state coverage.
6. Define long-running jobs, integrations, retries, and failure handling.
7. Define runtime configuration, secrets, deployment topology, probes, resource limits, and rollback path.
8. Define tests and checks for the critical path.
9. List risks, accepted exceptions, and validation still required.

## Architecture Defaults

- Start with a modular monolith: one web app, one API service, one PostgreSQL database, clear feature modules.
- Split services only when independent scaling, ownership, deployment cadence, security isolation, or integration boundaries justify the cost.
- Keep cross-cutting concerns in explicit infrastructure modules: config, auth, logging, errors, database, metrics, and health.
- Put reusable contracts and constants in shared packages. Do not put backend services, repositories, or browser-only code in shared packages.
- Prefer explicit status transitions over implicit boolean flags for approval, fulfillment, review, and workflow records.
- Use feature flags or staged rollout for risky behavior changes.

## Module Boundaries

Use business capabilities as module boundaries. Each module should own its routes, DTOs, service logic, repository/data-access code, tests, and local constants.

Expected backend dependency direction:

```text
controller -> service/domain logic -> repository/data access -> database
```

Rules:

- Controllers handle transport concerns only: auth context, validation, DTO mapping, status codes, and delegation.
- Services own business decisions, authorization checks that depend on domain state, state transitions, and transaction orchestration.
- Repositories own persistence queries and map database records to domain objects or DTO-ready shapes.
- Cross-module calls go through exported service APIs, not another module's repository.
- Shared packages contain schemas/types/constants only. They must not import from `apps/web` or `apps/api`.
- React components do not call raw HTTP clients directly; use feature API clients and query/mutation hooks.

## API Design

- Use resource-oriented REST endpoints by default.
- Keep collection endpoints predictable: pagination, filtering, sorting, and stable default order.
- Use explicit workflow actions when state changes are not simple CRUD: `/approval-requests/:id/approve`, `/exports/:id/cancel`.
- Use a stable error response shape:

  ```json
  {
    "code": "BUSINESS_RULE_FAILED",
    "message": "Human readable summary",
    "details": {},
    "requestId": "req_..."
  }
  ```

- Require idempotency keys for payment-like, external-side-effect, import/export, or retry-prone mutation endpoints.
- Do not leak database entities as API responses. Map database records to response DTOs.
- Document OpenAPI for APIs consumed outside the owning team or by generated clients.

## Data Design

- Model core business facts relationally first. Use JSONB for intentionally flexible attributes, not as a schema escape hatch.
- Add database constraints for invariants the application must never violate.
- Add indexes for foreign keys, unique business keys, common filters, status dashboards, and list page ordering.
- Include `created_at` and `updated_at` on business tables. Add actor fields and audit records where user actions matter.
- Use soft delete only when recovery, legal, or audit requirements justify the extra query complexity.
- Keep migrations backward compatible when possible: expand schema, deploy compatible code, backfill, then contract.
- Use transactions for multi-step writes. Keep external network calls outside database transactions.
- Use optimistic locking or checked status transitions for concurrent workflow updates.

## Workflow And Integration Design

- Make external calls through integration clients with timeouts, retries, rate-limit handling, and structured error mapping.
- Store external identifiers and last-sync state explicitly.
- Make background jobs idempotent. Record job inputs, status, retry count, failure reason, and completion time.
- Use an outbox or durable job table when a database change must reliably trigger an external side effect.
- Provide operator-visible retry or remediation paths for failed imports, exports, notifications, and syncs.
- Avoid cron-only business logic that cannot be audited or rerun safely.

## Frontend Design

- Design the first screen as the working internal tool: filters, primary table/list, key metrics when useful, and visible actions.
- Define the route tree and permission behavior before building pages.
- For each page, cover loading, empty, error, disabled, permission-denied, saving, save-failed, and stale-data states.
- Keep URL state for shareable filters, tabs, selected IDs, and pagination where useful.
- Use drawers for detail/edit workflows that keep list context; use full pages for complex multi-step flows.
- Keep business rules visible but enforce them in the backend.

## Operational Design

- Validate environment variables at startup and document safe `.env.example` values.
- Define health/readiness behavior for web, API, worker, and migration jobs.
- Log request ID, actor ID, operation name, target entity ID, result, and failure reason for critical operations.
- Define metrics for latency, error rate, job outcomes, queue depth, external API failures, and critical business counts.
- Add a runbook covering deploy, rollback, migrations, smoke tests, common failures, and support contacts.
- Confirm backup/restore assumptions for PostgreSQL before declaring production readiness.

## Design Output Template

Use this shape for design or generation tasks:

```text
## Technology Decisions
- Standard choices:
- Exceptions:
- Risks:

## Engineering Design
- Users and roles:
- Core workflows:
- Modules:
- API contracts:
- Data model and migrations:
- Frontend routes and pages:
- Jobs and integrations:
- Auth/RBAC:
- Runtime config and deployment:
- Tests and validation:
- Rollout and rollback:
```
