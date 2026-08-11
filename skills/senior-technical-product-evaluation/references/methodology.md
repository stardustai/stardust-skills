# Methodology: Senior Technical Product Leadership Evaluation

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

Match is relational. The same product experience can be highly relevant to one role and weak for another. Before scoring, mark any normally required gate that the target role explicitly does not require. Never remove a gate after seeing a candidate's result.

When the organization is genuinely willing to hire at more than one level or responsibility track, define those tracks before scoring. For example, a technical-director track may require operating ownership while an L4 hands-on architect track may not. Keep the same seven scores for comparability, but apply decision gates per declared track. Do not invent a lower role after seeing weak scores; use it only when it is a real hiring option with a defined mission and responsibility boundary.

The target definition must support HR routing, not only scoring. For every real track, record the product line, role/level, responsibility scope, interview decision standard, and upgrade path. If people can be assigned to whichever product they fit best, product scope is not an unresolved blocker: evaluate each product separately and select the best-supported primary route.

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
| Technical-team environment | Product ownership, sustained R&D, identifiable technical output, team quality, and whether the candidate sat in the core product team; use as fact and risk context only |
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

Company marketing can establish positioning and claimed capability. It cannot independently establish leadership or the candidate's personal contribution.

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

### 3.7 Evaluate GitHub and other public-code evidence

Public code is most useful when it shows a representative sample of difficult, relevant, attributable work. Use this order:

1. **Select representative projects first.** Choose no more than three project clusters using target relevance, technical substance, candidate attribution, recency, and project impact. Do not average every repository or rank candidates by repository count.
2. **Assess project impact separately.** Use stars, forks, releases, active contributors, downstream adoption, documentation, and production references to understand the upstream project's influence. These are product-context signals, not personal contribution.
3. **Assess the candidate's contribution.** Inspect candidate-authored diffs, commits, pull requests, review discussions, tests, merge status, releases, and follow-up fixes. Prefer merged upstream work over a fork merely displayed on the profile.
4. **Treat forks by their upstream result.** A fork's inherited code, stars, or size is not the candidate's work. Check which commits are new, which pull requests were sent upstream, whether they were merged, and whether the candidate continued to maintain the affected mechanism.
5. **Use code volume asymmetrically.** A large change adds positive signal only when it enters a core mechanism, has a clear responsibility boundary, survives review, and is merged or adopted. A small change is never negative merely because it has few lines; security fixes, concurrency corrections, API contracts, and architectural simplifications may create high value with little code.
6. **Keep tool choice neutral.** Use of Claude, Copilot, or another AI coding tool does not add or subtract points by itself. Lower personal-contribution judgment only when the candidate cannot explain or own the problem, design, implementation, tests, review corrections, and result.
7. **Sample quality and value.** PR, commit, star, and fork counts help select samples and estimate activity or impact, but they never replace inspection of problem value, technical complexity, review quality, tests, defects, and sustained result.

For reports with material public-code evidence, include a short ledger showing why each representative project was selected, project-level impact signals, candidate-attributable artifacts, merge/adoption result, code-volume interpretation, and what remains unproven.

## 4. Keep screening signal separate from confirmed ability

Use the same seven dimensions in both stages, but do not pretend that the stages have the same evidence:

- **Resume signal score（七维简历信号分）:** how strong, specific, difficult, and relevant the available claim appears if it is true. Public product evidence and resume detail can raise it. Keyword breadth, titles, team size, and brand prestige cannot. Resume screening does not apply E0-E4 as a second numerical cap.
- **Raw ability score（七维原始能力分）:** after interview evidence is available, how strong the claimed ability would be if the claim is true.
- **Current confirmed score（七维确认分）:** how much ability the available evidence proves now. This exists only for the interview/hiring stage and uses the evidence-grade cap.

Do not lower a signal or raw score merely because a strong claim has not yet been independently verified; put that uncertainty in evidence coverage, the missing-information state, and—at interview stage—the confirmed score. Conversely, do not give a high signal score to vague claims such as "led the AI platform" merely because public evidence proves the company had a strong product.

## 5. Evidence grades and confirmed-score caps

At the interview/hiring stage, grade each of the seven dimensions separately:

| Grade | Evidence quality | Confirmed-score cap |
|---|---|---:|
| E0 | Entity unresolved or no usable evidence | 0 contribution to the confirmed composite; label unresolved, not proven-zero ability |
| E1 | Resume/interview assertion or one marketing source only | 55 |
| E2 | Multiple sources but mostly self-reported, indirect, or not time-aligned | 70 |
| E3 | Time-aligned primary evidence plus a materially different corroborating source | 85 |
| E4 | E3 plus inspectable output, benchmark, code, architecture decision record, or pressure-tested candidate explanation | 100 |

Evidence caps prevent confidence from being smuggled into a hiring conclusion. A raw ability score may exceed the cap, but the confirmed score may not. E0-E4 are not used to impose a second numerical ceiling on resume signal scores.

## 6. Seven fixed evaluation dimensions

Use exactly this composite in both stages. At resume stage, each term is the dimension's resume signal score. At interview stage, calculate both a raw-ability composite and a confirmed composite using the corresponding seven dimension scores.

```text
统一综合分 = 产品/项目技术含金量 × 20%
           + 候选人个人技术贡献深度 × 20%
           + AI、算法、数据与评测判断 × 10%
           + 产品与客户判断 × 15%
           + 经营责任与创业型 ownership × 15%
           + 跨职能领导与信息整合 × 5%
           + 目标产品与阶段匹配 × 15%
```

Technical-team environment is recorded in the product fact card and risk context. It is not an eighth dimension and never enters the composite.

### 6.1 产品/项目技术含金量

Score the product or claimed project, not the candidate. Technical difficulty, period-appropriate leadership, innovation, technical selection, and validation dominate.

| 子项 | 权重 | 强证据 |
|---|---:|---|
| 问题重要性 | 5% | 技术问题值得解决，且失败有实质成本 |
| 技术复杂度 | 25% | 规模、一致性、可靠性、安全、模型、数据或系统机制不是通用组件直接可解 |
| 同期技术领先性 | 25% | 与任期同期替代方案比较，在质量、性能、成本、可靠性、安全或范式上有可验证优势 |
| 技术创新 | 20% | 有新机制、架构、算法、数据闭环、评测方法或工程方法，而非标准组件拼装 |
| 技术选择与品味 | 15% | 选中重要且未被充分解决的问题，并识别真正困难部分 |
| 真实世界验证 | 10% | 有生产时长、规模、基准、用户、运营结果或独立证据 |

Generic Agent harnesses, RAG wrappers, workflow builders, or chatbots do not score highly merely because their vocabulary resembles the target product. Missing public evidence is uncertainty, not automatically low technical taste; lower the score when the presented core project lacks a distinct hypothesis, mechanism, baseline, failure, and result.

### 6.2 候选人个人技术贡献深度

First infer the likely responsibility boundary from resume verbs, specificity, organizational scope, tenure, product layers, and plausibility. Output `likely owned part / inference basis / confidence / parts not attributable / verification question`. Score only what the candidate personally did or credibly led.

| 子项 | 权重 | 强证据 |
|---|---:|---|
| 个人责任边界真实性 | 15% | 一致地区分个人、团队、公司和第三方的工作与能力 |
| 关键架构与实现复杂度 | 20% | 个人工作深入架构、算法、数据、可靠性、性能、安全或实现机制 |
| 核心故障机制理解 | 20% | 找到并解决核心失败机制，而非只做外围集成或协调 |
| 技术方案比较与取舍 | 20% | 说明备选方案、约束、取舍和选择胜出的原因 |
| 失败诊断与迭代 | 15% | 说明失败方案、诊断、修正、设计变化和判断更新 |
| 生产持续性与当前能力 | 10% | 有持续生产、多版本、运行学习和当前仍可复用的能力，而非短期演示 |

Management scope matters only when tied to technical standards, architecture decisions, talent density, delivery quality, or measurable organizational leverage.

### 6.3 禁止重复计分

- 公司品牌、产品规模和公开架构只属于产品/项目技术含金量。
- 团队环境（包括团队能力、团队质量、融资、团队规模和领导者质量）始终只进入产品事实卡和风险上下文，不进入产品含金量、个人贡献或任何其他评分维度。
- 候选人个人决策、实现、失败诊断和可归因结果才属于个人技术贡献。
- “支持千万用户”不能同时抬高两个维度；只有证明候选人本人解决了该规模下的具体故障机制，才能在个人维度得分。
- 强产品不能在个人贡献不清时自动成为个人正面证据；产品分高而个人贡献低或未覆盖时，标记“优秀产品环境，搭便车风险”。

### 6.4 AI、算法、数据与评测判断

| 子项 | 权重 | 强证据 | 无效替代信号 |
|---|---:|---|---|
| 问题与模型/算法方案匹配 | 20% | 比较规则、检索、传统算法、模型或人工流程，说明选择条件和结果 | AI 品牌、模型名称或“接入大模型” |
| 数据质量与数据闭环 | 20% | 定义数据质量、采集偏差、标注、版本和生产反馈回流 | 数据量、ETL 或向量库本身 |
| 评测体系与基线比较 | 20% | 有离线/在线指标、基线、分层样本和可复算比较 | 单次演示或主观“效果好” |
| 反馈、失败样本与持续改进 | 15% | 分类 hard cases，追踪失败机制并验证迭代收益 | 只收集反馈或增加 Prompt |
| 可靠性、成本与延迟取舍 | 15% | 量化质量、可用性、成本、延迟之间的取舍及生产结果 | 只宣称高并发、低成本或稳定 |
| 权限、来源、安全与审计 | 10% | 说明权限边界、来源、隐私、安全、审计和失效处理 | 只写“企业级”或“合规” |

AI 术语不能单独得高分。普通数据采集、ETL、向量检索、Prompt 编排、LLM API 接入、通用 RAG 或 Agent 框架，在没有评测/反馈闭环、关键取舍、失败分析和比较结果时不能因术语相似自动达到 60 分。

### 6.5 产品与客户判断

| 子项 | 权重 | 强证据 | 无效替代信号 |
|---|---:|---|---|
| 客户问题识别 | 20% | 区分购买者、使用者和真实任务，以行为或损失验证问题 | 转述需求、行业热词或客户名单 |
| 产品边界与优先级 | 20% | 说明做什么、不做什么、先后顺序及被否决方案 | 功能数量或完整需求清单 |
| 产品与技术取舍 | 20% | 把客户价值与质量、成本、时限和工程约束连接起来 | 只说“业务技术对齐” |
| 客户验证与反馈闭环 | 15% | 通过试点、观察、访谈和行为数据改变假设与方案 | 参加评审或收集意见 |
| 使用、采购、续费或采用结果 | 15% | 有使用、采购、续费、转化、留存或采用结果及因果边界 | 交付上线或签约数量本身 |
| 产品选择与技术品味 | 10% | 选择重要未解问题，并用客户和技术事实持续校正方向 | PRD、路线图或产品经理头衔 |

“参与需求评审”“撰写 PRD”“支持客户交付”不能替代产品判断。强证据必须展示取舍、被否定方案、客户行为变化和结果。

### 6.6 经营责任与创业型 ownership

| 子项 | 权重 | 强证据 | 无效替代信号 |
|---|---:|---|---|
| 明确经营或客户结果 | 25% | 有明确目标、实际值、时间和本人责任边界 | 创业头衔、业务线名称或愿景 |
| 从问题到采用的完整责任 | 25% | 从问题发现、产品/技术选择到上线、采用和复盘持续负责 | 只负责研发交付或一个里程碑 |
| 收入、续费、毛利、成本或客户价值 | 20% | 有可复算指标、基线、变化及候选人行动的因果边界 | 只给营收规模、融资或客户数量 |
| 资源与优先级取舍 | 10% | 在人力、预算、时间和机会成本之间作出并承担取舍 | 团队规模或预算规模 |
| 不确定性下主动推进 | 10% | 信息不完整时提出可验证路径、获得资源并更新方向 | “推动落地”或加班完成 |
| 结果不达标后的调整与问责 | 10% | 承认未达标，诊断原因，改变资源/策略并承担后果 | 只归因市场、团队或上级 |

创业经历可以是强证据但不是必要条件；在大公司真正拥有独立产品线、预算和经营指标也可成立。创业头衔不能单独得高分，没有客户、指标、资源取舍和失败事实时不得用头衔补分。

### 6.7 跨职能领导与信息整合

| 子项 | 权重 | 强证据 | 无效替代信号 |
|---|---:|---|---|
| 复杂信息压缩与关键矛盾识别 | 20% | 把多方事实压缩成关键矛盾、选项和可执行判断 | 汇总材料或复述各方意见 |
| 产品、算法和工程之间的翻译 | 20% | 让不同专业约束进入同一决策并形成可验证接口/标准 | 参加跨部门会议 |
| 面向客户和销售的产品表达 | 15% | 准确说明价值、限制和适用边界并改变承诺或方案 | 演示、汇报次数或表达流畅 |
| 决策、责任和升级机制 | 15% | 明确谁决定、谁负责、何时升级以及冲突如何关闭 | “推动协作”或协调会议 |
| 技术标准与人才判断 | 15% | 建立并校正技术标准，用具体事实做招聘、培养和去留判断 | 团队规模或管理年限 |
| 团队效率与复用能力 | 10% | 用机制、平台或工作方式产生持续可量化复用 | 一次性攻坚或加人交付 |
| 接受反馈并纠正自身判断 | 5% | 能说明自己的误判、反馈来源、修正行为和结果 | 笼统表示开放、谦虚 |

团队规模、协调会议和“沟通能力强”不能单独得高分。必须追问冲突、候选人的最终判断、采取的行动、信息如何被压缩以及结果是否持续。

### 6.8 目标产品与阶段匹配

Score transferability, not keyword overlap. Use the fixed five subdimensions separately for each material target product line:

| 子项 | 权重 | 强证据 |
|---|---:|---|
| 核心难题相似度 | 25% | 目标产品中重复出现相同核心失败机制和决策模式 |
| 技术架构相似度 | 25% | 不只词汇相同，困难系统机制也可迁移 |
| 数据与评测闭环相似度 | 20% | 有可比的生产数据、人工反馈、评测、失败回流或模型改进闭环 |
| 客户与部署环境相似度 | 15% | 购买者、隐私、集成、可靠性、SaaS/私有化和合规约束相似 |
| 责任范围与发展阶段相似度 | 15% | 已证明责任与目标产品阶段、模糊度、团队规模和动手要求匹配 |

For Stardust/PreSeen, at minimum distinguish:

- **Friday:** collaborative intelligence workspace; cross-application context ingestion; layered personal/team/organization memory; knowledge extraction, consolidation, recall, provenance, access control; Agent skills and long-horizon knowledge work; Memory/Recipe compounding.
- **MorningStar:** enterprise AI data and model production platform; multimodal data ingestion and management; scenario/corner-case discovery; annotation and autolabeling; dataset/model/version lineage; evaluation and hard-case mining; training/deployment loops; SaaS/private deployment and enterprise data security.

Output separate Friday and MorningStar scores. Use the in-scope target product's score as the seventh dimension and treat the other as adjacent evidence. If scope is fixed but unresolved, calculate both seven-dimension composites and preserve the ambiguity. If the organization explicitly assigns the candidate to whichever product fits best, select the stronger evidence-supported product as the primary HR route and name the other as an adjacent alternative when useful. In both cases, never average the product lines or add a generic second fit score.

## 7. Recent-function evidence is a horizontal rule

Do not create an independent recent-role dimension. Apply the candidate's actual recent function and the following time shares across all candidate-ability dimensions:

```text
0—3 年证据至少占候选人能力判断的 70%；
3—7 年最多 20%；
7 年以上最多 10%；
最近主要从事 SRE、DevOps、质量、交付或纯管理时，只能在被实际证明的维度得分。
```

Use the current role plus the immediately preceding substantive role when needed to cover roughly 24–36 months. Do not transfer an absent recent share to old work to create a flattering total. A product's intrinsic historical score may remain time-aligned to its own period, but current candidate ability must discount stale personal evidence. Titles such as CTO, technical director, head of engineering, or AI lead do not prove current function.

Every report must include:

| Time window | Products and dates | Candidate-owned work | Weight used | Affected dimensions | What it proves / does not prove |
|---|---|---|---:|---|---|

## 8. Missing-information state machine

Every claim or verification item must use exactly one of these states:

```text
简历未覆盖
面试未覆盖
已覆盖待判断
已证明
已追问未证明
证据矛盾
不适用
```

- `简历未覆盖`: do not claim the candidate lacks the ability. Score only visible resume signal, explain whether a normally expected senior claim is absent, and add a next-round item.
- `面试未覆盖`: do not treat the omission as negative candidate evidence. The affected critical dimension remains unconfirmed and returns to the next-round list.
- `已覆盖待判断`: evidence exists but has not yet been weighed or reconciled.
- `已证明`: evidence is adequate for the stated claim and its attribution boundary.
- `已追问未证明`: a targeted question was asked but the claim remained unsupported. This is negative evidence; retain the original answer and lower the relevant raw and confirmed scores.
- `证据矛盾`: preserve conflicting resume, interview, public, and artifact evidence side by side; create a second verification or reference-check item.
- `不适用`: the target capability map declared the item unnecessary before candidate scoring. Exclude it from coverage denominators; do not use it as a post-hoc exemption.

State progression must preserve history. A later evaluation cites and updates unresolved earlier items instead of generating a disconnected report.

## 9. Two-stage scores and coverage

### 9.1 Resume screening

Output only:

- seven dimension resume signal scores and `简历信号综合分` using the fixed formula;
- `证据覆盖率`;
- uncertainty flags such as unresolved entity, missing tenure, unclear personal boundary, non-recomputable metric, company capability attributed to the candidate, or critical dimension not covered;
- screening conclusion: interview, targeted verification, reject, or insufficient information;
- an HR routing summary placed immediately after the one-line conclusion: recommended product, role/level, responsibility scope, interview decision, adjacent alternative, and upgrade path;
- the continuous verification checklist in section 12.

Do not output an E0-E4-capped second composite at resume stage. Public research supplies product context and contemporaneous baselines; it does not independently prove personal contribution.

Resume coverage uses an evidence object appropriate to each dimension:

- 产品/项目技术含金量：使用与候选人任期对齐的产品级证据；不要求该产品事实可归因到候选人，也不把团队环境事实计入覆盖率。
- 候选人能力维度（个人技术贡献、AI/算法/数据/评测判断、产品与客户判断、经营责任、跨职能领导）：只使用可归因到候选人的证据；公司、产品或团队能力不能替代个人证据。
- 目标产品与阶段匹配：同时要求目标产品事实和可归因到候选人的相关简历证据；简历阶段不要求该候选人证据已独立确认，只有一侧存在时对应子项不算覆盖。

For each dimension, resume coverage equals the sum of the subdimension weights that meet its evidence-object rule. Overall resume evidence coverage equals the sum of `fixed dimension weight × dimension coverage`. Coverage measures presence, not truth or evidence grade, and never replaces the score.

For resume-only cohort ranking, preserve the absolute score and optionally add rank/percentile. Default bands are `>=75 strong interview recommendation`, `70-74.9 interview recommendation`, `65-69.9 weak recommendation/priority verification`, `60-64.9 targeted verification`, and `<60 reject`, subject to the critical gates and missing-evidence rules below.

### 9.2 Interview and hiring

Output:

- seven dimension raw ability scores and the fixed-formula `原始能力综合分`;
- E0-E4 grade and current confirmed score for each dimension, plus `当前确认综合分`;
- `确认覆盖率`, contradictions, remaining risks, and gate decisions;
- the updated continuous verification checklist.

At interview stage, product technical value uses tenure-aligned product-level evidence, candidate-ability dimensions require evidence attributable to the candidate, and target fit requires both target-product facts and candidate-responsibility evidence that is decision-ready. Within those boundaries, confirmed coverage equals the sum of subdimension weights whose evidence is decision-ready: either the claim is `已证明`, or a targeted attempt is recorded as `已追问未证明` and can support a bounded negative conclusion. `简历未覆盖`, `面试未覆盖`, `已覆盖待判断`, and `证据矛盾` do not count as confirmed coverage. Overall confirmed coverage equals the sum of `fixed dimension weight × dimension confirmed coverage`, excluding predeclared `不适用` items from the denominator.

When a critical dimension is not covered, the conclusion can only be targeted/further verification, never a confirmed senior-hiring recommendation. High scores do not override insufficient coverage.

### 9.3 Multi-product portfolio aggregation

One row equals one candidate unless a candidate ID, name, explicit resume boundary, or equally direct linkage proves otherwise. For a confirmed multi-product candidate, preserve all rows but select no more than three representative product clusters based on technical substance, plausible personal ownership, recency, and target relevance. Score each product's intrinsic technology separately, then aggregate candidate-facing evidence with the time rules in section 7.

Do not average every historical project. Explain why each representative was selected, which rows it groups, and how time weight was applied. Never count the same flagship product as both product prestige and current personal ability without separate personal evidence.

Before finalizing, recompute every subdimension contribution, dimension score, composite term, and total. Printed formulas and reported totals must agree exactly.

## 10. Gates and decisions

Apply these gates independently of the unified composite and per role track:

- 候选人个人技术贡献深度低于 60：不能录用为技术总监或同级核心技术负责人。
- 产品与客户判断低于 60：不适合产品技术一体化岗位，可另评纯技术岗位。
- 经营责任与创业型 ownership 低于 60：不符合对经营结果负责的技术总监画像。
- AI、算法、数据与评测判断低于 60：不能领导当前 AI 产品技术方向。
- 目标产品与阶段匹配低于 60：不推荐当前目标岗位。
- 关键维度处于 `简历未覆盖`、`面试未覆盖`、`已覆盖待判断` 或 `证据矛盾`：可以进入针对性验证，不能给出已经证明的高级录用结论。
- 关键个人贡献只有 E0/E1：不能结论性认定高级技术 ownership。

If the target role does not require one of these gates, mark that exception in the target capability map before scoring. Do not waive it after seeing the candidate's score. A gate failure blocks only the tracks that require that gate. For example, operating ownership below 60 blocks an operating technical-director track but does not block a predeclared L4 hands-on architect track that does not own revenue, renewal, budget, or business-line results. Keep the operating dimension visible and scored; label it non-gating for that track rather than deleting it or recomputing an ad hoc composite.

The final decision must route the candidate to the strongest supported real option. State the recommended product line, role/level, concrete responsibility scope, and whether to interview or hire. Do not make HR infer placement from the highest fit score or from a paragraph of caveats.

Useful risk labels include:

- product technology above 75 with personal contribution below 60: `优秀产品环境，搭便车风险`;
- personal contribution above 75 with product technology below 60: `强工程能力，产品/技术选择证据弱`;
- target fit above 75 mainly from shared AI words: `表面匹配，待机制与当前证据验证`.

Unknown never becomes a positive score. Distinguish missing evidence from demonstrated weakness and from contradiction.

## 11. Technical-team environment as context

Research technical-team environment independently when it changes interpretation of access, standards, or attribution. Record product ownership, financing where relevant, sustained R&D, external customers, technical output, leader quality, and whether the candidate sat in the core team. Team quality can explain opportunity or risk, but cannot raise any dimension without dimension-specific candidate evidence.

Technical-team environment has no percentage, score, or optional composite. Company prestige, financing, team size, and employer category are contextual facts only.

## 12. Continuous verification checklist

Every evaluation maintains the same table, and every later reviewer updates unresolved rows rather than starting over:

| 待验证事项 | 当前材料 | 当前判断 | 影响维度 | 下一轮问题 | 合格证据 | 风险回答 | 建议验证人 | 状态 |
|---|---|---|---|---|---|---|---|---|
| 个人架构决策与责任边界 | 仅有笼统负责表述，未提供个人决策/取舍 | 边界不清 | 候选人个人技术贡献深度 | 哪三个关键决策由你本人作出？ | 方案、取舍、结果、失败 | 只描述团队工作 | 架构师 | 简历未覆盖 |
| 经营责任 | 简历未提供 | 未知 | 经营责任与创业型 ownership | 直接负责什么经营或客户指标？ | 目标、实际值、取舍、复盘 | 只有交付日期 | CEO/业务负责人 | 简历未覆盖 |
| 跨部门决策 | 面试写“推动协作” | 已问但仍缺最终判断与结果 | 跨职能领导与信息整合 | 各方冲突是什么，谁作出最终决定？ | 冲突、决策、行动、结果 | 主要工作是开会协调 | 管理面试官 | 已追问未证明 |

The status column must contain exactly one state from section 8. Preserve the source excerpt or exact interview answer behind each current-material entry.

## 13. Required output format

Use one auditable report. Omit the stage-inapplicable scoring table: resume reports must not print evidence grades or confirmed scores; interview/hiring reports must include them.

```markdown
## 一句话结论
[阶段、推荐产品、推荐岗位/级别、建议职责、面试或录用决定、最强证据、最大不确定性]

### HR 岗位与产品匹配摘要
| HR 决策项 | 建议 | 置信度 | 主要依据 | 不应据此认定 |
|---|---|---:|---|---|
| 是否进入面试/录用 | | | | |
| 优先产品 | | | | |
| 优先岗位/级别 | | | | |
| 核心职责建议 | | | | |
| 相邻备选 | | | | |
| 升级路径 | | | | |

## 目标岗位能力图
| 岗位使命 | 产品阶段 | 技术重点 | 关键约束 | 要求的责任范围 | 评分前声明的不适用门槛 |
|---|---|---|---|---|---|

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
| 技术团队环境与风险上下文 | | |
| 未知项 | | |

### 产品原文证据
| 来源 | 日期与位置 | 原文短摘录 | 能证明什么 | 不能证明什么 |
|---|---|---|---|---|

## 原始材料
### 内部产品原文摘录
[原文、来源、日期、位置]

### 候选人原文摘录
[原文、来源、日期、是否经过格式清理]

## 互联网研究账本
| 产品层/项目 | 公开事实与原文 | 直接来源与位置 | 来源阶梯 | 能证明什么 | 不能证明什么 | 是否与任职时间对齐 | 反证 |
|---|---|---|---|---|---|---|---|

### GitHub / 公开代码代表项目账本（存在公开代码证据时）
| 代表项目及选择理由 | 项目影响信号 | 候选人可归因 diff/commit/PR/review/test | 上游 merge/发布/采用 | 代码量解释 | 能证明什么 | 不能证明什么 |
|---|---|---|---|---|---|---|

## 候选人负责范围反推
| 可能负责部分 | 反推依据 | 置信度 | 不应归给候选人的部分 | 面试验证问题 |
|---|---|---|---|---|

## 主张核验
| 简历/候选人主张 | 已证明部分 | 未证明或矛盾部分 | 是否证明为候选人个人贡献 | 缺失信息状态 |
|---|---|---|---|---|

## 最近三年实际职能证据
| 时间窗口 | 产品与日期 | 候选人个人工作 | 使用权重 | 影响维度 | 能证明 / 不能证明 |
|---|---|---|---:|---|---|

## 产品能力与个人贡献边界
| 证据 | 只进入产品含金量 | 可进入个人贡献 | 不得重复计分的理由 |
|---|---|---|---|

## 七维评分

### 简历阶段（仅简历筛选使用）
| 评价维度 | 权重 | 简历信号分 | 加权贡献 | 证据覆盖率 | 评分依据 | 缺失信息状态 |
|---|---:|---:|---:|---:|---|---|
| 产品/项目技术含金量 | 20% | | | | | |
| 候选人个人技术贡献深度 | 20% | | | | | |
| AI、算法、数据与评测判断 | 10% | | | | | |
| 产品与客户判断 | 15% | | | | | |
| 经营责任与创业型 ownership | 15% | | | | | |
| 跨职能领导与信息整合 | 5% | | | | | |
| 目标产品与阶段匹配 | 15% | | | | | |

简历信号综合分：
证据覆盖率：
不确定性标记：

### 面试及录用阶段（仅已有面试证据时使用）
| 评价维度 | 权重 | 原始能力分 | 证据等级及上限 | 当前确认分 | 原始分加权贡献 | 确认分加权贡献 | 确认覆盖率 | 缺失信息状态 | 评分理由 |
|---|---:|---:|---|---:|---:|---:|---:|---|---|
| 产品/项目技术含金量 | 20% | | | | | | | | |
| 候选人个人技术贡献深度 | 20% | | | | | | | | |
| AI、算法、数据与评测判断 | 10% | | | | | | | | |
| 产品与客户判断 | 15% | | | | | | | | |
| 经营责任与创业型 ownership | 15% | | | | | | | | |
| 跨职能领导与信息整合 | 5% | | | | | | | | |
| 目标产品与阶段匹配 | 15% | | | | | | | | |

原始能力综合分：
当前确认综合分：
确认覆盖率：

### 七维子项明细
[为七个维度分别使用本方法论规定的子项和权重]
| 子项 | 权重 | 阶段适用分 | 加权贡献 | 证据依据 | 缺失信息状态 |
|---|---:|---:|---:|---|---|

### Friday / MorningStar 匹配矩阵
| 产品线 | 原始/简历信号分 | 证据等级（面试阶段） | 当前确认分（面试阶段） | 匹配机制 | 关键缺口 |
|---|---:|---|---:|---|---|
| Friday | | | | | |
| MorningStar | | | | | |

明确说明目标岗位采用哪条产品线作为第七维。岗位归属固定但未决时分别给出两套综合分并保留歧义；组织按适配分配时分别计算后选择一个主要产品，并写入 HR 摘要与最终结论。任何情况下都不平均。

## 关键门槛
| 门槛维度 | 60 分是否满足 | 证据覆盖是否足够 | 评分前是否声明不适用 | 判断 |
|---|---|---|---|---|

## 可迁移优势
- ...

## 风险与缺失证据
- ...

## 持续验证清单
| 待验证事项 | 当前材料 | 当前判断 | 影响维度 | 下一轮问题 | 合格证据 | 风险回答 | 建议验证人 | 状态 |
|---|---|---|---|---|---|---|---|---|

## 筛选或录用结论
[推荐产品、岗位/级别、职责范围、进入面试 / 针对性验证 / 淘汰 / 信息不足 / 录用建议 / 不录用；相邻备选与升级路径]

## 评审反馈
| 待确认判断 | 当前判断及证据编号 | 评审者反馈 |
|---|---|---|
```

Every factual public claim needs a direct source link. Clearly label inference. Do not cite a search-results page. Every score must trace to an original excerpt, public fact, interview answer, artifact, or explicit missing state.
