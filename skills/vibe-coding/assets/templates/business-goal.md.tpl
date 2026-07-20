# 业务目标与成功指标

## 事实源

- Spec：`__SPEC_PATH__`
- Spec ID / Version：`__SPEC_ID__` / `__SPEC_VERSION__`
- Business Owner：__BUSINESS_OWNER__
- 确认时间：__CONFIRMED_AT__

本文件只引用并解释已确认 Spec，不重新定义业务目标、业务规则或成功终态。若内容冲突，
返回 `spec-intake` 由 Business Owner 决策并更新 Spec。

## 业务问题

__PROBLEM_STATEMENT_FROM_SPEC__

## 目标与非目标

### 本期目标

- __BUSINESS_GOAL_1__
- __BUSINESS_GOAL_2__

### 本期不做

- __OUT_OF_SCOPE_1__
- __OUT_OF_SCOPE_2__

## 业务成功场景

| Scenario ID | 角色 | 触发与前置条件 | 业务成功终态 | 可观测成功信号 | 业务不变量 | 不可接受结果 | 异常/恢复 | Owner 确认 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| __SCENARIO_ID__ | __ACTOR__ | __TRIGGER_AND_PRECONDITIONS__ | __EXPECTED_BUSINESS_OUTCOME__ | __OBSERVABLE_SIGNAL__ | __INVARIANT__ | __UNACCEPTABLE_OUTCOME__ | __RECOVERY_PATH__ | __CONFIRMATION__ |

责任边界：业务主导成功流程；Skill 结构化并阻止跳过门禁；QA 只补充专业覆盖；工程只选择
自动化工具、环境、Fixture、命令、信号与证据。QA 和工程不得自行改变业务成功终态。

## 业务指标

| Metric ID | 指标 | 基线 | 目标 | 统计口径 | 数据来源 | 观察窗口 | Owner | 阻断阈值 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| __METRIC_ID__ | __METRIC_NAME__ | __BASELINE__ | __TARGET__ | __FORMULA_AND_SCOPE__ | __SOURCE__ | __WINDOW__ | __OWNER__ | __BLOCKING_THRESHOLD__ |

## 验收边界

- 业务验收人：__BUSINESS_ACCEPTANCE_OWNER__
- 验收环境与数据：__ACCEPTANCE_ENVIRONMENT_AND_DATA__
- 业务签署证据路径：`__ACCEPTANCE_EVIDENCE_PATH__`
- 不允许用技术测试代替的业务判断：__BUSINESS_ONLY_JUDGMENTS__
