# Spec Intake Question Bank

Use this as a menu, not a script. Ask the next question that most reduces ambiguity or risk. Ask one question at a time.

Before asking:

1. Extract every explicit fact the user already gave.
2. Map those facts to spec fields.
3. State any clear conclusion and skip the corresponding question.
4. Ask only for missing, conflicting, or high-risk information.

If a user gives a paragraph, meeting note, transcript excerpt, or partially structured request, do not restart from "one-line requirement" mode. Summarize what is already known, list the remaining unknowns briefly, then ask the single most important next question.

## Opening And Progress

- 开场是否已经展示完整流程图：intake_routing -> business_feasibility -> product_shape -> engineering_gap_review -> technical_spec -> validation_design -> validation_execution -> engineering_delivery？
- 是否已经说明当前只在 `business_feasibility`，还没有进入 `product_shape`、PoC 或工程？
- 在 Codex 环境里是否已经调用 `update_plan`？仅在工具不可用时，文本进度提示才可以作为 fallback。
- 用户是否知道每次阶段切换都需要确认？

## Product Basis

- 这个需求第一版应该基于我们哪个产品形态来做：Friday Agent、Domain Pack、Friday Memory、MorningStar、内部工具、全新独立产品，还是 demo？
- 这是一个 Domain Pack，还是只是未来可能沉淀成 Domain Pack？
- 如果不是基于现有产品，为什么需要全新独立产品？
- 如果是 demo，demo 要证明什么，不证明什么？

## Opportunity Assessment

- 这个想法现在面向 KA、SMB、hybrid、内部使用，还是未知？
- 这是一个 L2 单点场景，还是多个 L2 拼起来的 L3 行业主流程？
- 谁会付钱？谁每天使用？买方和使用者是不是同一个人？
- 第一版最小可付费交付物是什么？客户愿意为哪一个具体 Artifact 付钱或投入资源验证？
- 客户为什么愿意付钱？是省人、省时间、提转化、降风险、增加收入，还是满足刚性合规/交付要求？
- 目标客户池在哪里？有没有已知设计伙伴或种子客户？
- 客户 POC 怎么跑通？谁参与，跑多久，用什么数据，什么结果算继续推进？
- 最大交付风险是什么：数据拿不到、效果不可验证、集成太重、预算不确定、owner 不明确，还是合规风险？
- 下一步销售动作是什么：约客户确认、拿样例数据、确认预算、定 POC 范围、找设计伙伴，还是先内部评审？

## Evidence Registry

- 现在有哪些证据是事实，哪些只是判断或假设？
- 每条证据来自哪里：客户访谈、客户数据、付费信号、使用数据、历史 artifact、内部判断，还是其他？
- 这条证据是 hypothesis、anecdotal、single_case、repeated，还是 commercial_proof？
- 哪条证据能支撑客户愿意买？哪条支撑市场讲得清？哪条支撑技术价值？哪条支撑 GTM 可复制？
- 如果没有可追溯证据，是否应该把当前状态降级为 `needs_more_evidence`？

## Design Partner Registry

- 真实设计伙伴是谁？状态是 target、contacted、confirmed、rejected，还是 unknown？
- 预算 owner 是谁？
- 谁负责 review 生成结果？
- 客户愿意承诺哪些资源：真实资料、脱敏样例、review 时间、付费 POC、采购流程？
- 数据是否可用：yes、partial、no，还是 unknown？

## PMF Validation

- 这个 use case 的评估单位是什么：一个客户需求、一个可复用工作流，还是一个技术模块？
- Target ICP 能否同时说清行业、公司规模、业务成熟度和预算类型？
- 买方原话是什么？销售或客户能否用同一种语言复述这个痛点？
- 当前替代方案是什么？人工、GPT、RAG、已有 SaaS、外包，还是内部流程？
- 替代方案为什么不够好？是速度、质量、可追溯、协作、经验复用、合规，还是成本问题？
- 决策链是什么：谁感知痛点，谁评估，谁审批，谁付费，谁阻塞？
- 付费信号是什么：预算金额或区间、付费 POC、采购阶段、商业 deadline，还是客户愿意投入数据和人力？
- 四因子里当前最低分是哪一项：客户愿意买、市场讲得清、技术价值，还是 GTM 可复制？
- 如果要批准客户 PoC，是否已经有 confirmed design partner、预算 owner、可用数据、baseline、验收方式和时间盒？

## Market Sizing

Market sizing belongs to `business_feasibility`. It is not a single TAM number. First extract what the user already provided, then ask for the missing dimension that most changes the business gate or priority score.

- 客户价值有多大？如果这个问题被解决，客户具体获得什么：省钱、省人、省时间、增加收入、降低风险、提高成交率，还是满足刚性合规？
- 客户支付意愿有多强？是否有预算 owner、预算区间、付费 POC、采购 deadline、已批准项目或明确的人力/数据投入？
- 预计客单价是多少？是 POC 包、年费、席位费、按项目收费，还是私有 Pack 交付费？如果不确定，先给区间和依据。
- 可触达客户数量有多少？目标 ICP 下有多少已知客户、销售名单、渠道客户、行业客户池或可复用线索？
- 市场竞争程度如何？客户会拿我们和通用 LLM、已有 SaaS、传统系统、外包服务还是人工流程比较？
- 竞争越强时，是否有足够差异化支撑客单价和客户转化？如果没有，市场吸引力不能高分。
- 当前市场体量判断的证据是什么？哪些是客户事实，哪些只是内部估算？
- 有没有咨询公司报告、行业报告、市场研究、公开行业数据或分析师报告可以支撑客户数量、客单价、竞争格局？
- 有没有一手客户反馈可以支撑客户价值和支付意愿：客户访谈、预算 owner 反馈、付费 POC、客户数据、使用数据、销售 pipeline 或设计伙伴反馈？
- 哪些字段只是内部估算？内部估算只能作为补充，不能单独支撑 `business_ready`。
- 当前证据质量是 unverified_estimate、partially_supported、supported，还是 strongly_supported？
- `market_attractiveness_score` 打几分？1 表示小众且难付费，5 表示客户价值高、愿付费、客单价高、客户数量多且竞争可防守。
- 如果市场体量证据不足，下一步要补什么：客户名单、预算访谈、客单价验证、竞品价格、渠道规模，还是行业数据？

## Opportunity Priority

- 这个机会的商业价值打几分，为什么？
- 商业信号清晰度打几分，为什么？buyer、预算、决策链、付费信号、证据链接和下一步销售动作是否都清楚？
- 产研投入量打几分，为什么？需要多少产品、设计、AI 工程、工程、QA、DevOps、集成、合规和长期维护？
- 当前 `机会优先级指数 = 商业价值 * 商业信号清晰度 / 产研投入量` 是多少？
- 如果销售说“都要”，哪些部分会显著抬高产研投入量？
- 第一版砍掉哪一块最能提高机会优先级指数，同时不损害核心商业验证？
- 是否可以先做一个更窄的 wedge：一个 ICP、一个角色、一个工作流、一个输出、一个真实数据集、一个验收标准？

## Competitive Research

- 你们有没有已知竞品或当前替代方案对比？如果没有，我需要自动调研相关产品并给出对比矩阵。
- 客户现在拿我们和谁比：通用 LLM、已有 SaaS、内部系统、外包服务，还是人工流程？
- 竞品的目标客户是谁？核心 workflow 是什么？
- 竞品最强的 3 个能力是什么？
- 竞品最弱或不满足客户痛点的地方是什么？
- 相比竞品，我们和它的重叠度是几分，1 表示几乎不同，5 表示几乎同一个工作流？
- 相比竞品，我们的差异度是几分，1 表示没明显差异，5 表示有难复制的 workflow/data/product loop/delivery model 差异？
- 这份竞品矩阵是否经过业务用户确认？如果没有，只能标记为 pending，不能进入 product_ready。

## Stage Gate

- 当前 JSON 是给谁看的：业务负责人、产品负责人、技术负责人、QA/DevOps，还是高层决策？
- 现在只能继续取证，还是已经可以交给产品？
- 产品形态是否足够清楚，可以让 AI 工程做技术缺口评审？
- 这是请求技术缺口评审，还是请求工程排期？两者不能混用。
- 当前是否具备验证方案设计 ready？是否具备验证执行 ready？
- 如果现在交接，接收方下一步最需要回答哪个问题？
- 当前哪些 next actions 应该被 blocked，避免被误解为可以开工？
- 如果准备切换阶段，退出总结是否覆盖：当前阶段、下一阶段、已确认事实、剩余假设或 blocker、为什么允许下一阶段、什么仍然禁止？
- 用户是否明确确认阶段切换？如果没有，`stage_gate.stage_exit_check.status` 不能写成 `confirmed`。
- 如果从 `business_feasibility` 切到 `product_shape`，是否已经问过：是否确认结束业务验证并进入产品形态？

## Product Shape

- 谁每天会用它？
- 使用发生在客户沟通前、沟通中、还是沟通后？
- 现在这件事怎么做？靠 Excel、PDF、销售经验、群里问人，还是已有系统？
- 第一版成功后，用户手里会多出什么具体产物？
- 输出是内部建议、客户方案、正式报价、还是销售话术？
- 业务 owner 对产品目标的原始定义是什么？产品 owner 如何把它细化为第一版可验证的目标？
- 业务先定义的指标是什么？产品要把它细化成哪个可记录的事件、状态、质量或行为？
- 这个指标的 baseline、target、测量方式、复盘节奏和工程改进用途是什么？
- 这个产品目标对应哪些 `validation_plan.metrics`，以及哪些 loop engineering 信号必须被记录？
- 第一版一定要做什么？
- 哪些事情明确不做？
- 这个需求需要拆成多个 spec 吗？如果不拆，第一版为什么必须一起做？

## Product Technical Leadership

- 这个产品形态的技术领先性或独特性是什么？
- 相对竞品、通用 LLM、客户现有流程，它领先在哪里？
- 领先性来自模型能力、数据闭环、Memory、Recipe、Artifact review、评测体系、交付模式，还是其他？
- 产品 owner 能给出什么证明或论述？
- spec agent 给这个领先性打几分：1 表示通用能力，5 表示跨客户/部署被证明的难复制优势。
- 产品 owner 是否确认这个分数？如果不确认，原因是什么？

## Workflow

- 这个 spec 的唯一 canonical workflow 是什么？
- Agent 需要替代哪一步，辅助哪一步，人必须审哪一步？
- 人审点是在推荐前、生成方案后、还是发给客户前？
- 如果资料找不到、客户信息不完整、条件冲突，应该怎么处理？
- 输出要能追溯到哪些原文证据？
- 主要用户旅程有哪些？请按角色覆盖日常用户、review 人、管理员、产品/更新 owner，而不是只写一条主流程。
- 每条 user journey 的入口、正常路径、异常路径和退出条件是什么？
- 每条 journey 下面有哪些具体用户操作流：创建、查看、编辑、review、批准/拒绝、导出/分享、重试、权限失败、资料缺失、重复操作、外部系统失败、回滚/更新？
- 每个操作流的触发、前置条件、用户动作、系统响应、预期结果和失败模式是什么？
- 哪个 `test_case_seed` 能让 QA 直接从该操作流派生测试用例？
- 当前是否有明显缺失的操作流？如果有，不能标记为 `product_ready`，只能继续 `product_shape`。

## Business Success Scenarios

These questions collect product input from business users. Do not ask the business user
about E2E frameworks, selectors, fixtures, APIs, test commands, or automation tools. First
extract any real scenario already present, then ask only the single missing question that
most changes the business outcome or product gate.

- 请讲一个真实案例：谁在什么业务状态下开始，要完成什么目标，最后什么业务状态才算真正成功？
- 这个成功流程的发起角色、参与角色和最终确认角色分别是谁？
- 开始这条流程前，哪些业务条件必须已经成立？
- 哪些输入值最能代表真实业务，而不是为了演示而准备的理想数据？
- 这个场景会经过 `workflow.steps` 中的哪些步骤？有没有跨角色交接或人工决策？
- 页面显示“成功”但业务实际上仍然失败，最可能是哪一种情况？
- 哪些结果绝对不可接受，例如重复单据、越权审批、错误写入、遗漏通知或错误业务状态？
- 如果发生资料缺失、重复提交、权限不足、外部系统超时或部分成功，业务上应该停在哪个状态、恢复到哪个状态，谁负责接管？
- 这是本期 `in_scope`、延期 `deferred`，还是明确 `out_of_scope`？优先级是 `critical`、`important` 还是 `optional`？
- 我已经把你的口述整理成结构化业务成功场景。业务目标、成功终态、不可接受结果和异常恢复是否准确？A. 准确并确认；B. 有一处需要修改；C. 场景不成立。

Before marking `product_ready` or later, check:

- 是否至少有一个本期关键场景？
- 每个本期场景是否有明确、非空的 `expected_business_outcome`？
- 每个本期场景是否由真实 business owner 确认，而不是由 agent、产品、QA 或工程代为确认？
- 是否把业务场景与通用 `workflow.canonical_workflow` 区分开，而不是只写一条抽象主流程？

## Delivery Risk Profile

Do not ask the user to choose R0-R3 before collecting facts. Extract every dimension
already present and ask only the single unresolved dimension most likely to raise the
risk floor.

- 第一版谁会使用？A. 只做隔离演示；B. 一个内部团队；C. 多个内部团队；D. 外部用户；E. 直接面向客户。
- 第一版可能读取、生成或记录的最高敏感数据是什么？A. 模拟；B. 公开；C. 内部；D. 机密；E. 受限。
- 系统对业务系统的操作是什么？A. 不操作；B. 只读；C. 可撤销写入；D. 不可撤销写入；E. 批量破坏性操作。
- 它需要什么集成或权限？A. 无；B. 已批准内部系统；C. 外部系统或提权；D. 生产特权。
- 如果结果错误，恢复到最后正确状态有多难？A. 容易；B. 中等；C. 困难；D. 不可恢复。
- 最坏的合理业务影响是什么？A. 演示失败；B. 低；C. 中；D. 高；E. 关键业务影响。
- 哪个维度给出了最高风险下限？是否存在试图用其他低风险维度把它平均掉的情况？
- R1-R3 分别需要哪些具体控制：脱敏、最小权限、只读、人工审批、幂等、审计、回滚、灰度或生产审批？
- 谁是 `owners.decision_owner`？是否确认六维事实、风险等级、理由和控制项？
- 如果用户直接要求 `engineering_ready`，六维是否全部解决、assessment 是否确认、Business Owner 场景是否确认、阶段和 next_stage 是否一致？任何一项缺失都必须拒绝该门禁。

## Friday Object Model

- 这个需求里的 Task 是什么真实工作实例？
- 最核心的 Artifact 是什么？它是否可打开、可审阅、可修改、可导出？
- Recipe 沉淀的是方法、rubric、流程和纠偏规则，还是事实材料？
- 哪些事实、历史、偏好、决策应该进入 Workspace Memory？
- Feedback/Comment 如何绑定 Artifact？
- 哪些反馈只留在 Workspace，哪些能成为 Recipe 或 Memory 更新候选？
- Room 是围绕哪个真实任务实例和 Artifact 展开的？
- Task -> Artifact -> Feedback -> Recipe/Memory 的闭环在哪里？

## Domain Pack

- 这个 Domain Pack 是给个人、团队、公司、客户私有使用，还是 owner 做好后选择分享出去？
- 这个 Pack 是 KA 团队定制生产，还是 SMB 用户在平台自助创建？
- 这个 Pack 的行业/场景边界是什么？它为什么不是单个 recipe、单个 prompt、一次性 demo？
- 这个 Pack 里至少包含哪些 Recipe、Memory、Connector、界面配置、权限和版本信息？
- Workspace 加载这个 Pack 后，会创建什么客户/团队实例？
- Workspace 里的本地修改如何进入待审队列？哪些必须经过发布流程才能更新主 Pack？
- Domain Pack、Recipe、Workspace 如何标版本？如何发布、升级、回滚？

## Knowledge And Memory Policy

- 哪些领域资料、模板、规则、案例、反馈应该成为 Memory 资产？
- 哪些只是单次客户/候选人/项目上下文，不能进入长期 Memory？
- 每类来源是否允许写入 Memory？
- 写入目标是 domain_pack_memory、workspace_memory、task_context_only、not_allowed，还是 unknown？
- 写入是否必须人工确认？
- 是否需要脱敏？
- 如果误写或效果变差，如何回滚？
- 原始证据和 Memory 摘要之间如何追溯？

## UI And Wireframe

- 这个需求有没有 UI、工作台、编辑器、审批页、看板或配置页？
- 用户第一屏应该看到什么对象列表？
- 点击一个对象后，详情页左边/右边分别看什么？
- 哪些 AI 建议可以直接采纳，哪些必须人工确认？
- 哪些操作必须放在主界面，哪些可以放在设置或后台？
- 需要生产哪些 SVG 线框图才能确认意图：列表页、详情页、配置页、输出编辑页、review 页？
- SVG 线框图文件应该保存在哪里，并如何在 `ui_requirements.wireframe_artifacts` 中引用？

## Capability Boundary

- 哪些事情只是资料存储和证据召回？
- 哪些事情需要 Agent 或 Recipe 做判断、整理和生成？
- 哪些事情必须由产品界面承载，例如编辑、发布、版本和权限？
- 哪些事情必须来自外部业务系统，例如实时价格、可售状态、CRM、核保或合规结果？
- 哪些事情必须由人或合规确认？
- 哪些事情第一版明确不拥有？

## Validation Plan

- 业务如何验收第一版？
- 产品如何验收第一版？
- 每个本期关键 `business_success_scenarios[].scenario_id` 是否都有对应的 `validation_plan.scenario_coverage`？
- QA 为每个业务场景补充了哪些边界、负向、权限、重复、外部失败和恢复用例？这些补充是否保持原业务成功终态不变？
- 哪些场景必须自动化，哪些允许人工验证，哪些不适用？理由和 owner 是什么？
- 要进入 `engineering_ready` 的场景是否已经 QA approved，且所有 required automation 至少为 planned？
- 现在只是验证方案设计 ready，还是验证执行 ready？
- 有没有黄金样例：客户画像 + 产品资料 + 标准答案？
- 失败样例有哪些：信息缺失、客户预算不匹配、产品互斥、地区限制、资料过期？
- 每个指标的 metric_id、definition、baseline、target、measurement_method、fixture_id、owner、pass_fail_rule 是什么？
- 每个测试资产的 asset_id、type、path_or_link、status、owner、version、redaction_status、linked_metrics 是什么？
- 什么错误算 blocking error？

## Implementation Mapping

- 这个能力在现有 Friday 代码里已有、部分已有、缺失、外部系统负责，还是未知？
- 现有代码或文档路径在哪里？
- 缺哪个 API、对象模型或产品能力？
- 哪个外部系统是权威源？
- 技术评审现在是 `engineering_gap_review`、`technical_design`，还是 `delivery_plan`？

## Technical Design Scoring

- 这个阶段是否已经进入技术方案设计，还是仍然只是技术缺口评审？
- 技术方案涉及哪些代码路径、接口、模块或架构文档？哪些已经读过？
- 还有哪些必须读但没读的代码路径？
- 基于源代码，技术方案和现有架构是否匹配？`architecture_fit` 打几分？
- 现有代码可以复用多少？`code_reuse` 打几分？
- 需要接多少外部系统？集成复杂度是否可控？`integration_complexity` 打几分？
- 数据、Memory scope、引用和写入规则是否清楚？`data_and_memory_fit` 打几分？
- 权限、隐私、审计、合规是否清楚？`security_and_compliance` 打几分？
- 是否能用 fixtures、metrics、regression 做自动或半自动验证？`testability` 打几分？
- 监控、fallback、support、rollback 是否清楚？`operability` 打几分？
- 最大交付风险是什么？`delivery_risk` 打几分？
- AI 工程师是否确认这个评分？如果不确认，分歧在哪里？

## Review Gates

- 谁必须在开发前确认业务范围？
- 产品必须确认哪些对象、UI、Artifact 和 scope？
- AI 工程必须确认哪些 Memory、Recipe、Artifact、权限和引用边界？
- QA 必须确认哪些样例、rubric、指标和阻断错误？
- 是否需要合规/法务审查？
- 工程启动前还有哪些条件必须满足？

## Virtual Review Panel

- 这个 spec 是否复杂到需要虚拟多角色评审，而不是只让一个 agent 总结？
- 哪些角色最可能指出盲点：PM、算法/ML、真实或代表性用户、领域专家、researcher、owner、QA、合规、销售/GTM、工程？
- 每个虚拟角色应该评审什么：商业证据、产品范围、算法可行性、用户操作流、领域正确性、合规边界、测试覆盖，还是工程落点？
- 哪个角色应该挑战哪个角色的假设？例如用户挑战 PM 的范围假设，算法挑战 owner 的效果预期，专家挑战 AI 生成内容的领域边界。
- 多角色互评后，哪些设计结论被保留、收窄、推迟或否决？
- 哪些虚拟评审结论必须写入 `review_gates.virtual_review_panel[].decision_impact`，并影响 `stage_gate`？
