# Subagent and Review Standard

## When to use subagents

Prefer `subagent-driven-development` for cross-module work, multiple independent
tasks, external systems, data migration, permissions, concurrency, algorithms,
Eval, architecture adjustment, technical-debt repair, or high-impact failure.
Use an isolated feature branch/worktree for complex work.

## Task packet

Give each implementation subagent a fresh context containing the exact task,
pinned Spec/Design/Plan IDs, allowed files, relevant repository evidence, scoped
agent rules, feedback contract, test commands, expected evidence, and forbidden
scope. The implementer performs TDD, self-review, fresh checks, and a task-focused
commit.

Tasks with code dependencies run sequentially. Parallel agents must not edit the
same files or shared working tree unless an explicit integration plan prevents
conflicts.

## Independent review chain

After each implemented task:

1. **Spec Reviewer:** checks every linked requirement/scenario, missing behavior,
   extra behavior, and traceability using the Spec and diff.
2. **Code Quality Reviewer:** checks architecture, simplicity, contracts, data and
   permissions, observability, recovery, tests, and new debt.
3. **Test Agent:** on the integrated delivery commit, independently executes the
   full test and Eval suite and inspects runtime evidence.

Independent execution produces its own runner manifest, `run_id`, timestamps, and
digest. A copied or renamed primary manifest is rejected even when its path differs.

The implementation agent's self-review cannot substitute for these roles. Review
findings use Critical/Important/Minor severity; Critical and Important block
delivery and require repair followed by another review.

Use `requesting-code-review` to create a complete review request and
`receiving-code-review` to validate findings against code, Spec, tests, and runtime
evidence rather than accepting them by authority.

## IDE without subagents

If the IDE supports Skills but not subagents, the main agent may execute tasks
sequentially. It must still reset context between roles as far as the platform
allows and must not omit independent Spec review, quality review, or the final
fresh full test/Eval run.
