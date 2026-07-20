# Pull Request Standard

状态：滚动设计稿。

## 1. 何时可以直接 Push 或 Merge

项目是否多人协作不单独决定 PR。满足以下条件时可以直接 Push 或 Merge：

- 项目为个人 Own，或者变更属于小功能；
- 操作者拥有直接 Push 权限；
- 仓库规则允许直接 Push；
- 风险为 R0 或 R1；
- 不改变架构、公共接口、数据结构、权限或生产迁移；
- 完整测试和适用 Eval 已通过；
- 变更可以独立回滚。

第一项是“个人 Own 或小功能”的或关系，再与其余条件组成与关系。多人协作项目中的
小功能可以直接 Push；个人 Own 项目中的较大功能也可以直接 Push，但仍不能绕过
R2/R3、结构性变更或仓库规则等独立 PR 条件。

小功能指单一职责、局部模块、不改变既有合同、可以独立测试和回滚的变更，不以
代码行数判断。

## 2. 何时必须 PR

满足任一条件：

- 多人协作项目中的大功能；
- R2 或 R3；
- 架构、公共接口、数据模型或权限变化；
- 新增外部依赖或系统集成；
- 数据迁移、批量写入或关键运行方式变化；
- 本轮包含技术债修复或局部重构；
- Spec 或 Plan 发生实质变化；
- 仓库保护规则要求 PR；
- 用户明确要求 PR 或 Pair Review。

## 3. 创建前门禁

- 所有计划任务已经完成；
- Pre-commit 未被绕过；
- 完整测试和全部适用 Eval 使用本轮新鲜结果通过；
- Spec、Design、Plan、代码和追踪关系一致；
- 技术债登记和关闭状态已更新；
- Runtime、Runbook 和回滚方式已验证；
- 功能分支已 Push 到确认的 Remote。

## 4. PR 必须包含

- Spec、Design、Plan 和任务 ID 链接；
- 业务目标、本次范围和明确不包含的内容；
- 架构、公共接口、数据、权限和依赖变化；
- 主要代码变更及文件范围；
- 技术债发现、修复和关闭记录；
- 完整测试命令、退出码和结果；
- Eval Case、版本、指标、失败案例和结果；
- Runtime 与 Smoke Test 证据；
- 风险、已知限制和回滚方式；
- Reviewer 需要重点判断的问题；
- 是否启用部署，以及部署状态。

## 5. 自动 Review

PR 创建后，必须由独立测试/审查 Agent：

1. 使用独立上下文，从正式 Spec、Design、Plan、Commit SHA 和 Diff 开始；
2. 检查 Spec 覆盖和计划外实现；
3. 检查架构偏离、新技术债、数据、权限、依赖和恢复风险；
4. 重新执行完整测试和 Eval，不信任实现 Agent 的自述；
5. 核对 Runtime、Smoke 和回滚证据；
6. 输出通过、阻断问题、非阻断问题和实际证据；
7. 问题修复后重新 Review。

实现 Agent 的自查不能替代独立 Review。

## 6. 人工 Review 与 Merge

- 是否要求人类 Reviewer，由工程团队和仓库规则决定；
- AI Review 是公司默认自动门禁，但不修改仓库已有的人工审批策略；
- 是否允许 Auto-merge 同样由工程团队和仓库规则决定；
- 安全、合规或更高层公司政策明确要求人工批准时，项目不得降低要求；
- 测试或 Eval 失败时，任何 Reviewer 都不能批准合并。

建议在 PROJECT.yaml 中记录：

```yaml
pull_request:
  automated_review: required
  automated_test: required
  human_review: repository_defined
  auto_merge: repository_defined
```

## 7. Review 严重度

- Critical：阻断合并，修复后重新执行完整相关验证和 Review。
- Important：合并前修复并重新 Review。
- Minor：修复或在 PR 中明确记录处理决定。

Reviewer 意见与代码事实冲突时，用代码、测试、运行和 Spec 证据裁决，不因 Reviewer
身份自动接受或拒绝。
