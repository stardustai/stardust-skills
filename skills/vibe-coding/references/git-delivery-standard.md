# Git Delivery Standard

## Start state

Formal coding requires an accessible Remote Repository URL. Verify that `origin`,
default branch, feature branch, baseline commit, working-tree state, and
`last_green_commit` match `PROJECT.yaml`. Protect user-owned changes; never mix or
discard them.

Complex or risky features use `using-git-worktrees` and a feature branch. Keep
architecture/technical-debt repair separate from feature implementation.

## Commits

Automatic local commits are allowed. One plan task maps to one or a small number
of single-purpose commits. Commit messages include the task ID; staged content must
match the plan and may not contain unrelated user changes.

Every commit passes the versioned full-suite pre-commit hook. Never use
`--no-verify`. A failed hook means there is no completed commit. After committing,
update task/commit traceability and only advance when the worktree is in the
expected state.

## Direct push decision

Classify size from change shape, not line count or confidence. A change is small
only when it has one bounded responsibility, stays inside existing private
contracts, introduces no new integration/dependency/job/migration, and can be
independently reverted. It is large when it spans coordinated modules or owners,
introduces a new workflow or public contract, or needs multiple coupled rollout
steps. Record the classification and evidence in `PROJECT.yaml` and the Plan.

Direct push or merge is allowed only when all are true:

- the project is single-owner **or** the change is a small, single-responsibility,
  local feature with stable contracts;
- the operator has direct push permission and the repository permits it;
- risk is R0 or R1;
- architecture, public API, data schema, permissions, and production migration do
  not change;
- full tests and applicable Eval pass with fresh evidence;
- the change is independently recoverable.

The first line is an **or** ownership/size condition; it is combined with every
remaining line as an **and** condition. A small feature in a multi-person project
may still direct-push when every condition holds. A larger single-owner R0/R1
change may also direct-push only if none of the structural or policy PR triggers
below applies.

## PR decision and final delivery

A PR is mandatory if any applies: multi-person large feature, R2/R3, architecture/
API/data/permission change, dependency/integration change, migration or bulk write,
technical-debt repair/refactor, material Spec/Plan change, critical runtime change,
repository protection, or explicit user requirement.

Before push/PR, rerun full tests, all applicable Eval, traceability validation,
runtime verification, and independent review on the delivery commit. Push the
feature branch to the confirmed Remote. Follow `finishing-a-development-branch`;
never claim a remote or merge state that has not been observed.
