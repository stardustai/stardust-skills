# 系统架构

## 事实与决策来源

- Spec：`__SPEC_PATH__`
- Design：`__DESIGN_PATH__`
- 适用 Agent 规则：`docs/agent-rules-audit.md`
- 风险等级：`__RISK_TIER__`
- 架构确认人 / 时间：__ARCHITECTURE_APPROVER__ / __APPROVED_AT__

## 系统边界

__SYSTEM_CONTEXT_AND_BOUNDARY__

| 外部参与者或系统 | 输入 | 输出 | 权威事实归属 | 失败影响 |
| --- | --- | --- | --- | --- |
| __ACTOR_OR_SYSTEM__ | __INPUT__ | __OUTPUT__ | __SOURCE_OF_TRUTH__ | __FAILURE_IMPACT__ |

## 已选架构

- 采用的现有模式或公司蓝图：__APPROVED_PATTERN__
- 选择理由：__RATIONALE__
- 明确不采用：__REJECTED_ALTERNATIVES_AND_REASON__
- 与现有代码的接入点：__INTEGRATION_POINTS__

## 组件与职责

| 组件 | 唯一职责 | 公共接口 | 依赖 | 数据所有权 | 失败与恢复 |
| --- | --- | --- | --- | --- | --- |
| __COMPONENT__ | __RESPONSIBILITY__ | __INTERFACE__ | __DEPENDENCIES__ | __DATA_OWNERSHIP__ | __FAILURE_AND_RECOVERY__ |

禁止建立平行架构、重复事实源、兼容层或为绕过技术债增加特殊分支。

## 数据模型与生命周期

| 实体/事件 | 字段或载荷 | 来源 | 敏感等级 | 创建/更新者 | 保存期限 | 删除/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| __ENTITY__ | __FIELDS__ | __SOURCE__ | __SENSITIVITY__ | __WRITER__ | __RETENTION__ | __DELETE_OR_ROLLBACK__ |

## 身份、权限与审计

__AUTHN_AUTHZ_AUDIT_DESIGN__

## 接口与失败模式

| Interface ID | 合同 | 超时 | 幂等 | 重试边界 | 部分失败 | 可观测信号 |
| --- | --- | --- | --- | --- | --- | --- |
| __INTERFACE_ID__ | __CONTRACT__ | __TIMEOUT__ | __IDEMPOTENCY__ | __RETRY_POLICY__ | __PARTIAL_FAILURE__ | __SIGNAL__ |

## 可观测性与恢复

__LOG_METRIC_TRACE_ALERT_RECOVERY_DESIGN__

## 架构不变量

- __ARCHITECTURE_INVARIANT_1__
- __ARCHITECTURE_INVARIANT_2__

## 已批准偏离

无偏离时写“无”。任何新模块边界、公共接口、数据结构或核心依赖变化必须暂停并让用户选择，
随后同步 Design、Plan、测试和追踪关系。

__APPROVED_EXCEPTIONS_OR_NONE__
