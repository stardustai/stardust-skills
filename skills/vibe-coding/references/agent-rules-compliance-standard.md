# Agent Rules Compliance Standard

## Scope discovery

Before planning or editing, find every `AGENTS.md` or `AGENT.md` that applies from
the workspace root to the target file. Follow pointer files to the canonical shared
rule. More specific directory rules refine broader rules unless a higher-priority
instruction says otherwise.

## Audit artifact

Write `docs/agent-rules-audit.md` with, for each material rule:

- source path and effective scope;
- the actionable requirement in concise form;
- code, configuration, command, or runtime evidence checked;
- status: compliant, technical debt, readiness gap, or process violation;
- linked TD-ID/gap, repair, and verification when non-compliant.

Do not copy secrets or large rule files into the artifact. Record enough context
for a reviewer to reproduce the check.

## Classification

- A rule violation embedded in existing code or architecture is technical debt.
- Missing documentation, Remote, test entry, Eval entry, or pre-commit is an
  engineering-readiness gap.
- The current agent's failure to follow communication, evidence, permission, or
  workflow rules is a process violation and blocks the current step.
- Conflicting rules are not resolved by guessing; surface the conflict and seek
  the appropriate decision.

## Graphify exclusion

Graphify may exist in an individual workspace and may be used when that workspace's
local instructions require it. It is not a company Vibe Coding requirement, is
not part of this Skill's portable project contract, and its absence or freshness
must not block initialization, coding, verification, completion, or delivery.
