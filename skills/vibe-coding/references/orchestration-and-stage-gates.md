# Orchestration and Stage Gates

## Operating model

The user invokes `vibe-coding`; the orchestrator chooses and sequences specialist
skills. Non-technical employees are not expected to know when to call TDD,
debugging, review, worktree, QA, or deployment skills.

## Stages

1. **Intake:** locate and validate the current engineering-ready Spec.
2. **Repository contract:** verify Remote, Git baseline, rules, README,
   `PROJECT.yaml`, and required documents.
3. **Initialization:** for an existing project, establish a reproducible baseline,
   audit architecture and technical debt, and complete the chosen clean repair.
4. **Design and plan:** inspect real implementation patterns; confirm architecture,
   UI, runtime, algorithm, and data design as applicable; use `writing-plans`, pin
   the Spec, invoke `qa-generated-test-case` for business features, and map every
   critical scenario to QA, automation, task feedback, rollback, and confirmation.
5. **Feedback contract:** define target, baseline, observable signals, pass/fail
   rules, command arrays, evidence paths, and rollback for the next slice.
6. **Implementation:** execute one independently verifiable task at a time using
   TDD and, for complex work, subagents and isolated worktrees.
7. **Convergence:** run the task feedback loop until local, integration/E2E, Eval,
   runtime, and business signals meet their explicit pass criteria.
8. **Independent verification:** conduct Spec review, code-quality review, and an
   independent fresh full test/Eval run.
9. **Delivery:** commit through the full-suite pre-commit hook; push directly or
    create a PR according to risk, change, collaboration, and repository policy.
10. **Optional deployment and handoff:** invoke `production-devops-sre` only when
    deployment is enabled; update documents and report the exact achieved state.

## Gate rule

A stage may not start until its predecessor's required artifacts and evidence
exist. Later-stage evidence does not retroactively approve a skipped decision.
The orchestrator should repair missing deterministic artifacts automatically;
it must pause for missing product, business, risk, permission, or architecture
decisions.

## Per-task execution

```text
select task -> confirm feedback contract -> write failing test -> confirm failure
-> minimum implementation -> run feedback loop -> Spec review -> quality review
-> full configured checks -> commit -> update traceability -> next task
```

Architecture repair and feature implementation use separate designs, plans,
tasks, and commits.

## Required state updates

After every gate, update `PROJECT.yaml`, the active plan, and affected traceability
records. Preserve historical Spec, Design, and Plan files; point the machine-readable
contract to the current version instead of overwriting history.
