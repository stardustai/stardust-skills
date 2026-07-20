# 技术债登记

## 本轮策略

- 审计范围：__AUDIT_SCOPE__
- 选择：`full_remediation` / `minimum_safe`
- Decision Owner：__DECISION_OWNER__
- 确认时间：__APPROVED_AT__
- 独立修复 Plan / Commit：__REMEDIATION_PLAN_AND_COMMITS__

技术债是已有代码、架构或运行方式中的结构性问题：它会使后续修改更易出错、更难测试或恢复，
或持续依赖绕路与补丁。必须有代码或运行证据和明确风险。风格偏好、未批准功能、Spec 缺口、
边界清楚的普通 Bug、无实际风险的旧依赖，以及只因“更优雅”的重构不自动构成技术债。

## 登记表

| TD-ID | 结构性问题 | 代码/运行证据 | 影响模块 | 后续风险 | 本轮触及 | 全量方案 | 最小安全方案 | 验证 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| __TD_ID__ | __PROBLEM__ | __EVIDENCE__ | __MODULES__ | __RISK__ | __TOUCHED__ | __FULL_REMEDIATION__ | __MINIMUM_SAFE_REMEDIATION__ | __VERIFICATION__ | open/closed/deferred |

## 两种合法选择

1. `full_remediation`：关闭本轮系统化审计识别的全部技术债。
2. `minimum_safe`：修复本轮将修改或依赖的模块，以及影响正确性、测试性、权限、数据或运行稳定性
   的架构问题；所有未修复技术债必须从本轮实现路径排除。

只要功能触及已知技术债，该债务自动进入修复范围。禁止在坏架构上新增兼容层、特殊分支或补丁。

## 关闭证据

| TD-ID | 修复 Commit | 验证命令 | 新鲜证据 | Reviewer | 关闭时间 |
| --- | --- | --- | --- | --- | --- |
| __TD_ID__ | __COMMIT__ | __COMMAND__ | `__EVIDENCE_PATH__` | __REVIEWER__ | __CLOSED_AT__ |
