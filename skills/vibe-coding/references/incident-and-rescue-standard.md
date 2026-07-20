# Incident and Rescue Standard

## Immediate safety

For production impact, data corruption, permission bypass, Secret exposure, or an
irreversible operation, stop writes and feature work, preserve evidence, follow the
project incident/runbook path, and involve the authorized owner. Do not perform
unapproved destructive recovery.

For other failures, freeze scope: no new feature, broad refactor, framework change,
or unrelated dependency upgrade. Preserve the failing commit/worktree and identify
the last known green commit.

## Evidence package

Create a reproducible handoff containing:

- issue summary, expected and observed behavior, impact, and affected users/data;
- exact reproduction steps, environment, active Spec version, and commit;
- timestamps, logs, stack traces, screenshots, requests/responses with secrets
  removed, and relevant runtime signals;
- the deterministic failing test or Eval case;
- last known green commit and rollback method;
- hypotheses tested, changes attempted, commands/results, and why each was rejected;
- open product, architecture, permission, or risk decisions.

## Causal debugging loop

Use `systematic-debugging`: reproduce first, classify the failing layer, trace data
and control flow, form one falsifiable hypothesis, run one discriminating
experiment, and compare results. Before modifying implementation, add a regression
test or Eval case that fails for the observed defect. Make the smallest root-cause
repair and then execute adjacent regression, full tests, applicable Eval, runtime,
and business-scenario verification.

Do not use a fixed number of failed attempts as the rescue trigger. Continue only
while signals are observable and evidence converges. Pause when the failure cannot
be reproduced, observability is insufficient, experiments do not converge, the
fix changes an approved product/architecture contract, risk expands, or authority
is missing.

## Rescue completion

Close only with a causal explanation supported by evidence, passing regression and
full verification on the repaired commit, restored business/runtime signals,
updated Spec/Design/Runbook/technical-debt records where affected, independent
review, and an explicit release or rollback state. Otherwise deliver the evidence
package as a blocked handoff, not a “likely fixed” claim.
