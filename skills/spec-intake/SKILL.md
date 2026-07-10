---
name: spec-intake
description: "Use this when the user gives a one-line business requirement, vague customer request, POC idea, internal tool idea, automation request, Domain Pack idea, or product feature and needs to turn it into the company's Spec Driven JSON format. This skill interactively interviews business users one question at a time, checks commercial evidence and scope before product detail, requires SVG wireframes for UI specs, reads relevant code/docs when technical boundaries matter, and produces a stage-gated spec for sales, product, AI engineering, QA, and DevOps collaboration."
---

# Spec Intake

Turn a one-line requirement into a stage-gated Spec Driven JSON document.

The goal is not to write code. The goal is to make the requirement clear enough that business, product, AI engineering, QA, DevOps, and compliance can decide what the next gate is without relying on oral context.

## Core Rules

1. Extract first, ask second. If the user has already provided enough information for a field or decision, fill it, state the conclusion, and skip that question.
2. Ask one question at a time only for the highest-risk missing information.
3. First identify the company product form: Friday Agent, Domain Pack, Friday Memory, MorningStar, internal tool, standalone product, or demo.
4. For commercial ideas, validate business feasibility before product or technical detail.
5. Do not let vague commercial evidence move into engineering delivery.
6. If UI exists, produce an SVG wireframe and get it reviewed before product-ready or later gates.
7. If Domain Pack is involved, model Friday objects explicitly: Workspace Memory, Task, Artifact, Recipe, Feedback/Comment, and Room.
8. Treat engineering gap review as different from engineering delivery. A spec can be ready for technical gap review while still blocked for implementation.
9. Market validation includes competitor research. If the user cannot provide competitor comparison, research relevant products or substitute workflows and show a comparison matrix for confirmation.
10. Product validation includes technical leadership and uniqueness. The product owner provides the claim; the agent scores it; the product owner confirms.
11. Technical design includes source-code reading and AI scoring. The agent scores the design from code evidence; the AI engineer confirms.
12. If the current schema cannot express the situation, propose a schema bump before inventing fields.

## Extraction Before Questions

The interaction is not a form-filling interview. At the start of each turn:

1. Parse the user's latest message and map any explicit facts to spec fields.
2. State concise conclusions for fields that are already clear.
3. Mark assumptions separately from confirmed facts.
4. Ask only the next question that would change the stage gate, priority decision, product shape, or technical readiness.

Good behavior:

> 你已经明确了买方、使用者和第一版目标，所以这三项我先写入 spec，不再追问。现在真正缺的是是否有 confirmed design partner，因为这会决定能否从 business_ready 进入 product handoff。

Bad behavior:

> 请依次回答：买方是谁？使用者是谁？第一版目标是什么？

Do not ask a question just because it appears in `references/question-bank.md`. The question bank is a menu. Skip any question whose answer is already explicit, inferable with low risk from the user's provided facts, or irrelevant to the current gate.

## Required References

Read only as needed:

- `references/spec-schema.json` - v1.3 JSON structure.
- `references/question-bank.md` - question patterns by gate.
- `scripts/validate_spec.py` - deterministic validator.

When the spec depends on Friday, Memory, Domain Pack, Recipe, Workspace, MCP, document upload, CRM, policy database, or any existing system, inspect the relevant local docs/code before declaring technical boundaries.

## Product Basis

Ask this early:

> 这个需求第一版应该基于我们哪个产品形态来做？A. Friday Agent；B. Domain Pack；C. Friday Memory；D. MorningStar；E. 内部工具；F. 全新独立产品；G. 只是 demo。

Do not infer this silently. A "tool" may be a Domain Pack, Friday Agent workflow, internal tool, or standalone product.

## Business Feasibility Gate

For a Domain Pack, customer POC, commercial product idea, or Pack prioritization request, first fill `opportunity_assessment`.

Ask for:

1. Customer segment: KA, SMB, hybrid, internal, or unknown.
2. Scenario level: L2, L3, L2-to-L3, or unknown.
3. Target buyer and daily user.
4. Current alternative and buyer language.
5. Minimum paid artifact: the smallest thing the buyer would pay for or commit resources to validate.
6. Evidence registry: separate assumptions from customer interviews, customer data, paid signals, usage data, and artifacts.
7. Design partner registry: name/status, budget owner, reviewer, committed resources, data availability.
8. PMF four-factor scores: customer willingness, market clarity, technical value, GTM repeatability.
9. Opportunity priority: `机会优先级指数 = 商业价值 * 商业信号清晰度 / 产研投入量`.
10. Scope-reduction recommendation when scope expansion risk is high.
11. Competitive research: user-provided competitor comparison, or agent-researched comparison matrix when the user has none.

Use evidence levels:

- `hypothesis`: internal assumption.
- `anecdotal`: loose anecdote.
- `single_case`: one traceable customer or workflow case.
- `repeated`: repeated evidence across customers, flows, or channels.
- `commercial_proof`: paid POC, signed commitment, expansion, or repeatable GTM proof.

Do not approve PoC unless there is a confirmed design partner, budget owner or committed resources, available data, baseline, acceptance method, timebox, and minimum paid artifact.

## Competitive Research Gate

In market validation, ask whether the business user already has competitor comparison.

Good question:

> 你们有没有已知竞品或当前替代方案对比？如果没有，我会基于这个痛点和解法做一版产品调研，给出对比矩阵和差异度评分让你确认。

If the user provides competitors, record them in `opportunity_assessment.competitive_research` with `status=user_provided`.

If the user does not provide competitors, research relevant products or substitute workflows. Use current web/product research when available, and cite sources in the comparison matrix. Compare at least:

- Target customer.
- Core workflow.
- Key capabilities.
- Pricing or packaging, if available.
- Strengths.
- Weaknesses.
- Overlap score, 1-5.
- Differentiation score, 1-5.

Use this scoring:

- `overlap_score`: 1 means barely solves the same problem; 5 means it addresses almost the same workflow and buyer need.
- `differentiation_score`: 1 means our proposed solution has no clear difference; 5 means it has a hard-to-copy difference in workflow, data, product loop, or delivery model.

Show the matrix to the user and ask for confirmation. Do not mark product-ready or later gates unless `competitive_research.user_confirmation=confirmed` when research is required.

## Stage Gate

Use `stage_gate` as the single source of truth for where the spec can go next.

Valid next gates include:

- `continue_business_validation`
- `handoff_to_product`
- `continue_product_shape`
- `request_engineering_gap_review`
- `continue_technical_spec`
- `mark_poc_design_ready`
- `mark_poc_execution_ready`
- `ready_for_engineering`
- `stop_archive`

Important distinctions:

- `handoff_to_product` means product should shape the product, not engineering should start.
- `request_engineering_gap_review` means AI engineering may identify capability gaps, not commit to delivery.
- `ready_for_engineering` means owners, scope, validation, implementation mapping, data policy, and gates are ready for implementation planning.

If `opportunity_assessment.priority_decision.recommendation` is `needs_more_evidence`, do not set the decision to `continue_technical_spec`, `mark_poc_design_ready`, `mark_poc_execution_ready`, or `ready_for_engineering`.

## Product Shape Gate

After the commercial gate, define:

- `product_context`
- `business_context`
- `scope`
- `workflow.canonical_workflow`
- `friday_object_model`
- `ui_requirements`
- `capability_boundaries`

Put `spec_type` inside `product_context.spec_type`; do not output a separate top-level `spec_type`.

The `workflow.canonical_workflow` is the one canonical business flow. Avoid repeating the same workflow in multiple sections with slightly different wording.

Use structured workflow steps with:

- `step_id`
- `phase`
- `actor`
- `input`
- `action`
- `output`
- `human_review_required`
- `failure_handling`

## Product Leadership Gate

During product shape, ask the product owner to state the technical leadership or uniqueness claim.

Good question:

> 这个产品形态的领先性或独特性是什么？请给一个论述或证明：它相对竞品、通用 LLM、客户现有流程，领先在哪里？

Record this in `product_context.technical_leadership`.

The agent must score the claim from 1 to 5:

- 1 = mostly commodity capability; no defensible difference.
- 2 = difference exists in packaging or UX, but core capability is easy to copy.
- 3 = clear single-point differentiation in workflow, data, or delivery.
- 4 = strong differentiation across workflow, data/Memory, review loop, and evaluation loop.
- 5 = repeated proof that the product has a hard-to-copy advantage across customers or deployments.

Ask the product owner to confirm or reject the score. Do not mark product-ready or later gates unless `product_context.technical_leadership.product_owner_confirmation=confirmed`, unless the field is not applicable.

## Domain Pack Gate

For Domain Pack specs, do not treat the Pack as a single prompt or Recipe.

Model these explicitly in `friday_object_model`:

| Object | Purpose |
| --- | --- |
| Workspace Memory | Reusable facts, source-backed history, confirmed preferences, domain knowledge |
| Task | The user's real work instance |
| Artifact | Reviewable output such as draft, report, proposal, decision record |
| Recipe | Reusable method, rubric, flow, constraints, correction rules |
| Feedback/Comment | Human review tied to Artifact, used to create update candidates |
| Room | One task instance around one shared Artifact or conclusion |

The object relationship must state the loop:

`Task -> Artifact -> Feedback/Comment -> human-confirmed Recipe or Memory update candidate`

Workspace changes must not silently mutate the master Pack.

## Knowledge And Memory Policy

Use `knowledge_and_memory_policy` to decide what can be remembered.

For each `memory_write_rules[]` item, specify:

- `source_type`
- `write_allowed`
- `requires_human_approval`
- `target_scope`
- `redaction_required`
- `rollback_method`

If `write_allowed=true`, require human approval and rollback method. Customer private data, health data, salaries, personal identifiers, and unrelated personal information should generally be task context only or not allowed.

## UI Wireframe Gate

If the feature has a UI, dashboard, workspace, editor, approval screen, or visual workflow:

1. Produce a low-fidelity `.svg` wireframe.
2. Add the file path to `ui_requirements.wireframe_artifacts`.
3. Set `wireframe_status` to `drafted` until the user confirms it.
4. Do not mark `product_ready`, `engineering_gap_review_ready`, `poc_design_ready`, `poc_execution_ready`, or `engineering_ready` until `wireframe_status=reviewed`.

Markdown, Mermaid, or ASCII diagrams can explain the UI, but they do not satisfy the SVG requirement.

## Technical Context Gate

If the requirement mentions an existing product, repo, API, MCP tool, Memory, Friday, Agent, Recipe, Domain Pack, Workspace, document upload, CRM, policy database, or customer system, inspect local docs/code before filling `implementation_mapping`.

Separate:

- existing capability
- partial capability
- missing API
- external authoritative system
- unknown owner or uncertainty

Do not promise pricing, compliance approval, plan recommendation, CRM writeback, or customer-facing quote generation unless the spec includes data source, owner, validation method, and review gate.

## Technical Design Scoring Gate

When the user moves from engineering gap review to technical design, read source code and architecture docs before scoring the design.

Fill `implementation_mapping.source_code_review`:

- `required=true`
- `status=completed` before technical design or delivery plan
- `paths_read` with local code/doc paths
- `summary` with what the code proves
- `unread_required_paths` empty before technical design can pass

Then score `implementation_mapping.technical_design_assessment`.

Use these dimensions, each 1-5:

- `architecture_fit`: whether the design fits existing Friday architecture and ownership boundaries.
- `code_reuse`: whether existing code/docs/APIs can be reused instead of building a parallel system.
- `integration_complexity`: lower complexity earns higher score; heavy cross-system coupling lowers score.
- `data_and_memory_fit`: whether data, Memory scope, traceability, and write rules are clear.
- `security_and_compliance`: whether permissions, privacy, audit, and compliance review are addressed.
- `testability`: whether the design can be evaluated with fixtures, metrics, and regression.
- `operability`: whether monitoring, fallback, support, and rollback are defined.
- `delivery_risk`: lower delivery uncertainty earns higher score.

Overall `ai_score` should reflect the weakest major risk, not the average only. A design with one blocking compliance or architecture issue should not score above 3.

Ask the AI engineer to confirm the score. Do not mark `engineering_ready` unless `source_code_review.status=completed`, required dimensions are scored, and `technical_design_assessment.ai_engineer_confirmation=confirmed`.

## QA And PoC Gate

Use `validation_plan`, not scattered acceptance/testing fields.

`poc_design_ready` requires:

- scenario
- golden cases or fixture plan
- rubric
- failure cases
- acceptance method
- metric definitions

`poc_execution_ready` additionally requires:

- available or approved assets
- owners
- environment
- data permission
- privacy approval
- regression set
- blocking error definition
- observability or audit events

Each metric must include:

- `metric_id`
- definition
- baseline
- target
- measurement method
- fixture id
- owner
- pass/fail rule

## Final Output

When enough information is available, output:

1. Short human-readable summary.
2. Completed `spec.json` following `references/spec-schema.json`.
3. Missing fields.
4. Review recommendation.
5. Current `stage_gate`.

Use `null`, empty arrays, or `"unknown"` for missing facts. Do not invent facts. Important unknowns must appear in `missing_fields`.

Required top-level sections:

- `spec_version`
- `spec_id`
- `title`
- `status`
- `priority`
- `stage_gate`
- `opportunity_assessment`
- `product_context`
- `owners`
- `business_context`
- `scope`
- `workflow`
- `friday_object_model`
- `knowledge_and_memory_policy`
- `ui_requirements`
- `capability_boundaries`
- `validation_plan`
- `operation_standards`
- `implementation_mapping`
- `review_gates`
- `missing_fields`

If saving JSON to disk, run:

```bash
python3 scripts/validate_spec.py <path-to-spec.json>
```

## Final Self-Review

Before returning or saving the final spec, check:

1. JSON parses.
2. All required top-level keys are present.
3. `stage_gate.decision` matches the real next gate.
4. `needs_more_evidence` does not move to engineering delivery.
5. Evidence refs point to `evidence_registry`.
6. PMF scores >= 3 have non-assumption evidence.
7. `competitive_research` has a competitor/substitute matrix, differentiation score, and user confirmation when research is required.
8. `product_context.technical_leadership` has a claim, proof or argument, agent score, and product owner confirmation before product-ready or later gates.
9. Domain Pack specs declare the Friday object loop.
10. Memory write rules have approval, target scope, redaction, and rollback.
11. UI specs include a produced SVG and reviewed status before product-ready or later gates.
12. `validation_plan` separates PoC design readiness from execution readiness.
13. `implementation_mapping` distinguishes existing, partial, missing, external, and unknown capabilities.
14. Technical design specs include completed source code review, scoring dimensions, and AI engineer confirmation.
15. `engineering_ready` has real owners, no missing fields, and no missing or unknown implementation capabilities.

## Style

- Use concrete business language.
- Prefer multiple-choice questions for non-technical users.
- Ask open questions only when the user likely has the detail.
- Do not dump a giant JSON template at the start.
- Do not hide uncertainty. Make it a blocker or missing field.
