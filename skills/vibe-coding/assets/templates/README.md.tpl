# __PROJECT_NAME__

> 状态：`__PROJECT_STATUS__`
> 风险等级：`__RISK_TIER__`
> 当前 Spec：`__SPEC_PATH__`

## 项目目标

__ONE_SENTENCE_BUSINESS_GOAL__

业务目标、成功指标和业务主导的端到端成功流程见
[`__BUSINESS_GOAL_PATH__`](__BUSINESS_GOAL_PATH__)。本 README 只作为员工、Reviewer 和接管者的入口，
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
[`__RUNTIME_CONSTRAINTS_PATH__`](__RUNTIME_CONSTRAINTS_PATH__)。不得把 Secret 写入本文件。

## 验证

```bash
__BUILD_COMMAND_DISPLAY__
__FULL_TEST_COMMAND_DISPLAY__
__FULL_EVAL_COMMAND_DISPLAY__
__SMOKE_COMMAND_DISPLAY__
```

“测试通过”必须来自本轮执行结果；AI 自述、旧日志或页面能打开都不是完成证据。业务场景、
QA 用例、自动化命令和证据路径的映射见
[`__TRACEABILITY_PATH__`](__TRACEABILITY_PATH__) 及其机器可读合同。

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

以下机器可核验的 `responsibility -> path` 行同时作为人类导航；不得只写路径前缀、别名或
`.bak` 文件。

- `organization`: `__standard_OR_adapt_existing__`
- `spec`: `__SPEC_PATH__`
- `design`: `__DESIGN_PATH__`
- `plan`: `__PLAN_PATH__`
- `business_goal`: `__BUSINESS_GOAL_PATH__`
- `system_architecture`: `__SYSTEM_ARCHITECTURE_PATH__`
- `algorithm_design`: `__ALGORITHM_DESIGN_PATH__`
- `ui_spec`: `__UI_SPEC_PATH__`
- `runtime_constraints`: `__RUNTIME_CONSTRAINTS_PATH__`
- `test_plan`: `__TEST_PLAN_PATH__`
- `traceability`: `__TRACEABILITY_PATH__`
- `eval_plan`: `__EVAL_PLAN_PATH__`
- `runbook`: `__RUNBOOK_PATH__`
- `technical_debt_register`: `__TECHNICAL_DEBT_REGISTER_PATH__`
- `agent_rules_audit`: `__AGENT_RULES_AUDIT_PATH__`
- `qa_normalized_spec`: `__QA_NORMALIZED_SPEC_PATH__`
- `qa_test_design`: `__QA_TEST_DESIGN_PATH__`
- `qa_test_cases`: `__QA_TEST_CASES_PATH__`
- `content_review`: `__DOCUMENTATION_REVIEW_PATH__`

采用 `adapt_existing` 时，本节必须列出所有真实路径并说明现有组织方式；缺失内容在最合适的
现有位置补齐，不为了模仿模板创建第二份事实源。

## 求助与接管

遇到无法观测、验证不收敛、Spec/业务目标冲突、架构或权限需要改变、风险扩大，或必须修改
计划外模块时停止继续修改。提交以下接管信息：当前 Spec/Design/Plan、分支与 Commit、稳定复现、
新鲜日志、失败测试或 Eval、已尝试方案、最后稳定 Commit、影响范围和待决选项。

## 发布状态

__PRECISE_RELEASE_STATUS__

必须精确区分“开发完成但未部署”“已 Push”“PR 等待处理”“已 Merge”“非生产部署完成”
和“生产发布完成”。
