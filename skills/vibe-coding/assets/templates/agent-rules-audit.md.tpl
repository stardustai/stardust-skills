# Agent 规则合规审计

## 已读取规则

| 来源文件 | 生效范围 | 指向的共享规则 | 读取时间 | 校验值/Commit |
| --- | --- | --- | --- | --- |
| __RULE_FILE__ | __SCOPE__ | __CANONICAL_RULE_FILE__ | __READ_AT__ | __VERSION_EVIDENCE__ |

必须读取当前工作目录及所有父级作用域中的 `AGENTS.md` / `AGENT.md` 和其明确指向的共享规则。
Graphify 不是公司通用门禁，不在本审计中强制。

## 合规矩阵

| Rule ID | 规则原文/准确摘要 | 检查对象 | 证据 | 状态 | 分类 | TD-ID/准备缺口 | 修复与验证 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| __RULE_ID__ | __RULE_TEXT__ | __CHECK_TARGET__ | __EVIDENCE__ | pass/fail/not_applicable | structural/readiness/process | __LINK__ | __REMEDIATION_AND_VERIFICATION__ |

分类规则：固化在代码或架构中的违规属于技术债；缺测试入口、文档、Remote 或 Pre-commit 属于
工程准备缺口；Agent 沟通或执行方式违规属于过程违规。

## 阻断项

__BLOCKERS_OR_NONE__

## 审计结论

- 初始化是否可以完成：__INITIALIZATION_READY__
- 未关闭技术债：__OPEN_TECHNICAL_DEBT__
- 未关闭工程准备缺口：__OPEN_READINESS_GAPS__
- 审核人 / 时间：__REVIEWER__ / __REVIEWED_AT__
