# Pull Request Standard

## Creation gate

Create a PR only after all plan tasks finish, pre-commit was not bypassed, the
feature branch exists on the confirmed Remote, and fresh full tests, all applicable
Eval, traceability, runtime/smoke, rollback, Spec/Design/Plan consistency, and
technical-debt status pass.

## Required PR body

Include:

- active Spec, Design, Plan, and task IDs;
- business goal, included scope, and explicit non-scope;
- architecture, API, data, permission, dependency, and runtime changes;
- material files and behavior changed;
- technical debt found, repair choice, and closure evidence;
- exact test and Eval commands, commit/environment, exit codes, counts, metrics,
  failed cases, and evidence links;
- business scenario/E2E traceability and runtime/smoke evidence;
- risk, known limitations, rollback, and reviewer focus;
- deployment enabled/disabled and observed deployment state.

Do not paste unverifiable “all tests passed” summaries without command evidence.

## Automated PR review

An independent test/review agent begins from the formal Spec, Design, Plan, commit
SHA, and diff. It checks missing and extra behavior, architecture drift, new debt,
data/permission/dependency/recovery risk, reruns the complete tests and Eval, and
verifies runtime/smoke/rollback evidence. It reports pass, blocking findings,
non-blocking findings, and actual evidence. Repair requires another full relevant
review.

Severity:

- **Critical:** blocks merge; full affected verification and review after repair.
- **Important:** fix before merge and review again.
- **Minor:** fix or record an explicit disposition.

## Human approval and merge

Human review and auto-merge follow the engineering team's repository rules. The
company Vibe Coding standard requires automated review but does not add a universal
human-approval rule or weaken an existing one. Security, compliance, or higher
company policy always remains binding. No reviewer may approve while a required
test or Eval is failing.

When a comment conflicts with implementation facts, resolve it through Spec,
code, test, and runtime evidence—not reviewer identity.
