## Summary

- Task / Spec：__TASK_AND_SPEC_REFS__
- Business goal：__BUSINESS_GOAL__
- In scope：__IN_SCOPE__
- Out of scope：__OUT_OF_SCOPE__
- Risk tier：`__RISK_TIER__`

## Business success

| Scenario ID | Expected business outcome | QA / E2E / Eval | Fresh evidence | Business acceptance |
| --- | --- | --- | --- | --- |
| __SCENARIO_ID__ | __OUTCOME__ | __VERIFICATION__ | `__EVIDENCE_PATH__` | __ACCEPTANCE_STATUS__ |

## Implementation

- Design：`__DESIGN_PATH__`
- Plan：`__PLAN_PATH__`
- Changed components and why：__COMPONENT_CHANGES__
- Architecture/API/data/permission changes：__STRUCTURAL_CHANGES_OR_NONE__
- New or changed dependencies：__DEPENDENCIES_OR_NONE__

## Technical debt

- Strategy：`__DEBT_STRATEGY__`
- Debt fixed in separate Commit(s)：__DEBT_COMMITS__
- Open debt excluded from this implementation path：__EXCLUDED_DEBT_OR_NONE__

## Verification

- [ ] Versioned Pre-commit full suite passed
- [ ] Clean full test run passed
- [ ] Full acceptance Eval run passed (deterministic or model-based as applicable)
- [ ] Critical business-scenario traceability passed
- [ ] Runtime install/start/health/smoke/stop/restart checks passed
- [ ] Independent Spec review passed
- [ ] Independent code-quality review passed
- [ ] Independent test agent reran checks

| Check | Command | Result | Fresh evidence |
| --- | --- | --- | --- |
| __CHECK__ | `__COMMAND__` | __RESULT__ | `__EVIDENCE_PATH__` |

## Risk, operations, and rollback

- Data/security/privacy impact：__DATA_SECURITY_IMPACT__
- Runtime/cost/performance impact：__RUNTIME_IMPACT__
- Known limitations：__KNOWN_LIMITATIONS__
- Runbook：`docs/runbook.md`
- Rollback trigger and method：__ROLLBACK__
- Deployment：__DEPLOYMENT_STATUS_AND_TARGET__

## Reviewer focus

__REVIEWER_FOCUS__

是否需要人类 Review、是否允许自动 Merge 由仓库和工程团队规则决定；AI Review 不替代仓库
明确要求的人类审批，也不额外创造公司统一人审门禁。
