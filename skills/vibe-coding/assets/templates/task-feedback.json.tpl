{
  "$schema": "skills/vibe-coding/assets/schemas/task-feedback.schema.json",
  "schema_version": "1.0",
  "task_id": "__TASK_ID__",
  "current_commit": "__CURRENT_COMMIT__",
  "environment": "__ENVIRONMENT__",
  "business_goal_refs": ["__SCENARIO_OR_REQUIREMENT_ID__"],
  "target": "__OBSERVABLE_TARGET__",
  "observable_signals": [
    {
      "signal_id": "__SIGNAL_ID__",
      "source": "__SIGNAL_SOURCE__",
      "expected": "__EXPECTED_VALUE_OR_BEHAVIOR__"
    }
  ],
  "baseline": {
    "measured_at": "__ISO_8601_TIMESTAMP__",
    "commit": "__PRE_CHANGE_BASELINE_COMMIT__",
    "environment": "__ENVIRONMENT__",
    "evidence_paths": ["docs/evidence/tasks/__TASK_ID__-baseline.json"]
  },
  "pass_fail_rules": [
    {
      "rule_id": "__RULE_ID__",
      "signal_id": "__SIGNAL_ID__",
      "operator": "__SUPPORTED_OPERATOR__",
      "expected": "__EXPECTED_VALUE__"
    }
  ],
  "verification_commands": [
    ["__CHECK_EXECUTABLE__", "__CHECK_ARG__"]
  ],
  "evidence_paths": ["docs/evidence/tasks/__TASK_ID__-result.json"],
  "rollback_method": "__ROLLBACK_METHOD__"
}
