---
name: spec-intake
description: "Use this when the user gives a one-line business requirement, vague customer request, POC idea, internal tool idea, automation request, Domain Pack idea, or product feature and needs to turn it into the company's Spec Driven JSON format. This skill interactively interviews business users one question at a time, checks evidence and scope, reads relevant code/docs when technical boundaries matter, and produces an engineering-ready spec for business, product, AI engineering, QA, and DevOps collaboration."
---

# Spec Intake

Turn a one-line business requirement into a structured Spec Driven JSON document through interactive questioning.

This skill is for business, sales, solution, product, and engineering collaboration. The goal is not to write code. The goal is to make the requirement clear enough that product, AI engineers, QA, and DevOps can evaluate and execute it without relying on oral context.

The intake is staged. A one-line need first becomes a business feasibility JSON. After commercial feasibility is clear, the user can hand it to product or continue to product shape. After product shape is clear, the user can hand the JSON to technology or continue to technical specification. Do not force business users through technical questions before the business gate is clear.

## Hard Gate

Do not write implementation code, create tickets, assign engineers, or propose a final technical architecture until the spec has enough business context, scope, acceptance standards, test standards, operation standards, and review gates.

If the request is vague, ask the next highest-leverage question. Do not dump the whole JSON template onto a business user at the start.

## Core Principle

A valid spec must answer these core questions:

1. Which company product form is this based on?
2. Who has the problem?
3. What evidence proves the problem is real?
4. What result counts as success?
5. What is inside and outside the delivery boundary?
6. How will product, engineering, QA, and DevOps know it is acceptable?

For a Domain Pack candidate or market-facing idea, a valid intake must also answer:

7. Is this commercially worth product attention now?
8. Is it KA, SMB, hybrid, internal, or still unknown?
9. Is it an L2 scenario, an L3 aggregation of multiple L2 scenarios, or still unclear?
10. Which handoff gate is the user choosing now: handoff to product, continue product shape, handoff to technology, or continue technical spec?

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

### 2. Classify Product Basis

Before classifying the work item, ask which company product form this should be built on.

Use one `product_context.build_target`:

- `friday_agent`
- `domain_pack`
- `friday_memory`
- `morningstar`
- `internal_tool`
- `standalone_product`
- `demo`
- `unknown`

Good first product-basis question:

> 这个需求第一版应该基于我们哪个产品形态来做？A. Friday Agent；B. Domain Pack；C. Friday Memory；D. MorningStar；E. 内部工具；F. 全新独立产品；G. 只是 demo。

Do not silently assume product basis from the use case. A "面试流程管理工具" could be an internal tool, a Friday Agent workflow, a Domain Pack, or a standalone product; the downstream spec is different.

If the user chooses `domain_pack`, immediately switch on the Domain Pack questions before implementation details.

Use this company product model:

- Domain Pack is an industry or scene-level resource package, not a single recipe, prompt, folder, or one-off demo.
- Domain Pack is private by default: produced for a person, team, company, or customer and used in that private context. It is not designed to be generic first.
- Sharing or marketplace distribution is an optional later choice by the Pack owner, not the default product goal.
- Domain Pack is the reusable workbench and delivery unit for that private context. It can be shared, deployed, upgraded, versioned, and rolled back.
- A Domain Pack can contain runnable Recipes, Memory assets, Connectors, interface/workspace configuration, permissions, evaluation assets, and version metadata.
- Recipe is the method asset inside the Domain Pack: reusable task method, rubric, strategy, flow, expert judgment structure, and failure-correction rule.
- Memory is the factual/context asset: enterprise, project, customer, person, time, fact, history, decision, and source evidence.
- Workspace is the customer runtime instance that loads a Domain Pack. Workspace may collect feedback and local updates, but it must not silently mutate the master Pack.
- Friday is the execution substrate for running the Pack through Workspace, Room, Artifact, Memory, Recipe, Connector, review, and versioned updates.

Domain Pack anti-patterns:

- Treating the Pack as only a prompt or one Recipe.
- Treating Memory as a document folder.
- Treating Workspace as the master Pack.
- Letting a customer's Workspace changes silently contaminate the reusable Pack.
- Designing self-learning without review, versioning, evaluation, and rollback.
- Building a full business operating system when Friday should only own the shared artifact / conclusion layer.

- What repeatable domain workflow is being packaged?
- What domain materials should become Memory?
- What should not be remembered?
- What Recipe produces the first version?
- What feedback loop improves the Recipe after real use?
- What Workspace screens or artifacts does the user operate in?

### 2.5 Business Feasibility Gate

For every one-line Domain Pack idea, customer POC, commercial product idea, or Pack prioritization discussion, start with business feasibility before product or technical detail.

The first goal is to determine whether the idea is worth product attention and whether it should be handed to product now. Do not ask about Recipe internals, Memory partitioning, Workspace implementation, SVG wireframes, or engineering architecture until the commercial gate is clear enough.

Ask the minimum questions needed to fill `commercial_context`:

1. KA, SMB, hybrid, internal, or unknown.
2. L2 scenario, L3 aggregation, L2-to-L3 path, or unknown.
3. Target buyer and target user.
4. Customer pain and current alternative.
5. Real evidence: customer meeting, sales lead, paid POC, quote, usage data, or other source.
6. Deliverable and why the customer would pay.
7. Market or customer pool, design partner, POC path, cooperation model, and pricing hypothesis.
8. Biggest delivery risk and next sales action.

After this gate, present a short decision:

- `business_ready`: enough business context exists to hand JSON to product.
- `not_ready`: commercial feasibility is still vague; continue business interview.
- `review_required`: the idea is commercially important but needs leadership, legal, compliance, security, or delivery review before product shaping.

Then ask one explicit handoff question:

> 商业可行性已经能形成第一版 JSON。现在是 A. 交给产品继续判断产品形态，还是 B. 我们继续把产品形态也补清楚？

If the user chooses handoff, set `intake_stage` to `business_feasibility`, `handoff_options.selected_next_action` to `handoff_to_product`, and do not keep asking product/technical questions.

If the user chooses to continue, set `handoff_options.selected_next_action` to `continue_product_shape` and proceed to product shape.

### 3. Classify the Spec Type

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

### 4. Ask One Question at a Time

Ask only one question per message.

Prefer multiple-choice questions when the user may not know how to answer. Use open-ended questions only when the user clearly has the detail.

Use this default order, but skip fields already answered:

1. Business feasibility, if the idea is a Domain Pack candidate, customer POC, commercial product idea, or prioritization candidate.
2. Product basis.
3. Product shape: spec type, user/scenario, business objects, scope, workflow, UI need.
4. Handoff to product or continue to technical spec.
5. Domain Pack / Memory / Recipe / Workspace fit, if applicable.
6. Input materials.
7. Workflow details.
8. Acceptance standards.
9. Testing standards.
10. Operation standards.
11. Capability boundaries.
12. Review gates.
13. Handoff to technology or continue technical detail.

Do not mechanically ask every field. Ask the next question that most reduces ambiguity or risk.

### 5. Pull Evidence, Not Opinions

Business users often state conclusions. Convert conclusions into evidence.

If the user says "客户很需要", ask for customer quote, workflow observation, failed workaround, or commercial signal.

If the user says "提升效率", ask for baseline time, target time, and measurement method.

If the user says "做一个 agent", ask what human workflow the agent replaces or assists.

If the user says "资料很多", ask what kinds of files, who owns them, update frequency, and whether they can be uploaded or searched.

If the user says "给客户方案", ask whether it is advisory material, regulated recommendation, quote/proposal, or final sales document.

### 6. Maintain a Working Spec

Maintain a working draft internally while interviewing.

After every 3-5 user answers, summarize:

- Confirmed facts
- Still unclear
- Current risk or decision needed
- Next question

Keep summaries short enough that a business user can correct them quickly.

### 6.5 Identify Business Objects

Before asking implementation questions, identify the business objects the spec is really about.

Examples:

- A stable product library.
- A single customer case.
- A generated proposal draft.
- A reusable Domain Pack candidate.
- An audit log.

If a requirement includes both a durable asset and a generated artifact, represent both explicitly. Do not hide them inside one generic "feature" field.

For the insurance example, the durable asset is the versioned insurance product library. The generated artifact is the editable customer proposal draft. The future reusable asset is the insurance Domain Pack.

### 7. Inspect Technical Context When Needed

If the requirement mentions an existing system, repo, API, MCP tool, Memory, Friday, Agent, Recipe, Domain Pack, Workspace, document upload, CRM, policy database, or customer system, inspect the relevant local code/docs before filling technical boundaries.

For Friday Memory / memory-connector style work, use these boundary rules unless current code/docs prove otherwise:

- Memory stores, ingests, recalls, ranks, and assembles evidence.
- Memory is not the business workflow owner.
- Agent or Recipe decides when to call Memory and how to turn recalled evidence into an artifact.
- Product layer owns UI, proposal editing, workflow state, approval, packaging, and customer-facing experience.
- Customer business systems own authoritative policy, pricing, eligibility, compliance, and final sales record unless the spec explicitly includes integration.

Do not promise capabilities such as pricing, compliance approval, plan recommendation, CRM writeback, or customer-facing quote generation unless the spec includes data source, owner, validation method, and review gate.

### 7.5 Domain Pack Design Gate

If `product_context.build_target` is `domain_pack` or the user says the result should become a reusable Domain Pack, the spec must include `domain_pack_context`.

Do not enter this gate until the business feasibility gate is either `business_ready` or explicitly skipped because the user is not discussing commercial prioritization.

Before Recipe, Memory, Connector, and Workspace details, confirm the product shape:

1. Is this Pack a KA custom/private-delivery Pack, SMB self-serve Pack, hybrid Pack, internal Pack, or demo Pack?
2. Is it one L2 scene, or an L3 solution composed from several L2 scenes?
3. If L3, which L2 scenes compose the closed business loop?
4. Does the product team receive the JSON now, or should intake continue into technology detail?

Ask these questions before final JSON:

1. What industry or scene-level workflow is being packaged, and why is it reusable across customers or teams?
2. What is the Pack's private production/use boundary: individual, team, company, customer deployment, internal demo, or shared Pack after the owner chooses to publish it?
3. What Memory assets are part of the Pack?
4. What facts, customer case details, private transcripts, salaries, medical data, pricing, or one-off project context must not become reusable Memory?
5. Which runnable Recipes are in the Pack, and which one creates the first useful output?
6. Which Connectors are required, and which external systems remain authoritative?
7. What Workspace instance is created when the Pack is loaded?
8. What Rooms and Artifacts exist inside that Workspace? A Room should usually be one real task instance around one shared artifact, not a generic department room.
9. What human review updates a Recipe, Memory asset, rubric, or Pack version?
10. What self-learning signal is allowed, what only creates an update candidate, and what requires explicit approval?
11. What versioning, release, upgrade, rollback, and customer-instance policy applies?
12. What evaluation assets prove the Pack works: golden tasks, rubrics, failure cases, acceptance checklist, regression set?
13. What Workspace screens, artifacts, or controls does the user need?

The first Recipe should usually be simple and reviewable. Do not design a self-learning autonomous system by default. Prefer: generate first artifact -> human edits/reviews -> capture approved correction -> update Recipe or Memory after review.

For Domain Pack specs, make the following distinction explicit:

| Object | Owns |
| --- | --- |
| Domain Pack | private reusable workbench/package, recipe list, memory scope, connector list, UI config, permission scope, version, delivery/sharing metadata |
| Recipe | task method, rubric, execution steps, constraints, required evidence, review hints |
| Memory | durable facts, context, source-backed history, decisions, reusable domain knowledge |
| Evidence / References | original source snippets and files used for traceability, not all loaded into runtime context |
| Workspace | customer/team instance that loads a Pack, runs rooms/artifacts, captures local feedback |
| Room | one real task instance around one target artifact or conclusion |
| Artifact | draft, report, plan, decision record, feedback summary, or other reviewable output |

### 7.6 UI Wireframe Gate

If the feature has a UI, dashboard, workspace, editor, approval screen, or visual workflow, create a low-fidelity wireframe before final JSON and ask the user to confirm it.

The wireframe must include a produced `.svg` image artifact. Markdown, Mermaid, or ASCII wireframes may be used as explanatory companions, but they do not satisfy the UI wireframe requirement by themselves.

The purpose is not visual polish; the purpose is to confirm object relationships, screen flow, and user intent.

At minimum, discuss:

- Primary screens.
- Left/right panel or list/detail layout.
- Main objects shown on each screen.
- Critical actions.
- Which AI suggestions are editable, confirmable, or only informational.

Do not mark a UI-bearing spec `engineering_ready` or `review_required` if no `.svg` wireframe artifact has been produced and referenced in `ui_requirements.wireframe_artifacts`.

If you save the final JSON to disk and the spec has UI, run `scripts/validate_spec.py`; it enforces that `ui_requirements.wireframe_artifacts` includes an existing `.svg` file or an `.svg` URL.

### 8. Scope Check

Before producing final JSON, check whether the request is one spec or multiple specs.

Split the request if it contains multiple independent workflows, users, data sources, products, compliance regimes, or delivery paths.

If the request has two tightly coupled tracks, such as "maintain a product library" and "generate a customer proposal from that library", keep them in one spec only when the first release needs both to prove value. In that case, add a `spec_decomposition.recommended_followups` section so engineering can later split work cleanly.

Say:

> 这个需求现在包含多个独立交付对象，直接放进一个 spec 会让产研边界不清。我建议拆成以下 spec。

Then ask which one to complete first.

### 9. Readiness Decision

Before final output, assign one readiness label:

- `not_ready`: too vague; continue business interview.
- `business_ready`: business scenario and value are clear; product review needed.
- `product_ready`: commercial feasibility and product shape are clear enough for technology review, but technical details may still need expansion.
- `engineering_ready`: scope, workflow, acceptance, testing, and operation standards are clear.
- `review_required`: high-risk spec requiring technical committee, QA, DevOps, security, compliance, or business decision review.

Do not call a spec `engineering_ready` if the data source, workflow, acceptance standards, and operation standards are still unknown.

Do not call a spec `business_ready` if target buyer, customer pain, current alternative, evidence, deliverable, willingness-to-pay reason, delivery risk, or next sales action is missing for a commercial Domain Pack or POC.

Do not call a spec `product_ready` if product basis, spec type, user/scenario, scope boundary, business objects, UI need, and Domain Pack product shape are still unknown.

Do not call a Domain Pack spec `engineering_ready` if Memory assets, non-memory boundaries, first Recipe, iteration loop, and Workspace surface are unknown.

Do not call a UI-bearing spec `engineering_ready` if wireframes have not been shown and confirmed.

### 9.5 Finalization Gate

Before outputting final JSON, ask one explicit finalization question unless the user already asked for the final JSON:

Use the question that matches the current stage:

- Business feasibility gate:
  > 商业可行性已经能形成第一版 JSON。现在是直接交给产品，还是继续把产品形态补清楚？
- Product shape gate:
  > 产品形态已经能形成第一版 JSON。现在是交给技术，还是继续把技术规格补清楚？
- Technical spec gate:
  > 我已经能形成工程可评审 spec。现在是直接输出 JSON，还是再补一个具体字段，例如导出格式、版本规则、owner 姓名或测试样例？

If the user says to continue, ask the next missing high-value question. If the user says to output, produce the final JSON.

### 10. Final Output

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
- `intake_stage`
- `commercial_context`
- `handoff_options`
- `product_context`
- `spec_type`
- `owners`
- `business_context`
- `business_objects`
- `scope`
- `input_materials`
- `workflow`
- `domain_pack_context`
- `priority_decision`
- `ui_requirements`
- `capability_boundaries`
- `evidence_requirements`
- `data_governance`
- `acceptance_standards`
- `testing_standards`
- `operation_standards`
- `review_gates`
- `missing_fields`
- `readiness_label`

For spec v0.2 and later, also include these sections when relevant to the requirement:

- `spec_decomposition`

The final JSON should include these high-signal sections when relevant:

- `intake_stage`: whether the current output is business feasibility, product shape, or technical spec.
- `commercial_context`: KA/SMB, L2/L3, buyer, pain, evidence, deliverable, willingness to pay, POC, pricing, risk, and sales action.
- `handoff_options`: whether the user chose to hand off to product, continue product shape, hand off to technology, or continue technical spec.
- `product_context`: which company product form the work is based on.
- `domain_pack_context`: Memory, non-memory, Recipe, self-learning, and Workspace decisions for Domain Pack work.
- `priority_decision`: whether a Domain Pack candidate should be top 8, backlog, rejected, or needs more evidence.
- `ui_requirements`: whether UI exists, wireframe status, confirmed screens, and the `.svg` wireframe artifact path.
- `business_objects`: durable assets and generated artifacts.
- `spec_decomposition`: current spec choice and recommended follow-up specs.
- `capability_boundaries`: what belongs to Memory, Agent/Recipe, product UI, external systems, and human/compliance review.
- `evidence_requirements`: what must be traceable to source material.
- `data_governance`: sensitivity, versioning, retention, and audit requirements.

Use structured workflow step objects with actor, input, action, output, review requirement, and failure handling. Avoid a bare list of step strings in final JSON.

### 11. Final Self-Review

Before saving or returning the final spec, do a short self-review:

1. JSON parses as JSON.
2. All required top-level keys are present.
3. `intake_stage` and `handoff_options.selected_next_action` match the user's chosen handoff point.
4. If the current stage is business feasibility, `commercial_context` contains buyer, pain, evidence, deliverable, willingness-to-pay reason, POC path, risk, and next sales action.
5. `product_context.build_target` is explicit before product or technical handoff.
6. If Domain Pack is involved, `commercial_context` distinguishes KA/SMB/hybrid and L2/L3 before technical details.
7. If Domain Pack technical detail is involved, `domain_pack_context` covers Memory assets, non-memory boundaries, first Recipe, iteration loop, and Workspace.
8. If UI is involved, `ui_requirements.wireframe_status` is reviewed or unresolved, not silently skipped, and `ui_requirements.wireframe_artifacts` includes a produced `.svg` file.
9. `business_objects` separates durable assets from generated artifacts.
10. `workflow.steps` uses structured step objects, not only strings.
11. `capability_boundaries` separates Memory, Agent/Recipe, product UI, external systems, and human/compliance review.
12. `evidence_requirements` states what needs source traceability.
13. `data_governance` states sensitivity, permissions, versioning, retention, or audit requirements.
14. `readiness_label` matches the actual risk level.
15. Important unknowns are explicit instead of silently invented.
16. Unknown owners, export format, retention, permission model, acceptance method, product basis, Domain Pack boundaries, or UI wireframes prevent `engineering_ready`.

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
