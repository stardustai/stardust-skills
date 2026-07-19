# 模板目录与选用条件

模板是生成素材，不是无需判断即可部署的成品。复制后必须替换全部 `__...__`
变量并通过生产验证器。

## Docker

- `assets/templates/docker/go.Dockerfile.tpl`：标准 Go 二进制项目，需确认入口包。
- `assets/templates/docker/node.Dockerfile.tpl`：具有 lockfile 和 `npm run build` 的
  Node.js 项目，需确认实际构建器和入口。
- `assets/templates/docker/java.Dockerfile.tpl`：Maven Wrapper 项目，Gradle 项目需
  按实际构建工具改写。
- `assets/templates/docker/nginx.Dockerfile.tpl` 与 `nginx.conf.tpl`：静态前端，
  使用非 root 8080 端口和 `/tmp` 临时目录。

所有基础镜像变量由项目构建流水线或运维环境提供，Skill 不固化镜像仓库地址和
命名规则。

## Kubernetes 默认生成

生成器根据工作负载类型使用 Namespace、ServiceAccount、ConfigMap、Deployment、
Worker Deployment、StatefulSet、Migration Job、Service、Headless Service、
Ingress、NetworkPolicy 和 PDB 模板。Kustomization 按实际资源动态生成。

## Kubernetes 可选模板

- `hpa.yaml.tpl`：仅在无状态、指标可用、容量测试完成后启用。
- `resource-quota.yaml.tpl`、`limit-range.yaml.tpl`：仅在 Namespace 资源预算由运维
  确认后启用。
- `role.yaml.tpl`、`role-binding.yaml.tpl`：只有应用确实访问 Kubernetes API 且
  最小权限规则经过审查时启用；否则保持 Token 自动挂载关闭。
- `external-secret.yaml.tpl`：只有集群安装对应 CRD，且运维已分配 SecretStore 和
  远程键映射后启用。不得在模板中放真实 Secret。

IngressClass、ClusterIssuer、StorageClass、最终 AccessMode、WAF/CDN 和 DNS 目标
由运维服务器侧 Overlay 或发布流程负责，应用模板不固化这些平台值。

## Policy as Code

`assets/policies/` 提供 Conftest/OPA 策略素材，覆盖非 root、只读根、seccomp、
资源、Capability、镜像 Digest、latest、普通 Secret、域名审批和 NetworkPolicy
基线。项目 CI 使用前必须在实际 Conftest/OPA 版本上编译验证；无该工具时以内置
`validate_deployment.py` 作为核心阻断器，并把 Rego 未执行记录为验证缺口。

`scripts/ci_release_gate.sh` 用于 CI 生产阶段，始终运行内置生产验证器，并在环境
存在时附加运行 Conftest、kubeconform 和 Trivy。工具缺失不会被伪装成已执行；
组织若要求这些工具为强制门禁，应在流水线镜像中预装并另行检查其存在。
