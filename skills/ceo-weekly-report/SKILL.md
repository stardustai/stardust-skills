---
name: ceo-weekly-report
description: Use when preparing, reconciling, reviewing, validating, or publishing the CEO's weekly management report or its company and business-line sections from DingTalk evidence.
metadata:
  managed_by: ceo-agent-service
---

# CEO Weekly Report

## Overview

Produce an evidence-backed management mechanism, not an activity summary. Track
results, deviations, recurring causes, decisions, and unresolved issues across
Beijing-calendar weeks.

Read [report-contract.md](references/report-contract.md) and
[dingtalk-runbook.md](references/dingtalk-runbook.md) completely before work.

## Required Inputs

- Exact target DingTalk document URL or node ID and target date.
- Prior weekly report and current company DingTang OKR.
- MorningStar, Friday, international, and world-model marketing source reports.

An unresolved target, inaccessible prior report, incomplete Minutes/message
inventory, unresolved CEO identity, or inaccessible core source blocks
publication.

## Workflow

1. Require the runtime to provide `CEO_WORKSPACE`, then create the dated run
   directory under `${CEO_WORKSPACE}/02_管理与组织/CEO周报运行/`. Never infer a
   machine-specific home or memory path.
2. Resolve the Beijing window and exact target/prior identity. Save the target
   revision and full JSONML before editing.
3. Inventory all accessible AI Minutes. Screen every item from title, summary,
   actions, participants, and links; read complete transcripts for relevant
   meetings.
4. Resolve the CEO's DingTalk identity from the authenticated profile or another
   verified identity source. Search all accessible chats for that verified
   identity's messages and read sufficient context for every selected message.
5. Read all four source reports and linked evidence without editing them. Read
   authoritative operating actuals when accessible; otherwise write `无数据`.
   Use CRM as the sole system of record for sales data, including orders,
   Pipeline, Lead/Opportunity Gate, expected signing, and commercial POC
   status. Do not ask finance to supply or confirm sales-funnel data. Finance
   remains the source only for accounting metrics such as recognized revenue,
   cash received, gross margin, and overdue receivables.
   For decision-critical missing actuals, include the responsible native mention
   and a dated next checkpoint; never substitute a target or plan for an actual.
6. Extract prior open issue IDs. Reconcile new evidence against the original
   question, prior diagnosis, deadline, and closure standard.
7. Draft the seven-section `report.json`. Classify every consequential claim
   and retain evidence IDs.
8. Run `scripts.validate_run`; fix blockers locally. Render JSONML and inspect
   tables, folds, links, and resolved native mentions.
9. With explicit authorization to update the named report, save a recoverable
   document version, re-fetch the revision, and stop on any change.
10. Perform one revision-guarded overwrite. Fetch the complete result and pass
    every readback check before reporting completion. Unknown write status
    requires readback, never a blind second write.

## Management Reasoning

- Ask what result changed, what proves it, what deviated, why it recurred, and
  which management choice is required.
- Separate fact, participant statement, forecast, CEO judgment, current
  judgment, and hypothesis. Treat coordination gaps as coordination gaps rather
  than unsupported blame.
- Friday demand, resources, and timing require Derek's unified confirmation.
  Financial demand requires Shawn and Derek alignment.
- MorningStar's overall plan is decided by Shawn; market direction, product
  path, and technical leadership require Derek's confirmation and feedback.
  Test the plan for new opportunities, customer profile, sales assumptions,
  market validation, leading features, and commercial feedback loops.
- Reconcile Friday product and technical milestones, release Gate, business and
  general Eval ownership, scenario evidence, staffing, and reusable assets.

## Completion Gate

Completion requires `publishable: true`, a saved version, unchanged expected
revision, one guarded write, and a full matching readback. A successful command
response alone is insufficient.
