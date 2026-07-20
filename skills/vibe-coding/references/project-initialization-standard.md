# Existing Project Initialization Standard

## Entry rule

Do not add a feature to an existing project until its real engineering contract,
runtime baseline, architecture, and relevant technical debt are understood and
clean enough to support the change.

## Procedure

1. Read scoped `AGENTS.md`/`AGENT.md` files and referenced shared rules.
2. Inspect Git status, Remote, branches, baseline commit, and user-owned changes.
3. Read actual architecture, dependencies, build, test, runtime, and deployment.
4. Locate existing analogues, shared components, models, and interfaces.
5. From a clean environment, attempt install, build, start, health, existing tests,
   and applicable Eval; retain observed results.
6. Inventory existing documents by responsibility and identify missing content.
7. If the repository is not already standard, ask the user to choose exactly one
   organization path: convert to the standard structure, or adapt the existing
   structure in place.
8. Add or correct README, `PROJECT.yaml`, and every applicable repository document
   under the selected organization path. In adapt-in-place mode, map actual paths
   in both `PROJECT.yaml` and README; do not create duplicate sources of truth.
9. Run an independent semantic content review that binds every mapped document's
   required topics and exact locators to its current SHA-256; fill gaps and repeat
   until the review passes.
10. Establish behavioral, test, Eval, and runtime baselines; name anything that
   cannot be observed.
11. Compare the active Spec with current behavior, data, permissions, architecture,
   and runtime.
12. Produce an evidenced debt register and an independent architecture-repair plan.
13. Ask the user to choose exactly one: full debt repair or minimum clean repair.
14. Execute the selected repair with characterization tests, full verification,
    independent review, and separate commits.
15. Record the new baseline and `last_green_commit`; only then plan the feature.

The repository-organization choice and technical-debt choice are separate. Moving
documents does not repair architecture debt, and adapting paths does not excuse
missing content.

## Required classifications

Separate verified facts, evidence-backed inferences, engineering-readiness gaps,
ordinary bugs, product/Spec gaps, technical debt, new architecture requirements,
and blockers. Do not relabel a product decision as technical debt or a missing
test command as a product issue.

## The two permitted debt choices

- **Full repair:** close every debt item found by this systematic initialization
  audit.
- **Minimum clean repair:** close all debt in modules the feature changes or
  directly/indirectly depends on, plus anything affecting correctness, testability,
  data, permission, recovery, or runtime stability.

Minimum clean repair is not patching. The feature may not depend on, extend, or
circumvent known bad architecture. Touching a debt brings it into repair scope.
If a clean testable boundary cannot be formed, choose full repair or reduce/cancel
the feature.

## Completion gate

Initialization completes only after the repository contract validates, standard
commands work, Spec/code differences are resolved, selected debt scope is closed,
architecture matches code, full tests and applicable Eval pass, and a reviewed
baseline commit is recorded. Initialization repair and feature work must not share
a plan or commit.
