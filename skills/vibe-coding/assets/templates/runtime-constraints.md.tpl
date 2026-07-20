# 运行约束

## 环境矩阵

| 环境 | 用途 | Runtime/版本 | 数据 | 网络 | 与生产差异 |
| --- | --- | --- | --- | --- | --- |
| development | __DEV_PURPOSE__ | __DEV_RUNTIME__ | __DEV_DATA__ | __DEV_NETWORK__ | __DEV_DIFFERENCE__ |
| test | __TEST_PURPOSE__ | __TEST_RUNTIME__ | __TEST_DATA__ | __TEST_NETWORK__ | __TEST_DIFFERENCE__ |
| staging（如部署 Skill 要求） | __STAGING_PURPOSE__ | __STAGING_RUNTIME__ | __STAGING_DATA__ | __STAGING_NETWORK__ | __STAGING_DIFFERENCE__ |
| production | __PROD_PURPOSE__ | __PROD_RUNTIME__ | __PROD_DATA__ | __PROD_NETWORK__ | — |

## 标准命令

命令的机器事实源是 `PROJECT.yaml.commands`，必须使用 argv 数组，不通过 shell 字符串执行。

| 操作 | 命令 | 预期信号 | 超时 |
| --- | --- | --- | --- |
| 安装 | `__INSTALL_COMMAND__` | __INSTALL_SIGNAL__ | __INSTALL_TIMEOUT__ |
| 启动 | `__START_COMMAND__` | __START_SIGNAL__ | __START_TIMEOUT__ |
| 停止 | `__STOP_COMMAND__` | __STOP_SIGNAL__ | __STOP_TIMEOUT__ |
| 构建 | `__BUILD_COMMAND__` | __BUILD_SIGNAL__ | __BUILD_TIMEOUT__ |
| 完整测试 | `__TEST_FULL_COMMAND__` | __TEST_SIGNAL__ | __TEST_TIMEOUT__ |
| 完整 Eval | `__EVAL_FULL_COMMAND__` | __EVAL_SIGNAL__ | __EVAL_TIMEOUT__ |
| Smoke | `__SMOKE_COMMAND__` | __SMOKE_SIGNAL__ | __SMOKE_TIMEOUT__ |
| 健康检查 | `__HEALTH_CHECK_COMMAND__` | __HEALTH_SIGNAL__ | __HEALTH_TIMEOUT__ |

## 配置与 Secret

| 名称 | 环境 | 必需 | 来源/注入方式 | Owner | 轮换 | 是否敏感 |
| --- | --- | --- | --- | --- | --- | --- |
| __CONFIG_NAME__ | __ENV__ | __REQUIRED__ | __INJECTION_SOURCE__ | __OWNER__ | __ROTATION__ | __SENSITIVE__ |

只记录变量名和获取方式，不记录值。Secret 不得进入代码、文档、测试数据、日志或证据。

## 网络与依赖

__PORTS_NETWORK_UPSTREAM_DOWNSTREAM_DEPENDENCIES__

## 性能、资源与成本

| 约束 | 目标/上限 | 测量命令 | 证据 | 超限行为 |
| --- | --- | --- | --- | --- |
| 延迟 | __LATENCY__ | __LATENCY_COMMAND__ | __LATENCY_EVIDENCE__ | __LATENCY_FAILURE_ACTION__ |
| 并发/吞吐 | __THROUGHPUT__ | __THROUGHPUT_COMMAND__ | __THROUGHPUT_EVIDENCE__ | __THROUGHPUT_FAILURE_ACTION__ |
| CPU/内存/磁盘 | __RESOURCES__ | __RESOURCE_COMMAND__ | __RESOURCE_EVIDENCE__ | __RESOURCE_FAILURE_ACTION__ |
| 成本 | __COST__ | __COST_COMMAND__ | __COST_EVIDENCE__ | __COST_FAILURE_ACTION__ |

## 可靠性

- 超时：__TIMEOUT_POLICY__
- 重试：__BOUNDED_BACKOFF_AND_IDEMPOTENCY__
- 数据目录与持久化：__DATA_DIRECTORIES__
- 健康检查：__HEALTH_CHECK_CONTRACT__
- 日志、指标和告警：__OBSERVABILITY__
- 备份与恢复：__BACKUP_AND_RECOVERY__
- 重启验证：__RESTART_VERIFICATION__
