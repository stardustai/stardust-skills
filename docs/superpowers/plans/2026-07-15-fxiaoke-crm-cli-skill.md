# Fxiaoke CRM CLI Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the custom-MCP-oriented Fxiaoke skill with a tested `sharecrm` CLI skill, publish it through `stardust-skills`, install it locally, and announce it to the sales engineering group.

**Architecture:** Keep runtime behavior documentation-only: a concise `SKILL.md` defines source-of-truth, permission, query, metric, and write-safety decisions; a separate reference contains command syntax and verified examples. Shell tests validate the package contract, while live read-only commands validate the external CLI path.

**Tech Stack:** Markdown Agent Skills, Bash tests, official `sharecrm` CLI, `jq`, Git, DingTalk `dws`.

---

### Task 1: Add The Failing Package Contract Test

**Files:**
- Create: `tests/fxiaoke-crm-cli.test.sh`

- [ ] **Step 1: Write a shell test that defines the new package contract**

The test must assert that `skills/fxiaoke-crm-cli/SKILL.md` and `references/cli-reference.md` exist, `skills/fxiaoke-crm-mcp` does not exist, frontmatter names `fxiaoke-crm-cli`, the skill references live schema discovery and explicit write confirmation, the reference includes the five metric examples, and `README.md` names the new skill and official CLI dependency.

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$ROOT/skills/fxiaoke-crm-cli/SKILL.md"
REFERENCE="$ROOT/skills/fxiaoke-crm-cli/references/cli-reference.md"

test -f "$SKILL"
test -f "$REFERENCE"
test ! -e "$ROOT/skills/fxiaoke-crm-mcp"
grep -Fq 'name: fxiaoke-crm-cli' "$SKILL"
grep -Fq 'sharecrm auth status' "$SKILL"
grep -Fq 'data describe get' "$SKILL"
grep -Fq 'explicit confirmation' "$SKILL"
grep -Fq 'Signed contract amount' "$REFERENCE"
grep -Fq 'Deal cycle' "$REFERENCE"
grep -Fq 'Opportunity conversion' "$REFERENCE"
grep -Fq 'Delivery volume' "$REFERENCE"
grep -Fq 'Payment amount' "$REFERENCE"
grep -Fq '`fxiaoke-crm-cli`' "$ROOT/README.md"
grep -Fq '`sharecrm` CLI' "$ROOT/README.md"
```

- [ ] **Step 2: Run the test and verify RED**

Run: `bash tests/fxiaoke-crm-cli.test.sh`

Expected: non-zero exit because `skills/fxiaoke-crm-cli/SKILL.md` does not exist.

### Task 2: Replace The Skill Package

**Files:**
- Rename: `skills/fxiaoke-crm-mcp/` to `skills/fxiaoke-crm-cli/`
- Rewrite: `skills/fxiaoke-crm-cli/SKILL.md`
- Create: `skills/fxiaoke-crm-cli/references/cli-reference.md`

- [ ] **Step 1: Rename the tracked skill directory**

Run: `git mv skills/fxiaoke-crm-mcp skills/fxiaoke-crm-cli`

Expected: Git reports a tracked rename; no old skill directory remains.

- [ ] **Step 2: Write the minimal main skill**

The main skill must contain:

```yaml
---
name: fxiaoke-crm-cli
description: Use when the user asks for Fxiaoke CRM or 纷享销客 records, customers, contacts, opportunities, contracts, deal cycle, conversion, sales orders, delivery, payments, receivables, follow-ups, CRM statistics, or CRM write operations through the official sharecrm CLI.
---
```

Its body must define the `auth status -> remote help -> describe -> query` flow, CRM-user permission inheritance, read-only default, explicit confirmation for writes, pagination, metric口径, credential redaction, and routing to the reference file.

- [ ] **Step 3: Write the CLI reference**

Document exact runnable examples for:

```bash
sharecrm auth status
sharecrm --help
sharecrm data describe get -d '{"apiName":"ContractObj"}'
sharecrm data record query-by-sql --sql "SELECT _id, contract_amount FROM ContractObj LIMIT 50 OFFSET 0" --need_count true
```

Add live-schema-first examples for `ContractObj`, `NewOpportunityObj`, `SalesOrderObj`, and `PaymentObj`; numeric millisecond date filtering; pagination; local `jq` aggregation; all five requested metrics; IP whitelist diagnosis; empty results; and safe writes.

- [ ] **Step 4: Run the package test**

Run: `bash tests/fxiaoke-crm-cli.test.sh`

Expected: still FAIL only because README has not yet been updated.

### Task 3: Update Repository Documentation And Evals

**Files:**
- Modify: `README.md`
- Create: `skills/fxiaoke-crm-cli/evals/evals.json`

- [ ] **Step 1: Replace all README references to the MCP skill**

Update the skill table, installation prerequisites, usage examples, permission table, and directory tree. State that the CLI stores its own authenticated session locally, CRM permissions are inherited from the logged-in user, and the repository stores no credentials.

- [ ] **Step 2: Add trigger and behavior eval cases**

Create JSON cases covering positive requests for customer lookup, five-metric reporting, ambiguous tenant fields, authentication failure, and a write request; include negative cases for generic SQL help, another CRM product, and changes to the custom connector repository.

- [ ] **Step 3: Verify GREEN**

Run: `bash tests/fxiaoke-crm-cli.test.sh`

Expected: exit 0.

Run: `bash tests/sync-from-agents.test.sh && bash tests/sync-to-agents.test.sh`

Expected: both existing sync test suites pass.

### Task 4: Install Locally And Run Live Read-Only Verification

**Files:**
- Install target: `/Users/derek/.agents/skills/fxiaoke-crm-cli/`

- [ ] **Step 1: Sync the repository skill to the local skill directory**

Run: `./install.sh`

Expected: `~/.agents/skills/fxiaoke-crm-cli/SKILL.md` and its reference exist; the old installed `fxiaoke-crm-mcp` directory is absent or removed as part of the explicit replacement.

- [ ] **Step 2: Verify authentication and remote command discovery**

Run:

```bash
sharecrm auth status
sharecrm --help
```

Expected: token status is normal and the remote `data` command appears. Treat a whitelist rejection as a query-path failure even when authentication status is normal.

- [ ] **Step 3: Verify schema and one filtered query**

Run:

```bash
sharecrm data describe get -d '{"apiName":"ContractObj"}'
sharecrm data record query-by-sql --sql "SELECT _id, contract_amount, confirm_time, life_status FROM ContractObj WHERE confirm_time >= 1767196800000 LIMIT 1" --need_count true
```

Expected: object fields and at least one permission-visible record return without exposing credentials.

- [ ] **Step 4: Scan for secrets and validate the final diff**

Run:

```bash
rg -n '(APPSecret|permanentCode|refresh[_ -]?token|Authorization: Bearer|cookie)' skills/fxiaoke-crm-cli README.md
git diff --check
bash tests/fxiaoke-crm-cli.test.sh
```

Expected: no credential values, no whitespace errors, and all package tests pass.

### Task 5: Commit And Publish

**Files:**
- Commit all files from Tasks 1-4.

- [ ] **Step 1: Inspect and stage only intended files**

Run: `git status --short && git diff -- README.md skills/fxiaoke-crm-cli tests/fxiaoke-crm-cli.test.sh`

Expected: only the renamed skill, reference, evals, README, test, and implementation plan are changed.

- [ ] **Step 2: Commit the feature**

Run:

```bash
git add README.md skills/fxiaoke-crm-cli tests/fxiaoke-crm-cli.test.sh docs/superpowers/plans/2026-07-15-fxiaoke-crm-cli-skill.md
git commit -m "Replace Fxiaoke MCP skill with official CLI workflow"
```

Expected: one feature commit after the existing design commit.

- [ ] **Step 3: Push and verify**

Run: `git push origin main`

Expected: remote `main` contains both the design and feature commits.

### Task 6: Notify The DingTalk Group

**External target:** DingTalk group `解决方案工程师&销售工程师`

- [ ] **Step 1: Resolve the exact group**

Use the DingTalk chat tools to search by exact group name and verify a unique conversation ID. Do not guess or send to a partial match.

- [ ] **Step 2: Send the release message**

The message must include the GitHub repository, `./install.sh`, the `sharecrm auth login` prerequisite, example prompts for customer lookup and the five-metric report, user-level CRM permission inheritance, and the instruction not to share credentials.

- [ ] **Step 3: Verify delivery**

Record the returned message ID and group name in the task result. Do not include CRM records, live metric values, secrets, or internal IP addresses in the notification.
