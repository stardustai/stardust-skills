# Stack And Engineering Standard

## Contents

- Standard repository structure
- Technology and architecture decisions
- Module boundaries
- API and contract rules
- Configuration and secrets
- Testing and quality gates

## Standard Repository Structure

Use this structure for new systems. For existing systems, migrate toward it incrementally.

```text
.
├── apps/
│   ├── web/                 # React + Vite + Ant Design
│   └── api/                 # NestJS TypeScript service
├── packages/
│   └── shared/              # Shared DTOs, zod schemas, constants, typed API contracts
├── db/
│   ├── schema.prisma        # Default DB schema source for new systems
│   ├── migrations/          # Committed PostgreSQL migrations
│   └── seeds/               # Idempotent seed data for local/dev
├── infra/
│   ├── docker/              # Optional shared Docker assets
│   └── k8s/
│       ├── base/            # Environment-neutral manifests
│       └── overlays/
│           ├── dev/
│           ├── staging/
│           └── prod/
├── scripts/
│   ├── build.sh
│   ├── test.sh
│   ├── migrate.sh
│   ├── deploy.sh
│   └── rollback.sh
├── docs/
│   ├── architecture.md
│   └── runbook.md
├── package.json
├── pnpm-workspace.yaml
└── tsconfig.base.json
```

## Technology And Architecture Decisions

- Record the selected stack before generating a new system. Use `technology-selection.md` when the user asks for stack choice, architecture, scaffolding, or production readiness.
- Start new systems as a modular monolith with one web app, one API service, one PostgreSQL database, and explicit feature modules.
- Keep stack exceptions visible in docs or the final answer. State why the standard was not used and what operational cost the exception creates.
- Do not introduce extra services, queues, caches, search systems, workflow engines, or micro-frontends without a named workflow and owner.
- Keep generated projects runnable by the standard scripts. Avoid framework-specific commands that only work on the creator's machine.

## Module Boundaries

- Keep frontend, backend, database, and deployment concerns separated.
- Put reusable request/response types, zod schemas, enums, and constants in `packages/shared`.
- Keep business logic in backend services/domain modules, not controllers.
- Keep persistence logic behind repository/data-access classes.
- Keep React components presentation-focused; put remote data access in hooks or service clients.
- Prefer feature modules over generic buckets. Good: `users`, `approvals`, `reports`. Weak: `utils`, `common` for business code.

## API And Contract Rules

- Use REST JSON by default for internal systems.
- Use stable nouns and explicit actions: `/api/users`, `/api/approval-requests/:id/approve`.
- Version only when cross-team consumers or backward compatibility require it.
- Validate request bodies, params, and query strings at the boundary.
- Return typed error shapes with machine-readable codes.
- Generate or document OpenAPI for APIs consumed outside the owning team.
- Avoid sharing database entities directly with the frontend.
- Require idempotency keys for retry-prone writes or writes that trigger external side effects.

## Configuration And Secrets

- Validate environment variables at process startup.
- Keep `.env.example` current and safe to commit.
- Use Kubernetes Secrets or the company's secret manager for real secrets.
- Never commit `.env`, tokens, private keys, database dumps, or production credentials.
- Keep environment-specific values out of code and Docker images.

## Testing And Quality Gates

Minimum expected checks for production-bound internal systems:

- `pnpm lint`
- `pnpm typecheck`
- backend unit tests for domain services
- backend integration tests for database-critical flows
- frontend component or interaction tests for critical pages
- migration apply test on a disposable PostgreSQL database
- Docker image build
- K8s manifest render or dry-run
