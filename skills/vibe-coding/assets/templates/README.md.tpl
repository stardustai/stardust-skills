# __PROJECT_NAME__

> 状态：`__PROJECT_STATUS__`
> 风险等级：`__RISK_TIER__`
> 当前 Spec：`__SPEC_PATH__`

## 项目目标

__ONE_SENTENCE_BUSINESS_GOAL__

业务目标、成功指标和业务主导的端到端成功流程见
[`docs/business-goal.md`](docs/business-goal.md)。本 README 只作为员工、Reviewer 和接管者的入口，
不重新定义 Spec。

## 当前范围

- 本期范围：__IN_SCOPE_SUMMARY__
- 明确不做：__OUT_OF_SCOPE_SUMMARY__
- 当前任务：__CURRENT_TASK_ID__
- 最后稳定 Commit：`__LAST_GREEN_COMMIT__`

## 责任人

| 责任 | Owner |
| --- | --- |
| Business Owner | __BUSINESS_OWNER__ |
| Product Owner | __PRODUCT_OWNER__ |
| Engineering Owner | __ENGINEERING_OWNER__ |
| QA Owner | __QA_OWNER__ |
| Decision Owner | __DECISION_OWNER__ |

业务成功流程由 Business Owner 定义并确认；Vibe Coding Skill 负责结构化、门禁和编排；
QA 补齐边界、负向、权限与恢复覆盖；工程将覆盖实现为可重复执行的自动化和新鲜证据。

## 快速开始

前置条件：__RUNTIME_PREREQUISITES__

```bash
__INSTALL_COMMAND_DISPLAY__
__START_COMMAND_DISPLAY__
```

健康检查：

```bash
__HEALTH_CHECK_COMMAND_DISPLAY__
```

停止服务：

```bash
__STOP_COMMAND_DISPLAY__
```

具体版本、配置、Secret、端口、依赖和环境差异见
[`docs/runtime-constraints.md`](docs/runtime-constraints.md)。不得把 Secret 写入本文件。

## 验证

```bash
__BUILD_COMMAND_DISPLAY__
__FULL_TEST_COMMAND_DISPLAY__
__FULL_EVAL_COMMAND_DISPLAY__
__SMOKE_COMMAND_DISPLAY__
```

“测试通过”必须来自本轮执行结果；AI 自述、旧日志或页面能打开都不是完成证据。业务场景、
QA 用例、自动化命令和证据路径的映射见 [`docs/traceability.md`](docs/traceability.md) 与
`docs/traceability.json`。

## Git 与交付

- Remote：__REMOTE_URL__
- 默认分支：`__DEFAULT_BRANCH__`
- 功能分支：`__FEATURE_BRANCH__`
- 交付方式：`__DELIVERY_MODE__`
- PR：__PULL_REQUEST_URL_OR_NOT_APPLICABLE__

本地 Commit 会运行版本化 Pre-commit Hook 的完整项目测试套件。最终交付还必须重新执行
完整测试、Eval、业务 Traceability 和独立 Review。`docs/evidence/` 是本地/CI Artifact，
不提交到 Git；需要留存时上传到批准的证据存储。

## 文档导航

- 当前 Spec：`__SPEC_PATH__`
- 当前设计：`__DESIGN_PATH__`
- 当前实施计划：`__PLAN_PATH__`
- [业务目标与指标](docs/business-goal.md)
- [系统架构](docs/system-architecture.md)
- [算法设计（如适用）](docs/algorithm-design.md)
- [运行约束](docs/runtime-constraints.md)
- [测试计划](docs/test-plan.md)
- [需求追踪](docs/traceability.md)
- [Eval 计划](docs/eval-plan.md)
- [运行手册](docs/runbook.md)
- [技术债登记](docs/technical-debt-register.md)
- [Agent 规则审计](docs/agent-rules-audit.md)

## 求助与接管

遇到无法观测、验证不收敛、Spec/业务目标冲突、架构或权限需要改变、风险扩大，或必须修改
计划外模块时停止继续修改。提交以下接管信息：当前 Spec/Design/Plan、分支与 Commit、稳定复现、
新鲜日志、失败测试或 Eval、已尝试方案、最后稳定 Commit、影响范围和待决选项。

## 发布状态

__PRECISE_RELEASE_STATUS__

必须精确区分“开发完成但未部署”“已 Push”“PR 等待处理”“已 Merge”“非生产部署完成”
和“生产发布完成”。
