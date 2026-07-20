{
  "$schema": "skills/vibe-coding/assets/schemas/project.schema.json",
  "schema_version": "1.0",
  "project_id": "__PROJECT_ID__",
  "name": "__PROJECT_NAME__",
  "status": "initializing",
  "repository": {
    "remote_url": "__REMOTE_URL__",
    "default_branch": "main",
    "feature_branch": "__FEATURE_BRANCH__",
    "baseline_commit": "__FULL_BASELINE_COMMIT_SHA__",
    "last_green_commit": "__FULL_LAST_GREEN_COMMIT_SHA__",
    "working_tree": "clean",
    "known_dirty_paths": []
  },
  "artifacts": {
    "spec": "docs/superpowers/specs/__DATE__-__TOPIC__-spec.json",
    "spec_sha256": "__SPEC_SHA256__",
    "design": "docs/superpowers/specs/__DATE__-__TOPIC__-design.md",
    "plan": "docs/superpowers/plans/__DATE__-__TOPIC__.md"
  },
  "documentation": {
    "organization": "__standard_OR_adapt_existing__",
    "content_review": "__DOCUMENTATION_REVIEW_PATH__",
    "paths": {
      "business_goal": "__BUSINESS_GOAL_PATH__",
      "system_architecture": "__SYSTEM_ARCHITECTURE_PATH__",
      "runtime_constraints": "__RUNTIME_CONSTRAINTS_PATH__",
      "test_plan": "__TEST_PLAN_PATH__",
      "traceability": "__TRACEABILITY_PATH__",
      "eval_plan": "__EVAL_PLAN_PATH__",
      "runbook": "__RUNBOOK_PATH__",
      "technical_debt_register": "__TECHNICAL_DEBT_REGISTER_PATH__",
      "agent_rules_audit": "__AGENT_RULES_AUDIT_PATH__",
      "qa_normalized_spec": "__QA_NORMALIZED_SPEC_PATH__",
      "qa_test_design": "__QA_TEST_DESIGN_PATH__",
      "qa_test_cases": "__QA_TEST_CASES_PATH__"
    },
    "conditional_paths": {
      "algorithm_design": null,
      "ui_spec": null
    }
  },
  "risk": {
    "tier": "__RISK_TIER__",
    "source": "docs/superpowers/specs/__DATE__-__TOPIC__-spec.json#/delivery_risk_profile"
  },
  "owners": {
    "business": "__BUSINESS_OWNER__", "product": "__PRODUCT_OWNER__",
    "engineering": "__ENGINEERING_OWNER__", "qa": "__QA_OWNER__", "decision": "__DECISION_OWNER__"
  },
  "commands": {
    "install": ["__INSTALL_EXECUTABLE__", "__INSTALL_ARG__"],
    "start": ["__START_EXECUTABLE__", "__START_ARG__"],
    "stop": ["__STOP_EXECUTABLE__", "__STOP_ARG__"],
    "build": ["__BUILD_EXECUTABLE__", "__BUILD_ARG__"],
    "pre_commit_full": ["__PRE_COMMIT_EXECUTABLE__", "__PRE_COMMIT_ARG__"],
    "test_full": ["__TEST_EXECUTABLE__", "__TEST_ARG__"],
    "eval_full": ["__EVAL_EXECUTABLE__", "__EVAL_ARG__"],
    "smoke": ["__SMOKE_EXECUTABLE__", "__SMOKE_ARG__"],
    "health_check": ["__HEALTH_EXECUTABLE__", "__HEALTH_ARG__"],
    "business_e2e": ["__BUSINESS_E2E_EXECUTABLE__", "__BUSINESS_E2E_ARG__"]
  },
  "command_timeouts_seconds": {
    "default": 300, "install": 600, "start": 120, "stop": 120, "build": 600,
    "pre_commit_full": 1800, "test_full": 1800, "eval_full": 1800,
    "smoke": 300, "health_check": 120, "business_e2e": 1800
  },
  "verification": {
    "check_inventory": ["build", "pre_commit_full", "test_full", "eval_full", "start", "health_check", "smoke", "stop", "business_e2e"],
    "runtime": {
      "check_names": ["start", "health_check", "smoke", "stop"],
      "required_evidence_fields": ["health_endpoint", "smoke_result", "restart_result"]
    },
    "business": {
      "check_names": ["business_e2e"],
      "required_evidence_fields": ["scenario_results", "observable_signals"]
    },
    "applicability": {
      "format_static_type": {"status": "required", "reason": "Required by the approved test plan.", "evidence": "__TEST_PLAN_PATH__", "approved_by": "__QA_OWNER__"},
      "unit": {"status": "required", "reason": "Required by the approved test plan.", "evidence": "__TEST_PLAN_PATH__", "approved_by": "__QA_OWNER__"},
      "integration": {"status": "required", "reason": "Required by the approved test plan.", "evidence": "__TEST_PLAN_PATH__", "approved_by": "__QA_OWNER__"},
      "business_e2e": {"status": "required", "reason": "Business success must be observed end to end.", "evidence": "__TEST_PLAN_PATH__", "approved_by": "__QA_OWNER__"},
      "permissions": {"status": "required", "reason": "Required by the approved test plan.", "evidence": "__TEST_PLAN_PATH__", "approved_by": "__QA_OWNER__"},
      "ui_accessibility": {"status": "required", "reason": "Required when the product has a business UI.", "evidence": "__TEST_PLAN_PATH__", "approved_by": "__QA_OWNER__"},
      "performance_cost": {"status": "required", "reason": "Required by the approved test plan.", "evidence": "__TEST_PLAN_PATH__", "approved_by": "__QA_OWNER__"},
      "recovery_rollback": {"status": "required", "reason": "Recovery behavior must be proven.", "evidence": "__TEST_PLAN_PATH__", "approved_by": "__QA_OWNER__"},
      "eval": {"status": "required", "reason": "Every project needs an acceptance Eval, deterministic or model-based.", "evidence": "__EVAL_PLAN_PATH__", "approved_by": "__QA_OWNER__"}
    }
  },
  "features": {"algorithmic": false, "business_ui": false},
  "technical_debt": {
    "strategy": "minimum_safe", "approved_by": "__DECISION_OWNER__",
    "decision_record": "__TECHNICAL_DEBT_REGISTER_PATH__",
    "excluded_debt_ids": ["__EXCLUDED_TD_ID__"], "excluded_paths": ["__EXCLUDED_PATH__"]
  },
  "pre_commit": {"hook_path": ".githooks/pre-commit", "full_suite": true},
  "delivery": {
    "collaboration": "__single_owner_OR_multi_person__",
    "change_size": "__small_OR_large__",
    "direct_push_permitted": true,
    "explicit_pr_required": false,
    "change_dimensions": {
      "architecture": false, "public_api": false, "data_schema": false,
      "permissions": false, "dependency_or_integration": false,
      "migration_or_bulk_write": false, "technical_debt_or_refactor": false,
      "material_spec_or_plan": false, "critical_runtime": false
    },
    "mode": "direct_push", "requires_pr": false
  },
  "deployment": {
    "required": false,
    "sre_skill": "production-devops-sre",
    "target_environment": null,
    "lifecycle_status": "not_started"
  }
}
