# Methodology: Product Leadership, Technical Depth, and Role Fit

## 1. First define the target

Translate the target role into a capability map before reading product prestige into the resume:

| Target dimension | Questions |
|---|---|
| Mission | What business and customer outcome must this person own? |
| Product stage | Research, 0-to-1, product-market fit, scale-up, platformization, turnaround, or efficiency? |
| Technical paradigm | AI-native agents, model/data systems, SaaS, distributed systems, security, hardware, or another core paradigm? |
| Constraints | Privacy, latency, accuracy, cost, safety, multi-tenancy, private deployment, compliance, or global delivery? |
| Ownership | Hands-on architect, technical product owner, engineering manager, organization builder, or executive? |
| Time horizon | What must be delivered in 90 days and in 12 months? |

Match is relational. The same product experience can be highly relevant to one role and weak for another.

## 2. Convert the resume into claims

Separate each resume item into five claim types:

1. Product claim: what the product did and for whom.
2. Leadership claim: why it was differentiated or leading.
3. Scale claim: users, traffic, revenue, reliability, cost, or adoption.
4. Contribution claim: what the candidate personally decided, built, changed, or stopped.
5. Outcome claim: measurable result and the causal link to the candidate's action.

Words such as "led", "owned", "core", "0-to-1", "platform", "AI", "high concurrency", and team size are claims, not evidence.

## 3. Internet research protocol

### 3.1 Resolve the entity

Confirm exact product identity before attaching sources. Match company, product, dates, product category, geography, and any repository or domain. If identity remains ambiguous, say so. A similarly named open-source project cannot validate a candidate's private project.

### 3.2 Build a product fact card before scoring

Write the fact card for a reviewer who knows neither the company nor the product. It must contain:

| Field | Required content |
|---|---|
| Plain-language description | One or two sentences explaining what is sold and what job it performs; do not substitute a category label or technical noun list |
| Product boundary | Single product, product family, platform layer, internal project, or company-wide product stack |
| Buyer and users | Who pays, who administers it, and who uses it in daily work |
| End-to-end workflow | The actual sequence from purchase/setup through routine use, operation, feedback, and renewal or outcome |
| Major modules | The functional layers users can distinguish; separate core product, management plane, infrastructure, and add-on capabilities |
| Business model | SaaS subscription, usage, license, implementation, managed service, outcome pricing, or unknown |
| Hard technical problems | The mechanisms that materially determine reliability, quality, cost, safety, or product value |
| Product history | Capabilities and market position during the candidate's tenure, not only the current page |
| Original-source ledger | Short source excerpt, direct URL, date, exact page/section, what it proves, and what it does not prove |
| Unknowns | Missing facts that could change product identity, leadership, or candidate attribution |

Do not score a product until this card is adequate. If one resume row merges several products or layers, split the row. If a company product stack is used as the object, explain each layer and later attribute only the layer the candidate can prove they owned.

### 3.3 Use a source ladder

Prefer sources in this order:

1. Primary technical evidence: source repository, paper, benchmark, patent, architecture talk, release notes, product documentation.
2. Primary business evidence: filing, annual report, audited metrics, named customer case, procurement or regulatory record.
3. Independent evidence: recognized benchmark, customer-authored account, reputable technical or industry analysis.
4. Company marketing or executive interview.
5. Candidate resume or interview statement.

Company marketing can establish positioning and claimed capability. It cannot independently establish leadership.

### 3.4 Time-align evidence

Judge the product against the market during the candidate's tenure:

- Was the capability novel then or already table stakes?
- Was the candidate present before or after the key release?
- Did the relevant scale or customer adoption occur during the candidate's ownership?
- Does a current product page describe capabilities added after the candidate left?

### 3.5 Establish a comparison baseline

At minimum identify:

- Main alternative products or architectures at the time.
- The dimension on which this product could be leading: outcome, cost, quality, reliability, developer experience, deployment, safety, or distribution.
- Public evidence that supports the comparison.

Do not use "large", "complex", "famous", or "serves major customers" as synonyms for leading.

### 3.6 Search for contrary evidence

Look for weak adoption, commodity features, discontinued products, public incidents, unproven claims, missing benchmarks, and dependence on third-party models or platforms. The goal is not to attack the candidate; it is to prevent one-sided evidence from becoming a hiring conclusion.

Do not drop contrary evidence merely to shorten the report. Preserve any fact that changes product identity, proprietary-versus-third-party system boundaries, candidate tenure attribution, ownership, differentiation, or customer validation.

## 4. Keep screening signal separate from confirmed ability

For each dimension, produce two numbers when possible:

- **Raw signal score:** How strong, specific, difficult, and relevant the available claim appears if it is true. Public product evidence and resume detail can raise this score. Keyword breadth, titles, team size, and brand prestige cannot.
- **Current confirmed score:** How much ability the available evidence actually proves today. Apply the evidence-grade cap to this score.

Do not lower the raw signal score merely because the claim has not yet been independently verified; that uncertainty belongs in the evidence grade and confirmed score. Conversely, do not give a high raw signal score to vague claims such as "led the AI platform" simply because public evidence proves the company had a strong product.

This distinction prevents two opposite errors:

- treating an impressive but unverified resume as proven senior ability;
- rejecting every senior candidate at resume stage because personal contribution has not yet been interviewed.

## 5. Evidence grades and confirmed-score caps

Grade each of the three scores separately:

| Grade | Evidence quality | Confirmed-score cap |
|---|---|---:|
| E0 | Entity unresolved or no usable evidence | 0 contribution to the confirmed composite; label unresolved, not proven-zero ability |
| E1 | Resume/interview assertion or one marketing source only | 55 |
| E2 | Multiple sources but mostly self-reported, indirect, or not time-aligned | 70 |
| E3 | Time-aligned primary evidence plus a materially different corroborating source | 85 |
| E4 | E3 plus inspectable output, benchmark, code, architecture decision record, or pressure-tested candidate explanation | 100 |

Evidence caps prevent confidence from being smuggled into a hiring conclusion. A raw signal may exceed the cap, but the confirmed score may not.

## 6. Score A: Product technical complexity and leadership

Score the product or claimed project, not the candidate. This is not a product-design score. Business importance and generic feature differentiation receive little weight; technical difficulty, period-appropriate leadership, innovation, and technical taste dominate.

| Subdimension | Weight | What strong evidence looks like |
|---|---:|---|
| Problem importance | 5 | The technical problem is worth solving and failure has material cost |
| Technical complexity | 25 | Hard scale, consistency, reliability, security, model, data, or systems mechanisms that common components do not solve directly |
| Technical leadership | 25 | Period-appropriate advantage in quality, performance, cost, reliability, safety, or engineering paradigm, supported by comparison evidence |
| Technical innovation | 20 | A new mechanism, architecture, algorithm, data loop, evaluation method, or engineering approach rather than recombination of standard components |
| Technical selection and taste | 15 | Chooses an important, under-solved technical problem and identifies the genuinely hard part instead of following fashionable vocabulary |
| Real-world validation | 10 | Production duration, scale, benchmark, users, operational result, or independent evidence |

Do not equate missing public evidence with low technical taste by itself. Lower technical-taste and innovation scores when the candidate voluntarily presents a highly repetitive topic as a core project but neither public information nor the candidate's description contains a distinct hypothesis, mechanism, baseline, failure, or result. A generic Agent harness, RAG wrapper, workflow builder, or chatbot should not receive a high score simply because its terminology matches the target product.

Interpretation:

- 80-100: demonstrably leading, not merely competitive.
- 70-79: strong product with meaningful differentiation.
- 60-69: credible and useful, but leadership is limited or unproven.
- Below 60: commodity, internal-only, weakly validated, or mostly positioning.

## 7. Infer responsibility, then score candidate technical depth

Before scoring, infer the candidate's likely responsibility boundary. Use resume verbs, specificity, organizational scope, tenure, product layers, and plausibility. Output `likely owned part / inference basis / confidence / parts not attributable / verification question`. Broad claims spanning models, infrastructure, applications, teams, and business models usually indicate route-setting or organizational responsibility, not personal implementation of every layer.

Score only what the candidate most likely contributed.

| Subdimension | Weight | What strong evidence looks like |
|---|---:|---|
| Responsibility authenticity and boundary | 15 | Specific and internally consistent distinction between personal work, team work, company capability, and third-party capability |
| Implementation complexity | 20 | Personal work reaches architecture, algorithms, data, reliability, performance, security, or implementation mechanics |
| Hard-problem depth | 20 | Identifies and solves the core failure mechanism rather than peripheral integration or coordination |
| Technical decisions | 20 | Explains alternatives, constraints, tradeoffs, and why the chosen design won |
| Failure and iteration | 15 | Describes failed approaches, diagnosis, correction, changed design, and learned judgment |
| Development duration and continuity | 10 | Sustained production use, multiple versions, operational learning, and continued ownership rather than a short demo |

Management scope is relevant only when tied to technical standards, architecture decisions, talent density, delivery quality, or measurable organizational leverage.

## 8. Score C: Product-line fit

Score transferability to each target product line, not keyword overlap. This is the only fit score used in the final composite; do not calculate a second generic target-role-fit score.

| Subdimension | Weight | What strong evidence looks like |
|---|---:|---|
| Hard-problem similarity | 25 | The same core failure mechanisms and decision patterns recur in the target product |
| Technical-architecture similarity | 25 | The same difficult system mechanisms recur beyond shared vocabulary |
| Data and evaluation-loop similarity | 20 | Comparable production data, human feedback, evaluation, failure return, or model-improvement loop |
| Customer and deployment similarity | 15 | Similar buyer, privacy, integration, reliability, SaaS/private-deployment, and compliance constraints |
| Responsibility and stage similarity | 15 | Candidate's inferred ownership matches the target product's stage, ambiguity, team size, and hands-on requirement |

Industry equality is neither necessary nor sufficient. Distributed reliability experience may transfer across industries; enterprise delivery experience may not transfer to AI product discovery without evidence of current experimentation and product judgment.

### 8.1 Separate product lines are mandatory when the company has multiple products

Do not use one generic company-fit score when the target company has materially different product lines. Build one current capability map per product, then apply the fixed Score C dimensions above separately to each product line.

For Stardust/PreSeen, at minimum distinguish:

- **Friday:** collaborative intelligence workspace; cross-application context ingestion; layered personal/team/organization memory; knowledge extraction, consolidation, recall, provenance, access control; Agent skills and long-horizon knowledge work; Memory/Recipe compounding.
- **MorningStar:** enterprise AI data and model production platform; multimodal data ingestion and management; scenario/corner-case discovery; annotation and autolabeling; dataset/model/version lineage; evaluation and hard-case mining; training/deployment loops; SaaS/private deployment and enterprise data security.

Output a separate raw and confirmed fit score for each product line. If the hiring role is scoped to Friday, use Friday fit directly as Score C and treat MorningStar as adjacent evidence; reverse this for a MorningStar role. If scope is unresolved, calculate both final composites and do not hide the ambiguity in an average. Do not add any additional generic fit score because it would duplicate Score C.

## 9. Composites and gates

### 9.0 Resume-only screening

If the available and intended decision input is the resume alone, the primary score is the resume signal composite. Do not apply E0-E4 numerical ceilings to create a confirmed composite: there is no later evidence in the current stage that could make such a score comparable across candidates. Public research provides product context and contemporaneous benchmarks only. Candidate-specific uncertainty must be expressed through the personal-depth subdimensions and explicit risk flags, without a second penalty.

For resume-only cohort ranking, add rank and percentile while preserving the absolute score. Use these default bands: `>=75 strong interview recommendation`, `70-74.9 interview recommendation`, `65-69.9 weak recommendation/priority verification`, `60-64.9 targeted verification`, `<60 reject`.

### 9.1 Multi-product portfolio aggregation

Default input identity rule: one row equals one candidate. Adjacency, similar employers, plausible career progression, or related technical topics are not identity evidence. Merge rows only when a candidate ID, name, explicit resume boundary, or equally direct source linkage confirms that they belong to the same person. Otherwise produce a separate fact card, responsibility inference, scoring breakdown, and final score for every row.

When one candidate is confirmed to have many product rows, preserve a coverage table for all rows and select no more than three representative product clusters. Choose them using technical substance, plausible personal ownership, recency when known, and target-product relevance. Score each representative product separately, then aggregate the product-technology score with fixed weights:

- Three representatives: `50% / 30% / 20%` in ranked order.
- Two representatives: `60% / 40%`.
- One representative: `100%`.

Do not average every historical project merely because it appears in the input. Explain why each representative was selected and which rows were grouped into it. Candidate technical depth and product-line fit can use the full portfolio, but must cite concrete inferred-owned components rather than company names or titles.

For a general senior technical product role:

```text
Signal composite = raw Product technical complexity and leadership * 30% + raw Technical depth * 40% + raw Product-line fit * 30%
Confirmed composite = confirmed Product technical complexity and leadership * 30% + confirmed Technical depth * 40% + confirmed Product-line fit * 30%
```

Change weights only when the target role explicitly requires it, and disclose the change.

Before finalizing, recompute each weighted term and the total separately. The printed formula, component scores, and reported composite must agree exactly.

If one dimension is E0/Unknown, keep any separately justified raw claim score for resume screening, but use 0 for that dimension's contribution to the evidence-capped confirmed composite. Label the zero as an unresolved-evidence penalty, not as proof that the candidate's actual ability is zero.

Product-line fit has direct 30% impact on the final score. Calculate it from the candidate's inferred responsibility boundary rather than the full former-company product. When the target product is unresolved, calculate separate final composites for each material product line and label the highest one as the best-fit product-line score; do not average product lines. Always display both the raw resume-signal composite and the evidence-capped confirmed composite.

Apply two different gates after calculating the scores.

### Resume-screen gate

- **Advance to targeted interview:** raw technical depth and raw fit are normally at least 70, the claims are specific enough to test, and no material contradiction has been found.
- **Targeted verification:** at least one critical raw score is 60-69, or a high raw score depends on identity, dates, ownership, or one missing artifact that can be checked cheaply.
- **Reject at screen:** a critical raw score is below 60 even if the claim is true, the experience is materially stale or stage-mismatched, or research contradicts the central claim.
- **Insufficient identity:** do not advance through the normal loop until the exact product, candidate identity, repository, or employment dates are supplied.

### Senior-hiring gate

- Confirmed technical depth below 60: not yet qualified as proven senior technical ownership.
- Confirmed target-role fit below 60: do not recommend for this role, even if generally strong.
- Critical contribution evidence E0/E1: do not conclude senior-level ownership without interview or work-sample verification.
- Product technical leadership above 75 with technical depth below 60: label "leading technology context, passenger risk".
- Technical depth above 75 with product technical leadership below 60: label "strong engineering, technical-selection evidence weak".
- Fit above 75 based mainly on shared AI keywords: reduce to apparent fit until mechanism, recency, and work products are verified.

Use these decision labels:

- 80+: strong evidence of senior-level fit.
- 70-79: credible fit with bounded risks.
- 60-69: marginal; only advance when targeted verification is cheap and important.
- Below 60: does not meet the target role.
- Unknown: insufficient evidence; never translate unknown into a positive score.

## 10. Required output format

```markdown
## 产品事实卡
### [产品名称]
| 字段 | 内容 | 原文依据 |
|---|---|---|
| 一句话说明 | | |
| 产品边界 | | |
| 购买者与使用者 | | |
| 实际工作流 | | |
| 主要模块 | | |
| 商业模式 | | |
| 核心技术难点 | | |
| 候选人任期内状态 | | |
| 未知项 | | |

### 产品原文证据
| 来源 | 日期与位置 | 原文短摘录 | 能证明什么 | 不能证明什么 |

## 原始材料
### 内部产品原文摘录
[原文、来源、日期、位置]

### 候选人原文摘录
[原文、来源、日期、是否经过格式清理]

## 互联网增强信息
| 产品层/项目 | 公开事实与原文 | 直接来源与位置 | 能证明什么 | 不能证明什么 |

## 候选人负责范围反推
| 可能负责部分 | 反推依据 | 置信度 | 不应归给候选人的部分 | 面试验证问题 |

## 一句话结论
[筛选判断、最强证据、最大不确定性]

## 目标岗位画像
| 岗位使命 | 产品阶段 | 技术重点 | 关键约束 | 要求的责任范围 |

## 互联网调研
| 编号 | 产品主张 | 公开事实 | 来源与日期 | 来源类型 | 能支持什么 | 不能支持什么 | 是否与任职时间对齐 |

## 主张核验
| 简历/候选人主张 | 已证明部分 | 未证明或矛盾部分 | 是否证明为候选人个人贡献 |

## 评分
| 评价维度 | 原始简历信号分 | 证据等级 | 当前确认分 | 评分理由 |
| 产品技术复杂度与领先性 | | | | |
| 候选人技术深入度 | | | | |
| Friday 产品线匹配度 | | | | |
| MorningStar 产品线匹配度 | | | | |

### 产品线匹配矩阵
| 产品线 | 原始相似度 | 证据等级 | 当前确认相似度 | 匹配机制 | 关键缺口 |
| Friday | | | | | |
| MorningStar | | | | | |

明确说明：更匹配哪条产品线；目标岗位匹配度采用哪条产品线作为主要依据；是否存在岗位归属不明的问题。

### 子项打分明细

分别为产品技术复杂度与领先性、候选人技术深入度，以及每条目标产品线匹配度输出一张表：

| 子项 | 权重 | 原始分 | 加权贡献 | 打分依据与缺失证据 |
|---|---:|---:|---:|---|

每张表必须满足：

- 产品技术复杂度与领先性、候选人技术深入度各展示六个规定子项；每条产品线匹配度使用且仅使用 `25/25/20/15/15` 五个规定子项，不能再输出旧版 `30/20/20/15/15` 通用岗位匹配表。
- 加权贡献之和必须与该维度的原始分一致；如有四舍五入，明确标注。
- 打分依据应指向前文公开证据、候选人主张或明确的缺失证据，不能只写形容词。
- 原始分反映“如果主张属实”的信号强度；当前确认分另行结合证据等级、时间对齐和个人归因计算，不要把两者混在子项表中。
- E0/未知的维度不编造子项数字，逐项标记未知并说明缺少什么证据。

### 确认分调整

| 评价维度 | 原始分 | 证据等级及上限 | 确认分 | 从原始分扣减的具体原因 |
|---|---:|---|---:|---|

简历信号综合分：
当前确认综合分：
简历筛选门槛：
高级人才录用门槛：

## 可迁移优势
- ...

## 风险与缺失证据
- ...

## 筛选结论
[进入面试 / 针对性验证 / 淘汰 / 信息不足]

## 下一步问题
| 问题 | 验证的主张 | 合格回答 | 风险信号 |

## 评审反馈
| 待确认判断 | 当前判断及证据编号 | 评审者反馈 |
```

Every factual public claim needs a direct source link. Clearly label inference. Do not cite a search-results page.
