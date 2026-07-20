# 测试计划

## 输入与责任

- Spec：`__SPEC_PATH__`
- 业务成功场景：`business_success_scenarios`
- 场景覆盖：`validation_plan.scenario_coverage`
- QA Owner：__QA_OWNER__
- Engineering Owner：__ENGINEERING_OWNER__

业务定义“成功是什么”，QA 补齐专业覆盖，工程实现可重复自动化。测试不得重新定义产品成功终态。

## 测试策略

每一类验证都必须在 `PROJECT.yaml.verification.applicability` 中记录
`required` 或 `not_applicable`、原因、证据和批准人。业务 E2E 与 Eval 不得豁免；
有业务 UI 时可访问性不得豁免；R2/R3 的权限和恢复/回滚不得豁免。其他豁免只能由
QA Owner 或 Decision Owner 批准，实施 Agent 不能批准自己的豁免。

| 类别 | 状态 | 原因 | 证据 | 批准人 |
| --- | --- | --- | --- | --- |
| format_static_type | __required_OR_not_applicable__ | __REASON__ | __EVIDENCE__ | __APPROVER__ |
| unit | __required_OR_not_applicable__ | __REASON__ | __EVIDENCE__ | __APPROVER__ |
| integration | __required_OR_not_applicable__ | __REASON__ | __EVIDENCE__ | __APPROVER__ |
| business_e2e | required | __REASON__ | __EVIDENCE__ | __APPROVER__ |
| permissions | __required_OR_not_applicable__ | __REASON__ | __EVIDENCE__ | __APPROVER__ |
| ui_accessibility | __required_OR_not_applicable__ | __REASON__ | __EVIDENCE__ | __APPROVER__ |
| performance_cost | __required_OR_not_applicable__ | __REASON__ | __EVIDENCE__ | __APPROVER__ |
| recovery_rollback | __required_OR_not_applicable__ | __REASON__ | __EVIDENCE__ | __APPROVER__ |
| eval | required | __REASON__ | __EVIDENCE__ | __APPROVER__ |

| 层级 | 覆盖目标 | 风险依据 | 环境/数据 | 命令 | Owner |
| --- | --- | --- | --- | --- | --- |
| 单元/业务规则 | __UNIT_SCOPE__ | __UNIT_RISK__ | __UNIT_FIXTURES__ | `__UNIT_COMMAND__` | __UNIT_OWNER__ |
| 集成/合同 | __INTEGRATION_SCOPE__ | __INTEGRATION_RISK__ | __INTEGRATION_FIXTURES__ | `__INTEGRATION_COMMAND__` | __INTEGRATION_OWNER__ |
| E2E | __E2E_SCOPE__ | __E2E_RISK__ | __E2E_FIXTURES__ | `__E2E_COMMAND__` | __E2E_OWNER__ |
| 权限负向 | __AUTH_SCOPE__ | __AUTH_RISK__ | __AUTH_FIXTURES__ | `__AUTH_COMMAND__` | __AUTH_OWNER__ |
| UI/可访问性 | __UI_SCOPE__ | __UI_RISK__ | __UI_FIXTURES__ | `__UI_COMMAND__` | __UI_OWNER__ |
| 性能/恢复/回滚 | __RESILIENCE_SCOPE__ | __RESILIENCE_RISK__ | __RESILIENCE_FIXTURES__ | `__RESILIENCE_COMMAND__` | __RESILIENCE_OWNER__ |

## 业务场景覆盖

| Scenario ID | QA Case | 主/分支/异常/边界/权限/恢复 | 自动化级别 | 命令 | 可观测信号 | 证据路径 |
| --- | --- | --- | --- | --- | --- | --- |
| __SCENARIO_ID__ | __QA_CASE_ID__ | __COVERAGE_KIND__ | __AUTOMATION_LEVEL__ | `__COMMAND__` | __SIGNAL__ | `__EVIDENCE_PATH__` |

每个本期关键业务场景必须在 `docs/traceability.json` 中有 QA 用例、可执行命令和新鲜证据路径。

## TDD 与回归

- R1–R3 的功能、行为变化和 Bug 修复先写失败测试，并记录预期失败原因。
- 只实现使当前测试通过的最小代码；测试全绿后才重构。
- Bug 修复包含稳定复现原问题的回归测试。
- 每个任务完成时执行局部检查，Commit 前执行风险等级要求的完整套件，最终交付重新执行完整测试与 Eval。

## 测试数据与隔离

__TEST_DATA_SOURCE_REDACTION_RESET_AND_ISOLATION__

## 阻断与退出条件

- 阻断性失败：__BLOCKING_FAILURES__
- Flaky 判定与处理：__FLAKY_POLICY__
- 退出条件：所有强制检查通过，失败数为 0，证据来自本轮，关键场景追踪完整，业务验收完成。
