# Repository Contract and Organization Standard

## Principle

The template defines required information and operational capabilities. It is a
recommended layout, not a mandate to rearrange a coherent existing repository.
Formal projects keep two stable root entry points:

- `README.md`: human navigation and handoff;
- `PROJECT.yaml`: machine-readable paths, commands, owners, risk, and state.

Detailed documents may use either the standard structure or an adapted existing
structure. Content completeness, one source of truth, reproducibility, and
traceability are mandatory in both modes.

## Standard structure option

Use this by default for a new repository or when the user chooses conversion:

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

The internal organization of source, tests, Evals, scripts, and framework files
follows the selected technology. The tree above does not require empty folders.

`eval-plan.md` is always required and records deterministic or probabilistic
acceptance cases. `algorithm-design.md` and a dedicated `evals/` implementation
are additionally required for algorithm, model, Agent, search, ranking,
classification, generation, or automated-decision systems. Because every formal
Vibe Coding Spec contains business success scenarios, the QA normalized Spec,
test design, and test cases are required for every formal project. Do not create empty
not-applicable files; record `not_applicable` and a reason in `PROJECT.yaml` and
README. The machine contract also records the supporting evidence and QA/Decision
Owner approval. Business E2E and Eval are always required; UI, permission, and
recovery requirements are derived from feature and risk facts.

## Adapt-in-place option

When an existing repository has a coherent nonstandard structure, ask the user
to choose exactly one:

1. **Convert to standard structure:** move/consolidate documents, update every
   reference and tool, and verify the repository after the move.
2. **Adapt in place:** preserve real paths and record them in
   `PROJECT.yaml.documentation.paths` and `conditional_paths`.

For adapt-in-place:

- inspect existing documents before creating files;
- map by responsibility and content, not filename similarity alone;
- allow one existing document to cover multiple responsibilities when its
  content really does so;
- fill missing sections or create missing documents beside the repository's
  related documentation;
- do not create a second architecture, test, or runbook source solely to match
  the example tree;
- list the active Spec, Design, Plan, and every mapped document path in README;
- map the QA normalized Spec, QA test design, and QA test cases wherever they live;
- use normalized project-relative paths only; absolute paths and `..` traversal
  are invalid because the contract must survive clone and worktree moves;
- update the map whenever a document moves.

Adaptation never makes a required responsibility optional. An incomplete mapped
document fails the same gate as a missing standard-path document.

## Content completeness review

Existence and length do not prove that a document is complete. Before
initialization passes, an independent review agent creates the mapped
`documentation.content_review` JSON artifact. For each document responsibility it
records the project-relative path, SHA-256, every required semantic topic, and an
exact unique full-line locator plus the located section's SHA-256. The validator
rejects missing topics, stale hashes, reused/nonexistent locators, incomplete or
changed sections, duplicate responsibilities, or a review that does not cover
every mapped document. When content is missing, AI fills the real document first
and the independent reviewer then regenerates the review artifact.

The editable review JSON is an audit record, not cryptographic identity proof.
The orchestrator must dispatch a separate Review Agent and retain its actual
execution trace; final independent review checks that provenance.

The review is evidence of coverage, not authority to change business facts. Any
product or business ambiguity still returns to the responsible owner.

## README

README is the human handoff entry and contains: problem and users, current status
and deployment status, active Spec/Design/Plan links, exact install/start/build/
full-test/Eval/smoke commands, runtime prerequisites, safe configuration and
Secret acquisition, owners and support path, document navigation, known limits,
and recovery entry. Every mode includes exact ``- `responsibility`: `path` ``
entries for organization, active artifacts, mapped documents, and content review;
this makes navigation machine-verifiable. For `adapt_existing`, it additionally
explains why the existing organization is retained. It summarizes and links; it
does not redefine Spec facts.

## PROJECT.yaml

This is the machine-readable state contract. It records project identity, status,
Remote URL, default/feature branches, baseline and last-green commits, active
artifacts, document organization and path map, confirmed risk source/tier, owners, standard commands, feature flags,
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
installation and validation from README, all mapped paths and commands are real,
pre-commit failure blocks a commit, Remote/baseline are verifiable, and no required
artifact is an empty placeholder or contradicts another source.
