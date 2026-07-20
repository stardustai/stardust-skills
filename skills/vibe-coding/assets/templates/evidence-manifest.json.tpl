{
  "$schema": "skills/vibe-coding/assets/schemas/evidence-manifest.schema.json",
  "schema_version": "1.0",
  "run_id": "__UUID_RUN_ID__",
  "phase": "full",
  "project_root": "__ABSOLUTE_PROJECT_ROOT__",
  "git": {
    "commit": "__FULL_DELIVERY_COMMIT_SHA__",
    "branch": "__FEATURE_BRANCH__",
    "clean": true
  },
  "started_at": "__ISO_8601_START__",
  "finished_at": "__ISO_8601_FINISH__",
  "checks": [
    {
      "name": "test_full",
      "command": ["__EXACT_PROJECT_TEST_EXECUTABLE__", "__EXACT_PROJECT_TEST_ARG__"],
      "timeout_seconds": 1800,
      "started_at": "__ISO_8601_CHECK_START__",
      "finished_at": "__ISO_8601_CHECK_FINISH__",
      "status": "passed",
      "exit_code": 0,
      "stdout": {"byte_count": 0, "sha256": "__SHA256__", "summary": "[no output]"},
      "stderr": {"byte_count": 0, "sha256": "__SHA256__", "summary": "[no output]"}
    },
    {
      "name": "eval_full",
      "command": ["__EXACT_PROJECT_EVAL_EXECUTABLE__", "__EXACT_PROJECT_EVAL_ARG__"],
      "timeout_seconds": 1800,
      "started_at": "__ISO_8601_CHECK_START__",
      "finished_at": "__ISO_8601_CHECK_FINISH__",
      "status": "passed",
      "exit_code": 0,
      "stdout": {"byte_count": 0, "sha256": "__SHA256__", "summary": "[no output]"},
      "stderr": {"byte_count": 0, "sha256": "__SHA256__", "summary": "[no output]"}
    }
  ]
}
