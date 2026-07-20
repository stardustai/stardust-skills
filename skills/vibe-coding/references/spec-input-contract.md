# Spec Input Contract

## Purpose

`vibe-coding` consumes an approved engineering contract; it does not turn an
unconfirmed idea into code. The input is the current `spec-intake` JSON pointed
to by `PROJECT.yaml`.

## Admission gate

Formal implementation may start only when all of the following are true:

- `stage_gate.readiness_label` is `engineering_ready`;
- `stage_gate.decision` is `ready_for_engineering`;
- the Spec validates against the installed `spec-intake` schema and validator;
- the Spec ID, version, path, and checksum are pinned in the implementation plan;
- required Business, Product, QA, Engineering, and Decision Owner decisions exist;
- no blocking open question or unresolved decision is hidden in prose.

Any earlier stage may only continue through `spec-intake` or technical gap review.
An isolated R0 prototype using synthetic data may be created only after the user
explicitly authorizes that prototype and the decision is recorded. Without that
authorization, do not create code. An R0 prototype must not be represented as
formal implementation.

## Three sources of truth

1. The Spec defines what the product must do. The agent may not invent behavior,
   change a business rule, or enlarge scope.
2. The checked-in repository defines how the new behavior integrates with the
   existing system. The agent must inspect real code, tests, configuration, and
   runtime paths before designing changes.
3. Fresh test and Eval evidence defines whether the result works. Agent confidence,
   screenshots alone, and a process exit without assertions are not proof.

When these sources disagree, stop and use the change-control standard. Never
silently reinterpret one to fit another.

## Business success scenario contract

Every in-scope critical journey originates in
`business_success_scenarios`. Each scenario must include a stable ID, actor,
business goal, preconditions, trigger, workflow references, successful business
end state, observable success signals, invariants, unacceptable outcomes,
exception/recovery paths, and Business Owner confirmation.

The fixed responsibility model is:

- **Business leads:** describes real successful end-to-end work and confirms the
  business end state.
- **Skill guides:** asks structured questions, reflects the scenario back, checks
  completeness, and blocks missing confirmation.
- **QA completes coverage:** adds boundary, negative, permission, duplicate,
  dependency-failure, and recovery cases through
  `validation_plan.scenario_coverage`.
- **Engineering automates:** chooses the framework, environment, fixtures,
  commands, signals, and evidence needed for repeatable verification.

QA and Engineering may strengthen coverage but may not change the confirmed
business end state. If it is wrong or incomplete, return to the Business Owner
and revise the Spec.

## Traceability required before coding

The plan and project traceability must form this chain:

```text
scenario_id / requirement_id / workflow.step_id / metric_id
  -> QA case
  -> implementation task
  -> files and commit
  -> automated test or Eval
  -> evidence path
```

Every critical in-scope scenario needs QA-approved coverage and an automation
decision before implementation. `engineering_ready` means the verification work
is planned, not that the post-implementation tests already pass.
