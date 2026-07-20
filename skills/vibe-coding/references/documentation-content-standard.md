# Documentation Content Standard

## Purpose

Repository layout is flexible; required engineering knowledge is not. A mapped
document is complete only when an independent reviewer confirms every topic below
against exact text in the current file and records its SHA-256 in
`documentation.content_review`.

## Required topics

| Responsibility | Required topic IDs |
| --- | --- |
| `business_goal` | `problem_and_users`, `business_goal`, `success_metrics`, `business_success_scenarios` |
| `system_architecture` | `system_context`, `boundaries`, `components`, `data_flow`, `authorization`, `observability`, `failure_recovery` |
| `runtime_constraints` | `environments`, `versions`, `commands`, `configuration`, `resources`, `dependencies`, `observability`, `recovery` |
| `test_plan` | `scope`, `traceability`, `test_layers`, `commands`, `test_data`, `pass_fail_rules`, `evidence` |
| `traceability` | `requirements`, `business_scenarios`, `qa_cases`, `automated_checks`, `evidence` |
| `eval_plan` | `acceptance_cases`, `datasets`, `metrics`, `thresholds`, `commands`, `evidence` |
| `runbook` | `start_stop`, `health`, `monitoring`, `incidents`, `rollback`, `ownership` |
| `technical_debt_register` | `definition`, `evidence`, `strategy`, `scope`, `verification` |
| `agent_rules_audit` | `sources`, `scope`, `compliance`, `evidence`, `exceptions` |
| `qa_normalized_spec` | `scope`, `requirements`, `business_rules`, `success_scenarios`, `risks` |
| `qa_test_design` | `coverage_strategy`, `positive`, `negative`, `permissions`, `recovery` |
| `qa_test_cases` | `case_ids`, `preconditions`, `steps`, `expected_results`, `traceability` |
| `algorithm_design` when applicable | `problem`, `inputs_outputs`, `algorithm`, `constraints`, `evaluation`, `failure_modes` |
| `ui_spec` when applicable | `user_flows`, `screens`, `states`, `validation`, `accessibility`, `permissions` |

Topic IDs are review categories, not required heading text. `locator` must equal a
unique complete line in the mapped document, normally a heading. Different topics
in the same responsibility cannot reuse a locator. The text after that locator up
to the next heading must be nontrivial, and `section_sha256` binds that section.
The reviewer assesses whether the section substantively covers the topic;
repeating topic names above generic prose is a failed semantic review.

## Review contract

The review artifact must:

- be produced by an independent review execution context;
- cover exactly every required and applicable mapped responsibility;
- record the exact project-relative path and current SHA-256;
- cover each required topic exactly once;
- use a unique full-line locator and bind its nontrivial section hash;
- report `pass` only after AI fills all missing content in the real source;
- be regenerated whenever a mapped file changes or moves.

The deterministic validator proves that the review is complete, internally
consistent, and bound to current files and sections. It can compare declared
author/reviewer identities after normalization, but an editable JSON file cannot
cryptographically prove who ran the review. The Vibe Coding orchestrator must
therefore dispatch a separate Review Agent and retain the real tool/subagent trace;
the delivery review verifies that provenance. The independent reviewer remains
responsible for semantic judgment and must reject generic prose that merely names
the topics.
