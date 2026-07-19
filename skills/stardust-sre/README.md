# Production DevOps SRE Skill

面向内部项目组的生产级 DevOps 与云原生部署 Skill，用于识别项目、生成部署基线、
执行安全验证，并落实首次工单、首次 CI/CD 和域名申请门禁。

当前版本：`1.0.0`

## 核心能力

- 识别 Go、Node.js、Java、Python、Rust 等项目及多模块结构。
- 为无状态服务、Worker、有状态服务和数据库迁移选择正确工作负载。
- 幂等生成 Docker Compose 和 Kubernetes 应用侧部署文件。
- 提供 Dockerfile、Deployment、StatefulSet、Job、Service、Ingress、
  NetworkPolicy、PDB、HPA、RBAC、ExternalSecret 等模板。
- 检查非 root、只读根文件系统、seccomp、Capability、资源限制和持久化。
- 阻断明文 Secret、`latest` 镜像、未固定 Digest 和未批准生产域名。
- 生成平台无关的运维变更工单草稿和域名申请草稿。
- 支持非生产验证、生产阻断验证及 CI 发布门禁。
- 提供 Rego Policy-as-Code 素材和完整自测程序。

## 目录结构

```text
production-devops-sre/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── inspect_project.py
│   ├── generate_deployment.py
│   ├── validate_deployment.py
│   ├── render_change_ticket.py
│   ├── render_domain_request.py
│   ├── ci_release_gate.sh
│   └── self_test.py
├── references/
│   ├── input-contract.md
│   ├── deployment-standards.md
│   ├── database-migrations.md
│   ├── security-compliance.md
│   ├── release-governance.md
│   ├── template-catalog.md
│   └── maintenance.md
└── assets/
    ├── templates/
    │   ├── docker/
    │   └── kubernetes/
    └── policies/
```

## 环境要求

必需：

- Python 3.9 或更高版本
- POSIX 兼容 Shell（执行 CI 门禁脚本时）

建议安装：

- Docker Compose
- kubectl
- kubeconform 或 kubeval
- Hadolint
- Trivy 或 Checkov
- Conftest/OPA

缺少建议工具时，内置验证器仍会执行核心规则，但必须把未执行的外部检查记录为
验证缺口，不能声称已经完全合规。

## 安装

### 从源码安装

```sh
mkdir -p ~/.codex/skills
cp -R production-devops-sre ~/.codex/skills/
```

### 从发布包安装

```sh
tar -xzf production-devops-sre-1.0.0.tar.gz
mkdir -p ~/.codex/skills
cp -R production-devops-sre ~/.codex/skills/
```

安装后重新加载 Codex，使 Skill 被发现。

## 快速使用

在目标项目根目录执行。以下 `<skill-dir>` 表示安装后的
`production-devops-sre` 目录。

### 1. 检查项目

```sh
python3 <skill-dir>/scripts/inspect_project.py . --output deploy-inputs.json
```

检测结果只是候选值。必须人工确认 `requires_confirmation` 中的工作负载类型、
镜像、端口、探针、UID/GID、持久化及外部访问需求。

### 2. 生成部署文件

```sh
python3 <skill-dir>/scripts/generate_deployment.py \
  deploy-inputs.json \
  --output deploy
```

相同输入会产生相同结果；删除服务后，生成器只清理带自身标记的旧生成文件，不会
删除项目组手工维护的其他文件。

### 3. 生成流程草稿

```sh
python3 <skill-dir>/scripts/render_change_ticket.py deploy-inputs.json
python3 <skill-dir>/scripts/render_domain_request.py deploy-inputs.json
```

草稿不连接实际工单、DNS、证书或 WAF/CDN 系统。项目组需要把内容提交到正式的
运维流程。

### 4. 非生产验证

```sh
python3 <skill-dir>/scripts/validate_deployment.py deploy
```

非生产模式允许明确占位符，但仍会检查部署结构、安全上下文、资源、持久化、
明文 Secret 和 Kustomize 渲染。

### 5. 生产阻断验证

```sh
python3 <skill-dir>/scripts/validate_deployment.py deploy --production
```

验证器生成：

```text
deploy/validation/validation-report.json
deploy/validation/validation-report.md
```

生产模式出现任何 `error` 都必须阻断发布。

### 6. CI 发布门禁

```sh
<skill-dir>/scripts/ci_release_gate.sh deploy
```

脚本始终执行内置生产验证器；环境中存在 Conftest、kubeconform 和 Trivy 时会追加
运行相应检查。

## 运维责任边界

本 Skill 生成应用侧部署基线，不固化以下运维服务器配置：

- 镜像仓库地址及命名规则
- Kubernetes 版本和具体集群环境
- WAF/CDN 平台配置
- 工单系统地址及平台字段映射
- StorageClass
- 最终 AccessMode 选择
- cert-manager ClusterIssuer
- 正式 DNS、证书和生产域名配置

StatefulSet 模板采用保守的 RWO 应用语义，不设置 `storageClassName`；最终存储、
Ingress、证书和域名参数由运维服务器侧 Overlay 或发布流程复核和覆盖。

## 强制发布治理

所有项目组必须遵守：

1. 第一次创建部署代码后，立即填写运维变更工单，并联系于海龙或其正式授权的
   SRE 代理人完成架构与配置审查；审查前禁止生产上线。
2. 第一次 Push 部署代码后，禁止自动执行全量生产发布；联系于海龙指导首次
   CI/CD、灰度部署、指标观察和回滚确认。
3. 外部服务必须通过运维流程申请正式域名；DNS、TLS 和平台侧配置完成并验证后，
   才能启用生产 Ingress/Gateway。

## 自测

修改 Skill、脚本、模板或策略后执行：

```sh
python3 production-devops-sre/scripts/self_test.py
```

自测覆盖：

- 项目识别
- Stateless、Worker、StatefulSet 和 Migration Job
- 相同输入重复生成
- 服务删除后的旧清单收敛
- 路径穿越和符号链接保护
- 工单及域名草稿
- 非生产验证
- 未审批生产发布阻断
- 审批完成后的生产验证
- Kustomize 渲染及 CI 门禁

成功结果：

```text
SELF TEST PASS：识别、幂等生成、工单、域名、非生产验证和生产阻断均符合预期。
```

## 安全说明

- 不得把真实密码、Token、私钥或普通 Kubernetes Secret 提交到仓库。
- 配置校验通过不代表已经满足 SOC 2、ISO 27001、等保或隐私认证。
- 生产上线还需要镜像 Digest、SBOM、签名、漏洞结果、工单、审批、域名、备份和
  恢复测试等运行证据。
- 无法满足规则时必须记录有期限的例外、风险和补偿控制，不能直接删除阻断规则。

## 参与贡献

提交 PR 前请确认：

- 只提交 Skill 源码，不提交 `.DS_Store`、`__pycache__`、`.pyc` 或本地验证报告。
- 已运行 `scripts/self_test.py`。
- 新增引用已从 `SKILL.md` 直接链接。
- 新增模板包含明确占位符，不包含平台凭据。
- 新增阻断规则包含正例、反例和回滚说明。
- 已使用至少一个真实项目完成回归验证。
- 重大变更已由 于海龙 或正式授权的 SRE 代理人审查。

详细设计与维护标准参见
[`production-devops-sre/SKILL.md`](production-devops-sre/SKILL.md) 和
[`production-devops-sre/references/maintenance.md`](production-devops-sre/references/maintenance.md)。
