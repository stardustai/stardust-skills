# Language Quality Rules

Engineering-quality review starts with language and framework detection. Apply the norms of the dominant language and the repository's existing architecture before judging abstraction, package boundaries, reuse, and maintainability.

## Universal Questions

| Dimension | Review question |
| --- | --- |
| Modularity | Does each changed file have one clear responsibility? |
| Package boundary | Do dependencies point inward toward stable domain/application boundaries, or across layers unpredictably? |
| Reuse | Did the PR duplicate existing validation, formatting, data access, API clients, or business rules? |
| Abstraction | Is abstraction supported by multiple real call sites or clear volatility, or is it speculative? |
| Testability | Can core behavior be tested without UI, network, time, filesystem, or real external services? |
| Error handling | Are failures represented in the language's normal style and visible at the right boundary? |
| Change scope | Are unrelated rewrites, formatter churn, lockfile noise, or framework changes mixed into the PR? |

Always connect a quality finding to a cost: harder tests, larger blast radius, hidden data coupling, unclear ownership, unsafe reuse, or future change risk.

## TypeScript / JavaScript

Review TypeScript and JavaScript through typed boundaries, runtime validation, and framework separation.

- React components should render UI, manage local interaction state, and call typed hooks/clients. They should not directly access databases, filesystem, backend SDKs, or environment secrets.
- NestJS/Express/Fastify route handlers should be thin: parse/validate input, call application services, map errors to responses.
- Shared business rules should not live in React components, ad hoc controllers, or copied utility functions.
- `any`, `as any`, `@ts-ignore`, and untyped JSON parsing require a narrow boundary and tests.
- Env names must align among code, `.env.example`, README, CI, Docker/K8s, and frontend exposure rules such as `VITE_*` or `NEXT_PUBLIC_*`.
- Async failures should not become empty arrays, default objects, or HTTP 200 unless there is an explicit degraded-mode contract.

Common findings:

| Signal | Better design |
| --- | --- |
| `.tsx` imports Prisma/SQL/ORM/fs | Move IO behind backend API or application service; component consumes hook/client. |
| Controller contains large business workflow | Extract service/use-case with unit tests and typed DTO validation. |
| Same mapping/validation repeated | Move to shared schema or narrow utility in the owning package. |
| New dependency for small helper | Use standard library or existing dependency unless the new package has clear ownership and maintenance value. |

## Python

Review Python through explicit boundaries, simple modules, clear dependency injection, and visible failures.

- Avoid mutable default arguments; use `None` and initialize inside.
- Avoid bare `except` and broad `except Exception` fallback returning empty/default data.
- Prefer small pure functions for domain logic and adapters for IO.
- Keep scripts, libraries, web handlers, and background jobs separated when the repository already has those boundaries.
- Use dataclasses, Pydantic, TypedDict, or clear dictionaries at IO boundaries when shape matters.
- Do not hide provider failures by returning `[]`, `{}`, `None`, or stale demo data unless the degraded contract is explicit.

Common findings:

| Signal | Better design |
| --- | --- |
| `except Exception: return []` | Catch narrow exceptions; return typed failure or raise domain error. |
| `def fn(items=[])` | Use `items=None`; initialize per call; add repeated-call regression test. |
| Web handler doing parsing, business logic, DB, and formatting | Split handler, service, repository/client, and serializer where it improves testability. |

## Go

Review Go through explicit errors, small packages, interfaces at consumers, and context propagation.

- Do not ignore returned errors with `_ =` unless the reason is documented and safe.
- Request paths should return errors/responses, not `panic`.
- Pass `context.Context` through IO boundaries.
- Keep interfaces near consumers; avoid speculative interface layers for one implementation.
- Prefer table-driven tests for boundary and error cases.

## Java / Kotlin

Review JVM code through layering, transaction boundaries, typed exceptions, and dependency direction.

- Controllers should not own business workflows or persistence details.
- Services should define transaction scope and invariants.
- Empty catch blocks or broad `Exception` catch-and-continue hide failures.
- DTO/entity/domain objects should not be collapsed into one mutable shape when external contracts matter.
- Reuse mappers/validators where they are already established, but avoid framework-heavy abstraction for a single path.

## Frontend-Specific Quality

- Server state belongs in a query/cache layer, not duplicated across form state, global stores, and local component state without a source-of-truth rule.
- UI should represent loading, empty, error, permission denied, and partial-degraded states.
- Generated UI code often overuses cards, oversized wrappers, copied handlers, and fake loading state. Treat these as quality issues only when they harm workflow, accessibility, or maintainability.

## Backend/Data Quality

- Writes that affect more than one record need transaction, idempotency, or recovery analysis.
- New fields require migration, backfill/default/nullability plan, read/write compatibility, and rollback notes when relevant.
- API/schema/DTO/database changes must be checked as one contract, not as isolated files.
