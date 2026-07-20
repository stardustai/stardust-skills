# 公司 Vibe Coding 独立标准索引

本目录保存公司 Vibe Coding 总控 Skill 的独立设计标准。总体架构和决策记录见
[`../2026-07-19-company-vibe-coding-design.md`](../2026-07-19-company-vibe-coding-design.md)。

## 已建立

| 文档 | 职责 | 状态 |
| --- | --- | --- |
| [`repository-template-standard.md`](repository-template-standard.md) | 仓库目录、README、PROJECT.yaml、Remote 和 Pre-commit 基线 | 滚动设计稿 |
| [`project-initialization-standard.md`](project-initialization-standard.md) | 已有项目进入功能开发前的初始化与架构修复 | 滚动设计稿 |
| [`technical-debt-standard.md`](technical-debt-standard.md) | 技术债定义、证据、修复范围和关闭条件 | 滚动设计稿 |
| [`pull-request-standard.md`](pull-request-standard.md) | PR 触发条件、内容、自动 Review、测试和 Merge 边界 | 滚动设计稿 |

## 已确认的 Spec 接口

公司 Vibe Coding 总控 Skill 接收 `spec-intake` v1.5 的 `engineering_ready` Spec。
业务端到端成功流程由 Business Owner 定义并确认，保存在顶层
`business_success_scenarios`；QA 和工程只通过
`validation_plan.scenario_coverage` 建立 QA 用例、自动化要求、Eval 资产和证据映射，
不得改写业务成功终态。详细总体约定见主设计稿“业务成功场景是编码输入合同”。
字段、职责和门禁细则由 `spec-intake/references/business-success-scenarios.md` 维护，
总控 Skill 只消费其已确认结果。

同一 v1.5 Spec 的 `delivery_risk_profile` 在产品阶段收集用户范围、数据敏感度、
写入影响、集成与权限、可恢复性和业务影响六个维度，按最高风险维度确定 R0-R3，
并由 Decision Owner 确认。字段、等级和门禁细则由
`spec-intake/references/delivery-risk-profile.md` 维护；总控 Skill 按该等级选择测试、
Review、Git、运行和部署深度，不在编码阶段自行降级。

## 待后续讨论后建立

- `risk-classification-standard.md`
- `project-yaml-standard.md`
- `interaction-and-change-control-standard.md`
- `testing-standard.md`
- `eval-standard.md`
- `ui-implementation-standard.md`
- `subagent-development-standard.md`
- `git-delivery-standard.md`
- `runtime-standard.md`
- `loop-engineering-standard.md`
- `incident-and-rescue-standard.md`
- `deployment-adapter-standard.md`
- `skill-evaluation-standard.md`
- `spec-input-contract-standard.md`

独立标准只记录已经确认的规则。尚未确认的问题保留在总体设计稿的“已确认但尚待
详细设计”章节，不在独立标准中自行补充答案。
