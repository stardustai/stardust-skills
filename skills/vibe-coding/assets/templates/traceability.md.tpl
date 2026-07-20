# 需求、实现与证据追踪

机器可读合同：`docs/traceability.json`。本文件用于人类审查，不替代机器门禁。QA Case、
自动化测试和 Eval 引用必须与已批准 Spec 的 `validation_plan.scenario_coverage` 完全一致。

## 追踪矩阵

| Spec / Scenario / Workflow / Metric | 实现任务 | 修改文件 | Commit | QA Case | Automated Test | Eval Asset | Business Signal | Evidence | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| __SOURCE_REF__ | __TASK_ID__ | __FILES__ | __COMMIT__ | __QA_CASE_REFS__ | __AUTOMATED_TEST_REFS__ | __EVALUATION_ASSET_REFS__ | __BUSINESS_SIGNAL_REFS__ | __EVIDENCE_PATHS__ | __STATUS__ |

每个 Evidence 路径必须位于项目根目录内并指向真实 JSON 执行产物。产物必须记录当前 commit、
目标环境、场景 ID、带时区时间，以及每个业务信号的来源、预期、观测值和通过结果。每个信号的
来源、操作符和阈值由 Business Owner 批准并写入机器合同；执行证据必须绑定 runner 生成的
manifest 路径、SHA-256、当前 commit、实际 argv 和退出码。仅回显 Spec、写“pass”或勾选完成
不构成证据。

## 关键场景完整性

| Scenario ID | Business Owner 已确认 | QA 批准覆盖 | 自动化已实现 | 新鲜证据 | 业务验收 | 阻断项 |
| --- | --- | --- | --- | --- | --- | --- |
| __SCENARIO_ID__ | __BUSINESS_CONFIRMED__ | __QA_APPROVED__ | __AUTOMATED__ | __FRESH_EVIDENCE__ | __BUSINESS_ACCEPTED__ | __BLOCKER_OR_NONE__ |

## 变更记录

当 Spec、Design 或 Plan 变化时，列出受影响映射并标记旧证据过期；不得静默沿用旧证据。

| 时间 | 变更 | 影响映射 | 旧证据状态 | 决策人 |
| --- | --- | --- | --- | --- |
| __CHANGED_AT__ | __CHANGE__ | __AFFECTED_MAPPINGS__ | __EVIDENCE_STATUS__ | __DECISION_OWNER__ |
