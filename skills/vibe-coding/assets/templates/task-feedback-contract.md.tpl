# 逐任务反馈合同

机器可读合同：`docs/evidence/tasks/__TASK_ID__-feedback.json`。

## 任务

- Task ID：`__TASK_ID__`
- Current Commit：`__CURRENT_COMMIT__`
- Environment：`__ENVIRONMENT__`
- 业务/Spec 引用：__BUSINESS_GOAL_REFS__
- 目标：__TARGET__
- 修改范围：__ALLOWED_FILES_AND_MODULES__
- 回滚方式：__ROLLBACK_METHOD__

## 执行前基线

- 测量时间：__BASELINE_MEASURED_AT__
- 变更前 Commit：`__PRE_CHANGE_BASELINE_COMMIT__`
- 证据：`__BASELINE_EVIDENCE_PATH__`（绑定变更前 commit；失败测试可记录
  `status=expected_fail` 和非零退出码，且该 commit 必须是结果 commit 的祖先）

## 可观测信号与通过规则

| Signal ID | 来源 | 预期 | Pass/Fail 规则 | 验证命令 | 证据路径 |
| --- | --- | --- | --- | --- | --- |
| __SIGNAL_ID__ | __SOURCE__ | __EXPECTED__ | __PASS_FAIL_RULE__ | `__COMMAND__` | `__EVIDENCE_PATH__` |

每次修改后重新执行信号，比较结果与成功标准的距离。循环次数不是完成或停止条件；只有局部测试、
集成/E2E、适用 Eval、Runtime 信号和业务验收共同收敛才算完成。无法观测、不收敛、目标/架构
需改变、风险扩大或需要越权时暂停并给用户 2–3 个互斥选项。

结果 Evidence 必须位于项目内，记录当前 commit、环境、实际 argv 命令、退出码和所有信号的观测
结果；命令必须来自机器合同的 `verification_commands`。占位符、缺失文件和只有结论没有测量值的
声明不能通过门禁。`passed` 是冗余声明，验证器会根据 `operator`、`observed` 和 `expected`
重新计算；自填 `passed=true` 不能覆盖不满足的观测。
