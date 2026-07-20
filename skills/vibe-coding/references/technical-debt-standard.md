# Technical Debt Standard

## Definition

Technical debt is an existing structural problem in code, architecture, data, or
runtime that makes a later change less predictable, testable, recoverable, or safe,
or forces development through workarounds and patches. Every item needs code,
configuration, test, runtime, or historical-change evidence. Personal taste and
“more elegant” are insufficient.

## Evidence-bearing indicators

- unpredictable cross-module effects, duplicate truth, or confused ownership;
- unstable public interfaces, data contracts, or state transitions;
- divergence from approved architecture or applicable agent rules;
- critical behavior that cannot be verified reliably;
- circular/wrong-direction dependencies or production-only testability;
- hidden failures, weak observability, or no recovery/rollback path;
- unclear authorization, sensitive-data, or Secret boundaries;
- runtime constraints the current structure cannot meet;
- a long-lived temporary implementation that new work must keep extending;
- hard-coded branches, compatibility layers, retries, or fallbacks that conceal
  rather than remove a root cause.

## Not automatically debt

Style preference, unfamiliar code, an unapproved feature, a missing Spec decision,
a bounded reproducible bug, an old dependency with no demonstrated risk, justified
new complexity, and optional refactoring are not debt by themselves.

## Boundary with other work

| Type | Meaning | Route |
| --- | --- | --- |
| Product gap | Spec does not decide behavior | Return to `spec-intake` |
| Ordinary bug | Code violates an approved behavior within a clear boundary | Systematic debugging and regression test |
| Readiness gap | README, Remote, test/Eval entry, or pre-commit is absent | Initialization |
| Technical debt | Structure prevents reliable change/test/recovery | Full or minimum clean repair |
| New architecture | Existing design cannot support approved capability | Design change and user confirmation |
| Process violation | Agent skipped evidence/approval/process | Stop and correct execution |

## Register and closure

For each TD-ID record: problem, rule source, evidence, affected modules, future
risk, whether this feature touches it, full repair, minimum clean repair,
verification, owner, status, and closure evidence. Do not write vague labels such
as “architecture bad.”

The user chooses either full audit repair or minimum clean repair. Continuing on
in-scope debt with a special case, compatibility layer, or patch is not an option.
Close debt only when the root cause is gone, boundaries are clear, a relevant test
failed before and passes after, full regression/Eval succeeds, documents match,
and an independent reviewer finds no replacement debt.
