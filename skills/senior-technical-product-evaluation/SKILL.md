---
name: senior-technical-product-evaluation
description: Evaluate senior technical candidates by researching the products they worked on and separating product technical complexity and leadership, the candidate's inferred responsibility and technical depth, and target-role fit. Use whenever screening resumes or assessing CTOs, technical directors, principal engineers, architects, AI leaders, or other senior technical candidates, especially when the resume lists impressive companies, large systems, AI platforms, Agent frameworks, 0-to-1 products, or claims of leading/core ownership. Requires internet cross-checking, responsibility-boundary inference, and explicit technical-taste assessment rather than accepting resume or company marketing claims at face value.
---

# Senior Technical Product Evaluation

Use this skill to answer a narrow but important question: does a senior technical candidate's product history demonstrate the kind of technical and product judgment required by the target role?

Do not collapse this into one vague "product experience" score. Evaluate three separate objects:

1. The product: was it technically complex, leading, and innovative for its market and time, or merely a common implementation of a popular topic?
2. The candidate: which parts did this person most likely own, and did they solve the hard parts or merely participate around them?
3. The transfer: does that experience map to the target role's product, stage, constraints, and technical paradigm?
4. The recent function: what did the candidate actually spend the last three years doing, and is that work function the same as the target role rather than merely adjacent to it?

Read [references/methodology.md](references/methodology.md) before evaluating a candidate. Follow its research protocol, score caps, gates, and output format.

## Required inputs

Collect these before scoring:

- Target role mission, level, product stage, customers, technical priorities, and near-term problems.
- Current internal product definitions for every product line the role may serve. For Stardust/PreSeen, evaluate Friday and MorningStar separately unless the role is explicitly scoped to only one.
- Candidate employment dates and exact product or project claims.
- The actual function of the candidate's current and recent roles, including whether they owned core product R&D, infrastructure/SRE, DevOps, quality, delivery, project management, or another responsibility center.
- Candidate's stated role, decisions, implementation, metrics, failures, and results.
- Public information about each relevant product during the candidate's tenure.
- A product fact card for every material candidate product: plain-language description, buyer and user, end-to-end workflow, product boundary, major modules, business model when knowable, hard technical problems, and dated source excerpts.

If the target role or product is unclear, state the working assumptions. Do not silently judge against a generic "senior engineer" profile.

## Internet research is mandatory

Research every product that materially affects the decision. A resume, interview summary, company name, or internal table is only a lead.

For each product:

1. Resolve the exact entity using company, product name, dates, geography, and product category. Do not attach evidence from a similarly named project without identity proof.
2. Search primary sources first: official product documentation, repositories, papers, patents, regulatory filings, annual reports, technical talks, release notes, and customer case studies with named outcomes.
3. Add an independent source when available: recognized benchmarks, customer evidence, reputable industry analysis, or credible technical reporting.
4. Compare the product with alternatives available during the candidate's tenure. Current popularity does not prove historical leadership, and an old architecture is not weak merely because newer technology now exists.
5. Search for limitations, failed launches, weak adoption, security incidents, discontinued products, and contradictory metrics. Marketing claims are not independent verification.
6. Record source URL, publication date, source type, supported claim, and whether the evidence aligns with the candidate's dates.

Do not start from a score or from a list of technical nouns. First explain the product so that a reviewer unfamiliar with it can understand what is bought, what users actually do, and where the candidate's claimed system sits. Resolve whether the input names a single product, a product family, one platform layer, an internal project, or an entire company product stack. If several layers are merged into one resume row, split them before comparison. If the exact product cannot be resolved, mark it E0/Unknown instead of inventing a product description.

Use at least two materially different sources, including one primary source, for a high-confidence product-leading claim. When only company marketing or candidate wording is available, mark the claim unverified and apply the evidence cap.

## Evaluation sequence

1. Build the target-role capability map and a separate capability map for each relevant internal product line.
2. Resolve the boundary of each candidate product and create its product fact card before assigning any score.
3. Quote the relevant internal product-definition excerpts and the candidate's original resume/project text before interpreting either one. Preserve source links, document dates, and wording; label any cleanup such as removed HTML styling.
4. Turn each resume item into explicit claims.
5. Research and time-align the product evidence. Keep a source log showing what each source proves and cannot prove.
6. Infer the candidate's likely responsibility boundary from resume verbs, technical specificity, scope, tenure, and organizational plausibility. Label each inferred part with confidence and explicitly list company capabilities that must not be attributed to the candidate.
7. Separate product facts from candidate attribution. Public evidence that a company had a capability does not prove the candidate designed or built it.
8. Score product technical complexity and leadership independently of the candidate. Put most weight on technical complexity, technical leadership, innovation, and technical taste; give problem importance and generic product differentiation little weight.
9. Score candidate technical depth only on the inferred responsibility boundary. Examine claim authenticity, implementation complexity, hard problems, technical decisions, failures and iteration, and development duration.
10. Research and score the candidate's technical-team environment. Verify financing stage, investors, business type, product identity, technical leadership, R&D/product evidence, and whether the company is product-led or project/outsourcing-led. Do not infer team quality from a company name alone.
11. Score product-line fit for each relevant target product using exactly: hard-problem similarity 25%, technical-architecture similarity 25%, data/evaluation-loop similarity 20%, customer/deployment similarity 15%, and responsibility/stage similarity 15%. Do not average unrelated product lines merely to produce one number.
12. Score recent-role functional fit separately. Product-line fit asks whether the former product's mechanisms transfer; recent-role functional fit asks what the person actually did recently. Do not let work at a relevant company or on a relevant product substitute for core-function ownership.
13. Apply evidence caps and senior-level gates when not in resume-only mode.
14. Show every required subdimension, weight, weighted contribution, and evidence basis; do not expose only a top-level score.
15. Recalculate every weighted score independently and verify the displayed arithmetic.
16. Confirm that the final report retains any contrary evidence that could change product identity, system boundaries, candidate ownership, team environment, recent function, or time alignment.
17. Produce screening questions that target the largest unresolved claims.

When a candidate highlights a highly repetitive technical topic such as a generic Agent harness, RAG wrapper, workflow builder, or chatbot, do not award technical-currency points for vocabulary alone. If neither public evidence nor the candidate's own description identifies an original problem, mechanism, comparison baseline, failure, or result, treat the project as evidence of weak technical selection and technical taste, not merely missing evidence.

Treat each input row as one candidate by default. Never merge adjacent rows merely because companies, career stages, or technical topics appear related. Merge multiple rows into one career portfolio only when the source provides a stable candidate ID, candidate name, explicit resume boundary, or an equally direct identity link. If identity linkage is absent, score and report every row independently.

For a confirmed multi-product career portfolio, first list every input row and preserve coverage. Then choose at most three representative product clusters using technical substance, plausible candidate ownership, recency when known, and relevance to the target products. Calculate each representative product's technology score, then derive the portfolio product-technology score with fixed weights `50%/30%/20%`; with two representatives use `60%/40%`, and with one use `100%`. Explain the selection and do not silently average every old or irrelevant project. Candidate technical depth and product-line fit may use evidence across the full portfolio, but every positive signal must cite a specific inferred-owned component.

## Senior-level decision rule

For a senior technical hire, impressive context is not enough. The candidate must demonstrate both hard technical ownership and relevant transferability.

- A leading product with shallow personal contribution indicates a passenger, not a senior owner.
- Deep work on a mature or non-leading product may still show strong engineering, but does not prove product-forward judgment.
- A highly similar product without metrics, decisions, failures, or public verification is only apparent fit.
- Large team size proves organizational scope, not technical depth or product quality.
- AI vocabulary proves neither current technical understanding nor AI-native product judgment.

Separate two decisions that use the same evidence but have different burdens of proof:

- **Resume-screen decision:** Is the claim specific, difficult, relevant, and valuable enough to justify a targeted interview?
- **Senior-hiring decision:** Has the candidate's ownership and ability been verified strongly enough to support level and hiring risk?

The raw signal score supports the first decision. The evidence-capped confirmed score supports the second. Resume-only evidence can justify a targeted interview when the underlying claim is strong; it cannot by itself validate a senior hire.

### Resume-only screening mode

When the recruiting workflow explicitly states that only the resume will ever be available at this stage, use **resume-only screening mode**:

- Produce one primary `简历评估分`; do not evidence-cap it into a lower `确认分`, and do not use E0-E4 as a numerical multiplier or ceiling.
- Internet research is still required to understand the former product, its real workflow, technical complexity, contemporaneous baseline, and technical leadership. It does not verify the candidate's personal contribution.
- Evaluate personal ownership only from resume wording, specificity, plausible scope, technical mechanisms, metrics, decisions, failures, iteration, and duration. Missing evidence lowers the relevant depth subdimensions directly; do not penalize the same absence again through a separate confirmation cap.
- Keep uncertainty as non-numeric flags such as `产品实体未解析`, `任期缺失`, `个人边界模糊`, `指标不可复算`, or `疑似公司能力归因`, rather than compressing the final score.
- Use the fixed final formula `产品技术 25% + 个人技术深入度 30% + 产品线匹配度 25% + 最近岗位职能匹配度 20%` and show the stronger of Friday and MorningStar as the primary resume score while retaining both product-line scores.
- When technical-team environment is part of the requested screen, use `产品技术 20% + 个人技术深入度 25% + 产品线匹配度 20% + 最近岗位职能匹配度 20% + 技术团队环境 15%`. Show the team score, category, sources, and adjustment reasons. Do not additionally use the former formula as the decision score.
- For cohort screening, show rank and percentile in addition to the absolute score. Do not stretch or normalize the absolute score merely to create visual separation.
- Default decision bands: `>=75 强推荐进入面试`, `70-74.9 推荐进入面试`, `65-69.9 弱推荐/优先验证`, `60-64.9 针对性验证`, `<60 淘汰`. A material red flag may lower the decision, but the reason must be explicit.

Do not recommend a candidate as proven senior-level product/technology leadership when confirmed technical depth, product-line fit, or recent-role functional fit is below 60, or when candidate-contribution evidence is only resume-level and the critical claim has not been pressure-tested.

## Output

Use the exact structure in the methodology reference. Produce one consolidated report, not separate summary, evidence, scoring, and product-description files. Keep original input, internet-enhanced facts, responsibility inference, public evidence, and conclusions visibly separate inside that file. Every score needs a reason and an evidence grade. For each top-level dimension, include a subdimension breakdown table with `子项 / 权重 / 原始分 / 加权贡献 / 打分依据`; then explain separately why the evidence grade raises or lowers the current confirmed score. A top-level score without this breakdown is incomplete.

For Stardust/PreSeen reports, include a Friday/MorningStar product-line fit matrix showing raw similarity, evidence-capped confirmed similarity, matching mechanisms, and critical gaps. State which product line is the stronger match. Also include a recent-role functional-fit table that distinguishes core product R&D from SRE/DevOps, infrastructure, quality, delivery, and management functions.

Include a technical-team environment fact card when requested. Use this preference order, verified through internet research:

1. Product-led technical team with disclosed Series A-C financing.
2. Excellent B2B product team inside a top-tier technology company.
3. Product-led B2C technology company.
4. Technology subsidiary or product technology team inside a large enterprise.
5. No clear product, project/outsourcing-led B2B company, state-owned or central enterprise, or public institution.

Financing news alone is insufficient: verify the round, date, investors, product, and technical-team signals. State-owned status does not erase a concrete leading product team, but absent contrary product/technical evidence it belongs in the lowest band.

If a standalone B2B company has a clear product but neither disclosed Series A-C financing nor evidence that it is a top-tier technology company, do not create an extra high-scoring category for it. Evaluate it conservatively alongside the fourth band and cap the team score at 69. A real standardized product, core-team position, sustained R&D, and strong engineering output can move it toward the top of that band; project revenue, implementation-heavy delivery, unstable operations, or unclear ownership move it toward the lowest band.

The report must be auditable by a human reviewer. Include enough original product and candidate text to evaluate whether the interpretation is faithful, plus a research ledger with `source / fact / supports / does not support`. If the reviewer cannot trace a score back to original text and a named evidence item, the report is incomplete. Add a short feedback table for disputed assumptions and judgment calls.

Put the product fact card before the scores. It must make sense to a reviewer who has never heard of the product. A report that says only “enterprise email”, “AIGC platform”, “Agent Runtime”, or another category label without explaining the actual product and workflow is incomplete.

Always calculate a final score. Product-line fit contributes 25% without a team-environment dimension and 20% when team environment is included; recent-role functional fit contributes 20% in both cases. Base both on the candidate's inferred responsibility boundary, not whole-company keyword similarity. Use the fixed product-line-fit weights `25/25/20/15/15`; do not substitute the former generic fit weights `30/20/20/15/15`. If the role's product line is unresolved, calculate separate Friday and MorningStar final scores, identify the higher as the best-fit product-line score, and still show both. In normal evidence-rich mode, report both the raw resume-signal final score and the evidence-capped confirmed final score. In resume-only screening mode, report one primary resume score plus non-numeric uncertainty flags; do not use the confirmed score for ranking or decisions.

Write the report in the user's language. For Stardust/PreSeen recruiting tasks or Chinese prompts, default to Chinese; keep product names, technical terms, and source titles in their original language when translation would reduce precision.
