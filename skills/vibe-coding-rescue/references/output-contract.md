# Output Contract

Use this structure for rescue reports and final replies. Keep it concise, but do not omit evidence.

## Fixed

```markdown
**Rescue Verdict:** fixed

**Original Failure**
- Command:
- Exit/code before:
- Failing boundary:

**Failure Chain**
- Symptom:
- Root cause:
- Repair:

**Changed Files**
- `path`: reason

**Verification**
- `command`: exit 0, key evidence
- `command`: exit 0, key evidence

**Newcomer Runbook**
- README/env/start/test status:
- Clean checkout/container evidence, or explicit reason this is local-only:

**Remaining Risk**
- None known / specific residual risk

**Git**
- Commit:
- Branch/PR/push:
```

## Partially Fixed

Use when one proven failure is repaired but another verified blocker remains.

```markdown
**Rescue Verdict:** partially fixed

**Repaired**
- Failure chain and proof:

**Still Failing**
- Command:
- Current error:
- Why this is a separate blocker:

**Next Action**
- Exact owner/material/credential/decision needed:
```

## Blocked

Use when safe local work cannot proceed.

```markdown
**Rescue Verdict:** blocked

**Last Safe Evidence**
- Files inspected:
- Commands run:
- Error or missing artifact:

**Blocked By**
- Missing authorization / private package / database / secret / product decision / unsafe command:

**What I Did Not Do**
- Explicitly list skipped production, destructive, or credentialed actions.

**Next Action**
- Minimal request to unblock:
```

## Wording Rules

- Avoid "should be fixed", "probably", "looks good", or "seems fine" in verdicts.
- Never report a command as passing unless it was run fresh in the current rescue.
- If only local checks were run, say local-only.
- If README was not executed end to end from a clean or equivalent isolated state, do not say newcomer-ready.
- If CI or deploy was not run, do not say CI-ready or deployable.
