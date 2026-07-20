# 公司 Vibe Coding 总控 Skill 设计

状态：v1.0 实现基线，已记录截至 2026-07-20 的确认结论并获准实施。

详细执行标准采用独立文档维护。本文件只保存总体设计和已确认决策；详细标准索引见
[`company-vibe-coding/README.md`](company-vibe-coding/README.md)。当摘要与独立标准
冲突时，以较新的已确认独立标准为准，并同步修订本文件。

## 1. 目标

本项目交付一个符合 Agent Skills 格式的公司级总控 Skill。它以 `spec-intake`
产出的 `engineering_ready` Spec 为输入，自动编排项目初始化、架构治理、计划、
编码、测试、Eval、Review、Git 交付和可选部署，把 Spec 转换为稳定、可测试、
可维护、可恢复、可接管的代码。

目标用户包括技术和非技术员工。员工不需要自行理解或调用 TDD、代码 Review、
系统化排障、Subagent、Git 门禁和部署流程；总控 Skill 自动选择正确方法。只有
涉及产品行为、业务目标、架构变更、数据权限、成本、风险或计划外重构时，才暂停
并向用户提供选择题。

## 2. 核心定位

`spec-intake` 和公司 Vibe Coding Skill 的职责严格分开：

```text
spec-intake
  业务需求 -> 业务确认的成功场景 -> stage-gated spec.json -> engineering_ready

company-vibe-coding
  engineering_ready spec.json -> 稳定代码 -> Git 交付 -> 可选部署
```

正式编码必须同时遵守三个事实源：

1. Spec 决定做什么。AI 不得擅自补需求、修改业务规则或扩大范围。
2. 真实仓库决定如何接入。AI 必须读取现有代码、架构、依赖、测试和运行方式，
   不得建立平行架构。
3. 测试与 Eval 决定是否完成。AI 自述、页面截图或“能够运行”不能代替验证证据。

只有 `stage_gate.readiness_label=engineering_ready` 且
`stage_gate.decision=ready_for_engineering` 的 Spec 可以进入正式编码。其他状态只能
补 Spec、做技术缺口评审或制作使用模拟数据的隔离原型。

### 2.1 业务成功场景是编码输入合同

`spec-intake` v1.5 必须把业务定义的真实端到端成功流程写入顶层
`business_success_scenarios`。这里记录角色、业务目标、前置条件、触发条件、关联
工作流步骤、成功后的业务终态、可观测成功信号、业务不变量、不可接受结果、异常和恢复路径，
并由 Business Owner 确认。责任模型固定为：业务主导成功流程，Skill 负责结构化引导与
门禁，QA 补齐专业覆盖，工程负责自动化实现和可重复执行证据；后续角色不能擅自改变
业务定义的成功终态。

业务人员不负责选择 E2E 框架、编写测试代码或定义技术环境。Product 或 Spec Agent
负责把业务口述结构化并回显确认；QA 通过 `validation_plan.scenario_coverage` 补充
边界、负向、权限、重复、外部失败和恢复用例；工程再选择自动化工具、环境、Fixture、
命令、可观测信号和证据路径。QA 和工程只能建立覆盖关系，不能自行改变业务成功终态。

```text
business_success_scenarios
  -> validation_plan.scenario_coverage
  -> QA cases
  -> automated E2E / integration / other verification
  -> fresh execution evidence
```

`product_ready` 或更后门禁至少需要一个本期关键业务成功场景，且所有本期场景均已由
Business Owner 确认。进入 `engineering_ready` 前，每个本期关键场景必须有 QA 批准的
覆盖映射，自动化要求已经确定，所有要求自动化的关键场景至少已有实施计划。此时不要求
测试已经通过；测试通过是编码后的交付门禁。

以上接口已在 `spec-intake` v1.5 的 Schema、Validator、Example 和单元测试中落地。
Business Owner 确认还必须满足：`confirmer_role=business_owner`，确认人同时匹配场景与
顶层 Business Owner，确认版本匹配 `spec_version`，确认时间为有效 ISO 日期。

## 3. 风险自适应

所有项目走同一条开发主干，但工程深度随风险变化。

`spec-intake` v1.5 新增能够直接驱动编码门禁的统一风险输入
`delivery_risk_profile`，至少覆盖：

- 用户范围；
- 数据敏感度；
- 系统操作及写入破坏性；
- 权限和外部集成；
- 可恢复性；
- 业务影响。

最终风险等级取最危险维度，不取平均值：

| 等级 | 定义 | 开发边界 |
| --- | --- | --- |
| R0 | 隔离原型 | 模拟数据；可简化 TDD；不可发布 |
| R1 | 低风险内部应用 | 完整业务测试、基础 Review、可恢复交付 |
| R2 | 真实数据、系统写入或重要流程 | 完整测试、技术 Review、运行与回滚方案 |
| R3 | 客户、高敏数据、财务、人事、法务或关键基础设施 | 工程团队主导，执行最高门禁 |

六维字段、R0-R3 下限、Decision Owner 确认、控制项和 Product-ready 门禁已经在
`spec-intake` v1.5 的 Schema、Validator、Example 和单元测试中落地；总控 Skill
直接消费该风险合同，不在编码阶段重新猜测或降低等级。

## 4. 项目文件规范

项目采用 Superpowers 的 Spec 和 Plan 路径：

```text
project/
├── README.md
├── PROJECT.yaml
├── docs/
│   ├── superpowers/
│   │   ├── specs/
│   │   │   ├── YYYY-MM-DD-<topic>-spec.json
│   │   │   └── YYYY-MM-DD-<topic>-design.md
│   │   └── plans/
│   │       └── YYYY-MM-DD-<topic>.md
│   ├── business-goal.md
│   ├── system-architecture.md
│   ├── algorithm-design.md
│   ├── runtime-constraints.md
│   ├── test-plan.md
│   ├── traceability.md
│   ├── eval-plan.md
│   ├── runbook.md
│   ├── technical-debt-register.md
│   ├── agent-rules-audit.md
│   └── qa/
│       ├── 01-normalized-spec.md
│       ├── 02-test-design.md
│       └── 03-testcases.md
├── evals/
├── src/
└── tests/
```

文件职责：

- `README.md` 是员工和接管者入口，说明项目目标、状态、启动、测试、求助和文档
  导航。
- `PROJECT.yaml` 是机器可读状态，记录 Remote URL、当前 Spec/Design/Plan、风险、
  Owner、标准命令、当前任务、最后稳定 Commit、PR 和部署策略。
- `*-spec.json` 是 `spec-intake` 产出的机器事实源。
- `*-design.md` 是经过用户确认的设计。
- `docs/superpowers/plans/` 只保存 `writing-plans` 生成的执行计划，项目中不得维护
  第二份实现计划。
- `business-goal.md` 只能引用并解释 Spec 的业务目标和指标，不得重新定义事实。
- `algorithm-design.md` 只在算法、模型、Agent、搜索、排序、分类、生成或自动决策
  项目中启用。

旧 Spec、Design 和 Plan 保留，不覆盖；`PROJECT.yaml` 指向当前生效版本。Spec
变化后，受影响的派生文档必须标记过期并重新生成或评审。

## 5. 编码前的执行合同

即使 Spec 已经 `engineering_ready`，AI 也不能一步生成整个项目。必须先使用
`writing-plans` 生成实施计划，并建立：

```text
Spec business_success_scenarios[].scenario_id / workflow.step_id / metric_id / operation requirement
  -> 实现任务
  -> 修改文件
  -> 代码 Commit
  -> 测试与 Eval
  -> 验证证据
```

实施计划必须固定 Spec ID、版本和校验值，列出读取过的仓库证据、可复用实现、
任务依赖、允许修改范围、测试命令、预期结果、风险、回滚点和人工确认点。

每次只执行一个可独立验证的小任务：

```text
选择任务 -> 写失败测试 -> 确认正确失败 -> 最小实现 -> 完整检查
-> Spec Review -> 代码质量 Review -> Commit -> 下一任务
```

## 6. 自动执行与人工确认

总控 Skill 默认自动执行仓库读取、计划、测试设计、TDD、代码修改、静态检查、
构建、完整测试、Eval、Review、证据收集和 Git 交付。

出现以下情况必须暂停：

- Spec 冲突或无法实现；
- 产品行为、业务规则、范围或用户体验需要改变；
- 数据、权限、成本或风险等级需要改变；
- 原计划与真实代码不一致；
- 必须修改计划外模块；
- 需要修改既有职责、公共接口、数据结构、模块边界或核心依赖；
- 需要局部重构或重新设计；
- 操作不可逆、破坏性高或需要新的生产权限。

提问格式固定为：发现与证据、不能自动决定的原因、影响、2–3 个互斥选项、推荐
选项及理由。不得向非技术员工询问不改变产品结果的底层技术细节。

纯局部实现细节可以自动处理，例如局部命名、格式、当前新增代码内部整理和不改变
文件职责的私有函数提取。

计划允许变更，但不得静默变更。用户确认后，必须同步更新 Plan、受影响任务、
测试计划、追踪关系，以及必要的 Technical Design 或 Spec。

## 7. 已有项目初始化

已有项目不得直接进入功能开发。总控 Skill 必须先：

1. 读取真实代码、Git 状态、适用的 `AGENTS.md` / `AGENT.md`、架构和运行方式；
2. 补齐 README、PROJECT.yaml 和全部适用文档；
3. 确认 Remote Repository URL、默认分支和基线 Commit；
4. 建立当前测试、Eval 和运行基线；
5. 审计 Spec 与现有实现差异；
6. 生成技术债清单和架构修复方案；
7. 让用户在“全量修复技术债”和“最小干净修复”之间选择；
8. 完成修复、验证和独立 Commit；
9. 建立新的初始化基线后再开发功能。

全量修复指关闭本轮系统化审计识别的全部技术债。

最小干净修复不是临时补丁。它必须修复本轮将修改或依赖的模块，以及所有影响本轮
正确性、测试性、权限、数据和运行稳定性的架构问题。只要本轮功能触及一项已知
技术债，该债务自动进入修复范围。不得在坏架构上增加兼容层、特殊分支或补丁。

架构修复和功能开发必须使用不同 Plan、任务和 Commit。

## 8. 技术债

技术债是已存在于代码、架构或运行方式中的结构性问题。它可能暂时不影响运行，
但会让后续修改更容易出错、更难测试、更难恢复，或者必须持续通过绕路和补丁开发。

技术债必须有代码或运行证据，并至少表现为以下一种风险：不可预测的跨模块影响、
重复事实源、职责混乱、接口或数据合同不稳定、与批准架构不一致、关键行为不可测、
依赖关系错误、失败不可恢复、权限和敏感数据边界不清、运行约束无法满足，或已知
临时方案被持续扩展。

以下内容不自动构成技术债：个人风格偏好、AI 不熟悉的写法、未批准的新功能、Spec
缺口、边界清楚的普通 Bug、没有实际风险的旧依赖，以及仅以“更优雅”为理由的
重构。

每项债务必须记录：TD-ID、问题、代码或运行证据、影响模块、后续风险、是否被本轮
触及、全量方案、最小干净方案、验证方法和关闭状态。

公司 Skill 保存 `references/technical-debt-standard.md`；项目保存
`docs/technical-debt-register.md`。

## 9. AGENTS 规则合规

总控 Skill 必须读取当前作用域内的 `AGENTS.md` 及其指向的共享规则。已固化在代码
或架构中的规则违规属于技术债；缺测试入口、文档、Remote 或 Pre-commit 属于工程
准备缺口；Agent 沟通或执行方式违规属于过程违规。

项目生成 `docs/agent-rules-audit.md`，记录规则来源、生效范围、规则原文、检查证据、
符合状态、对应 TD-ID 或工程准备缺口、修复方案和验证方式。

Graphify 是当前工作区的本地可选能力，不进入公司通用规范，不构成初始化或完成
门禁。

## 10. 测试规范

业务功能使用 `qa-generated-test-case` 从 Spec 生成业务测试覆盖：主流程、分支、
异常、边界、权限、上下游依赖和历史兼容风险。固定七列 QA 表只对业务功能强制，
不生搬硬套到纯底层代码库和基础设施项目。

测试设计必须从 `business_success_scenarios` 开始，而不是由 QA 或工程重新猜测产品
成功标准。`validation_plan.scenario_coverage` 是业务场景到 QA 用例、自动化测试和
Eval 资产的追踪关系。发现业务终态不合理或不完整时，返回产品阶段让 Business Owner
确认变更；不得把业务定义问题伪装成测试实现细节。

`qa-generated-test-case` 负责测试设计；`test-driven-development` 负责编码顺序；
独立测试 Agent 负责重新执行完整测试；Eval 负责算法和业务效果。

TDD 规则：

- R1–R3 的功能、行为变化和 Bug 修复必须先写失败测试并确认其因预期原因失败；
- 只实现让当前测试通过的最小代码；
- 重构只在测试全绿后进行；
- Bug 修复必须有稳定复现问题的回归测试；
- R0 可以不执行完整 TDD，但必须可启动、跑通核心路径、使用隔离数据并标记不可
  发布。

风险自适应测试包括构建启动、业务规则、异常边界、集成合同、权限负向、关键 E2E、
UI 状态、可访问性、性能、故障恢复和回滚。具体强度由 `delivery_risk_profile` 决定。

完成声明必须遵守 `verification-before-completion`：重新执行完整命令、读取退出码和
失败数量，以本轮新鲜证据支持结论。测试、构建、lint 和类型检查不能互相替代。

### Loop Engineering

稳定性的核心不是限制 AI 允许失败几次，而是让每个执行步骤都具备可观察、可比较、
可纠偏的反馈循环。AI 的信心和“已经修好”不是证据。每个任务在执行前必须绑定
业务目标、测试、Eval、E2E 或 Runtime 信号；每次修改后重新观察这些信号，比较
当前结果与成功标准的距离，再根据证据决定下一轮行动。

只有当局部测试、集成/E2E、适用 Eval、Runtime 信号和业务验收共同收敛时，任务才
能完成。循环次数本身不构成停止条件；无法观测、没有收敛、目标或架构需要改变、
风险扩大或下一步需要越权时，才暂停并让用户决策。

## 11. 算法与 Eval

算法、模型和 Agent 项目必须先定义业务问题、输入输出、数据来源、基线、算法选择、
阈值及业务含义、确定性、运行成本、权限、失败和降级、复现方式。

Eval 必须先于完整实现，包含 Golden Cases、异常与边界、权限、外部服务失败、
幻觉或错误决策、历史失败，以及成本、延迟和资源约束。每次运行记录数据集、模型、
依赖、配置、阈值、环境、随机因素、逐案例结果、总体指标、失败案例和基线差异。

不得用同一批反复调试的案例充当独立验收集，不得修改评分规则让实现通过，不得只
看平均分而忽略阻断性失败。

在已批准的成本、数据和业务边界内可以自动调参。更换模型供应商、数据源、业务
阈值、评分规则或成本上限时必须暂停并让用户选择。

## 12. UI

UI 实现必须服从已批准的 Spec 和 SVG Wireframe，先检查并复用现有设计系统、组件
和相似页面。不得擅自改变流程、字段、操作入口和权限。

必须覆盖所有适用的 Loading、Empty、Success、Validation Error、System Error、
No Permission 等状态，落实字段校验和权限，执行关键流程浏览器测试、截图或视觉
回归、可访问性和响应式验证，并由用户完成实际页面验收。

没有现成设计系统时，总控 Skill 在正式 UI 编码前提供 2–3 个可视化方向，由用户
选择。开发中发现 Wireframe 不适配真实数据或交互时，提供保持原设计、局部调整、
返回产品设计三个选项。

## 13. Subagent 开发与 Review

复杂功能尽量使用 `subagent-driven-development`。复杂信号包括跨模块、多项独立任务、
外部系统、数据迁移、权限、并发、算法、Eval、架构调整、技术债修复和高影响失败。

总控 Agent 为每个任务创建全新上下文的实现 Subagent，提供完整任务和必要代码背景；
实现 Subagent 执行 TDD、测试、Commit 和自查。随后依次由独立 Spec Reviewer 和
Code Quality Reviewer 检查，问题修复后必须重新 Review。最后由独立测试 Agent
执行全量测试和 Eval。

多个实现 Subagent 默认不同时修改同一工作区；有代码依赖的任务顺序执行。复杂功能
应使用隔离 Worktree 和功能分支。

不支持 Subagent 的 IDE 可以由主 Agent 顺序执行，但不得省略独立 Spec Review、
代码质量 Review 和最终测试步骤。

## 14. Git、Pre-commit 与交付

正式编码前必须有可访问的 Remote Repository URL。总控 Skill 确认 `origin`、默认
分支、功能分支、基线 Commit 和工作区状态，并保护用户已有修改。

允许在功能分支内自动 Commit。一个计划任务对应一个或少量职责一致的 Commit；
Commit message 包含任务 ID；不得混入计划外改动；不得使用 `--no-verify`。

版本化 Pre-commit Hook 在每次本地 Commit 前执行项目风险等级定义的完整测试套件，
包括格式、静态检查、类型、单元、集成和构建。Eval 在最终交付门禁执行，不要求每
个小 Commit 重跑。

最终必须重新运行完整测试、全部 Eval、追踪检查和独立 Review，再根据以下规则交付：

- 个人 Own 的项目，或者小功能，在拥有直接 Push 权限且仓库允许、风险为 R0/R1、
  不改变架构/API/数据/权限/集成或生产迁移时，可以直接 Push 或 Merge；第一项是
  “个人 Own 或小功能”的或关系，再与其余安全条件组成与关系。
- 多人协作的大功能、R2/R3、架构/API/数据/权限变化、迁移、关键运行变化或仓库
  保护要求时，必须 Push 功能分支并创建 PR。

PR 创建后，由独立测试/审查 Agent 从 Spec、Design、Plan 和 Commit Diff 开始重新
审查并执行完整测试和 Eval。是否需要人类 Review，以及是否允许自动 Merge，由工程
团队和仓库规则决定；公司规范不统一强制人工 Review。

PR 标准独立放在 `references/pull-request-standard.md`，覆盖关联产物、业务范围、
架构变化、技术债、测试、Eval、风险、权限、依赖、回滚和 Reviewer 重点。

## 15. Runtime

`docs/runtime-constraints.md` 必须定义运行环境、版本、安装、启动、停止、构建、测试、
Eval、配置、Secret、端口、网络、依赖、超时、并发、吞吐、资源、成本、数据目录、
健康检查、日志、监控、恢复和环境差异。

`PROJECT.yaml` 保存机器可读的 install、start、test_full、eval_full、build、smoke 和
health_check 命令。

最终运行验证包括干净安装、构建、启动、健康检查、Smoke Test、日志检查、完整测试、
完整 Eval、停止和重新启动。不得把 Secret 写入代码、测试、日志或文档；重试只能
用于已确认的暂时性外部故障，并具有上限、退避、日志和幂等保证。

## 16. 可选部署

部署默认关闭：

```yaml
deployment:
  required: false
  target_environment: null
  sre_skill: production-devops-sre
  lifecycle_status: not_started
```

Spec 明确要求或用户选择部署时，总控 Skill 调用 `production-devops-sre`。部署文件、
工作负载分类、非生产验证、生产阻断、数据库迁移、工单、域名、安全、灰度、监控和
回滚全部服从该 Skill。是否进入 Staging 不由 Vibe Coding Skill 自行判断。

未部署时必须准确描述为“开发完成，未部署”，不得声称生产就绪。

## 17. 总控 Skill 包

```text
skills/vibe-coding/
├── SKILL.md
├── README.md
├── references/
│   ├── risk-adaptive-controls.md
│   ├── project-initialization-standard.md
│   ├── repository-template-standard.md
│   ├── architecture-and-ui-standard.md
│   ├── technical-debt-standard.md
│   ├── agent-rules-compliance-standard.md
│   ├── testing-standard.md
│   ├── eval-standard.md
│   ├── loop-engineering-standard.md
│   ├── subagent-and-review-standard.md
│   ├── git-delivery-standard.md
│   ├── pull-request-standard.md
│   ├── interaction-and-change-control-standard.md
│   ├── deployment-adapter-standard.md
│   ├── runtime-standard.md
│   ├── completion-status-standard.md
│   └── incident-and-rescue-standard.md
├── assets/
│   ├── schemas/
│   │   ├── project.schema.json
│   │   ├── task-feedback.schema.json
│   │   ├── traceability.schema.json
│   │   ├── business-evidence.schema.json
│   │   ├── evidence-manifest.schema.json
│   │   └── review-evidence.schema.json
│   └── templates/*.tpl
├── scripts/
│   ├── schema_runtime.py
│   ├── validate_project.py
│   ├── validate_feedback.py
│   ├── validate_traceability.py
│   ├── run_project_checks.py
│   ├── validate_delivery.py
│   ├── install_pre_commit.py
│   └── self_test.py
├── tests/
└── evals/evals.json
```

`SKILL.md` 只负责判断阶段、检查前置条件、加载相关标准、调用其他 Skills、自动执行、
向用户提供必要选择以及阻止绕过门禁。详细规范放在 `references/`，避免主文件过长。

引用的执行能力包括：

- `writing-plans`
- `test-driven-development`
- `systematic-debugging`
- `verification-before-completion`
- `requesting-code-review`
- `subagent-driven-development`
- `using-git-worktrees`
- `finishing-a-development-branch`
- `qa-generated-test-case`
- 可选的 `production-devops-sre`

## 18. 完成定义

总控 Skill 只有在以下条件全部满足时才能声明完成：

- 输入 Spec、风险、Design、Plan 和人工选择完整；
- 项目初始化完成，本轮涉及技术债全部关闭；
- 所有计划任务和追踪关系完整；
- 测试、Eval、Review 和运行验证具有本轮新鲜证据；
- 没有计划外功能、未确认架构变化或新增未登记技术债；
- README、架构、算法、Runtime、测试、Eval 和 Runbook 文档同步；
- Git Remote 包含最终交付版本；
- PR 或直接 Push/Merge 符合项目规则；
- 部署启用时通过 `production-devops-sre`，未启用时明确说明未部署。

完成状态必须精确区分：开发完成但未部署、已 Push、PR 等待处理、已 Merge、非生产
部署完成、生产发布完成，或被测试/Eval/Review/部署门禁阻断。

## 19. 实现状态

上述设计已经实现为 `skills/vibe-coding/`：包括总控触发和阶段门禁、
`PROJECT.yaml` Schema、项目/反馈/追踪/交付验证器、全量 Pre-commit 安装器、
Loop Engineering 反馈合同、独立 Review 证据、行为 Eval，以及各项独立标准。
发布前由仓库测试、Skill 自测和独立审查共同验证。

## 20. 独立标准文档

已经拆分并维护：

- [`repository-template-standard.md`](company-vibe-coding/repository-template-standard.md)
- [`project-initialization-standard.md`](company-vibe-coding/project-initialization-standard.md)
- [`technical-debt-standard.md`](company-vibe-coding/technical-debt-standard.md)
- [`pull-request-standard.md`](company-vibe-coding/pull-request-standard.md)

测试、Eval、交互变更、Subagent、Git 交付、故障救援和部署适配等标准均已位于
`skills/vibe-coding/references/`。总控 `SKILL.md` 只引用这些标准，不重复承载详细正文。
