{
  "$schema": "skills/vibe-coding/assets/schemas/review-evidence.schema.json",
  "schema_version": "1.0",
  "commit": "__FULL_REVIEWED_COMMIT_SHA__",
  "author_agent_id": "__IMPLEMENTATION_AGENT_ID__",
  "status": "pass",
  "reviews": [
    {"review_type": "spec", "reviewer_id": "__SPEC_REVIEW_AGENT_ID__", "execution_context_id": "__SPEC_REVIEW_RUN_ID__", "reviewed_artifacts": ["__SPEC_PATH__", "__DESIGN_PATH__", "__PLAN_PATH__", "git:diff:__BASELINE__..__HEAD__"], "status": "pass", "findings_count": 0, "blocking_findings": 0, "evidence_uri": "docs/evidence/review/spec-review.json"},
    {"review_type": "code_quality", "reviewer_id": "__CODE_REVIEW_AGENT_ID__", "execution_context_id": "__CODE_REVIEW_RUN_ID__", "reviewed_artifacts": ["__SPEC_PATH__", "__DESIGN_PATH__", "__PLAN_PATH__", "git:diff:__BASELINE__..__HEAD__"], "status": "pass", "findings_count": 0, "blocking_findings": 0, "evidence_uri": "docs/evidence/review/code-review.json"},
    {"review_type": "independent_test", "reviewer_id": "__TEST_REVIEW_AGENT_ID__", "execution_context_id": "__TEST_REVIEW_RUN_ID__", "reviewed_artifacts": ["__SPEC_PATH__", "__DESIGN_PATH__", "__PLAN_PATH__", "git:diff:__BASELINE__..__HEAD__"], "status": "pass", "findings_count": 0, "blocking_findings": 0, "evidence_uri": "docs/evidence/review/test-review.json"}
  ],
  "independent_verification": {
    "commit": "__FULL_REVIEWED_COMMIT_SHA__",
    "checks": [
      {"name": "test_full", "command": ["__TEST_EXECUTABLE__", "__TEST_ARG__"], "exit_code": 0, "captured_at": "__ISO_8601_REVIEW_TIME__", "evidence_manifest": "docs/evidence/review/independent-full.json", "evidence_sha256": "__INDEPENDENT_EVIDENCE_SHA256__"},
      {"name": "eval_full", "command": ["__EVAL_EXECUTABLE__", "__EVAL_ARG__"], "exit_code": 0, "captured_at": "__ISO_8601_REVIEW_TIME__", "evidence_manifest": "docs/evidence/review/independent-full.json", "evidence_sha256": "__INDEPENDENT_EVIDENCE_SHA256__"}
    ]
  },
  "runtime_evidence": {
    "health_endpoint": {"check_name": "health_check", "evidence_manifest": "docs/evidence/full-latest.json", "evidence_sha256": "__FULL_EVIDENCE_SHA256__", "observed": "__OBSERVED_HEALTH__"},
    "smoke_result": {"check_name": "smoke", "evidence_manifest": "docs/evidence/full-latest.json", "evidence_sha256": "__FULL_EVIDENCE_SHA256__", "observed": "__OBSERVED_SMOKE__"},
    "restart_result": {"check_name": "start", "evidence_manifest": "docs/evidence/full-latest.json", "evidence_sha256": "__FULL_EVIDENCE_SHA256__", "observed": "__OBSERVED_RESTART__"}
  },
  "attestation": {"provider": "__REVIEW_RUNTIME_PROVIDER__", "run_id": "__REVIEW_RUN_ID__", "artifact_uri": "docs/evidence/review/attestation.json"},
  "reviewed_at": "__ISO_8601_REVIEW_TIME__",
  "pull_request_url": null
}
