# 算法、模型或 Agent 设计

> 仅当 `PROJECT.yaml.features.algorithmic=true` 时启用。

## 业务问题与输出含义

- 业务问题：__BUSINESS_PROBLEM__
- 输入：__INPUT_CONTRACT__
- 输出：__OUTPUT_CONTRACT__
- 输出如何影响业务决策：__BUSINESS_DECISION_IMPACT__
- 失败时的安全行为：__SAFE_FAILURE_BEHAVIOR__

## 数据

| 数据集 | 来源与权限 | 采样窗口 | 标签/Golden 来源 | 泄漏与偏差风险 | 版本 |
| --- | --- | --- | --- | --- | --- |
| __DATASET__ | __SOURCE_AND_PERMISSION__ | __WINDOW__ | __LABEL_SOURCE__ | __RISKS__ | __VERSION__ |

## 基线与方案

- 可比较基线：__BASELINE__
- 选择的方案：__SELECTED_APPROACH__
- 选择理由：__RATIONALE__
- 放弃方案：__REJECTED_APPROACHES__
- 确定性 / 随机性：__DETERMINISM__
- 可复现方式：__REPRODUCTION_COMMAND_AND_CONFIG__

## 阈值与业务含义

| Threshold ID | 值 | 对应业务取舍 | 变更审批人 | 阻断性失败 |
| --- | --- | --- | --- | --- |
| __THRESHOLD_ID__ | __VALUE__ | __BUSINESS_TRADEOFF__ | __APPROVER__ | __BLOCKING_FAILURE__ |

## 运行约束

- 延迟：__LATENCY_TARGET__
- 成本：__COST_LIMIT__
- 资源：__RESOURCE_LIMIT__
- 并发与吞吐：__CONCURRENCY_THROUGHPUT__
- 外部依赖：__EXTERNAL_DEPENDENCIES__

## Eval 合同

- Golden Cases：__GOLDEN_CASES__
- 独立验收集：__HOLDOUT_CASES__
- 异常、权限、外部失败和历史失败：__ADVERSARIAL_AND_FAILURE_CASES__
- 指标和最低阈值：__METRICS_AND_GATES__
- 逐案例结果证据：`__CASE_EVIDENCE_PATH__`

更换模型供应商、数据源、业务阈值、评分规则或成本上限时，必须暂停并由用户选择；不得通过
修改评分规则或反复调试验收集来让实现通过。
