# Repository Template Standard

状态：滚动设计稿。

## 1. 目的

公司当前不强制统一语言、框架或应用脚手架，但所有正式项目必须采用统一的仓库
合同。仓库合同使总控 Skill、员工、测试 Agent 和技术接管者能够从固定入口理解、
运行、验证和恢复项目。

## 2. 标准目录

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

项目可以遵循语言或框架惯例调整 `src/` 和 `tests/` 的内部结构，但不得改变 Spec、
Design、Plan、项目状态和工程合同的固定入口。

## 3. README.md

README 是员工和技术接管者的第一入口，至少包含：

- 项目解决的问题和目标用户；
- 当前状态及是否已部署；
- 当前生效的 Spec、Design 和 Plan 链接；
- 安装、启动、构建、完整测试、Eval 和 Smoke Test 命令；
- 运行环境和必要依赖；
- 配置与 Secret 获取方式，不包含真实 Secret；
- 项目 Owner、维护者和求助方式；
- 架构、测试、Eval、Runtime、Runbook 和技术债文档链接；
- 已知限制和恢复入口。

README 不重复定义 Spec 中的业务事实，只提供摘要和导航。

## 4. PROJECT.yaml

PROJECT.yaml 是总控 Skill 的机器可读入口，至少记录：

- 项目标识、名称和状态；
- Remote Repository URL、默认分支和当前功能分支；
- 当前生效的 Spec、Design 和 Plan；
- `delivery_risk_profile` 和最终风险等级；
- Business、Product、Engineering、QA 和 Decision Owner；
- 安装、启动、构建、完整测试、Eval、Smoke 和健康检查命令；
- 当前任务、基线 Commit 和 `last_green_commit`；
- 直接 Push、PR、自动 Review、人工 Review 和 Auto-merge 策略；
- 部署是否启用、目标环境、SRE Skill 和部署状态。

PROJECT.yaml 的完整 Schema 单独设计，未确认字段不得由总控 Skill 静默发明。

## 5. Spec、Design 和 Plan

- `docs/superpowers/specs/YYYY-MM-DD-<topic>-spec.json` 保存 `spec-intake` 输出。
- `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` 保存已批准设计。
- `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` 保存 `writing-plans` 输出。
- 旧版本保留；PROJECT.yaml 指向当前版本。
- 项目中只允许一份当前生效 Plan，不维护重复计划。
- Spec 更新后，受影响的 Design、Plan 和派生文档必须失效并重新评审。

## 6. 必须文档与条件文档

所有正式项目必须有：

- `business-goal.md`
- `system-architecture.md`
- `runtime-constraints.md`
- `test-plan.md`
- `traceability.md`
- `runbook.md`
- `technical-debt-register.md`
- `agent-rules-audit.md`

算法、模型、Agent、搜索、排序、分类、生成或自动决策项目还必须有：

- `algorithm-design.md`
- `eval-plan.md`
- `evals/`

业务功能还必须有：

- `docs/qa/01-normalized-spec.md`
- `docs/qa/02-test-design.md`
- `docs/qa/03-testcases.md`

不适用的条件文档不得生成空壳；应在 PROJECT.yaml 和 README 中明确
`not_applicable` 及理由。

## 7. Remote 和 Git 基线

正式编码前必须：

- 提供并验证 Remote Repository URL；
- 确认 `origin` 与指定 URL 一致；
- 确认默认分支、功能分支和基线 Commit；
- 识别并保护用户已有未提交修改；
- 禁止在未知 Remote、无基线或无法恢复的状态下开始正式开发。

## 8. Pre-commit

仓库必须版本化保存 Pre-commit Hook 或等价的仓库级安装配置。每次本地 Commit 前
执行项目风险等级定义的完整测试套件，至少编排适用的格式、静态检查、类型检查、
单元测试、集成测试和构建检查。

- 不得使用 `--no-verify` 绕过；
- Hook 失败时不得创建完成 Commit；
- R0 可以使用明确的精简套件；
- R1–R3 不允许临时删减项目合同要求的检查；
- Eval 在最终交付门禁执行，不要求每个小 Commit 重跑。

## 9. 仓库模板验收

仓库合同只有在以下条件满足时才算建立：

- README 可指导新接管者从干净环境运行项目；
- PROJECT.yaml 可被确定性校验；
- 当前 Spec、Design 和 Plan 路径存在且一致；
- 标准命令真实可执行；
- Pre-commit 安装和失败阻断经过验证；
- Remote、分支和基线 Commit 可确认；
- 适用文档没有空壳、占位符或互相矛盾的事实。
