# Eval 计划

## 适用性

- 是否包含算法、模型、Agent、搜索、排序、分类、生成、自动决策或业务效果判断：__APPLICABLE__
- 即使不含模型，仍需评估的业务效果：__BUSINESS_EFFECT_EVAL__
- Eval Owner：__EVAL_OWNER__

## 事实源与基线

- Spec：`__SPEC_PATH__`
- Algorithm Design：`__ALGORITHM_DESIGN_PATH_OR_NOT_APPLICABLE__`
- 当前基线版本/结果：__BASELINE_VERSION_AND_RESULT__
- 独立验收集版本：__HOLDOUT_DATASET_VERSION__

## 案例集

| Eval ID | 类型 | 对应 Scenario/Requirement | 输入来源 | 预期结果 | 阻断条件 | 是否调试集 |
| --- | --- | --- | --- | --- | --- | --- |
| __EVAL_ID__ | Golden/边界/权限/外部失败/历史失败/成本/延迟 | __SOURCE_REF__ | __INPUT_SOURCE__ | __EXPECTED__ | __BLOCKING__ | __DEBUG_SET__ |

独立验收集不得与反复调试集相同，不得因实现失败修改评分规则。

## 指标与门禁

| Metric ID | 计算方式 | 基线 | 最低通过值 | 阻断性子集 | 业务含义 |
| --- | --- | --- | --- | --- | --- |
| __EVAL_METRIC_ID__ | __FORMULA__ | __BASELINE__ | __PASS_THRESHOLD__ | __BLOCKING_SUBSET__ | __BUSINESS_MEANING__ |

不得只看平均分而忽略阻断性失败。

## 执行合同

- 命令：`__EVAL_COMMAND__`
- 数据、模型、依赖与配置版本：__VERSIONS__
- 环境：__ENVIRONMENT__
- 随机因素与固定方式：__RANDOMNESS_CONTROL__
- 逐案例结果：`__CASE_RESULTS_PATH__`
- 汇总结果：`__SUMMARY_PATH__`
- 与基线差异：`__BASELINE_DIFF_PATH__`

## 变更确认点

更换模型供应商、数据源、业务阈值、评分规则或成本上限时暂停，由用户在互斥选项中确认；
确认后同步 Spec/Design/Plan、测试与追踪关系。
