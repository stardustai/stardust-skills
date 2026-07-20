# Technology Selection Standard

## Contents

- Selection principles
- Default stack matrix
- Optional capabilities
- Non-standard choices
- Decision record

## Selection Principles

- Choose boring, team-owned technology that can be built, tested, deployed, monitored, and debugged by the owning team.
- Prefer one coherent TypeScript stack across frontend, backend, contracts, tests, and scripts.
- Preserve an existing production-proven stack when replacing it would create more risk than value.
- Add infrastructure only for a real product or operational need. Do not add queues, caches, search, workflow engines, or microservices because the generated scaffold looks modern.
- Make deviations explicit. Every non-standard choice needs a reason, owner, operational impact, and migration or rollback plan.

## Default Stack Matrix

| Area | Default | Why | Acceptable exceptions |
| --- | --- | --- | --- |
| Package manager | `pnpm` workspaces | Fast deterministic installs and clear monorepo boundaries. | Existing repo already standardizes on another manager and changing it is out of scope. |
| Language | TypeScript strict mode | Shared typing across web, API, contracts, tests, and tooling. | None for new systems. |
| Frontend runtime | React.js + Vite | Fast internal app development without SSR complexity. | Existing React build setup; Next.js only when SSR, file-based routing, or public SEO is truly required and accepted. |
| UI system | Ant Design | Enterprise-grade forms, tables, layout, feedback states, and theming. | Existing approved design system with comparable table/form coverage. |
| Routing | React Router | Explicit client-side routes for internal tools. | Existing router standard. |
| Server state | TanStack Query | Cache, loading, retry, invalidation, and mutation state belong outside components. | Existing repository standard with equivalent behavior. |
| Backend | NestJS | Modules, dependency injection, providers, guards, pipes, filters, and testing patterns support maintainable services. | Existing TypeScript backend with clear module boundaries and production track record. |
| API style | REST JSON | Internal CRUD/workflow systems are easier to operate and document with resource APIs. | GraphQL for complex client-driven graphs; gRPC for service-to-service contracts; both require ownership and documentation. |
| API contract | Shared schemas/types plus OpenAPI for cross-team APIs | Prevent frontend/backend drift and make external consumers reviewable. | Existing OpenAPI-first or generated-client workflow. |
| Validation | One boundary validation system per repo | Avoid duplicated schemas and inconsistent error behavior. | Use `zod` for shared contracts, or NestJS DTO validation when that is already the repo standard. |
| Database | PostgreSQL | Strong relational constraints, transactions, indexing, JSONB when appropriate, and operational maturity. | Existing production system has a documented data-store constraint. |
| Data access | Prisma for new systems | Type-safe client and migration workflow reduce boilerplate for internal systems. | Kysely/Drizzle/raw SQL for SQL-heavy domains; existing ORM if already established. |
| Migrations | Committed migrations with deploy-time apply | Schema changes must be reviewable and reproducible. | None for production-bound systems. |
| Auth/RBAC | Company identity provider plus backend-enforced roles/policies | Internal tools usually handle sensitive operational data. | Temporary local auth only for prototypes that will not be called production-ready. |
| Background work | Start synchronous; add jobs only for long or retryable work | Avoid unnecessary queue operations burden. | BullMQ/Redis or company standard queue for retries, scheduling, fanout, or external integration resilience. |
| Cache | No distributed cache by default | PostgreSQL and API-level pagination are enough for most internal tools. | Redis only for measured hot paths, coordination, rate limits, or queue backing. |
| Search | PostgreSQL indexes/full-text first | Keeps data ownership simple. | OpenSearch/Elasticsearch only for large fuzzy search or analytics search needs. |
| Object files | Company object storage or S3-compatible storage | Keeps binary files out of the database and app image. | Database storage only for small metadata, not large files. |
| Observability | Structured logs, metrics, request IDs, health/readiness endpoints | First-line incident diagnosis must not require code reading. | Use the existing platform standard if stronger. |
| Deployment | Docker images + Kubernetes manifests with environment overlays | Repeatable production deployment and rollback. | Existing CD platform may own apply/rollout, but manifests or deploy config must be reviewable. |

## Optional Capabilities

Add optional infrastructure only after the design names the workflow that needs it.

- `Redis`: rate limits, queue backing, short-lived coordination, or measured cache pressure.
- `BullMQ` or company queue: background retries, scheduled jobs, external API fanout, file processing, or long-running exports.
- `OpenSearch` or Elasticsearch: cross-field fuzzy search that PostgreSQL cannot satisfy within target latency.
- Object storage: uploads, generated reports, exports, attachments, and audit files.
- WebSockets or SSE: live status updates where polling is expensive or user experience requires push.
- Feature flags: staged rollout, risky workflow changes, or tenant/user-level enablement.
- Workflow engine: long-running multi-step business processes with human approvals, retries, and audit requirements that exceed simple status transitions.

## Non-Standard Choices

Block or escalate these choices for new systems unless the user explicitly accepts the exception:

- Vue, Angular, Next.js, Svelte, or a second frontend framework.
- Express-only backend without NestJS module boundaries.
- MongoDB, MySQL, Firebase, or serverless-only storage for core relational business data.
- TypeORM for new systems when Prisma, Kysely, or the existing repo standard would be simpler.
- GraphQL, gRPC, microservices, micro-frontends, event sourcing, or CQRS without a named operational reason.
- Custom component libraries before Ant Design has been evaluated.
- Ad hoc shell deployment, manually edited environment files, or unreviewed production manifests.
- Generated demo scaffolds that do not include auth/RBAC, migrations, tests, deploy path, and operational states.

## Decision Record

For new systems, stack changes, or large feature foundations, include a short decision record:

```text
Decision: <technology or architecture choice>
Standard option: <default from this skill>
Selected option: <actual choice>
Reason: <business or engineering reason>
Alternatives rejected: <1-3 options and why>
Operational impact: <deploy, monitor, backup, on-call, cost>
Migration/rollback: <how to change course safely>
Owner: <team or role>
```
