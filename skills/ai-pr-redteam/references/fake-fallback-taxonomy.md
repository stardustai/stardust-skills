# Fake and Fallback Taxonomy

AI-assisted PRs often look complete because they return a plausible value instead of exposing an unfinished integration or failure. Review every fake/fallback signal with reachability and intent.

## Classification

| Type | Signals | Default severity | Required proof |
| --- | --- | --- | --- |
| Production fake data | `mock`, `fake`, `dummy`, `sample`, demo arrays, hardcoded users/tasks/prices | `BLOCKER` when reachable | Production path cannot return fake data, or degraded mode is explicitly approved and observable. |
| Fallback success | `catch`/`except` returns `[]`, `{}`, `true`, default object, cached demo result | `BLOCKER` | Caller receives typed error or explicit degraded response with test coverage. |
| Fake integration | API/SDK failure falls back to local static result or bypasses the provider | `BLOCKER` | Real integration path is tested; fallback cannot impersonate success. |
| Fake auth/RBAC | Missing identity defaults to admin/allow/all tenant/all records | `BLOCKER` | Missing identity denies access or uses explicit public-access rule. |
| Fake config | Missing env becomes localhost/demo token/default password | `HIGH` or `BLOCKER` | Safe defaults are limited to local dev and documented in `.env.example`/README. |
| Fake persistence | Writes to memory/local file while PR claims DB/object storage/platform write | `BLOCKER` | Durable store is used or limitation is explicit in PR scope. |
| Fake tests | Tests assert mock calls, HTTP 200, snapshots, or hardcoded samples only | `HIGH` | Tests fail when business output is wrong. |
| Fake observability | Errors only `console.warn`/`print` and continue as success | `HIGH` or `BLOCKER` | Failure is observable to caller and operations. |

## Reachability Questions

- Is the fake/fallback path reachable from production runtime, CI, deploy, API, worker, or user UI?
- Is it only test fixture/demo/prototype code, and is that boundary enforced by path, config, or build target?
- Does the PR description explicitly claim real integration, real data, or production readiness?
- Does fallback preserve correctness, or does it make wrong data look valid?
- Are logs, metrics, alerts, user-visible degraded state, and tests present?

## Decision Rules

- Reachable fake data in production behavior blocks merge.
- Fallback that converts failure into success blocks merge.
- Permission, tenant, identity, or data-scope fallback blocks merge.
- A local-only fixture is acceptable when it lives in tests, examples, or docs and cannot ship in production.
- An intentional degraded mode is acceptable only when it has a named product decision, typed response, tests, and operational visibility.

## Reviewer Language

Say:

```text
This path returns sample data when the provider fails, so callers cannot distinguish a real empty result from integration failure.
```

Do not say:

```text
There is a fallback, maybe improve it.
```
