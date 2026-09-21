---
name: codex-model-capacity-retry
description: Use when an existing Codex task or session ends with “Selected model is at capacity”, “model at capacity”, “server_overloaded”, HTTP 429, or “too many requests”, especially when the original task must continue without changing its model or reasoning effort.
---

# Codex model-capacity retry

Use this skill for a provider-capacity interruption, not for a normal task failure. The important invariant is to continue the existing task: do not create a new `codex exec` task, do not choose a replacement model, and do not set reasoning effort.

## Start an independent watcher

A skill loaded inside the failed turn cannot intercept the request that already failed. Start the watcher from an independent terminal process:

```bash
python3 /Users/derek/.agents/skills/codex-model-capacity-retry/scripts/scan_and_retry_sessions.py --watch --daemon \
  --exclude-session-id CONTROL_TASK_SESSION_ID
```

`--daemon` detaches the watcher from the terminal, shell, or Codex tool session that started it. This is required when the launching terminal may close; without it, the operating system may reap the watcher with that terminal. It waits five seconds after detecting a capacity error, then retries indefinitely. Stop it only when the user asks or when the original task has completed. There is no fixed attempt limit. The watcher remembers the exact failed completion, so it does not duplicate one failure; a later capacity failure appended to the same task has a new signature and is retried again.

The detached watcher writes its PID to `~/.codex/codex-capacity-retry.pid` and its output to `~/.codex/codex-capacity-retry.log`. The state-file lock prevents a second watcher from duplicating retries.

`CONTROL_TASK_SESSION_ID` is the session ID of the task that owns the watcher or heartbeat. Exclude that task. Otherwise a Desktop writer-conflict fallback can queue a new visible retry message into the control task itself, causing the watcher to trigger its own next scan. Repeat `--exclude-session-id` when one watcher is coordinating more than one controller task. The same list can be supplied through `CODEX_RETRY_EXCLUDE_SESSION_IDS`, separated by commas.

## What it scans

The scanner groups rollout files by session and uses the newest turn boundary across the group. It retries only when that newest boundary is a capacity-failed completion; an older capacity failure is ignored while a newer turn is running or has completed. Capacity symptoms include `Selected model is at capacity`, `model at capacity`, `server_overloaded`, `429`, or `too many requests`. It must never retry an authentication, permission, validation, tool, or business-logic failure.

For a CLI-owned session it runs:

```text
codex exec resume --json --skip-git-repo-check SESSION_ID "continue"
```

The command keeps the original session ID, allows the detached watcher to run independently of the launching directory, and does not pass `--model`, `--thinking`, `model_reasoning_effort`, or an effort override.

## Desktop-owned tasks

Desktop tasks can appear in the app-server as a failed/system-error turn even when no new `task_complete` record is appended to the JSONL file. If `codex exec resume` reports `thread-store conflict` or `already has an active writer`, the script queues the same follow-up to the same thread through the shared app-server:

```text
codex queue --thread SESSION_ID --message "continue"
```

This is a continuation of the existing task, not a new exec session, and it deliberately omits model and reasoning settings. If the app-server is not reachable, inspect the last turn with the Codex app thread tools and use `send_message_to_thread` on the same thread ID, omitting `model` and `thinking`.

When checking a Desktop task manually, inspect only the newest turn first. A task is eligible only when its newest error is a capacity error; never revive a task just because it is `failed` or `systemError`.

## Boundaries

- Preserve the original task/session/thread ID and the original model settings.
- Retry continuously at five-second intervals until the task produces a non-capacity completion or the watcher is stopped.
- Do not retry semantic evaluation failures, Buildkite test regressions, missing fixtures, provider authentication failures, or ordinary tool errors.
- Do not use a new `codex exec` invocation as a substitute for resume or queue.
- The default scan age is six hours; set `CODEX_RETRY_MAX_AGE_SECONDS=0` to scan all session files.
- Use the state file to coordinate multiple watchers; a lock prevents duplicate watchers from retrying the same task.

## Verification

Run the bundled regression test:

```bash
bash /Users/derek/.agents/skills/codex-model-capacity-retry/tests/test_session_scanner.sh
```

The test proves capacity matching, same-session resume, no model/effort override, duplicate suppression, repeated retry after a new capacity failure, historical rollout suppression, controller-session exclusion, and Desktop writer-conflict routing through same-thread queue.

It also verifies that `--daemon --once` returns control to the launching process, preserves the launch working directory for `codex exec resume`, and exits cleanly.
