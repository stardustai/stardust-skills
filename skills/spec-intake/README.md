# Spec Intake Skill

`spec-intake` 用于把业务的一句话需求，逐步转成公司统一的 Spec Driven JSON。它不是让业务一次性填写大表，而是通过互动式提问，先判断商业和 PMF 是否成立，再决定交给产品、继续补产品形态、进入技术缺口评审，还是继续到工程可执行规格。

## 核心原则

1. 先抽取，再提问：用户已经提供的信息直接写入 spec；已经明确的问题直接给结论并跳过。
2. 只追问会改变 stage gate、优先级、产品形态或技术准备度的缺口。
3. 先判断业务和 PMF，不急着设计产品和技术。
4. 先确认基于哪个公司产品形态：Friday Agent、Domain Pack、Friday Memory、MorningStar、内部工具、独立产品或 demo。
5. 用 PMF 四因子判断 use case：客户愿意买、市场讲得清、技术价值、GTM 可复制。
6. 用“机会优先级指数”抑制范围膨胀：`机会优先级指数 = 商业价值 * 商业信号清晰度 / 产研投入量`。
7. 市场验证阶段必须处理竞品对比：业务可提供；如果没有，spec agent 自动调研并给出对比矩阵和差异度评分让用户确认。
8. 产品论证阶段必须判断技术领先性和独特性：产品 owner 给出论述，spec agent 打分，产品 owner 确认。
9. 技术方案设计阶段必须读取源代码：spec agent 根据技术方案和代码事实打分，AI 工程师确认。
10. 用 `stage_gate` 控制接力，区分产品交接、技术缺口评审、PoC 设计、PoC 执行和工程排期。
11. 开场必须展示完整流程图，并用 Codex 进度工具或文本进度提示当前阶段。
12. 阶段切换必须先给退出总结并得到用户确认，不能静默从业务验证跳到产品论证。
13. 有 UI 的需求在 `product_ready` 或更后门禁前必须产出 SVG 线框图并让用户确认；业务验证/交接阶段可先标记为 `needed`。
14. 如果是 Domain Pack，必须明确 Workspace Memory、Task、Artifact、Recipe、Feedback/Comment、Room 的闭环。
15. Memory 写入、自学习、隐私、人工确认和回滚必须结构化。
16. 验收测试统一进入 `validation_plan`，区分 `poc_design_ready` 和 `poc_execution_ready`。
17. 业务端到端成功流程统一进入顶层 `business_success_scenarios`：业务定义真实流程和成功终态，产品或 spec agent 负责结构化，业务 owner 负责确认。
18. QA 和工程不得重写业务成功定义；它们通过 `validation_plan.scenario_coverage` 补充 QA 用例、自动化计划、Eval 资产和执行证据。
19. 交付风险是产品输入：先采集用户范围、数据敏感度、写入影响、集成与权限、可恢复性、业务影响六个事实，再按最高风险维度确定 R0-R3，由 decision owner 确认。
20. 产品阶段必须把业务目标细化为产品目标、业务指标、用户旅程和用户操作流，方便 QA 生成测试用例，也方便工程埋点和 loop engineering。

## 交互流程

原则：这个流程不是固定问卷。每一轮先把用户已经说清楚的内容映射到字段；能直接判断的就给出判断；只把缺失、冲突或会影响下一关的问题拿出来问。

开场要先展示完整流程，而不是直接进入提问。Mermaid 节点保持短文本，不在节点标签里写 `\n` 换行或长说明，也不要画回退虚线，避免客户端把图挤乱：

```mermaid
flowchart TD
  A["0. 入口分流"]
  B["1. 商业可行性"]
  C["2. 产品形态"]
  D["3. 技术缺口评审"]
  E["4. 技术方案"]
  F["5. PoC 设计"]
  G["6. PoC 执行"]
  H["7. 工程交付"]
  A --> B --> C --> D --> E --> F --> G --> H
```

简单说明：

- 入口分流：论证需求类型，先判断这是 Domain Pack、Friday Agent、Friday Memory、内部工具、独立产品还是 demo。
- 商业可行性：论证客户、买方、痛点、付费理由、竞品和证据，不急着设计产品。
- 产品形态：论证第一版工作流、范围、Artifact、UI 和对象模型。
- 技术缺口评审：论证现有能力和缺口，不代表可以排期。
- 技术方案：论证源码、架构方案、技术评分和交付风险，并由 AI 工程师确认。
- PoC 设计：论证样本、指标、验收方式和时间盒。
- PoC 执行：论证数据、owner、baseline 都齐了，才开始跑验证。
- 工程交付：论证 spec、验证、责任人、排期和验收都确认后，才进入实现计划。

回退规则用文字说明，不画进图里：

- 证据不足：停留在 `business_feasibility`。
- 范围不清：停留在 `product_shape`。
- 技术缺口未解决：回到 `product_shape`。
- 技术方案未确认：停留在 `technical_spec`。

如果运行环境提供 Codex 进度工具，应在开场调用进度工具；否则每轮回答都要给出一句阶段提示，例如：

```text
当前阶段：business_feasibility；尚未进入 product_shape。
```

阶段切换必须先问用户确认，例如：

```text
我建议从 business_feasibility 切到 product_shape。已确认 X；仍未确认 Y；因此只允许产品收敛，不允许 PoC 或工程。是否确认结束业务验证？
```

```text
一句话需求
└── 产品形态判断
    └── 业务验证 opportunity_assessment
        ├── commercial_context：客户、买方、付费原因、POC、风险、销售动作
        ├── pmf_validation：PMF 状态、四因子评分、替代方案、买方语言、决策链
        ├── priority_decision：机会优先级指数、范围膨胀风险、收窄建议
        ├── competitive_research：竞品/替代方案矩阵、重叠度、差异度、用户确认
        ├── evidence_registry：证据等级，区分假设和真实证据
        ├── design_partner_registry：设计伙伴、预算 owner、review 人、数据可用性
        └── minimum_paid_artifact：第一版最小可付费交付物
            └── stage_gate
                ├── 继续取证
                ├── 交给产品
                ├── 继续补产品形态
                ├── 请求技术缺口评审
                ├── PoC 设计 ready
                ├── PoC 执行 ready
                └── 工程 ready
```

## 主要产物

- `spec.json`：结构化 Spec Driven JSON。
- `wireframe.svg`：如果需求包含 UI，产品形态确认前必须生成 SVG 线框图；业务验证阶段可先记录为待补产物。
- `interview-notes.md`：可选，记录问答过程和关键决策。
- `missing_fields`：JSON 内部字段，用于说明为什么还不能进入下一阶段。

## 文件说明

```text
spec-intake/
├── SKILL.md - Codex/agent 实际执行该 skill 时读取的主指令。
├── README.md - 给人阅读的说明文档，也适合培训和推广。
├── references/
│   ├── spec-schema.json - Spec Driven JSON v1.6 的结构定义和枚举。
│   ├── business-success-scenarios.md - 业务成功场景、QA/工程映射和阶段门禁的详细规范。
│   ├── delivery-risk-profile.md - 六维风险输入、R0-R3、控制项和产品门禁的详细规范。
│   └── question-bank.md - 按阶段和字段组织的问题库。
├── scripts/
│   └── validate_spec.py - JSON 校验脚本，包含 stage gate、证据、UI、PoC、Memory 规则。
├── examples/
│   ├── insurance-broker-proposal.spec.json - 保险经纪人 Domain Pack 样例。
│   └── insurance-broker-workspace-wireframe.svg - 对应 SVG 线框图。
└── evals/
    └── evals.json - skill 行为回归测试用例。
```

## 校验方式

```bash
python3 /Users/derek/.agents/skills/spec-intake/scripts/validate_spec.py path/to/spec.json
```

校验会检查：

- JSON 基础结构是否符合 schema。
- `stage_gate` 是否和证据状态、优先级状态匹配。
- 跨阶段决策是否包含 `stage_gate.stage_exit_check` 和用户确认。
- `needs_more_evidence` 是否被错误推进到工程执行。
- PMF 分数 >= 3 是否有非假设证据支撑。
- 市场验证是否包含业务提供或 agent 调研的竞品矩阵、重叠度、差异度和用户确认。
- 产品论证是否包含技术领先性/独特性论述、agent 评分和产品 owner 确认。
- 产品论证是否包含业务先定义、产品再细化的产品目标和业务指标。
- 产品论证是否包含覆盖主要角色、正常路径、异常路径和关键操作的 user journey / operation flows。
- UI spec 是否包含存在的 `.svg` 线框图，并在 product-ready 之后为 reviewed。
- Friday / Domain Pack 是否声明 Task -> Artifact -> Feedback -> Recipe/Memory 的闭环。
- Memory 写入是否有人工确认、scope、脱敏和回滚。
- `validation_plan` 是否区分 PoC 设计 ready 和 PoC 执行 ready。
- `product_ready` 或更后阶段是否至少有一个由业务 owner 确认的关键 `business_success_scenarios`，且所有本期场景都有明确业务终态。
- `validation_plan.scenario_coverage` 是否完整映射业务场景、QA 用例、自动化要求和 Eval 资产，并且没有改写业务预期结果。
- `delivery_risk_profile` 的六个维度是否已解决，R0-R3 是否不低于最高维度下限，R1-R3 是否有控制项，并由 `owners.decision_owner` 确认。
- 技术方案设计是否完成源码读取、技术评分维度和 AI 工程师确认。
- `engineering_ready` 是否没有缺失字段、没有 missing/unknown implementation capabilities。

## 顶层结构在流程中的作用

这些结构不是为了“填表完整”，而是为了让不同角色在正确阶段做正确决策。可以把它理解为一条接力线：业务先证明值得做，产品再定义做成什么，技术只先判断缺口，QA 再判断能否验收，最后才可能进入工程排期。

| 顶层结构 | 流程阶段 | 主要 owner | 作用 | 不应该承担的事 |
| --- | --- | --- | --- | --- |
| `spec_version / spec_id / title / status / priority` | 全流程 | PMF owner / 产品 owner | 让 spec 可追踪、可排序、可升级。 | 不表达需求内容和 gate 结论。 |
| `stage_gate` | 每次阶段切换 | PMF owner / 接收方 owner | 决定当前能交给谁、允许做什么、禁止做什么。它是防止“证据不足却进入工程”的总闸门。 | 不替代商业证据、产品定义或测试方案。 |
| `opportunity_assessment` | 业务验证 | 业务 owner / PMF owner / PMM | 判断这个 use case 是否值得产品注意。旧的 `commercial_context`、`pmf_validation`、`priority_decision` 都收敛在这里。 | 不描述 UI、技术实现或测试细节。 |
| `opportunity_assessment.competitive_research` | 市场验证 | 业务 owner / 解决方案 / spec agent | 记录业务提供或 agent 调研的竞品矩阵，给出重叠度、差异度和确认状态。 | 不替代 PMF 判断；它只说明外部参照和差异。 |
| `product_context` | 产品形态判断 | 产品 owner | 说明基于哪个公司产品形态做、spec 类型、产品目标、业务指标，以及产品领先性/独特性论证。`spec_type` 已合并到这里，因为它本质上是产品分类。 | 不判断客户是否愿意付钱；那属于 `opportunity_assessment`。 |
| `product_context.product_goals` | 产品形态判断 | 业务 owner / 产品 owner | 业务先定义希望达成什么，产品再细化为第一版必须支持的目标用户、目标结果、指标引用和 loop engineering 信号。 | 不替代 `business_success_scenarios` 的真实业务旅程，也不替代 `validation_plan.metrics` 的测试口径。 |
| `product_context.business_metrics` | 产品形态判断 | 业务 owner / 产品 owner | 把业务语言里的成功指标转成产品可测的事件、状态、质量或行为，并说明 baseline、target、测量方法、复盘节奏和工程改进用途。 | 不直接写测试用例；测试映射在 `validation_plan`。 |
| `product_context.technical_leadership` | 产品论证 | 产品 owner / spec agent | 要求产品 owner 给出领先性证明或论述，spec agent 给出 1-5 分，产品 owner 确认。 | 不等于技术方案可做；代码事实和方案可行性在 `implementation_mapping`。 |
| `owners` | 全流程 | PMF owner | 明确业务、产品、工程、QA、DevOps、合规和最终决策责任人。 | 不表达审批规则；审批规则在 `review_gates`。 |
| `business_context` | 产品形态判断 | 产品 owner / 业务 owner | 解释用户是谁、现在怎么做、成功后业务结果是什么。 | 不重复目标工作流细节；目标工作流统一放在 `workflow.canonical_workflow`。 |
| `scope` | 产品形态判断 | 产品 owner | 定义第一版做什么、不做什么、为什么不做。它控制范围膨胀。 | 不记录商业优先级公式；公式在 `opportunity_assessment.priority_decision`。 |
| `workflow` | 产品形态到技术评审 | 产品 owner / AI 工程 owner | 定义唯一 canonical workflow、结构化步骤、用户旅程和用户操作流，是产品、AI 工程和 QA 对齐的主线。 | 不承载 PMF 证据，也不重复 `business_context` 的用户背景。 |
| `workflow.user_journeys` | 产品形态判断 | 产品 owner | 覆盖主要角色的真实使用旅程，包括入口、正常路径、异常路径、退出条件和关联操作流。 | 不写成抽象流程口号；也不替代业务 owner 确认的成功终态。 |
| `workflow.user_operation_flows` | 产品形态判断 / QA 输入 | 产品 owner / QA owner | 把每个 journey 拆成可操作流程，记录触发、前置条件、用户动作、系统响应、预期结果、失败模式和测试种子。 | 不指定具体自动化框架或 selector；工程测试细节后续再定。 |
| `business_success_scenarios` | 产品形态 | 业务 owner；产品 owner / spec agent 负责结构化 | 记录真实业务旅程、前置条件、业务目标、关键步骤、成功终态、不可接受结果、异常恢复和业务确认。 | 不记录测试框架、API、selector、fixture 路径、命令或工程实现。 |
| `delivery_risk_profile` | 产品形态 | 产品 owner / decision owner | 用六个事实维度确定最低 R0-R3、理由、控制项和确认状态，约束后续产品边界和工程深度。 | 不按平均值降级，不等到编码后再补风险，也不把风险判断交给工程自行决定。 |
| `friday_object_model` | Domain Pack / Friday 产品形态判断 | 产品 owner / AI 工程 owner | 把 Friday 的 Workspace Memory、Task、Artifact、Recipe、Feedback/Comment、Room 建成一等对象，避免退化成“资料库 + prompt”。 | 不定义具体代码路径；代码落点在 `implementation_mapping`。 |
| `knowledge_and_memory_policy` | Domain Pack / Memory 设计 | AI 工程 owner / 合规 owner | 定义什么能进 Memory、什么不能进、如何人工确认、脱敏、回滚。 | 不描述最终 UI；UI 在 `ui_requirements`。 |
| `ui_requirements` | 产品形态判断 | 产品 owner / 设计 owner | 判断是否有 UI、需要哪些页面、SVG 线框图是否已确认。 | 不替代产品需求；它只确认界面意图和对象关系。 |
| `capability_boundaries` | 技术缺口评审 | AI 工程 owner / 产品 owner | 切清 Memory、Agent/Recipe、产品 UI、外部系统、人和合规分别负责什么。 | 不声明现有代码是否支持；现有支持度在 `implementation_mapping`。 |
| `validation_plan` | QA / PoC 设计 | QA owner / 产品 owner | 统一管理验收、指标、测试资产和 `scenario_coverage`，把业务成功场景映射为 QA 与工程验证，并区分 PoC 设计 ready 和执行 ready。 | 不重新定义业务成功终态，也不做运维监控；监控在 `operation_standards`。 |
| `operation_standards` | PoC 执行 / 交付准备 | DevOps owner / 工程 owner | 定义监控、兜底、支持和审计事件。 | 不定义 pass/fail 规则；规则在 `validation_plan.metrics`。 |
| `implementation_mapping` | 技术缺口评审 / 技术设计 / 工程准备 | AI 工程 owner / 工程 owner | 标明每个关键能力是已有、部分已有、缺失、外部系统负责还是未知，并给本地代码路径或缺口。技术设计阶段还必须记录源码读取和 AI 评分。 | 不代表可以排期；只有 `stage_gate` 到 `engineering_ready` 才能进入工程计划。 |
| `review_gates` | 阶段评审 | 各 owner | 记录业务、产品、AI 工程、QA、合规、工程启动前分别要 review 什么。 | 不替代 `stage_gate` 的当前决策。 |
| `missing_fields` | 全流程 | 当前推进 owner | 显式记录缺失字段和阻塞原因，避免 agent 编造事实。 | 不应该长期堆积；进入 `engineering_ready` 前必须清空。 |

## 字段合并原则

这次优化后，保留的合并关系如下：

- 旧 `commercial_context`、`pmf_validation`、`priority_decision` 合并到 `opportunity_assessment` 下，但保留原名字作为子结构，方便业务、PMM 和产研沟通。
- `competitive_research` 放在 `opportunity_assessment` 下，因为它属于市场验证，不属于产品设计或技术设计。
- 旧顶层 `spec_type` 合并到 `product_context.spec_type`，因为它和 `build_target` 都是在回答“这到底基于什么产品形态做”。
- `technical_leadership` 放在 `product_context` 下，因为它是产品 owner 对产品独特性的论证，不是工程实现方案。
- `product_goals` 和 `business_metrics` 放在 `product_context` 下，因为它们是产品 owner 对业务目标的细化，不是市场判断，也不是 QA 测试细节。
- `source_code_review` 和 `technical_design_assessment` 放在 `implementation_mapping` 下，因为它们必须基于真实代码和技术方案判断。
- 旧 `business_context.user_scenario.target_workflow` 删除，目标流程统一使用 `workflow.canonical_workflow`，避免同一工作流被写两遍。
- `workflow.canonical_workflow` 只描述通用主流程；具体、可确认的真实业务旅程单独放入 `business_success_scenarios`，避免把抽象流程当作可验收场景。
- `workflow.user_journeys` 和 `workflow.user_operation_flows` 不合并到 `business_success_scenarios`：前者是产品层操作覆盖，后者是业务 owner 确认的业务成功终态。
- QA 和工程对业务场景的覆盖关系放入 `validation_plan.scenario_coverage`；场景的业务终态仍以 `business_success_scenarios` 为准。
- `acceptance_standards`、`testing_standards`、`poc_metrics`、`evaluation_assets` 合并到 `validation_plan`，避免 QA 需要在多个地方找验收标准。
- `input_materials`、`evidence_requirements`、`data_governance`、Memory 自学习策略合并到 `knowledge_and_memory_policy`，因为它们都在回答“材料、证据和记忆如何被治理”。
- `capability_boundaries` 和 `implementation_mapping` 不合并：前者讲职责边界，后者讲现有代码/能力落点。合并会让产品边界和工程事实混在一起。

## Spec JSON 文件夹树

```text
spec.json
├── spec_version: string - Spec 格式版本，用于 schema 升级和兼容判断。
├── spec_id: string - Spec 唯一编号，便于追踪、引用和版本管理。
├── title: string - 需求标题，用一句话说明这个 spec 要解决什么。
├── status: enum - 当前状态，例如 draft、spec_review、poc_design、ready_for_engineering。
├── priority: enum - 业务或产研优先级，例如 P0、P1、P2、P3、unknown。
│
├── stage_gate: object - 当前能走到哪一关，以及明确不能走到哪一关。
│   ├── current_stage: enum - 当前阶段：业务验证、产品形态、技术缺口评审、PoC 设计、PoC 执行、工程交付。
│   ├── readiness_label: enum - 当前准备度：not_ready、business_ready、product_ready、engineering_gap_review_ready、poc_design_ready、poc_execution_ready、engineering_ready、review_required。
│   ├── decision: enum - 本次交接决策，例如继续取证、交给产品、请求技术缺口评审、工程 ready。
│   ├── allowed_next_actions: array - 当前允许做的下一步。
│   ├── blocked_next_actions: array - 当前明确禁止做的下一步。
│   ├── blockers: array - 阻塞进入下一关的问题。
│   ├── required_owner: string|null - 下一关必须负责的人。
│   └── stage_exit_check: object - 跨阶段切换前的退出总结、确认问题、确认人和下一阶段。
│
├── opportunity_assessment: object - 商业可行性、PMF 和优先级判断。
│   ├── commercial_context: object - 客户类型、L2/L3、买方、客户池、付费原因、POC 路径、价格假设、交付风险、销售动作。
│   ├── pmf_validation: object - use case、PMF 状态、工作流、痛点证据、替代方案、买方语言、决策链、付费信号、四因子评分。
│   ├── priority_decision: object - 机会优先级指数、范围膨胀风险、收窄建议、缺失证据。
│   ├── competitive_research: object - 竞品调研状态、业务是否提供、调研 query、对比矩阵、差异度评分、用户确认。
│   ├── evidence_registry: array - 证据登记表，每条证据有类型、等级、来源、是否假设、关联字段。
│   ├── design_partner_registry: array - 设计伙伴、预算 owner、review 人、承诺资源和数据可用性。
│   └── minimum_paid_artifact: object - 第一版客户愿意付费或投入资源验证的最小交付物。
│
├── product_context: object - 产品形态和 spec 类型，用于决定是 Friday Agent、Domain Pack、Friday Memory、内部工具、独立产品还是 demo。
│   ├── build_target: enum - 基于哪个公司产品形态做。
│   ├── spec_type: enum - spec 类型：customer_poc、domain_pack、product_feature、internal_tool、data_project、automation、platform_capability。
│   ├── company_product: string|null - 具体公司产品。
│   ├── product_goals: array - 业务 owner 先定义、产品 owner 再细化的产品目标，包含指标引用和 loop engineering 信号。
│   ├── business_metrics: array - 业务指标的产品化定义，包含 baseline、target、测量方法、复盘节奏和工程改进用途。
│   ├── product_assumptions: array - 产品假设。
│   ├── technical_leadership: object - 技术领先性/独特性论述、证据、agent 评分、产品 owner 确认。
│   └── product_open_questions: array - 产品待确认问题。
├── product_line: string|null - 所属产品线，可选。
├── created_at: string - 创建时间，可选。
├── updated_at: string - 更新时间，可选。
├── owners: object - 业务、产品、工程、QA、DevOps、合规和决策 owner。
│
├── business_context: object - 用户、场景、当前流程和成功结果；目标流程不在这里重复，统一放在 workflow.canonical_workflow。
├── scope: object - 第一版范围、明确不做、非目标、交付边界、假设和开放问题。
├── workflow: object - 唯一 canonical workflow 和结构化步骤。
│   ├── canonical_workflow: string|null - 标准工作流一句话。
│   ├── phases: array - 阶段列表。
│   ├── steps: array - 每步包含 actor、input、action、output、human_review_required、failure_handling。
│   ├── roles: array - 参与角色。
│   ├── user_journeys: array - 产品层用户旅程，覆盖入口、正常路径、异常路径、退出条件和关联操作流。
│   └── user_operation_flows: array - 用户操作流，覆盖触发、前置条件、用户动作、系统响应、预期结果、失败模式和测试种子。
│
├── business_success_scenarios: array - 由业务提供并确认的具体端到端成功场景。
│   └── item: object - scenario_id、title、scope_status、priority、business_owner、user_role、business_goal、preconditions、trigger、workflow_step_refs、expected_business_outcome、expected_final_state、success_signals、business_invariants、unacceptable_outcomes、alternate_paths、exception_paths、recovery_expectations、confirmation。
│
├── delivery_risk_profile: object - 产品阶段确认的交付风险合同。
│   ├── risk_tier: enum - R0、R1、R2、R3 或尚未解决时的 unknown；不得低于六维最高风险下限。
│   ├── rationale: string|null - 风险等级如何由真实产品事实得出。
│   ├── dimensions: object - user_exposure、data_sensitivity、write_impact、integrations_and_permissions、reversibility、business_impact。
│   ├── required_controls: array - 下游交付必须落实的权限、数据、审批、审计、回滚和发布控制。
│   └── assessment: object - status、assessed_by、confirmed_by、confirmed_at；product-ready 后由 decision owner 确认。
│
├── friday_object_model: object - Friday 核心对象模型。
│   ├── workspace_memory: array - 可复用记忆和上下文资产。
│   ├── tasks: array - 用户真实任务实例。
│   ├── artifacts: array - 可审阅、可修改、可交付的输出。
│   ├── recipes: array - 方法论、rubric、流程和纠偏规则。
│   ├── feedback_comments: array - 人的评论和反馈，绑定 Artifact。
│   ├── rooms: array - 围绕一个任务和 Artifact 的协作空间。
│   └── object_relationships: array - Task -> Artifact -> Feedback -> Recipe/Memory 的闭环。
│
├── knowledge_and_memory_policy: object - 输入材料、证据追溯、Memory 写入、自学习、隐私和回滚。
│   ├── input_materials: object - durable_sources、per_case_inputs、temporary_sources、excluded_inputs、update_frequency。
│   ├── source_traceability: array - 哪些结论必须能追溯到哪些来源。
│   ├── memory_write_rules: array - source_type、write_allowed、requires_human_approval、target_scope、redaction_required、rollback_method。
│   ├── non_memory_boundaries: array - 明确不能进入长期 Memory 的内容。
│   ├── privacy_and_redaction: array - 隐私和脱敏规则。
│   └── rollback_policy: array - Recipe、Memory、Pack 更新如何回滚。
│
├── ui_requirements: object - UI 是否存在、是否需要 SVG、线框图状态、关键页面和确认方式。
├── capability_boundaries: object - Memory、Agent/Recipe、产品 UI、外部系统、人和合规分别负责什么。
│
├── validation_plan: object - 业务验收、产品验收、PoC 准备度、指标和测试资产。
│   ├── business_acceptance: array - 业务验收标准。
│   ├── product_acceptance: array - 产品验收标准。
│   ├── scenario_coverage: array - scenario_id 对应的 QA 状态、QA 用例、自动化要求与计划、自动化测试引用、Eval 资产和 owner。
│   ├── poc_design_ready: object - PoC 设计是否 ready。
│   ├── poc_execution_ready: object - PoC 执行是否 ready。
│   ├── metrics: array - metric_id、definition、baseline、target、measurement_method、fixture_id、owner、pass_fail_rule。
│   └── evaluation_assets: array - asset_id、type、path_or_link、status、owner、version、redaction_status、linked_metrics。
│
├── operation_standards: object - 监控、兜底、支持、审计事件。
├── implementation_mapping: object - 技术评审类型、能力落点、源码读取和技术方案评分。
│   ├── engineering_review_type: enum - not_started、engineering_gap_review、technical_design、delivery_plan、unknown。
│   ├── capabilities: array - 每个关键能力是 existing、partial、missing、external 还是 unknown。
│   ├── source_code_review: object - 是否必须读代码、读取状态、已读路径、代码事实摘要、未读必需路径。
│   └── technical_design_assessment: object - 技术方案摘要、AI 总分、分维度评分、评分理由、AI 工程师确认。
├── review_gates: object - 业务、产品、AI 工程、QA、合规和工程启动前必须 review 的内容。
├── missing_fields: array - 当前缺失字段、状态和说明。
├── decision_log: array - 可选，关键决策记录。
└── change_log: array - 可选，版本变更记录。
```

## 使用建议

培训时先讲四个 gate：

1. 商业是否值得继续。
2. 产品形态是否清楚。
3. 技术只是做缺口评审，还是已经能排期。
4. PoC 是设计 ready，还是执行 ready。

最容易误用的是把 `engineering_gap_review_ready` 当成 `engineering_ready`。前者表示“可以让技术看缺口”，后者才表示“可以进入工程实现计划”。

另一个常见误用是让 QA 或工程自己定义“端到端成功”。正确关系是：

```text
业务确认的 business_success_scenarios
  -> validation_plan.scenario_coverage
  -> QA 用例
  -> 自动化 E2E 或其他验证
  -> 执行证据
```

业务不需要懂测试工具，只需要确认真实流程、业务终态、不可接受结果和失败后的业务状态。QA 负责专业化覆盖，工程负责自动化与可观测性。

产品阶段需要再向前推进一步：把业务语言里的成功目标变成产品目标、业务指标、用户旅程和操作流。这样 QA 后续可以直接从 `workflow.user_operation_flows[].test_case_seed` 推导测试用例，工程也能从 `product_context.product_goals[].loop_engineering_signal` 和 `product_context.business_metrics[].loop_engineering_use` 判断哪些数据要记录、哪些结果要进入下一轮改进。

风险也不要求业务先猜 R0-R3。业务和产品提供六个事实维度，Spec Agent 计算最低等级并解释原因，Decision Owner 确认。任何一个维度达到更高风险，都不能被其他低风险维度“平均掉”；产品边界变化后必须重新评估。
