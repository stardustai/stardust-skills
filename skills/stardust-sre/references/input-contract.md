# 应用侧输入契约与运维边界

## 输入文件

使用 `scripts/inspect_project.py` 生成 `deploy-inputs.json`，由项目组确认后再交给
`scripts/generate_deployment.py`。输入结构如下：

脚本要求 Python 3.9 或更高版本，只使用标准库；CI 门禁脚本兼容 POSIX shell。

```json
{
  "project": "orders-api",
  "namespace": "orders-api",
  "domain": "<DOMAIN_PENDING_APPROVAL>",
  "change_ticket": "<CHANGE_TICKET_REQUIRED>",
  "domain_request": "<DOMAIN_REQUEST_REQUIRED>",
  "first_cicd_approved": false,
  "services": [
    {
      "name": "api",
      "workload": "stateless",
      "runtime": "unknown",
      "image": "<IMAGE_DIGEST_REQUIRED>",
      "port": 8080,
      "health_path": "/healthz",
      "ready_path": "/readyz",
      "compose_healthcheck": ["CMD", "wget", "-q", "--spider", "http://127.0.0.1:8080/healthz"],
      "expose": false,
      "ingress_path": "/",
      "uid": 10000,
      "gid": 10000,
      "data_path": null,
      "storage_size": null
    }
  ]
}
```

`workload` 只允许：

- `stateless`：Deployment、Service、PDB。
- `worker`：Deployment，不生成 Service/Ingress；探针必须按项目语义确认。
- `stateful`：StatefulSet、Headless Service、Service、volumeClaimTemplates。
- `migration`：单独的 Kubernetes Job 和 Compose 一次性服务。

`migration` 必须提供 `migration_command` 数组；`worker` 必须提供
`probe_command` 数组；其他长期服务必须提供经过镜像验证的
`compose_healthcheck` 数组，不能假设镜像一定包含 wget/curl。只有
`expose: true` 的 HTTP 服务才生成 Ingress，且每个
暴露服务的 `ingress_path` 必须唯一。

生成器拒绝未知字段类型、不合法名称、重复服务名、非法端口和危险路径。检测脚本
只能提供候选值；项目组必须确认镜像、端口、探针、UID/GID、持久化和关闭行为。

## Skill 负责的内容

- 项目结构和运行时候选识别。
- Dockerfile 模板、Compose 和 Kubernetes 应用侧清单。
- 非 root、只读根、seccomp、资源、探针、日志、NetworkPolicy 等安全基线。
- 数据库迁移独立任务及恢复说明框架。
- 运维变更工单草稿、域名申请草稿和首次发布门禁说明。
- 本地 YAML、结构、安全、幂等及占位符验证。

## 运维服务器负责的内容

以下值不固化在 Skill，也不作为公司参数文件的必填项：

- 镜像仓库地址和命名规则。
- Kubernetes 版本和具体集群环境。
- WAF/CDN 平台配置。
- 工单系统地址及平台字段映射。
- StorageClass 和 AccessMode 的最终平台选择。
- cert-manager ClusterIssuer 或其他证书签发平台配置。

生成清单不设置 `storageClassName`，使用集群默认 StorageClass；有状态模板采用
应用侧保守的 `ReadWriteOnce` 语义，运维上线时按存储平台复核或覆盖。Ingress
只引用待分配 TLS Secret，不声明 ClusterIssuer。WAF/CDN 和 DNS 由批准后的运维
流程配置。

## 生产阻断条件

以下任一值未确认时，验证器返回生产阻断：

- 镜像仍为占位符、`latest` 或未使用 Digest。
- 域名仍为占位符。
- 变更工单或域名申请仍为占位符。
- `first_cicd_approved` 不是 `true`。
- 端口、探针、UID/GID、持久化路径来自推断但未人工确认。

可在非生产模式生成和验证占位清单，但不得把“结构校验通过”解释为允许上线。
