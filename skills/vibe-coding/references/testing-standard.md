# Testing Standard

## Responsibility and starting point

Testing starts from Business Owner-confirmed `business_success_scenarios`, not from
what the implementation happens to expose. The Skill structures and enforces the
contract; `qa-generated-test-case` adds professional coverage; Engineering selects
automation and produces repeatable evidence. QA and Engineering cannot rewrite the
business end state.

For business features, maintain:

```text
scenario_id -> scenario_coverage -> QA case ID -> automated test ID -> evidence
```

Use the QA skill's normalized Spec, test design, and seven-column case format for
business functionality. Do not force that tabular format onto a pure low-level
library or infrastructure component where contract tests are the actual product.

## Required coverage

The test plan must classify every category as `required` or `not_applicable`, with
reason, evidence, and approving owner. The implementation agent cannot approve its
own exemption. Any allowed exemption requires the recorded QA Owner or Decision
Owner. Business E2E and acceptance Eval cannot be exempted; projects with a business
UI cannot exempt UI/accessibility, and R2/R3 projects cannot exempt permission or
recovery/rollback verification.

Select by that approved applicability and risk decision, but consider every category:

- unit tests for rules, calculations, state transitions, and boundaries;
- integration/contract tests for APIs, persistence, queues, timeouts, retries,
  duplicate delivery, partial success, and dependency failure;
- critical end-to-end business journeys and recovery paths;
- authentication, authorization, role visibility, and negative permission paths;
- UI state, browser journey, accessibility, responsiveness, and visual checks;
- performance, cost, concurrency, resource, recovery, and rollback constraints;
- regression tests for every repaired bug and relevant historical failure.

R1–R3 behavior changes and bug fixes use `test-driven-development`: write the test,
observe the intended failure, make the smallest implementation pass, and refactor
only while green. R0 may simplify TDD but still needs a reproducible start, isolated
data, and a core-flow smoke test.

## Command and evidence rules

`docs/test-plan.md` defines test layers, IDs, commands, environment, data/fixtures,
expected signals, pass/fail rules, ownership, and evidence locations. `PROJECT.yaml`
defines the executable full-test command.

Before any completion or delivery statement, follow
`verification-before-completion`: run the exact current commands, record command,
commit, environment, time, exit code, pass/fail/skip counts, and artifact paths.
Lint, type checking, build, unit, integration, E2E, and Eval are distinct evidence;
one does not stand in for another. A skipped required test is a failure unless an
authorized contract change makes it not applicable.

Independent verification must start from the committed diff and rerun the full
suite. It must not accept the implementation agent's reported result as evidence.
Business observations use a Business Owner-approved measurement rule (source,
operator, and expected value) and must reference a runner-generated manifest by
path and SHA-256. Echoing the Spec sentence or writing `passed: true` is not evidence.
