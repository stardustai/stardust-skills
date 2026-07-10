# Spec Intake Skill

`spec-intake` 用于把业务的一句话需求，逐步转成公司统一的 Spec Driven JSON。它不是让业务一次性填写大表，而是通过互动式提问，先判断商业和 PMF 是否成立，再决定是否交给产品、继续补产品形态，或继续进入技术规格。

## 适用场景

- 业务、销售、解决方案同学提出一个客户需求、POC 机会、Domain Pack 想法或内部工具需求。
- 产品需要把模糊需求转成可评审、可排序、可交接的 spec。
- 产研需要在写代码前看清业务价值、范围边界、验收标准和技术责任边界。
- 团队需要用同一份 JSON 在业务、产品、AI 工程、工程、QA、DevOps 之间协作。

## 核心原则

1. 先判断业务和 PMF，不急着设计产品和技术。
2. 先确认基于哪个公司产品形态：Friday Agent、Domain Pack、Friday Memory、MorningStar、内部工具、独立产品或 demo。
3. 用 PMF 四因子判断 use case：客户愿意买、市场讲得清、技术价值、GTM 可复制。
4. 用“机会优先级指数”抑制范围膨胀：`机会优先级指数 = 商业价值 * 商业信号清晰度 / 产研投入量`。
5. 有 UI 就必须产出 SVG 线框图并让用户确认。
6. 如果是 Domain Pack，必须明确 Pack、Recipe、Memory、Workspace、版本、自学习和评测边界。
7. 任何进入技术的 spec 都必须能说明验收、测试、运维、数据治理和 review gates。

## 交互流程

```text
一句话需求
└── 业务理解
    ├── 复述需求
    ├── 确认产品形态
    └── 识别最关键未知项
        └── 业务验证
            ├── commercial_context：客户类型、买方、交付物、付费原因、下一步销售动作
            ├── pmf_validation：痛点证据、替代方案、PMF 状态、四因子评分、owner、证据链接、next action
            └── priority_decision：机会优先级指数、范围膨胀风险、收窄建议
                └── Handoff Gate
                    ├── 交给产品继续判断产品形态
                    └── 继续补产品形态
                        └── 产品形态
                            ├── product_context / spec_type
                            ├── business_objects / scope
                            ├── ui_requirements / wireframe
                            └── domain_pack_context（如适用）
                                └── Handoff Gate
                                    ├── 交给技术评审
                                    └── 继续补技术规格
                                        └── 技术规格
                                            ├── input_materials / workflow
                                            ├── capability_boundaries
                                            ├── evidence_requirements / data_governance
                                            └── acceptance / testing / operation / review_gates
```

## 主要产物

- `spec.json`：结构化 Spec Driven JSON。
- `wireframe.svg`：如果需求包含 UI，必须生成 SVG 线框图。
- `interview-notes.md`：可选，记录问答过程和关键决策。
- `missing_fields`：JSON 内部字段，用于说明为什么还不能进入下一阶段。

## 文件说明

```text
spec-intake/
├── SKILL.md - Codex/agent 实际执行该 skill 时读取的主指令。
├── README.md - 给人阅读的说明文档，也适合培训和推广。
├── references/
│   ├── spec-schema.json - Spec Driven JSON 的结构定义和枚举。
│   └── question-bank.md - 按阶段和字段组织的问题库。
├── scripts/
│   └── validate_spec.py - 轻量 JSON 校验脚本。
└── evals/
    └── evals.json - skill 行为回归测试用例。
```

## 校验方式

```bash
python3 /Users/derek/.agents/skills/spec-intake/scripts/validate_spec.py path/to/spec.json
```

校验会检查：

- JSON 基础结构是否符合 schema。
- `business_ready` 是否已经补齐商业、PMF 和机会优先级字段。
- `product_ready` 是否补齐产品形态、业务对象、范围和 UI/Domain Pack 必要字段。
- `engineering_ready` 是否补齐 owner、技术边界、验收测试、运维和 review gates。
- UI spec 是否包含已产出的 `.svg` 线框图。
- `批准 PoC` 是否具备 POC 启动门槛。
- `主线候选` 是否四个 PMF 因子都达到足够高的证据标准。

## 培训讲解建议

1. 先讲为什么需要 spec：避免口头需求、销售全都要、产研太晚介入。
2. 再讲三段式流程：业务验证、产品形态、技术规格。
3. 重点讲“机会优先级指数”：范围越大，产研投入越大，机会优先级越低。
4. 用一个真实需求现场跑一遍，让大家看到 agent 如何从一句话需求逐步问到 spec。
5. 最后用下面的文件夹树解释 JSON 结构。

---

## Spec JSON 文件夹树

这份文档用于向业务、产品、研发、QA 和 DevOps 解释 Spec Driven JSON 的层级关系。它不是发散图，而是按 JSON 文件夹树来读：越靠上越接近业务决策，越靠下越接近产品、技术、验收和交付。

读法：

- `object` 表示一组字段。
- `array` 表示列表。
- `string / number / boolean` 表示基础值。
- `可选` 表示 schema 允许存在但不是顶层必填。

```text
spec.json
├── spec_version: string - Spec 格式版本，用于 schema 升级和兼容判断。
├── spec_id: string - Spec 唯一编号，便于追踪、引用和版本管理。
├── title: string - 需求标题，用一句话说明这个 spec 要解决什么。
├── status: enum - 当前状态，例如 draft、spec_review、ready_for_engineering、launched。
├── priority: enum - 业务或产研优先级，例如 P0、P1、P2、P3、unknown。
├── intake_stage: enum - 当前访谈阶段：business_feasibility、product_shape、technical_spec。
├── readiness_label: enum - 当前可交付程度：not_ready、business_ready、product_ready、engineering_ready、review_required。
├── product_line: string|null (可选) - 所属产品线或业务线。
├── created_at: string (可选) - 创建时间。
├── updated_at: string (可选) - 最近更新时间。
│
├── commercial_context: object - 商业事实层：回答“客户类型是什么、谁买单、交付什么、为什么付钱、下一步商业动作是什么”。
│   ├── customer_segment: enum - 客户类型：KA、SMB、hybrid、internal、unknown、not_applicable。
│   ├── pack_level: enum - 场景层级：L2、L3、L2_to_L3、unknown、not_applicable。
│   ├── l2_scenario: string|null - 单点高价值业务场景。
│   ├── l3_aggregation_logic: string|null - 多个 L2 聚合成 L3 闭环的逻辑。
│   ├── target_buyer: string|null - 买单或推动预算的人。
│   ├── deliverable: string|null - 第一版具体交付物。
│   ├── why_customer_will_pay: string|null - 客户为什么愿意付钱。
│   ├── market_or_customer_pool: string|null - 目标客户池或市场范围。
│   ├── design_partners: array - 可共创或试点的客户、团队、个人。
│   ├── poc_path: string|null - POC 路径，包括周期、参与方、输入输出和验收方式。
│   ├── cooperation_model: string|null - 合作方式，例如付费试点、私有化项目、订阅、按 Pack 收费。
│   ├── pricing_hypothesis: string|null - 初步价格或包装假设。
│   ├── biggest_delivery_risk: string|null - 最大交付风险。
│   ├── next_sales_action: string|null - 下一步销售动作，必须可检查。
│   └── pmf_confidence: enum - PMF 信心：high、medium、low、unknown、not_applicable。
│
├── pmf_validation: object - PMF 判断层：回答“这个 use case 是否值得进入 PoC、产研评估或主线”。
│   ├── use_case_id: string|null - PMF use case 编号。
│   ├── source_entry: enum - 来源入口：销售线索池、市场/客户线索池 → 场景归类、internal。
│   ├── current_state: enum - PMF 状态：销售线索池、痛点诊断、产研评估、PoC / GTM 实验、复盘判定、主线 / 停损。
│   ├── target_icp: string|null - 目标 ICP，至少包含行业、规模、成熟度和预算类型。
│   ├── workflow: string|null - 可复用工作流，不是单个客户需求或技术模块。
│   ├── pain_evidence: array - 痛点证据列表。
│   ├── current_alternative: string|null - 当前替代方案，例如人工、GPT、RAG、SaaS、外包。
│   ├── buyer_language: string|null - 买方真实语言或可被销售复述的话术。
│   ├── competitive_gap: string|null - 当前替代方案为什么不够好。
│   ├── decision_chain: string|null - 谁感知痛点、谁评估、谁审批、谁付费、谁阻塞。
│   ├── paid_signal: string|null - 预算、付费 POC、采购阶段、deadline 或客户投入信号。
│   ├── four_factor_scores: object - PMF 四因子评分，1 到 5 分，每项都必须有证据。
│   │   ├── customer_willingness: object - 客户愿意买。
│   │   │   ├── score: number|null - 分数，1 表示证据弱，5 表示强重复证据加商业证明。
│   │   │   ├── evidence: array - 支撑该分数的证据。
│   │   │   └── notes: string|null - 评分备注。
│   │   ├── market_clarity: object - 市场讲得清。
│   │   ├── technical_value: object - 技术价值，包括 baseline、算法亮点、客户价值和可复用能力。
│   │   └── gtm_repeatability: object - GTM 可复制，包括 pitch、demo flow、案例素材、渠道和异议处理。
│   ├── overall_decision: enum - PMF 决策：继续诊断、进入产研评估、批准 PoC、主线候选、停止/归档。
│   ├── next_action: string|null - 下一步动作，必须能在一周内判断完成或未完成。
│   ├── owner: string|null - 当前推进 owner。
│   ├── evidence_links: array - 证据链接。没有链接不能批准 PoC 或主线候选。
│   ├── last_reviewed: string|null - 最近一次 PMF 评审日期。
│   └── poc_entry_criteria: object - POC 启动门槛。
│       ├── customer_evidence: string|null - 客户证据。
│       ├── paid_signal: string|null - 付费或客户投入信号。
│       ├── data_available: string|null - 数据、文档、系统权限或样例是否可得。
│       ├── baseline_defined: string|null - 当前 baseline，例如人工、GPT、RAG、SaaS、外包。
│       ├── acceptance_method: string|null - 验收人、验收方式、评分规则或指标。
│       └── timebox_and_resource_cap: string|null - 时间盒和资源上限。
│
├── priority_decision: object - 排序判断层：用机会优先级指数抑制“全都要”导致的范围膨胀。
│   ├── candidate_rank: integer|null - 候选项排序。
│   ├── recommendation: enum - 建议：top_8、backlog、reject、needs_more_evidence、not_applicable、unknown。
│   ├── business_value_score: number|null - 商业价值分数。
│   ├── commercial_signal_clarity_score: number|null - 商业信号清晰度分数。
│   ├── product_engineering_effort_score: number|null - 产研投入量分数。范围越大、集成越重、长期维护越复杂，分数越高。
│   ├── opportunity_priority_score: number|null - 机会优先级指数，越高越值得优先排。
│   ├── formula_name: enum - 固定为“机会优先级指数”。
│   ├── formula: enum - 机会优先级指数 = 商业价值 * 商业信号清晰度 / 产研投入量。
│   ├── scope_expansion_risk: enum - 范围膨胀风险：high、medium、low、unknown、not_applicable。
│   ├── scope_reduction_recommendation: string|null - 如何收窄第一版范围以提高优先级。
│   ├── reason: string|null - 排序理由。
│   ├── missing_evidence: array - 缺失证据。
│   └── decision_owner: string|null - 排序和取舍的决策人。
│
├── handoff_options: object - 交接决策：业务、产品、技术之间什么时候交接，还是继续补 spec。
│   ├── current_gate: enum - 当前 gate：business_to_product、product_to_technology、technology_to_delivery、continue_intake。
│   ├── available_next_actions: array - 可选下一步。
│   ├── selected_next_action: enum - 用户选择的下一步：handoff_to_product、continue_product_shape、handoff_to_technology、continue_technical_spec、stop。
│   ├── handoff_target: string|null - 交接对象。
│   └── handoff_notes: array - 交接说明。
│
├── product_context: object - 产品形态层：先判断基于公司哪个产品形态做。
│   ├── build_target: enum - friday_agent、domain_pack、friday_memory、morningstar、internal_tool、standalone_product、demo、unknown。
│   ├── company_product: string|null - 具体公司产品。
│   ├── product_assumptions: array - 产品假设。
│   └── product_open_questions: array - 产品待确认问题。
│
├── spec_type: enum - spec 类型：customer_poc、domain_pack、product_feature、internal_tool、data_project、automation、platform_capability。
│
├── owners: object - 责任人层。
│   ├── business_owner: string|null - 业务 owner。
│   ├── product_owner: string|null - 产品 owner。
│   ├── engineering_owner: string|null - 工程 owner。
│   ├── qa_owner: string|null - QA owner。
│   ├── devops_owner: string|null - DevOps owner。
│   ├── compliance_owner: string|null - 合规 owner。
│   └── decision_owner: string|null - 最终决策 owner。
│
├── business_context: object - 业务场景层：回答“谁在什么场景下怎么用，成功是什么”。
│   ├── user_scenario: object
│   │   ├── user_role: string|null - 用户角色。
│   │   ├── customer_type: string|null - 客户类型。
│   │   ├── business_scene: string|null - 业务场景。
│   │   ├── current_workflow: string|null - 当前流程。
│   │   └── target_workflow: string|null - 目标流程。
│   └── target_outcome: object
│       ├── user_success_result: string|null - 用户成功后的具体结果。
│       ├── business_result: string|null - 业务结果。
│       └── measurable_kpi: array - 可量化 KPI。
│
├── business_objects: object - 业务对象层：区分长期资产、一次性输入和生成产物。
│   ├── durable_assets: array - 长期资产，例如产品库、岗位画像、行业知识库。
│   ├── generated_artifacts: array - 每次生成的产物，例如方案草稿、报告、反馈总结。
│   ├── temporary_artifacts: array - 临时产物，例如中间草稿、一次性上传材料。
│   └── future_reusable_assets: array - 未来可沉淀为 Domain Pack、Recipe、Memory、测试集的资产。
│
├── spec_decomposition: object (可选) - 拆分建议层。
│   ├── current_spec_choice: string - 当前 spec 边界选择。
│   ├── why_not_split_now: string|null - 为什么暂时不拆。
│   └── recommended_followups: array - 后续可拆出的 spec。
│
├── scope: object - 范围边界层：明确做什么、不做什么、假设和开放问题。
│   ├── in_scope: array - 第一版必须做。
│   ├── out_of_scope: array - 第一版明确不做。
│   ├── non_goals: array - 非目标。
│   ├── delivery_boundary: string|null - 交付边界。
│   ├── assumptions: array - 已知假设。
│   └── open_questions: array - 未决问题。
│
├── ui_requirements: object - UI 和线框图层。只要有 UI，就必须产出 SVG 线框图并确认。
│   ├── has_ui: boolean - 是否有 UI。
│   ├── wireframe_required: boolean - 是否需要线框图。
│   ├── wireframe_status: enum - not_required、needed、drafted、reviewed、unknown。
│   ├── key_screens: array - 关键页面。
│   ├── wireframe_artifacts: array - SVG 线框图文件路径或链接。
│   ├── confirmation_method: string|null - 用户如何确认线框图。
│   └── open_questions: array - UI 待确认问题。
│
├── domain_pack_context: object - Domain Pack 层。只有 Domain Pack 场景需要重点展开，但结构始终存在。
│   ├── applicable: boolean - 当前 spec 是否适用 Domain Pack。
│   ├── pack_definition: string|null - Pack 的定义，不是单个 prompt、recipe 或文件夹。
│   ├── target_industry_or_scene: string|null - 目标行业或场景。
│   ├── pack_goal: string|null - Pack 目标。
│   ├── commercial_or_delivery_unit: string - Pack 作为商业或交付单元的定义。
│   ├── domain_workflow: string|null - 被包装的领域工作流。
│   ├── memory_assets: array - 应进入 Memory 的事实、规则、案例、偏好、历史决策。
│   ├── recipe_assets: array - 应进入 Recipe 的方法、流程、rubric、纠偏规则。
│   ├── connector_assets: array - 需要的外部系统连接。
│   ├── interface_configuration: array - 工作台或界面配置。
│   ├── permission_scope: array - 权限范围。
│   ├── non_memory_boundaries: array - 不应被长期记忆的内容边界。
│   ├── workspace_instance_policy: object - Workspace 实例策略。
│   │   ├── workspace_created_by: string|null - 谁创建 Workspace。
│   │   ├── workspace_lifecycle: array - Workspace 生命周期。
│   │   ├── room_granularity: string|null - Room 粒度。
│   │   ├── artifact_types: array - Artifact 类型。
│   │   ├── local_changes_policy: array - 本地修改策略。
│   │   └── master_pack_update_policy: array - 主 Pack 更新策略。
│   ├── first_recipe: object - 第一版 Recipe。
│   │   ├── name: string|null - Recipe 名称。
│   │   ├── goal: string|null - Recipe 目标。
│   │   ├── input: array - Recipe 输入。
│   │   ├── output: array - Recipe 输出。
│   │   ├── execution_logic: array - 执行逻辑。
│   │   ├── constraints: array - 约束。
│   │   ├── required_evidence: array - 必须引用的证据。
│   │   ├── human_review: array - 人工 review 节点。
│   │   └── owner: string|null - Recipe owner。
│   ├── iteration_loop: array - Pack / Recipe / Memory 的迭代闭环。
│   ├── self_learning_policy: array - 自学习策略，包括什么能自动学习、什么必须人工确认。
│   ├── versioning_policy: object - 版本策略。
│   │   ├── domain_pack_versioned: boolean - Domain Pack 是否版本化。
│   │   ├── recipe_versioned: boolean - Recipe 是否版本化。
│   │   ├── workspace_versioned: boolean - Workspace 是否版本化。
│   │   ├── memory_backup_or_rollback: array - Memory 备份或回滚策略。
│   │   ├── release_policy: array - 发布策略。
│   │   ├── upgrade_policy: array - 升级策略。
│   │   └── rollback_policy: array - 回滚策略。
│   ├── evaluation_assets: object - 评测资产。
│   │   ├── golden_tasks: array - 黄金任务。
│   │   ├── rubrics: array - 评分标准。
│   │   ├── failure_cases: array - 失败样例。
│   │   ├── acceptance_checklist: array - 验收清单。
│   │   └── regression_set: array - 回归集。
│   ├── marketplace_or_delivery: object - 交付或分享策略。Domain Pack 默认私有，不默认上 marketplace。
│   │   ├── offer_name: string|null - Offer 名称。
│   │   ├── target_buyers_or_users: array - 目标买方或用户。
│   │   ├── pricing_or_packaging_notes: array - 定价或包装说明。
│   │   ├── deployment_notes: array - 部署说明。
│   │   └── success_metrics: array - 成功指标。
│   └── workspace_design: object - 工作台设计。
│       ├── screens: array - 页面。
│       ├── artifacts: array - Artifact。
│       ├── controls: array - 操作控件。
│       └── open_questions: array - 工作台待确认问题。
│
├── input_materials: object - 输入材料层。
│   ├── durable_sources: array - 长期资料源。
│   ├── per_case_inputs: array - 每次任务输入。
│   ├── temporary_sources: array - 临时资料源。
│   ├── excluded_inputs: array - 明确不能进入系统或不能使用的输入。
│   └── update_frequency: string|null - 更新频率。
│
├── workflow: object - 工作流层。
│   ├── phases: array - 阶段列表。
│   ├── steps: array - 具体步骤列表。
│   │   └── item
│   │       ├── step_id: string - 步骤编号。
│   │       ├── phase: string - 所属阶段。
│   │       ├── actor: string - 执行角色。
│   │       ├── input: string - 输入。
│   │       ├── action: string - 动作。
│   │       ├── output: string - 输出。
│   │       ├── human_review_required: boolean - 是否需要人工 review。
│   │       └── failure_handling: string - 失败处理方式。
│   └── roles: array - 工作流角色。
│
├── capability_boundaries: object - 能力边界层，防止把 Memory、Agent、产品 UI、业务系统职责混在一起。
│   ├── memory_layer: array - Memory 层负责什么。
│   ├── agent_or_recipe_layer: array - Agent 或 Recipe 层负责什么。
│   ├── product_ui_layer: array - 产品 UI 层负责什么。
│   ├── external_business_systems: array - 外部业务系统负责什么。
│   ├── human_or_compliance_review: array - 人工或合规 review 负责什么。
│   └── explicitly_not_owned: array - 明确不负责的能力。
│
├── evidence_requirements: object - 证据要求层。
│   ├── must_trace: array - 必须追溯的结论或输出。
│   ├── source_granularity: array - 证据粒度要求。
│   └── unknown_or_uncertain_handling: array - 未知或不确定时如何处理。
│
├── data_governance: object - 数据治理层。
│   ├── sensitivity: array - 敏感信息类型。
│   ├── permission_model: array - 权限模型。
│   ├── versioning: array - 数据版本策略。
│   ├── retention: array - 数据保留策略。
│   └── audit_log: array - 审计日志要求。
│
├── acceptance_standards: object - 业务验收标准。
├── testing_standards: object - 测试标准，包括黄金样例、失败样例、回归集等。
├── operation_standards: object - 运营标准，包括监控、日志、回滚、人工兜底。
├── review_gates: object - 评审门禁，包括业务、产品、技术、QA、DevOps、合规。
│
├── product_requirements: object (可选) - 产品需求补充。
├── technical_requirements: object (可选) - 技术需求补充。
├── poc_metrics: object (可选) - POC 指标。
├── commercial_standards: object (可选) - 商业标准。
├── reuse_standards: object (可选) - 复用标准。
├── story_points: object (可选) - 工作量估算。
│
├── missing_fields: array - 缺失字段列表，用于说明为什么还不能进入下一阶段。
│   └── item
│       ├── field: string - 缺失字段路径。
│       ├── status: string - 缺失状态。
│       └── note: string - 补充说明。
├── decision_log: array (可选) - 决策记录。
└── change_log: array (可选) - 变更记录。
```

## 培训讲解顺序

```text
1. 先看业务验证
   ├── commercial_context：客户类型、买方、交付物、付费原因和销售动作是否清楚
   ├── pmf_validation：痛点证据、替代方案、PMF 证据是否足够，是否进入 PoC / 主线 / 停损
   └── priority_decision：机会优先级指数是否足够高，范围是否过大

2. 再看产品形态
   ├── product_context：基于 Friday Agent、Domain Pack、Memory、内部工具还是 demo
   ├── business_objects：长期资产、生成产物、临时材料分清楚
   ├── scope：第一版做什么和不做什么
   └── ui_requirements：如果有 UI，必须有 SVG 线框图

3. 如果是 Domain Pack，单独展开
   ├── Pack：商业和交付单元
   ├── Memory：事实、证据、历史、偏好
   ├── Recipe：方法论、流程、rubric、纠偏规则
   ├── Workspace：客户或团队运行实例
   └── Version / Evaluation：版本、评测、回滚、自学习边界

4. 最后看技术交付
   ├── input_materials：输入材料和更新频率
   ├── workflow：人、Agent、系统怎么协作
   ├── capability_boundaries：每一层负责什么
   ├── evidence_requirements：结论如何追溯
   ├── data_governance：权限、敏感信息、审计
   └── acceptance/testing/operation/review_gates：如何验收、测试、上线和运营
```
