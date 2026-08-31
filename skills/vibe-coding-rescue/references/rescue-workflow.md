# Rescue Workflow

## Phase 0: Safety Boundary

Before repair, state the allowed mutation scope:

- local files only;
- local commands that do not write to production;
- remote Git push only when requested and the remote is already approved;
- external services, production data, deployments, destructive DB operations, and secret access require explicit authorization.

Always run `git status --short --branch` before editing. If the tree is dirty, separate user changes from rescue changes and avoid unrelated files.

## Phase 1: Baseline Reproduction

Reproduce the reported failure first. Capture:

- command array or shell command;
- working directory;
- runtime versions when visible;
- exit code;
- key error lines;
- whether the command came from README, CI, package scripts, or user report.

If a command is unsafe, record the reason and use the closest safe substitute, such as dry-run, local test mode, fixture data, or static validation.

## Phase 2: Context Inventory

Use the collector output as a map, not a conclusion:

```bash
python3 <skill-dir>/scripts/collect_rescue_context.py <project-root> --output <workdir>/rescue-context.json
```

The script does not mutate the target project; the optional `--output` file is a diagnostic artifact. Put it outside the target repo unless the user explicitly asks to keep it, and do not commit it by default. Then read the relevant files yourself. The script does not prove root cause.

## Phase 3: Failure Chain

Write the chain before fixing:

```text
symptom -> command -> failing boundary -> upstream cause -> candidate repair -> proof command
```

Choose the earliest proven upstream cause. For example, a frontend 500 may be caused by a backend route, which may be caused by a missing database migration, which may be caused by README order drift. Fixing the UI first would be noise.

## Phase 4: Minimal Repair

Prefer changes in this order:

1. Document or env-template correction when the code already works but the run contract is wrong.
2. Config or script correction when the command invokes the wrong entrypoint or environment.
3. Fixture, seed, or migration correction when data setup is stale or incomplete.
4. Contract-source correction when API/schema/DTO definitions drifted.
5. Implementation correction when the code violates the intended behavior.

Do not do broad dependency upgrades, formatter sweeps, framework swaps, lockfile resets, or directory reshuffles unless the failure chain proves they are required and the user accepts the risk.

## Phase 5: Verification

At minimum, rerun the original failing command. Add checks based on the failure class:

- install failure: clean install command or package-manager equivalent;
- startup failure: start command plus local health/page smoke check;
- build/type failure: build/typecheck command;
- test failure: failing test, then relevant suite;
- API/contract failure: caller/server route validation or E2E request;
- database failure: migration/seed/generate command in safe local environment;
- README drift: execute the documented newcomer path or state what could not be run.

Do not claim clean-room readiness unless tested in a clean checkout or equivalent isolated environment.

Newcomer-ready requires all of the following:

- a fresh checkout/container or equivalent isolated state;
- only documented setup inputs, such as `.env.example`, README commands, local Docker services, or explicitly listed credentials;
- install/setup command completed or the missing external dependency was named;
- documented start command reached a real health/page smoke signal;
- documented test or smoke command ran, or the README states why it is not part of local setup.

## Phase 6: Delivery

Before commit or push:

- inspect `git diff` and `git status`;
- run the relevant checks fresh;
- scan for `.env`, secrets, local paths, debug data, generated dumps, and unrelated churn;
- record remaining risks and blocked checks.

If the user requested push, push only the intended branch/ref after verification. If push fails, report the exact Git blocker.

For multi-person or unknown repositories, prefer a rescue branch named from the failure, such as `codex/rescue-startup-env`, unless the user explicitly requested direct push and the repository permits it. If the worktree had user changes, commit only files you changed for the rescue and call out anything intentionally left untouched.
