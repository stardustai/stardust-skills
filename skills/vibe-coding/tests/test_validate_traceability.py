import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "validate_traceability.py"


class ValidateTraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=self.root, check=True)
        self.commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout.strip()
        self.spec = self.root / "spec.json"
        self.trace = self.root / "traceability.json"
        self.evidence = self.root / "docs" / "evidence" / "BIZ-001.json"
        self.manifest = self.root / "docs" / "evidence" / "business-run.json"
        self.evidence.parent.mkdir(parents=True)
        self.spec_data = {
            "business_success_scenarios": [
                {
                    "scenario_id": "BIZ-001",
                    "scope_status": "in_scope",
                    "priority": "critical",
                    "business_owner": "business@example.com",
                    "success_signals": ["SIG-001"],
                    "expected_business_outcome": "The order completes successfully",
                    "expected_final_state": ["completed"],
                    "confirmation": {"confirmed_version": "1.5"},
                },
                {"scenario_id": "BIZ-002", "scope_status": "out_of_scope", "priority": "critical"},
            ],
            "validation_plan": {
                "scenario_coverage": [
                    {
                        "scenario_id": "BIZ-001",
                        "qa_status": "approved",
                        "qa_case_refs": ["QA-001"],
                        "automation_requirement": "required",
                        "automation_plan_status": "verified",
                        "automated_test_refs": ["E2E-001"],
                        "evaluation_asset_refs": ["EVAL-001"],
                        "owner": "qa@example.com",
                    }
                ]
            },
        }
        self.trace_data = {
            "schema_version": "1.0",
            "mappings": [
                {
                    "scenario_id": "BIZ-001",
                    "qa_case_refs": ["QA-001"],
                    "automated_test_refs": ["E2E-001"],
                    "evaluation_asset_refs": ["EVAL-001"],
                    "business_signal_refs": ["SIG-001"],
                    "business_signal_rules": [{"signal_id": "SIG-001", "source": "completed-order-record", "operator": "equals", "expected": "order completed"}],
                    "business_owner_approval": {"approved_by": "business@example.com", "confirmed_version": "1.5"},
                    "verification_commands": [["python3", "-c", "print('ok')"]],
                    "evidence_paths": ["docs/evidence/BIZ-001.json"],
                }
            ],
        }
        self.write_files()

    def tearDown(self):
        self.tmp.cleanup()

    def write_files(self, *, age_minutes=1, status="pass", evidence_commit=None, environment="test"):
        self.spec.write_text(json.dumps(self.spec_data), encoding="utf-8")
        self.trace.write_text(json.dumps(self.trace_data), encoding="utf-8")
        captured_at = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
        manifest = {
            "$schema": "skills/vibe-coding/assets/schemas/evidence-manifest.schema.json",
            "schema_version": "1.0", "run_id": "33333333-3333-4333-8333-333333333333",
            "phase": "full", "project_root": str(self.root.resolve()),
            "git": {"commit": evidence_commit or self.commit, "branch": "master", "clean": True},
            "started_at": captured_at.isoformat(), "finished_at": captured_at.isoformat(),
            "checks": [{
                "name": "business_e2e", "command": ["python3", "-c", "print('ok')"],
                "timeout_seconds": 300, "started_at": captured_at.isoformat(), "finished_at": captured_at.isoformat(),
                "status": "passed" if status == "pass" else "failed", "exit_code": 0 if status == "pass" else 1,
                "stdout": {"byte_count": 0, "sha256": "a" * 64, "summary": "[no output]"},
                "stderr": {"byte_count": 0, "sha256": "b" * 64, "summary": "[no output]"},
            }],
        }
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        self.evidence.write_text(
            json.dumps(
                {
                    "$schema": "skills/vibe-coding/assets/schemas/business-evidence.schema.json",
                    "schema_version": "1.0",
                    "scenario_id": "BIZ-001",
                    "commit": evidence_commit or self.commit,
                    "environment": environment,
                    "captured_at": captured_at.isoformat(),
                    "status": status,
                    "business_passed": status == "pass",
                    "expected_business_outcome": "The order completes successfully",
                    "expected_final_state": ["completed"],
                    "runner_check_name": "business_e2e",
                    "evidence_manifest": "docs/evidence/business-run.json",
                    "evidence_sha256": hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
                    "business_observations": [
                        {
                            "signal_id": "SIG-001",
                            "source": "completed-order-record",
                            "expected": "order completed",
                            "observed": "order completed" if status == "pass" else "order pending",
                            "passed": status == "pass",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def run_validator(self, *extra):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(self.root),
                "--spec",
                str(self.spec),
                "--traceability",
                str(self.trace),
                "--environment",
                "test",
                *extra,
            ],
            capture_output=True,
            text=True,
        )

    def test_accepts_authoritative_mapping_and_fresh_business_evidence(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_unmapped_critical_scenario(self):
        self.trace_data["mappings"] = []
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BIZ-001", result.stderr)

    def test_rejects_qa_and_automation_refs_that_disagree_with_spec(self):
        mapping = self.trace_data["mappings"][0]
        mapping["qa_case_refs"] = ["QA-INVENTED"]
        mapping["automated_test_refs"] = ["E2E-INVENTED"]
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("qa_case_refs must match", result.stderr)
        self.assertIn("automated_test_refs must match", result.stderr)

    def test_rejects_business_signals_that_disagree_with_business_owned_spec(self):
        self.trace_data["mappings"][0]["business_signal_refs"] = ["SIG-INVENTED"]
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("business_signal_refs must match", result.stderr)

    def test_rejects_unapproved_or_unverified_authoritative_coverage(self):
        coverage = self.spec_data["validation_plan"]["scenario_coverage"][0]
        coverage["qa_status"] = "drafted"
        coverage["automation_plan_status"] = "planned"
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("qa_status must be approved", result.stderr)
        self.assertIn("automation_plan_status must be verified", result.stderr)

    def test_rejects_evidence_path_outside_project_root(self):
        outside = self.root.parent / f"{self.root.name}-outside.json"
        outside.write_text(self.evidence.read_text(encoding="utf-8"), encoding="utf-8")
        self.trace_data["mappings"][0]["evidence_paths"] = [str(outside)]
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be a project-relative path", result.stderr)
        outside.unlink()

    def test_rejects_missing_or_declaration_only_evidence(self):
        self.evidence.unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)
        self.evidence.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scenario_id", result.stderr)
        self.assertIn("business_observations", result.stderr)

    def test_rejects_stale_failed_or_wrong_commit_environment_evidence(self):
        self.write_files(age_minutes=120, status="fail", evidence_commit="deadbeef", environment="staging")
        result = self.run_validator("--max-age-minutes", "60")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale", result.stderr)
        self.assertIn("current commit", result.stderr)
        self.assertIn("environment must be test", result.stderr)
        self.assertIn("status must be pass", result.stderr)

    def test_rejects_business_observation_that_does_not_cover_or_pass_signal(self):
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["business_observations"][0]["signal_id"] = "SIG-INVENTED"
        evidence["business_observations"][0]["passed"] = False
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("business_observations must cover", result.stderr)
        self.assertIn("business_passed must be true", result.stderr)

    def test_rejects_uncontracted_business_observation(self):
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["business_observations"].append(
            {
                "signal_id": "SIG-INVENTED",
                "source": "invented-source",
                "expected": "invented",
                "observed": "invented",
                "passed": True,
            }
        )
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no Business Owner-approved measurement rule", result.stderr)

    def test_rejects_placeholder_contract_values(self):
        self.trace_data["mappings"][0]["qa_case_refs"] = ["__QA_CASE_ID__"]
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("placeholder", result.stderr.lower())

    def test_rejects_placeholder_evidence_values(self):
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["business_observations"][0]["observed"] = "__OBSERVED_VALUE__"
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("placeholder", result.stderr.lower())

    def test_computes_business_result_instead_of_trusting_passed_true(self):
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["business_observations"][0].update(
            expected="wrong outcome", observed="wrong outcome", passed=True
        )
        evidence["expected_business_outcome"] = "wrong outcome"
        evidence["expected_final_state"] = "wrong state"
        evidence["business_passed"] = True
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Business Owner-confirmed", result.stderr)

    def test_requires_runner_generated_manifest_for_business_observation(self):
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["checks"][0]["command"] = ["python3", "-c", "print('not contracted')"]
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["evidence_sha256"] = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contracted verification command", result.stderr)

    def test_rejects_fresh_wrapper_around_stale_business_runner_manifest(self):
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        stale = "2020-01-01T00:00:00+00:00"
        manifest["started_at"] = stale
        manifest["finished_at"] = stale
        manifest["checks"][0]["started_at"] = stale
        manifest["checks"][0]["finished_at"] = stale
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["evidence_sha256"] = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence_manifest is stale", result.stderr)


if __name__ == "__main__":
    unittest.main()
