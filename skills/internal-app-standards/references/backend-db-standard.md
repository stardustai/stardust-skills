# Backend And PostgreSQL Standard

## Contents

- Backend framework
- Backend structure
- Database design
- Migrations
- Transactions and data access
- Security and observability

## Backend Framework

Use NestJS + TypeScript for new backend services.

Recommended baseline:

- `@nestjs/config` for configuration.
- Validation at controller boundaries.
- Structured logging.
- Global exception filter with stable error response shape.
- Health endpoint for Kubernetes probes.
- OpenAPI generation when the API is consumed by other teams.

## Backend Structure

Use feature modules:

```text
apps/api/src/
├── main.ts
├── app.module.ts
├── config/
├── common/
│   ├── errors/
│   ├── filters/
│   ├── guards/
│   ├── interceptors/
│   └── logging/
├── database/
│   ├── prisma.service.ts
│   └── transaction.ts
└── modules/
    └── <domain>/
        ├── <domain>.module.ts
        ├── <domain>.controller.ts
        ├── <domain>.service.ts
        ├── <domain>.repository.ts
        ├── dto/
        └── tests/
```

Controllers should parse/validate input and delegate. Services own business rules. Repositories own persistence. Cross-module calls should go through explicit service APIs.

## Database Design

Use PostgreSQL as the system of record.

Default conventions:

- Table and column names: `snake_case`.
- Primary keys: UUID unless there is a clear reason for another strategy.
- Required audit columns: `created_at`, `updated_at`; add `created_by`, `updated_by` when user actions matter.
- Use `deleted_at` only when recovery/audit requirements justify soft delete.
- Add foreign keys for real relationships.
- Add indexes for foreign keys, frequent filters, unique business keys, and search paths.
- Prefer lookup tables over unstable enums.
- Store JSONB only for intentionally flexible attributes; do not use it to avoid schema design.
- Keep PII and sensitive business data explicitly documented.

## Migrations

- Every schema change must have a committed migration.
- New systems should use `db/schema.prisma` and `db/migrations`.
- Migrations must be reviewed like code.
- Make production migrations backward compatible when possible: expand, deploy code, backfill, contract.
- Include rollback or mitigation notes for destructive migrations.
- Do not edit already-applied production migrations; add a new migration.

## Transactions And Data Access

- Put multi-step writes in explicit transactions.
- Keep transaction scope short and free of external network calls.
- Keep raw SQL isolated and tested.
- Do not return database models directly to the frontend; map to response DTOs.
- Use pagination for list APIs.
- Use optimistic locking or explicit status transitions for approval/workflow records.

## Security And Observability

- Enforce authentication and RBAC in backend guards/policies.
- Validate all external input, including query params and uploaded files.
- Log request IDs, actor IDs, operation names, and failure reasons.
- Do not log secrets, tokens, full PII payloads, or raw credentials.
- Emit metrics for request latency, errors, background jobs, and critical business operations.
- Provide `/healthz` and `/readyz` endpoints.
