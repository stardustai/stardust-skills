# 运行与接管手册

## 服务信息

- 项目 / 服务：__PROJECT_NAME__
- Operations Owner：__OPERATIONS_OWNER__
- 风险等级：__RISK_TIER__
- 当前发布状态：__RELEASE_STATUS__
- Remote / 分支 / Commit：__REMOTE_URL__ / `__BRANCH__` / `__COMMIT__`

## 启停与健康检查

```bash
__INSTALL_COMMAND_DISPLAY__
__START_COMMAND_DISPLAY__
__HEALTH_CHECK_COMMAND_DISPLAY__
__SMOKE_COMMAND_DISPLAY__
__STOP_COMMAND_DISPLAY__
```

预期健康信号：__HEALTH_SIGNALS__

## 监控与告警

| Signal | 正常范围 | 告警阈值 | Dashboard/查询 | 响应人 |
| --- | --- | --- | --- | --- |
| __SIGNAL__ | __NORMAL__ | __ALERT__ | __QUERY__ | __RESPONDER__ |

## 常见故障

| 症状 | 业务影响 | 诊断证据 | 安全操作 | 禁止操作 | 升级条件 |
| --- | --- | --- | --- | --- | --- |
| __SYMPTOM__ | __IMPACT__ | __EVIDENCE__ | __SAFE_ACTION__ | __FORBIDDEN_ACTION__ | __ESCALATION__ |

## 回滚与恢复

- 最后稳定 Commit：`__LAST_GREEN_COMMIT__`
- 回滚触发条件：__ROLLBACK_TRIGGER__
- 回滚步骤：__ROLLBACK_STEPS__
- 数据恢复步骤：__DATA_RECOVERY__
- 回滚后验证：__POST_ROLLBACK_COMMANDS_AND_SIGNALS__
- 不可逆操作的备份证据：`__BACKUP_EVIDENCE_PATH__`

## 故障接管包

必须包含 Spec/Design/Plan、环境、分支与 Commit、稳定复现、预期/实际、日志与错误栈、失败测试或
Eval、当前新鲜证据、已尝试方案、最后稳定 Commit、数据和业务影响、未决选项。没有可观测信号、
反馈不收敛、目标/架构需改变、风险扩大或下一步越权时立即升级，不以失败次数作为停止标准。

## 联系与升级

| 领域 | Owner/队列 | 联系方式 | 响应目标 |
| --- | --- | --- | --- |
| Business | __BUSINESS_CONTACT__ | __BUSINESS_CHANNEL__ | __BUSINESS_SLA__ |
| Engineering | __ENGINEERING_CONTACT__ | __ENGINEERING_CHANNEL__ | __ENGINEERING_SLA__ |
| QA | __QA_CONTACT__ | __QA_CHANNEL__ | __QA_SLA__ |
| Security/Data | __SECURITY_CONTACT__ | __SECURITY_CHANNEL__ | __SECURITY_SLA__ |
