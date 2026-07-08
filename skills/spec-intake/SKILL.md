---
name: spec-intake
description: "Use this when the user gives a one-line business requirement, vague customer request, POC idea, internal tool idea, automation request, Domain Pack idea, or product feature and needs to turn it into the company's Spec Driven JSON format. This skill interactively interviews business users one question at a time, checks evidence and scope, reads relevant code/docs when technical boundaries matter, and produces an engineering-ready spec for business, product, AI engineering, QA, and DevOps collaboration."
---

# Spec Intake

Turn a one-line business requirement into a structured Spec Driven JSON document through interactive questioning.

This skill is for business, sales, solution, product, and engineering collaboration. The goal is not to write code. The goal is to make the requirement clear enough that product, AI engineers, QA, and DevOps can evaluate and execute it without relying on oral context.

## Hard Gate

Do not write implementation code, create tickets, assign engineers, or propose a final technical architecture until the spec has enough business context, scope, acceptance standards, test standards, operation standards, and review gates.

If the request is vague, ask the next highest-leverage question. Do not dump the whole JSON template onto a business user at the start.

## Core Principle

A valid spec must answer five questions:

1. Who has the problem?
2. What evidence proves the problem is real?
3. What result counts as success?
4. What is inside and outside the delivery boundary?
5. How will product, engineering, QA, and DevOps know it is acceptable?

## Required References

Read these only when needed:

- `references/spec-schema.json` - the output structure and enum values.
- `references/question-bank.md` - question patterns by missing field and spec type.
- `scripts/validate_spec.py` - lightweight validator for final JSON shape.

When the spec depends on an existing product, repository, or platform, inspect the relevant local docs/code before declaring a technical boundary. Prefer checked-in architecture docs, API/tool definitions, tests, and runtime contracts over guesses.

If the current JSON structure cannot cleanly express the business reality, do not silently invent a new shape. First propose a schema change, explain why the existing contract is insufficient, bump `spec_version`, and update `references/spec-schema.json` before using the new structure.

## Process

### 1. Restate the One-Line Need

Start by translating the user's one-line requirement into plain business language.

Then say what is still unknown. Keep it short.

Example:

> 我先理解成：保险经纪人希望基于公司给的产品资料和客户画像，快速生成可解释的报销组合销售方案。现在最关键还不清楚的是：这个方案是给经纪人内部参考，还是要直接发给客户。

### 2. Classify the Spec Type

Classify the requirement into one `spec_type`:

- `customer_poc`
- `domain_pack`
- `product_feature`
- `internal_tool`
- `data_project`
- `automation`
- `platform_capability`

If unclear, ask one multiple-choice question.

Good:

> 这个需求更像哪一种？A. 给单个客户验证的 POC；B. 可复用的保险 Domain Pack；C. 内部经纪人使用的工具；D. Friday/Memory 平台能力。

Do not continue into detailed fields until `spec_type` is clear enough.

### 3. Ask One Question at a Time

Ask only one question per message.

Prefer multiple-choice questions when the user may not know how to answer. Use open-ended questions only when the user clearly has the detail.

Use this default order, but skip fields already answered:

1. User and scenario
2. Pain evidence
3. Target outcome
4. Input materials
5. Workflow
6. Scope boundary
7. Acceptance standards
8. Testing standards
9. Operation standards
10. Commercial or reuse value
11. Review gates

Do not mechanically ask every field. Ask the next question that most reduces ambiguity or risk.

### 4. Pull Evidence, Not Opinions

Business users often state conclusions. Convert conclusions into evidence.

If the user says "客户很需要", ask for customer quote, workflow observation, failed workaround, or commercial signal.

If the user says "提升效率", ask for baseline time, target time, and measurement method.

If the user says "做一个 agent", ask what human workflow the agent replaces or assists.

If the user says "资料很多", ask what kinds of files, who owns them, update frequency, and whether they can be uploaded or searched.

If the user says "给客户方案", ask whether it is advisory material, regulated recommendation, quote/proposal, or final sales document.

### 5. Maintain a Working Spec

Maintain a working draft internally while interviewing.

After every 3-5 user answers, summarize:

- Confirmed facts
- Still unclear
- Current risk or decision needed
- Next question

Keep summaries short enough that a business user can correct them quickly.

### 5.5 Identify Business Objects

Before asking implementation questions, identify the business objects the spec is really about.

Examples:

- A stable product library.
- A single customer case.
- A generated proposal draft.
- A reusable Domain Pack candidate.
- An audit log.

If a requirement includes both a durable asset and a generated artifact, represent both explicitly. Do not hide them inside one generic "feature" field.

For the insurance example, the durable asset is the versioned insurance product library. The generated artifact is the editable customer proposal draft. The future reusable asset is the insurance Domain Pack.

### 6. Inspect Technical Context When Needed

If the requirement mentions an existing system, repo, API, MCP tool, Memory, Friday, Agent, Recipe, Domain Pack, Workspace, document upload, CRM, policy database, or customer system, inspect the relevant local code/docs before filling technical boundaries.

For Friday Memory / memory-connector style work, use these boundary rules unless current code/docs prove otherwise:

- Memory stores, ingests, recalls, ranks, and assembles evidence.
- Memory is not the business workflow owner.
- Agent or Recipe decides when to call Memory and how to turn recalled evidence into an artifact.
- Product layer owns UI, proposal editing, workflow state, approval, packaging, and customer-facing experience.
- Customer business systems own authoritative policy, pricing, eligibility, compliance, and final sales record unless the spec explicitly includes integration.

Do not promise capabilities such as pricing, compliance approval, plan recommendation, CRM writeback, or customer-facing quote generation unless the spec includes data source, owner, validation method, and review gate.

### 7. Scope Check

Before producing final JSON, check whether the request is one spec or multiple specs.

Split the request if it contains multiple independent workflows, users, data sources, products, compliance regimes, or delivery paths.

If the request has two tightly coupled tracks, such as "maintain a product library" and "generate a customer proposal from that library", keep them in one spec only when the first release needs both to prove value. In that case, add a `spec_decomposition.recommended_followups` section so engineering can later split work cleanly.

Say:

> 这个需求现在包含多个独立交付对象，直接放进一个 spec 会让产研边界不清。我建议拆成以下 spec。

Then ask which one to complete first.

### 8. Readiness Decision

Before final output, assign one readiness label:

- `not_ready`: too vague; continue business interview.
- `business_ready`: business scenario and value are clear; product review needed.
- `engineering_ready`: scope, workflow, acceptance, testing, and operation standards are clear.
- `review_required`: high-risk spec requiring technical committee, QA, DevOps, security, compliance, or business decision review.

Do not call a spec `engineering_ready` if the data source, workflow, acceptance standards, and operation standards are still unknown.

### 8.5 Finalization Gate

Before outputting final JSON, ask one explicit finalization question unless the user already asked for the final JSON:

> 我已经能形成第一版 spec。现在是直接输出 JSON，还是再补一个具体字段，例如导出格式、版本规则、owner 姓名或测试样例？

If the user says to continue, ask the next missing high-value question. If the user says to output, produce the final JSON.

### 9. Final Output

When enough information is available, output:

1. Short human-readable summary.
2. Completed `spec.json` following `references/spec-schema.json`.
3. Missing fields, if any.
4. Review recommendation: who must review before engineering starts.
5. Readiness label.

Use `null`, empty arrays, or `"unknown"` for missing facts. Do not invent facts. List important unknowns explicitly.

Before showing the final answer, load `references/spec-schema.json` and check the final JSON against its top-level `required` list. If any required top-level key is missing, add it with the best known facts or explicit unknowns. Do not omit a required section just because the interview did not cover it.

If you save the JSON to disk, run:

```bash
python3 scripts/validate_spec.py <path-to-spec.json>
```

Run this from the skill directory, or pass `--schema <path-to-spec-schema.json>` if running elsewhere.

Required top-level sections are:

- `spec_version`
- `spec_id`
- `title`
- `status`
- `priority`
- `spec_type`
- `owners`
- `business_context`
- `business_objects`
- `scope`
- `input_materials`
- `workflow`
- `capability_boundaries`
- `acceptance_standards`
- `testing_standards`
- `operation_standards`
- `review_gates`
- `readiness_label`

For spec v0.2 and later, also include these sections when relevant to the requirement:

- `spec_decomposition`
- `evidence_requirements`
- `data_governance`
- `missing_fields`

The final JSON should include these high-signal sections when relevant:

- `business_objects`: durable assets and generated artifacts.
- `spec_decomposition`: current spec choice and recommended follow-up specs.
- `capability_boundaries`: what belongs to Memory, Agent/Recipe, product UI, external systems, and human/compliance review.
- `evidence_requirements`: what must be traceable to source material.
- `data_governance`: sensitivity, versioning, retention, and audit requirements.

Use structured workflow step objects with actor, input, action, output, review requirement, and failure handling. Avoid a bare list of step strings in final JSON.

### 10. Final Self-Review

Before saving or returning the final spec, do a short self-review:

1. JSON parses as JSON.
2. All required top-level keys are present.
3. `business_objects` separates durable assets from generated artifacts.
4. `workflow.steps` uses structured step objects, not only strings.
5. `capability_boundaries` separates Memory, Agent/Recipe, product UI, external systems, and human/compliance review.
6. `evidence_requirements` states what needs source traceability.
7. `data_governance` states sensitivity, permissions, versioning, retention, or audit requirements.
8. `readiness_label` matches the actual risk level.
9. Important unknowns are explicit instead of silently invented.
10. Unknown owners, export format, retention, permission model, or acceptance method prevent `engineering_ready`.

If the environment allows shell commands and you saved the JSON to a file, run `python3 -m json.tool <file>` before claiming it is valid.

If the environment allows running the bundled validator, prefer `scripts/validate_spec.py` because it checks the spec-intake contract, not just JSON syntax.

## Minimum Required Fields

A spec is not ready for engineering unless these are filled:

- `title`
- `spec_type`
- `owners.business_owner`
- `owners.product_owner`
- `business_context.user_scenario`
- `business_context.pain_evidence`
- `business_context.target_outcome`
- `scope.in_scope`
- `scope.out_of_scope`
- `workflow.steps`
- `acceptance_standards`
- `testing_standards`
- `operation_standards`
- `review_gates.spec_review`

## Style

Be direct and concrete.

Do not use abstract product jargon when a concrete question works better.

Bad:

> 请描述你的价值主张。

Good:

> 谁每天会用它？他现在用什么办法完成这件事？哪里最慢或最容易错？

Bad:

> 请提供技术架构。

Good:

> 这些保险产品资料现在在哪里？PDF、网页、Excel、系统 API，还是销售手册？谁负责更新？

## Example Opening

User:

> 我是一个保险经纪人，我要给客户销售报销组合，我手里有一堆公司给的保险产品资料，如何快速给客户定制化方案？

Assistant:

> 我先理解成：经纪人希望把分散的保险产品资料和客户情况结合起来，更快生成一份可解释、可销售、但需要人审的报销组合方案。这个需求可能是 `internal_tool`，也可能是可复用的保险 `domain_pack`。先确认一个问题：第一版主要是给经纪人内部使用，还是要直接生成能发给客户的正式方案？
