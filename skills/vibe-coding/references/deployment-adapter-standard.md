# Optional Deployment Adapter Standard

## Default state

Deployment is disabled unless the active Spec requires it or the user explicitly
selects it. The project contract records:

```yaml
deployment:
  required: false
  target_environment: null
  sre_skill: production-devops-sre
  lifecycle_status: not_started
```

When disabled, stop after verified Git delivery and report “development complete,
not deployed.” Do not call a local run, preview, pushed branch, or merged PR a
deployment.

## Delegation boundary

When enabled, invoke `production-devops-sre` and treat its current rules as the
authority for workload classification, deployment artifacts, environment choice,
non-production verification, staging decision, production blockers, database
migration, tickets/approvals, domains/certificates, security, rollout strategy,
observability, rollback, and post-deployment evidence.

`vibe-coding` must not independently decide that staging can be skipped or replace
SRE controls with a generic checklist. If SRE requires information or approval,
surface that decision to the user and keep deployment state blocked until resolved.

## Handoff package

Provide the deployment skill with the pinned Spec/Design/Plan, delivery commit and
Remote reference, risk profile, runtime contract, configuration/Secret references,
test and Eval evidence, migration/data impact, smoke/health checks, monitoring,
runbook, rollback, owners, and known limitations.

## Status evidence

Update `PROJECT.yaml` only from observed deployment results. Distinguish
`not_started`, `blocked`, `non_production_deployed`, `production_rollout`,
`production_deployed`, and `rolled_back`. A command returning success is not enough;
verify health, critical smoke behavior, monitoring, and the actual target revision.
