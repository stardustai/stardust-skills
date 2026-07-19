# 部署实现标准

## Dockerfile

- 使用固定版本或 Digest 的可信基础镜像。根据运行时选择 distroless、Wolfi、
  Alpine 或厂商安全镜像，不以“体积小”替代漏洞和兼容性评估。
- 使用多阶段构建，只复制运行产物；合理排列依赖层以利用缓存。
- 使用 UID/GID 不低于 10000 的专用用户，明确 `USER uid:gid`。
- 使用 exec-form ENTRYPOINT/CMD，确保进程正确接收 SIGTERM。仅在应用会派生子
  进程且不能回收、转发信号时使用 `tini` 或等价 init；验证而非盲目安装。
- 中国大陆构建环境仅使用组织批准、支持 HTTPS 和完整性校验的镜像源。避免把
  长期凭据写入构建层；使用 BuildKit secret/cache mount。
- 设置 `TZ=Asia/Shanghai` 并安装时区数据。提供健康接口，但不要把 Secret 烘焙
  进镜像。

## Docker Compose

- 文件固定为 `deploy/docker-compose.yml`，只引用外部构建镜像，不含 `build:`
  或 `context:`。生产记录实际部署 Digest。
- 每个服务设置非 root 用户、`read_only: true`、`cap_drop: [ALL]`、
  `no-new-privileges:true`、受限 `/tmp`、PID/CPU/内存限制和健康检查。
- 同时考虑 Compose 实现兼容性：使用目标运行时实际生效的资源字段，不仅依赖
  可能被忽略的 `deploy.resources`；在交付说明中记录验证版本。
- 持久数据使用名称稳定的具名卷或显式宿主机目录，禁止匿名卷。说明备份、权限、
  所有者、容量和删除命令风险。
- 创建专用网络；只发布必要端口，管理端口默认绑定 `127.0.0.1`；按服务依赖
  设置网络连接和别名。
- 日志使用平台集中采集；本地驱动必须限制大小和文件数，组织默认上限为
  `max-size: "100m"`、`max-file: "3"`。
- `.env` 不是 Secret 管理系统。仅提交 `.env.example`；生产凭据由 CI/CD、宿主机
  Secret 文件或外部 Secret 系统注入，设置最小文件权限且不写入日志。

## Kubernetes 基础资源

- 创建 Namespace，并启用 Pod Security Admission `restricted` 的 enforce、
  audit 和 warn 标签。按需配置 ResourceQuota 与 LimitRange。
- 为应用创建专用 ServiceAccount，默认
  `automountServiceAccountToken: false`。只有确认需要 Kubernetes API 时才创建
  最小 namespaced Role/RoleBinding。
- 无状态 API、前端和 Worker 使用 Deployment；具有稳定存储或网络身份的数据
  服务使用 StatefulSet；一次性任务使用 Job/CronJob。
- Service 默认 ClusterIP；Ingress/Gateway 使用 TLS，并只暴露必要路径。不得
  生成真实私钥、证书值、IngressClass 或 ClusterIssuer；这些由运维服务器侧
  Overlay 或发布流程分配。正式域名必须来自
  已审批的域名分配记录；申请未完成时使用 `<DOMAIN_PENDING_APPROVAL>` 等明显
  占位符，并阻断生产发布。
- NetworkPolicy 默认拒绝，再按真实调用关系开放入口、DNS 和出口。不得在不知
  道依赖时假装“最小权限”；用明确待确认项阻断上线。

## Pod 与容器

- Pod 设置 `runAsNonRoot`、与镜像一致的 `runAsUser/runAsGroup`、
  `seccompProfile: RuntimeDefault`；持久卷需要时设置相同 `fsGroup` 和
  `fsGroupChangePolicy: OnRootMismatch`。存储驱动不支持时记录例外方案。
- 容器设置 `allowPrivilegeEscalation: false`、`readOnlyRootFilesystem: true`、
  `capabilities.drop: [ALL]`。只把已确认的写入路径挂载为 PVC、emptyDir 或 tmpfs。
- 每个容器定义 CPU、内存和临时存储 requests/limits。依据指标调优；JVM/Node
  内存参数留出 native/sidecar 余量，非敏感运行参数放 ConfigMap，只有敏感值
  放 Secret。
- 长期运行应用配置 readiness 和 liveness；启动缓慢或需保护初始化阶段时配置
  startupProbe。对于 Worker 使用适合其语义的 exec/gRPC/TCP 探针。探针不得
  依赖外部数据库等共享依赖而造成级联重启。
- `terminationGracePeriodSeconds` 不低于 30 秒并匹配应用关闭时间。对外服务采用
  应用 drain 命令或短暂 preStop 缓冲，同时配合 readiness、Endpoint 摘除和负载
  均衡连接排空；不得承诺“零 502”。
- 频繁访问公网或跨 VPC 域名且已有 DNS 证据时才调整 `ndots`；修改前验证短名、
  Service Discovery 和企业 DNS，禁止无条件切换 `dnsPolicy: Default`。

## 发布与可用性

- Deployment 明确 RollingUpdate `maxSurge/maxUnavailable`；StatefulSet 根据组件
  能力选择 RollingUpdate、Partition 或受控运维流程。
- 多副本优先使用 topologySpreadConstraints；按实际容量选择 preferred 或
  required anti-affinity，避免强反亲和使 Pod 永久 Pending。
- 配置 PDB，但确认它不会阻断单副本维护；只有具备指标、容量和无状态前提时添加
  HPA。配置 PriorityClass、节点选择和容忍前先确认平台策略。
- 镜像更新、配置更新和回滚命令必须幂等，保留 revisionHistory，并说明失败
  检测、暂停、回滚和发布观察窗口。
- 第一次 Push 不得直接触发全量生产部署。流水线应具有首次发布人工审批门禁，
  由 于海龙 指导部署、灰度扩容、指标观察、停止条件和回滚验证。

## 有状态工作负载

- StatefulSet 配套 Headless Service、`spec.serviceName` 和
  `volumeClaimTemplates`，明确应用容量及拓扑语义。应用侧模板不固定
  `storageClassName`；生成的 RWO 基线由运维服务器按存储平台覆盖或复核。
- 使用正确字段 `spec.persistentVolumeClaimRetentionPolicy`。组织默认
  `whenScaled: Retain`、`whenDeleted: Retain`；删除必须经过数据生命周期审批。
- 单 PVC 的 RWO 业务工作负载不得盲目多副本或滚动并发挂载。需要横向扩展时
  使用 RWX、每副本独立卷或把状态外置。
- PVC 不是备份。定义加密、快照/备份、异地副本、保留期限、访问权限、RTO、
  RPO 和定期恢复演练。
