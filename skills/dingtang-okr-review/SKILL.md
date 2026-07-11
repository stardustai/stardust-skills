---
name: dingtang-okr-review
description: Use when the user asks to export, review, audit, score, or summarize 叮当OKR/Dingdang OKR objectives, KR progress, CEO OKR review, people progress reports, Q2/Q3/Q4 OKR data, or asks to organize OKR data into Excel and evaluate KR completion with evidence.
---

# Dingtang OKR Review

Use this skill for two related workflows:

1. Export 叮当OKR data into a verified workbook.
2. Perform CEO-level OKR review at KR level using independent evidence.

This skill is for 叮当OKR (`https://dingokr.dingteam.com/...`), not DingTalk OA reports or DingTalk documents.

## Operating Boundaries

- For automated CEO OKR review runners, use a live 叮当OKR Web/API source for the `dingokr.dingteam.com` product. Do not default to Agoal just because the word OKR appears; this tenant has previously exported live OKR data from the Dingteam Web product while Agoal rule APIs returned no objective rule. Re-confirmed: even with all 10 Agoal permissions granted on the DingTalk app, `GET /v1.0/agoal/objectiveRuleLists/query` returns `success:true` with `totalCount:0` — the org uses 叮当OKR (蓝凌), not DingTalk-native Agoal, so the DingTalk Agoal API never has this data.
- Configure the service with `CEO_OKR_SOURCE_KIND=dingteam_web` and `CEO_OKR_LIVE_SOURCE_COMMAND`. The command must accept `{user_id}` and `{period_label}` placeholders and return live JSON containing `processed.objectives` and `processed.okrRows`.
- Three live-source commands are available (all return the same `processed.objectives` / `processed.okrRows`). Prefer the headless-browser source — it does NOT need an always-open Chrome tab:
  - **Preferred — headless browser + token cache** (`dingteam_okr_browser_source.py`): a dedicated, persistent browser profile (default `~/.dingteam-okr-profile`) holds the DingTalk SSO session. One-time interactive login, then the service drives a headless Chromium itself to mint/refresh the session JWT; the JWT is cached (`<profile>/token_cache.json`, mode 600) and reused until ~5 min before its `exp` (~6h), so most fetches launch no browser at all.
    - One-time (or when the DingTalk session expires): `python3 /Users/derek/.agents/skills/dingtang-okr-review/scripts/dingteam_okr_browser_source.py login` (opens a window; scan the DingTalk QR once).
    - `CEO_OKR_LIVE_SOURCE_COMMAND=/Users/derek/.agents/skills/dingtang-okr-review/scripts/dingteam_okr_browser_source.py fetch --user-id {user_id} --period-label {period_label}`
    - Requires `pip install playwright` (uses system Chrome via `channel="chrome"`). The dedicated profile is the source's OWN session store, not the user's Chrome profile; it never reads the user's Chrome cookie store and never prints the token.
  - **Alternative — direct API via open tab** (`dingteam_okr_direct_source.py`): touches an already-authorized `dingokr.dingteam.com` Chrome tab once (osascript) to read the live session header, then fetches all OKR data via direct server-side HTTP.
    `CEO_OKR_LIVE_SOURCE_COMMAND=/Users/derek/.agents/skills/dingtang-okr-review/scripts/dingteam_okr_direct_source.py --user-id {user_id} --period-label {period_label}`
  - **Fallback — page injection** (`/Users/derek/Documents/Projects/ceo-agent-service/scripts/dingteam_okr_live_source.py`): injects an extraction script that uses the page's `webpackChunkallinone` module and polls a DOM result attribute. It auto-opens a `dingokr.dingteam.com` tab if none is present (reusing the Chrome login session), and — like the other sources — also fetches the 评论/进展 comments via `findCommentListV2` and merges them into `krDetailsUpdatesAggregated`.
  - All three ultimately depend on a logged-in DingTalk session (the JWT is minted by 叮当OKR's DingTalk SSO and cannot be reproduced from stored AppKey/Secret without 叮当OKR's official OpenAPI). The headless source reduces this to a periodic background QR re-login when the session expires. On any failure they fail fast; do not fall back to stale local exports.
- Use Agoal `agoal_1.0` only when the enterprise's OKR data is confirmed to be exposed through Agoal objective APIs. Required permissions normally include `Agoal.Objective.Read`, `Agoal.ObjectiveRule.Read`, `Agoal.Period.Read`, and `Agoal.ObjectiveProgress.Read`; org-performance plan/document APIs additionally require `Agoal.OrgPerfPlan.Read` / `Agoal.OrgPerfDoc.Read`.
- For Agoal mode, use `CEO_OKR_SOURCE_KIND=agoal` and `CEO_OKR_OBJECTIVE_RULE_ID` when the enterprise has multiple Agoal rules. If the rule or period cannot be resolved unambiguously, fail fast and expose the configuration error.
- Use the user's logged-in Chrome tab only for interactive workbook export or for fields not exposed by the API. Chrome export does not require DingTalk Open Platform AppKey/AppSecret; it requires the browser user to be logged in and authorized to view the target OKR data.
- Do not inspect Chrome cookies, localStorage, browser profile files, passwords, or session stores.
- Do not print tokens, secrets, cookies, or authorization headers.
- Do not read local OKR/source files when the user asks to pull from 叮当 OKR; the source of truth is live 叮当OKR Web/API data or the authorized online page.
- For review/scoring, first export or load the OKR workbook, then use only user-authorized evidence sources: local files, `memory_recall`, and `dws` search/read commands.

## Live API Source For Review

For an automated OKR review request in this Dingteam Web tenant, collect live data in this order:

1. Run `CEO_OKR_LIVE_SOURCE_COMMAND`, substituting `{user_id}` and `{period_label}`.
2. Verify the returned JSON is live 叮当OKR data and contains `processed.objectives` and `processed.okrRows`.
3. Each KR row must include parent O, O weight/progress, KR title, KR weight/progress, and `krDetailsUpdatesAggregated`.
4. Pass the processed live JSON into the OKR review runner. If the command or API call fails, report that live OKR data is unavailable; do not silently fall back to old local exports.

The preferred `dingteam_okr_direct_source.py` calls these private 叮当OKR endpoints (base `https://dingokr.dingteam.com`, all `POST`, reusing the captured session headers — `Authorization`, `X-Dingteam-Auth-App-Id`, `X-Space-Id`, etc.):

| Step | Endpoint | Body |
| --- | --- | --- |
| period list | `/data/okr/person/period/list` | `{"userId"}` |
| objectives + KR cells | `/data/okr/objective/showListView/v2` | `{"mainId","type":0,"search":{"userIds","pageNo","pageSize"}}` |
| KR detail | `/data/okr/objective/findKrDetail` | `{"objId","krId"}` |
| KR progress history | `/data/okr/objective/log/progressHistory` | `{"objectiveId","krId"}` |
| 评论/进展 comments | `/data/okr/objective/findCommentList/v2` | `{"objectiveId","pageNo","pageSize","sort":false,"logTypeCells":[],"krId":"","commentId":""}` |

CRITICAL for scoring: the numeric KR progress is often 0 even when there is real progress, because people write their progress as **comments/进展 (评论)** rather than moving the % slider. `findCommentList/v2` returns those records (`type==5` = 评论; each item has `richTextContent`, `creator`, `createAt`, and `krInfo.krId`/`krInfo.name` to map to a KR). The source fetches them per objective, maps each to its KR (by `krInfo.krId`, then by matching `krInfo.name` to the KR title), and merges them into `krDetailsUpdatesAggregated` (KR-level) and `objectiveCommentsAggregated` (objective-level). Do NOT score from the numeric progress alone — use these comment records as the primary progress evidence.

It matches the requested period via the same normalization as the page (`2026 Q2` / `2026年2季度` / `2026年二季度` → `2026q2`), aggregates each KR's progress history into `krDetailsUpdatesAggregated` (`时间 | 进度变化 | 说明`, or `[未撰写进度]` when empty), and never prints the auth token. Unit tests live next to it: `scripts/test_dingteam_okr_direct_source.py`.

For confirmed Agoal tenants, collect live data in this order:

1. Resolve the Agoal objective rule.
   - Prefer configured `CEO_OKR_OBJECTIVE_RULE_ID`.
   - Otherwise query `GET /v1.0/agoal/objectiveRuleLists/query`; if exactly one rule is not available, stop and ask for the rule id.
2. Resolve the period by querying `GET /v1.0/agoal/objectiveRules/periodLists?objectiveRuleId=...` and matching the requested period, for example `2026 Q2` to `2026年二季度` / `2026年2季度`.
3. Query the user's objectives with `POST /v1.0/agoal/users/objectiveLists/query` using `dingUserId`, `objectiveRuleId`, and `periodIds`.
4. For each objective, query detail with `GET /v1.0/agoal/objectives/details?objectiveId=...`.
5. For each objective, query progress history with `GET /v1.0/agoal/objectives/progresses/lists?objectiveId=...`.
6. Before invoking the OKR review runner, the worker must merge objective detail and progress data into a processed O/KR hierarchy: `processed.objectives` and `processed.okrRows`. Each KR row must include parent O, O weight/progress, KR title, KR weight/progress, and `krDetailsUpdatesAggregated`.
7. Pass the processed live JSON into the OKR review runner. If any API call fails, report that live OKR data is unavailable; do not silently fall back to old local exports.

## Export Output

Create one workbook under:

```text
outputs/dingteam-okr-<period-slug>/dingteam_okr_<period-slug>.xlsx
```

Use these sheets:

- `Summary`: period, generation time, people count, cockpit target count, by-person objective total, average progress, task metrics.
- `People Overview`: one row per person with department, objective count, confirming/aligned/unaligned counts, Q2 progress, profile user id, profile URL.
- `Data Quality`: mismatches and no-detail profiles.
- One tab per person, named with a stable numeric prefix, for example `01_ET`, `22_Roy Han`.

Each person tab must use a hierarchical row structure:

| Level | O | O Progress | O Weight | KR | KR Progress | KR Weight | KR Details Updates (Aggregated) | Text |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| O | O1: Objective title | 50% | 100% | | | | | raw objective text |
| KR | O1: Objective title | 50% | 100% | KR1: KR content | 40% | 30% | aggregated update history | KR content |

Rules:

- O and KR are separate columns.
- O rows contain O details and leave KR blank.
- KR rows repeat the parent O in the O column so later AI review has local context.
- O Weight and KR Weight are both mandatory columns.
- `KR Details Updates (Aggregated)` should contain aggregated KR-detail update history when the raw capture has it.
- If the `所有记录` capture ran successfully but a KR has no matching progress/comment record, write `[未撰写进度]`.
- Use `未采集` only when KR detail/update capture was not run or failed, not when the person simply did not write KR progress.

Always keep the raw JSON capture next to the workbook for audit:

```text
outputs/dingteam-okr-<period-slug>/dingteam_okr_<period-slug>_raw.json
```

## Export Workflow

1. Confirm the target period and source page.
   - Example: `2026年2季度` with range `2026/03/31-2026/06/30`.
   - Open or claim the 叮当OKR Chrome tab.
   - Navigate to `#/report` and select the target period if needed.

2. Check whether `dws` has native OKR support or use the OpenAPI source:

```bash
dws --help
dws okr --help
```

If OKR is not listed as a service and the task is automated review, use the configured live source command. Use Agoal only after confirming the tenant's OKR data is exposed through Agoal APIs. If the task is interactive workbook export, continue with Chrome.

3. In the 叮当OKR report page:
   - Use `推行驾驶舱`.
   - Confirm the page shows `制定对齐详情`.
   - Switch pagination to `100 条/页` to avoid duplicate or missing rows at page boundaries.
   - Extract the visible people table: name, department, objective count, confirming count, aligned count, unaligned count.

4. For every person row:
   - Use a real row click, not `data-row-key`, because `data-row-key` changes across refreshes and is not the stable profile user id.
   - Wait for `#/okr/profile?profileUserId=...`.
   - Extract `document.body.innerText`.
   - Store `profileUserId`, `profileUrl`, `profileText`, and metadata.
   - For each visible objective in the target period, open the objective detail drawer and extract the `所有记录` list.
   - Map records whose reference starts with or contains `评论KR` to the matching `objectiveCode` + `krCode`; save those as `krUpdates`.
   - Also map progress-change rows to KR details when the record `ref` exactly or unambiguously matches a KR title from the same objective. These rows usually contain `状态`, `进度`, and `说明`, and are the main source for "why this progress" leads.
   - Keep objective-level replies, new-objective/new-KR events, or ambiguous records separately as unscoped records; do not attach them to a KR unless the record has a clear `评论KR` reference or an unambiguous KR-title match.
   - Return to `#/report`, ensure `100 条/页`, and continue.

5. Build the workbook with the bundled script:

```bash
node /Users/derek/.agents/skills/dingtang-okr-review/scripts/build_workbook.mjs \
  --input /absolute/path/to/dingteam_okr_2026q2_raw.json \
  --output-dir /absolute/path/to/outputs/dingteam-okr-2026q2 \
  --period-label 2026年2季度 \
  --period-slug 2026q2
```

6. Verify the `.xlsx` before reporting completion.
   - Import the workbook using `@oai/artifact-tool` when available, or `openpyxl` as a fallback.
   - Check that `People Overview` has one header row plus all people.
   - Check that the total `Level = O` rows across person tabs equals the sum of by-person objective counts, excluding explicit no-detail zero-OKR rows.
   - Check that person tabs exist for every person row.
   - Scan for `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A`.

## CEO OKR Review Workflow

Use this when the user asks to review, audit, or score a person's OKR.

### 1. Inputs

Start from the exported workbook or freshly exported OKR data. For each KR, collect:

- parent objective
- KR wording
- KR weight
- self-reported KR progress
- `KR Details Updates (Aggregated)`
- expected deadline or timing requirement from the KR text, OKR notes, or review context

If a KR has no clear deadline, mark `deadline=未明确` and do not apply the time discount.

### 2. Evidence Sources

Use independent evidence where accessible. KR self-progress and KR progress notes are leads, not proof, with one important exception: if the required evidence lives in an internal system the reviewer cannot independently access, such as CRM, 小青, a business cockpit, or another backend report, and the KR progress text gives a clear numeric result or calculation, accept that number as the working fact for scoring. Record the verification gap, source-system gap, or audit evidence needed, but do not discount the score solely because the reviewer cannot independently verify the backend number.

Allowed evidence sources:

- Local files explicitly relevant to the KR, such as project docs, delivery notes, proposals, reports, spreadsheets, code/repo artifacts, or meeting exports.
- Cloud memory through `memory_recall`, especially prior decisions, project status, customer context, delivery facts, and reusable business knowledge.
- `dws` search/read commands, selected by evidence type:
  - `dws doc` / `dws wiki` for DingTalk documents and knowledge-base material.
  - `dws minutes` for AI 听记 transcript/summary/todo/speaker evidence.
  - `dws aisearch` / `dws contact` for people, org, owner, and responsibility verification.
  - `dws report`, `dws todo`, `dws chat`, `dws calendar`, or other relevant products when the KR evidence lives there.

Do not use unsupported inference as evidence. If a claim cannot be verified, mark it as `证据不足`.

### 2.5 Subagent Scoring Mode

Use this mode when the main agent delegates initial OKR scoring to subagents.

Rules:

- Subagents are read-only reviewers. They must not edit the workbook, skill files, raw exports, or evidence files. The main agent is the only writer for the final Excel artifact.
- Subagents must read this `dingtang-okr-review` skill before scoring and explicitly state that they applied the current scoring rules.
- In early calibration, score one bounded subgroup at a time. The main agent must audit each subgroup before expanding to the next subgroup.
- Subagents must return candidate scoring only, with one row per KR:
  `姓名 | 部门 | KR | 权重 | 系统KR进度摘要 | 独立检索证据内容 | 证据评价 | 候选评分 | 置信度 | 需主审判断的问题`.
- `证据评价` must be point-by-point when the KR has numbered sub-items. Do not collapse multiple requirements into one generic comment.
- Scores `>80` require strong independent evidence or a concrete inaccessible-system metric in the system KR progress. If the evidence is mostly narrative, documents, meetings, demos, or process traces, keep the score conservative and explain the missing effect evidence.
- Product KR scores `>60` require actual effect evidence, such as launch, acceptance, reuse, customer/user validation, usage data, trial or PoC conversion, PMF/GTM signal, R&D/test acceptance, or measurable quality/efficiency improvement.
- Internal demos, mock data, local-only prototypes, shadow mode, personal tools, or meeting progress do not equal user/customer validation, PMF, production adoption, or team-wide reuse. If these are the strongest evidence for a KR that promised PMF, customer buy-in, production use, self-service, team use, or success cases, keep the score low-to-mid unless stronger effect evidence is found.
- If the original KR target was replaced by another direction or a smaller scope, do not treat the replacement as equivalent unless the KR progress or an owner decision explicitly confirms the changed target and comparable value. Score the delivered residual value and clearly state the original-result gap.
- If a KR requires multiple concrete outputs, such as three full proposals, two real recipes, a published dataset count, or a complete standard package, score against the missing outputs directly. Do not give a high score because the partially completed outputs are high-quality.
- Zero-weight culture, leadership, or value KRs should be reviewed separately when useful, but they do not enter the candidate weighted total unless the workbook or user explicitly says they should.
- For documentable-output claims, the subagent must say whether the artifact was found and read. If the artifact was not found or could not be read, treat it as missing for scoring. If it was found but effect is unproven, discount for missing landing value.
- For inaccessible backend metrics, if the KR progress gives a concrete number, numerator/denominator, or calculation, subagents should score from that number and record the audit gap instead of discounting only for lack of access.
- Do not use grade-like shorthand labels. Describe the business gap directly, for example: "原承诺是产品内嵌闭环，实际只落到临时表单".
- Subagents should flag uncertain or high-impact judgments instead of over-resolving them. The main agent decides final scores, wording, and workbook writeback.

### 3. Scoring Rules

Score at KR level. Do not score only at O level.

Recommended scale:

- `100`: KR target fully met with independent evidence.
- `80`: mostly met; minor gaps remain.
- `60`: partially met; core outcome is incomplete or weakly evidenced.
- `40`: limited progress; important outcome missing.
- `20`: minimal evidence of progress.
- `0`: no evidence, contradicted evidence, or not attempted.

The base score should be based on independently verified evidence when that evidence is accessible. If the relevant source system is not accessible to the reviewer but the system KR progress gives a concrete metric, numerator/denominator, or calculation result, score from that stated result and note the audit gap. Only discount for missing evidence when the required number/result is not stated, is vague, contradicts other evidence, or does not match the KR's required metric.

Effect/value scoring rule:

- First identify the KR's original expected effect from the wording: product behavior, launch state, customer/business value, adoption, efficiency, quality, revenue, risk reduction, or measurable metric. Score primarily by how much real effect and value were achieved, not by how many actions were taken.
- Check both the user's provided progress evidence and independently searchable evidence from local files, `memory_recall`, and relevant `dws` sources. Self-progress is a lead, not enough proof by itself.
- Read the full system KR progress text carefully before scoring. Do not give a score from the KR title alone or from a one-sentence summary. The review must say whether the system progress proves the promised result, only describes actions, shows execution downgrade from the original commitment, or leaves a gap.
- For product KRs, product evidence is primarily effect evidence, not document existence. Product architecture docs, PRDs, roadmaps, positioning materials, PMM briefs, demos, or meeting traces can prove that thinking and preparation happened, but they do not by themselves prove product success. If a product KR lacks evidence of launch, user/customer validation, sales/presales reuse, R&D/test acceptance, real workflow adoption, usage data, trial/PoC conversion, PMF/GTM signal, or measurable quality/efficiency improvement, keep the score in the `40-60` range even when document traces exist. Scores above `60` require a clear effect argument tied to the KR's promised result.
- For PMF, customer buy-in, technical PoC success, self-service, or team-use KRs, internal demo readiness is weak evidence. Mock demos, local demos, investor-demo preparation, shadow-mode tools, or meeting agreement usually justify only limited partial credit unless there is evidence of real user/customer use, accepted trial/PoC, team adoption, or measurable business effect.
- For Use Case KRs, distinguish "a scenario was discussed or demoed" from "a complete use case proposal was delivered and adopted". If the KR requires complete proposals, buyer chain, real workflow/data, and product adoption, missing adoption or incomplete proposal count should materially cap the score.
- For product mechanism KRs, such as VOC/P0 priority rules, product positioning, cross-department product口径, training mechanisms, sharing mechanisms, or product-side operating systems, do not score high from the mechanism being announced or used once. If the KR includes an effect metric, such as low-quality demand ratio下降、拦截率、复用率、优先级命中率、覆盖率、使用频次, the metric result is the main score anchor. When the mechanism exists but the promised effect metric is missing, normally cap the score around `55` unless another hard effect proof exists.
- For product launch or上线 claims, "已上线" in self-progress is not enough when the KR promised product value. Look for a release link/version, acceptance record, usage log, customer/internal user adoption, sales/presales reuse, or issue-closure evidence. If the only proof is a demo, meeting statement, local build, financing package, or "waiting for R&D/platform version", score it as preparation or partial delivery rather than launched product.
- For product organization capability KRs, such as "two people can independently design and promote new products", named examples and meeting participation are only leads. Scores above `60` require project-level evidence: named owner, PRD/design artifacts, decision ownership, limited manager intervention, launch or acceptance result, and downstream use. Without those, treat it as capability-building progress, not proven independent ownership.
- For activity-style product KRs, such as weekly sharing, product training, or knowledge-base operation, first decide whether the promised output is only the activity or includes value/effect. If the KR says "valuable", "拦截率", "统一使用", or "推动决策", require materials plus attendance/coverage and downstream reuse or decision impact; otherwise keep scores conservative.
- For engineering and technical KRs, score against the original technical result before asking for external business effect. Architecture design, component extraction, SDK encapsulation, technical debt count, demo-level implementation, test cases, deployment scripts, AI Jam sessions, and internal engineering tools can be valid KR outcomes when the KR wording promises those technical outputs. Good evidence includes readable architecture/design docs, code paths, merged PRs, package/API docs, test reports, demo links or recordings, release notes, issue/debt lists, meeting acceptance, or internal user records. Do not require customer validation, sales reuse, or PMF evidence unless the KR explicitly promises customer/product/business adoption.
- For engineering KRs that promise internal adoption, self-service, productivity uplift, stability, ROI, cycle-time reduction, or team capacity improvement, technical completion alone is insufficient. Require usage logs, acceptance records, before/after metrics, incident/bug data, cycle-time data, Story Points, self-service success rate, or another metric tied to the promised effect.
- For demo-level engineering KRs, grade against the promised demo standard. If the KR says "60分demo" or an internal demo milestone, a working internal demo, integration evidence, and a limited bug/risk list can justify a mid-to-high partial score. Missing customer adoption should not be a major deduction unless the KR promised external use; missing demo link, recording, acceptance, or core-flow stability should still discount.
- For technical debt count KRs, if the KR is explicitly count-based, such as "处理数量大于5项", score the count when the issue/debt list or clear progress text proves it. Treat quality metrics such as alert reduction, defect rate, or reuse rate as improvement suggestions unless the KR itself requires those metrics.
- Do not convert explicit partial progress into `0` solely because the final target was missed or resources changed. If the system progress, artifacts, or meeting evidence show relevant partial work, give low partial credit according to value delivered. Reserve `0` for no attempt, no relevant output, contradicted evidence, or when the available work creates no value for the KR.
- For inaccessible backend metrics, such as CRM win rate, 小青 recruitment conversion, cockpit ROI, usage counters, or similar operational systems, do not require a second independent source if the KR progress includes a clear number. Example: if the KR asks for CRM-confirmed PoC win rate above 50% and the progress says "win:participated = 9:11", score the metric as achieved; the gap is "need CRM/Shawn screenshot for audit", not a score deduction. If the KR needs a number and the progress does not state it, then apply a discount.
- Documentable-output claims have a higher verification bar across all KR types. If a KR says it produced a document, plan, policy, SOP, process, report, dashboard, analysis, proposal, pitch, demo, PRD, roadmap, user journey, evaluation case, standard offer, training material, hiring rubric, financial control, SLA, automation, system feature, or other inspectable artifact, the reviewer must search for and read the corresponding document or artifact. Treat the output as nonexistent for scoring if the artifact cannot be found or read. If the artifact exists, still check meeting minutes, usage records, acceptance records, business records, or operating metrics for downstream value, such as adoption, reuse, customer/investor/internal stakeholder use, launch, training completion, risk reduction, efficiency gain, revenue impact, or owner acceptance; otherwise discount for "artifact exists but landing value unproven".
- If the KR contains multiple numbered sub-items, such as `1、... 2、... 3、...`, evaluate point by point. The review must explicitly comment on each numbered point before giving the overall score. Do not collapse a multi-point KR into one generic sentence.
- If the delivered result is a downgraded execution of the original commitment, score with a discount instead of forcing `0`. The discount should reflect value loss: for example, a productized embedded workflow downgraded to a manual form may receive low partial credit if it produced usable feedback, but should be much lower than the original target. Do not write grade-like labels in the review text; describe the business gap directly.
- If the team delivered a different substitute that does not solve the original problem or create comparable value, keep the score very low. Use `0` only for no attempt, no evidence, contradicted evidence, or work that creates no relevant value.
- For metric KRs such as NPS, usage frequency, adoption rate, self-service success rate, ROI improvement, cycle-time reduction, or quality improvement, score by actual measurement and impact. If the metric was not launched but a downgraded proxy exists, explicitly describe the downgrade and apply a discount.
- Activity KRs, such as workshops or published documents, can score when the activity itself was the promised output. Do not infer extra business value unless there is evidence of adoption or effect.
- When the evidence-based score differs materially from the person's self-progress, explain the gap and state what evidence would close it. Typical gap items are missing user adoption, missing customer validation, missing system data, missed deadline, downgraded execution, weak business value, or missing independent proof.

Example: if a KR promised "embed NPS and usage feedback into the product, collect NPS, and use it for product iteration", but the product NPS was not launched and only a temporary form or group feedback was used, do not give full credit. Score based on whether the downgraded proxy produced useful feedback and iteration decisions; if it did not create measurable product or business value, the score should be very low, and the review should say how to supplement the gap.

### 4. Time Discount

Compare actual completion time with the KR required time.

- If the KR was completed after the required time, apply a 50% discount to the evidence-based base score.
- Formula: `final_score = base_score * 0.5`.
- If only part of the KR was completed late, apply the discount to the late portion when the evidence allows separation; otherwise apply it to the whole KR and explain why.
- If the KR is still incomplete after the deadline, score the actual completed evidence first, then apply the same 50% late discount to the completed portion if it arrived late.
- If no required time can be established, do not apply a time discount; mark `time_discount=未适用`.

Examples:

- Base score `80`, completed after deadline -> final score `40`.
- Base score `60`, no clear deadline -> final score `60`.
- Base score `0`, no evidence -> final score `0`.

### 5. CEO Review Lens

For each KR, evaluate:

- whether the KR's measurable target was actually achieved
- whether the output was delivered by the required time
- whether the result created business, customer, delivery, product, team, or operational value
- whether the evidence shows durable completion rather than a demo, draft, or intent
- whether the work is reusable, adopted, shipped, paid, accepted, or otherwise externally validated when the KR implies those outcomes

### 6. Output Format

Create a review artifact as Markdown and/or Excel. Use one row per KR.

Required simplified columns for management-facing Excel:

| KR | 权重 | 系统KR进度 | 独立检索证据内容 | 证据评价 | 评分 | 提升建议 |
| --- | --- | --- | --- | --- | --- | --- |

`证据评价` should include the score rationale, gaps, deadline or DDL issues, execution downgrade from the original commitment, and why the score differs from self-progress when the gap is material. Use plain business language such as "原承诺是产品内嵌闭环，实际只落到临时表单" instead of grade-like labels.
If the KR has numbered sub-items, `证据评价` must use the same numbering and comment on each sub-item, for example `1）... 2）... 3）... 总体：...`.

Rules:

- Management-facing review tables should use Chinese headers. Avoid English headers and avoid excessive columns.
- `独立检索证据内容` should summarize the evidence content, not paste file paths or raw source URLs. Keep source provenance in raw capture files or internal audit notes if needed, but do not clutter the management sheet.
- Do not add a separate evidence-list sheet or evidence index unless the user explicitly asks for audit inventory.
- `证据评价` must say what is missing, not just "insufficient".
- `提升建议` should name the specific proof, delivery, owner, or next decision needed.
- If evidence is weak, say so and keep the score conservative.

## Chrome Collection Notes

Use the Chrome plugin/browser client when available. Keep updates concise while collecting many profiles.

Important details from the working run:

- `#/report` showed the period and cockpit metrics.
- `100 条/页` gave the stable full people table.
- The `data-row-key` changed across refreshes, so do not use it as `profileUserId`.
- Some zero-objective users may not have details. Record them as `暂无数据`, not as extraction failures.
- The cockpit top-level target count can differ from the by-person table total; keep that in `Data Quality`.

## Reporting Back

For export tasks, include:

- short summary of rows collected and workbook sheets
- data-quality caveats, especially count mismatches or no-detail users
- standalone Markdown link to the final `.xlsx`

For CEO review tasks, include:

- final review artifact path
- number of KRs reviewed
- number of KRs with sufficient independent evidence
- number of KRs discounted for missed timing
- strongest evidence gaps requiring Derek's judgment

Do not paste raw OKR content into chat unless the user explicitly asks.
