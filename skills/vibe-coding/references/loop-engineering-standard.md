# Loop Engineering Standard

## Principle

Stability comes from continuously comparing observable results with explicit
success criteria, not from trusting the agent's confidence or stopping after an
arbitrary number of attempts. “Fixed” is a hypothesis until the feedback contract
passes.

## Task feedback contract

Before changing code, every task records:

- `target`: linked business/technical outcome and Spec IDs;
- `observable_signals`: local, integration/E2E, Eval, runtime, and business signals
  relevant to the task;
- `baseline`: the measured pre-change commit, including the expected failing test;
- `pass_fail_rules`: exact target, invariant, threshold, and blocker rules;
- `verification_commands`: reproducible commands and environment;
- `evidence_paths`: where raw and summarized results are written;
- `rollback_method`: last known good commit or reversible action.

Signals must measure the intended result. A green HTTP status is not proof of a
correct business transition; a screenshot is not proof of permission enforcement.
The baseline commit must resolve and be an ancestor of the result commit. An expected
failing baseline records `expected_fail` and its real non-zero exit code. The result
validator recomputes each rule from operator, observed value, and expected value;
it never trusts a self-declared `passed: true`.

## Execution loop

1. Run the feedback contract and save the baseline.
2. Make one small, causal change.
3. Rerun the closest deterministic signal.
4. If it improves as predicted, run broader integration/E2E, Eval, runtime, and
   business signals required by the contract.
5. Compare current result with baseline and pass/fail criteria.
6. Preserve a passing increment or revert the local attempt; update evidence.
7. Repeat only while evidence shows a bounded path toward convergence.

Each iteration records hypothesis, changed files/commit, commands, observed result,
comparison, conclusion, and next action. Do not accumulate unrelated changes before
observing their effect.

## Completion and pause

A task converges only when every required signal passes together on the current
code and no critical scenario/invariant regresses. Loop count is not a completion
or failure criterion.

Pause and seek a decision when signals are unavailable or unreliable, results do
not converge, the target itself is unclear, the required fix changes product or
architecture, risk expands, permissions are insufficient, or the next experiment
is destructive/irreversible. Use systematic debugging to establish causal evidence;
do not convert repeated uncertainty into fallback branches or broad rewrites.
