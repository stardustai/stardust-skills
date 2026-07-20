# Completion Status Standard

## Definition of done

The orchestrator may state development is complete only when all applicable items
are proven on the final commit:

- engineering-ready Spec, confirmed risk, Design, Plan, and user decisions agree;
- project initialization is complete and all debt touched or depended on by this
  work is closed;
- every plan task and required traceability link is complete;
- all critical business scenarios have QA coverage, automation, and fresh evidence;
- configured static, build, unit, integration, E2E, UI, permission, recovery,
  performance, and other required tests pass;
- all applicable Eval passes its pinned rubric without blocking cases;
- independent Spec, quality, and test reviews have no blocking finding;
- clean runtime/start/health/smoke/restart and rollback evidence passes;
- no plan-external behavior, unconfirmed architecture change, or new unregistered
  debt remains;
- README, architecture, algorithm, runtime, test, Eval, runbook, audit, debt, and
  traceability documents match implementation;
- the final version exists on the confirmed Remote and delivery policy was followed;
- optional deployment, when enabled, passed the deployment adapter's evidence gate.

Evidence must be fresh, tied to the final commit and environment, and include actual
commands/results. Agent self-assessment is not evidence.

## Exact status vocabulary

Report one observed terminal or intermediate state:

- **development_complete_not_deployed** — all development gates pass; deployment
  disabled or not requested;
- **pushed** — verified delivery commit exists on the Remote, with no PR required;
- **pr_open_waiting** — PR created; name remaining review/check/merge conditions;
- **merged** — the delivery revision is observed in the target branch;
- **non_production_deployed** — verified target revision runs in the named
  non-production environment;
- **production_rollout** — production rollout is in progress under the SRE
  adapter; report current health, scope, and the next observation gate;
- **production_deployed** — production target revision, health, smoke, and monitoring
  are verified;
- **blocked** — name the failed gate, evidence, owner/decision needed, and safe state;
- **rolled_back** — name the restored revision/environment and remaining follow-up.

Multiple facts may be reported together when precise, such as “PR open; development
checks passed; not deployed.” Never collapse them into “done” or “production-ready.”

## Handoff summary

Include final Spec/Design/Plan and commit references, risk tier, test/Eval/runtime
evidence locations, business scenario coverage, technical-debt state, Remote/PR/
merge/deployment links, known limitations, rollback, owners, and next required
human or automated action.
