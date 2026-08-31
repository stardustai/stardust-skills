# Failure Taxonomy

Use this taxonomy to classify the first failing boundary. A rescue can have multiple symptoms, but the repair order should follow the earliest proven upstream failure.

| Failure class | Typical symptoms | Evidence to collect | First checks |
| --- | --- | --- | --- |
| Dependency/install | install exits nonzero, lockfile conflict, native module build failure, package manager mismatch | package manager, lockfile, Node/Python/runtime version, registry/private package errors | Compare README command, `packageManager`, lockfile, CI install command, runtime version files. |
| Startup/runtime | dev server crashes, port conflict, module not found, app opens blank, health check fails | start command, env files present, process output, port, browser/server log | Verify install succeeded, env template is complete, DB/service dependencies are available, and entrypoint matches README. |
| Build/type | TypeScript, bundler, import alias, generated client, schema type errors | build command, compiler output, tsconfig/path aliases, generated artifacts | Check stale generated files, missing codegen, package boundary, dependency versions, and uncommitted schema changes. |
| Test | unit/integration/E2E failures, flaky tests, missing fixture, snapshot drift | exact test command, failing test names, seed/fixture setup, env mode | Confirm test env and fixtures before changing implementation. Do not mark tests wrong without evidence. |
| API/contract | frontend 404/500, request body mismatch, DTO/schema/OpenAPI drift | request path/method/body, server route, DTO/schema, validation error, generated client | Trace caller to route and contract source. Fix contract source first, then generated clients and callers. |
| Database/migration | migration fails, ORM client stale, relation/column missing, seed fails | migration command, schema, applied migration state, seed logs | Check whether schema, migrations, generated client, seed data, and README order agree. |
| CI/deploy | local green but CI red, Docker build fails, K8s manifest invalid, missing secret | CI logs, Dockerfile, workflow file, env/secret names, build context | Reproduce locally where possible. Separate CI environment drift from code failure. |
| README/runbook drift | documented command missing, env not documented, wrong order, missing service dependency | README command blocks, package scripts, env examples, compose/runbook | Treat docs as part of the broken contract; update them only after verifying the real command. |
| AI fake completion | TODO, mock path in production, hardcoded sample, swallowed errors, fake green evidence | suspicious code paths, tests that only assert mocks, absence of command evidence | Replace fake completion with real behavior or explicitly block if requirements are unknown. |

## Common Signals

- Multiple lockfiles usually mean package-manager ambiguity; choose the repo's declared manager or ask before deleting lockfiles.
- `.env` present without `.env.example` is a newcomer-readiness risk; never copy actual values into examples.
- A passing unit test does not prove startup, API contract, database migration, E2E, or README correctness.
- A generated file mismatch is often downstream of schema or OpenAPI drift; repair the source of generation.
- CI failures caused by missing secrets should be reported as environment blockers, not hidden by code changes.

## React/Nest Environment Checklist

For React + NestJS or similar TypeScript full-stack projects, check these before changing business logic:

- Frontend env names: Vite exposes only `VITE_*`; Next.js exposes only `NEXT_PUBLIC_*` to browser code.
- Backend env validation: NestJS `ConfigModule`, `zod`, `joi`, or custom config loaders should agree with `.env.example`.
- Test env: Vitest/Jest setup files, `.env.test`, docker-compose service names, and database URLs may differ from local dev.
- API base URL: frontend `.env.example`, proxy config, generated client, and backend port must agree.
- Container env: Docker Compose service names and K8s secret/configmap names are not proof that local README setup works.
- Do not copy actual `.env` values into examples; document variable names, safe placeholders, and where real values come from.
