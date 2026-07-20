# Business Success Scenarios

Use this reference whenever `spec-intake` collects, confirms, reviews, or maps
`business_success_scenarios`, and before setting `product_ready`, `poc_design_ready`,
`poc_execution_ready`, or `engineering_ready`.

## Purpose

A business success scenario describes a concrete journey whose final business state can
be confirmed by the Business Owner. It is product input, not an engineering E2E script.

Keep these three structures separate:

- `workflow.canonical_workflow`: the general product flow.
- `business_success_scenarios`: concrete business journeys and expected business states.
- `validation_plan.scenario_coverage`: QA and engineering coverage of those journeys.

Neither a general workflow nor a list of tests substitutes for a confirmed business
success scenario.

## Responsibility Boundary

| Role | Owns | Must not do |
| --- | --- | --- |
| Business Owner | Real journey, business rules, success state, invariants, unacceptable outcomes, important branches and recovery expectations | Choose test frameworks or delegate business confirmation to AI |
| Product Owner / Spec Agent | Extract, normalize, identify ambiguity, link workflow steps, present the structured scenario for confirmation | Invent or silently change business meaning |
| QA | Add boundary, negative, permission, duplicate, concurrency, integration-failure and recovery coverage | Rewrite the expected business outcome |
| Engineering | Select automation method, environment, fixtures, commands, observability and evidence | Treat implementation convenience as a reason to change the business contract |

If QA or Engineering discovers that the business outcome is incomplete or wrong, return
to `product_shape`, revise the scenario, and obtain a new Business Owner confirmation.

## Business Interview

Do not ask the business user about selectors, APIs, fixtures, test commands, E2E tools, or
automation frameworks. Extract facts already supplied and ask one high-risk gap at a time:

1. Who starts the real journey, in what business state, and with what business goal?
2. Which roles, decisions, and handoffs are essential?
3. What final business state proves success?
4. What could look successful in the UI but still be a business failure?
5. Which invariant must remain true across the whole journey?
6. For rejection, duplicate submission, missing data, permission failure, timeout, or
   partial success, what state must be preserved or restored?

Show the structured result back to the Business Owner:

> 我已把真实流程整理为业务成功场景。业务目标、最终状态、不可接受结果和异常恢复是否准确？A. 确认；B. 修改一处；C. 场景不成立。

## `business_success_scenarios` Contract

Each item contains:

| Field | Meaning |
| --- | --- |
| `scenario_id` | Stable identifier, for example `BIZ-E2E-001` |
| `title` | Short business-readable scenario name |
| `scope_status` | `in_scope`, `deferred`, or `out_of_scope` |
| `priority` | `critical`, `important`, or `optional` |
| `business_owner` | Person or role accountable for the business meaning |
| `user_role` | Role performing the journey |
| `business_goal` | Business purpose, not a UI action |
| `preconditions` | Business facts that must already hold |
| `trigger` | Event that starts the journey |
| `workflow_step_refs` | Existing `workflow.steps[].step_id` references |
| `expected_business_outcome` | Human-readable definition of success |
| `expected_final_state` | Observable business states after success |
| `success_signals` | Signals that show the outcome actually occurred |
| `business_invariants` | Rules that must remain true throughout the journey |
| `unacceptable_outcomes` | False-success or prohibited results |
| `alternate_paths` | Valid non-primary business branches |
| `exception_paths` | Condition, expected business response, and expected final state |
| `recovery_expectations` | State restoration or human handoff requirements |
| `confirmation` | `status`, `confirmer_role`, `confirmed_by`, `confirmed_at`, and `confirmed_version` |

Do not put selectors, API payloads, test code, fixture paths, shell commands, or framework
choices in this object.

## `validation_plan.scenario_coverage` Contract

Each coverage item references one scenario without copying or rewriting its business
meaning:

| Field | Meaning |
| --- | --- |
| `scenario_id` | Existing business scenario ID |
| `qa_status` | `not_started`, `drafted`, or `approved` |
| `qa_case_refs` | QA case IDs or artifact references |
| `automation_requirement` | `required`, `optional`, or `not_applicable` |
| `automation_plan_status` | `not_started`, `planned`, `implemented`, or `verified` |
| `automated_test_refs` | Automated test IDs or paths when available |
| `evaluation_asset_refs` | Linked golden cases, failure cases, rubrics, or regression assets |
| `owner` | QA or engineering owner of coverage delivery |

The mapping direction is one-way:

```text
business_success_scenarios
  -> validation_plan.scenario_coverage
  -> QA cases
  -> automated E2E / integration / other verification
  -> fresh execution evidence
```

## Gate Rules

- `business_ready`: scenarios may be empty or pending; missing scenarios remain
  product-shape blockers.
- `product_ready` and later product-proof labels: at least one `in_scope` + `critical`
  scenario is required. Every in-scope scenario must have complete business fields and a
  complete Business Owner confirmation. `confirmer_role` must be `business_owner`;
  `confirmed_by` must match both the scenario `business_owner` and
  `owners.business_owner`; `confirmed_version` must match the top-level `spec_version`;
  `confirmed_at` must be a valid ISO date such as `2026-07-20`.
- `poc_design_ready` and `poc_execution_ready`: every in-scope critical scenario requires
  a coverage item, QA coverage at least `drafted`, and QA cases or evaluation assets.
- `engineering_ready`: every in-scope critical scenario requires `qa_status=approved`.
  When automation is `required`, `automation_plan_status` must be `planned`,
  `implemented`, or `verified`.
- Passing automated tests is not an intake prerequisite. It is a downstream engineering
  delivery gate with fresh execution evidence.

Agent confidence, Product review, QA review, generated tests, or a stage-exit confirmation
does not substitute for Business Owner confirmation of the scenario content and version.
