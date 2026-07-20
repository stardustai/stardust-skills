# Repository Template Standard

## Required contract

Company projects may use different languages and frameworks, but all formal
projects expose the same operational entry points:

```text
README.md
PROJECT.yaml
.gitignore
.githooks/pre-commit
scripts/vibe-coding/run_project_checks.py
docs/
  superpowers/specs/YYYY-MM-DD-<topic>-spec.json
  superpowers/specs/YYYY-MM-DD-<topic>-design.md
  superpowers/plans/YYYY-MM-DD-<topic>.md
  business-goal.md
  system-architecture.md
  runtime-constraints.md
  test-plan.md
  traceability.md
  runbook.md
  technical-debt-register.md
  agent-rules-audit.md
  qa/01-normalized-spec.md
  qa/02-test-design.md
  qa/03-testcases.md
evals/
src/
tests/
```

`eval-plan.md` is always required and records deterministic or probabilistic
acceptance cases. `algorithm-design.md` and a dedicated `evals/` implementation
are additionally required for algorithm, model, Agent, search, ranking,
classification, generation, or automated-decision systems. QA files are required
for business features. Do not create empty
not-applicable files; record `not_applicable` and a reason in `PROJECT.yaml` and
README. The machine contract also records the supporting evidence and QA/Decision
Owner approval. Business E2E and Eval are always required; UI, permission, and
recovery requirements are derived from feature and risk facts.

## README

README is the human handoff entry and contains: problem and users, current status
and deployment status, active Spec/Design/Plan links, exact install/start/build/
full-test/Eval/smoke commands, runtime prerequisites, safe configuration and
Secret acquisition, owners and support path, document navigation, known limits,
and recovery entry. It summarizes and links; it does not redefine Spec facts.

## PROJECT.yaml

This is the machine-readable state contract. It records project identity, status,
Remote URL, default/feature branches, baseline and last-green commits, active
artifacts, confirmed risk source/tier, owners, standard commands, feature flags,
technical-debt decision, pre-commit contract, direct-push/PR policy, and optional deployment state. It must validate
against the package schema and agree with the real repository.

## Remote, baseline, and pre-commit

Before formal coding, verify an accessible Remote URL and that `origin`, default
branch, feature branch, and baseline commit match the contract. Preserve existing
user modifications and never begin from an unknown or unrecoverable state.

Version the pre-commit installation or hook. Every local commit runs
`commands.pre_commit_full`, the repository-owned risk-tier aggregate for applicable
format, static analysis, type check, unit, integration, and build. Never use
`--no-verify`. Final Eval remains a delivery gate and need not run on every small
commit.

Generated `docs/evidence/` files are runtime/CI artifacts and are ignored by Git;
publish them through the approved CI artifact or evidence store when retention is
required. Never commit secrets or raw sensitive command output as evidence.

## Acceptance

The repository contract is established only when a new maintainer can reproduce
installation and validation from README, all paths and commands are real,
pre-commit failure blocks a commit, Remote/baseline are verifiable, and no required
artifact is an empty placeholder or contradicts another source.
