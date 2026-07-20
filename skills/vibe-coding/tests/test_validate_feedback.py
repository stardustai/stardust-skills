import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "validate_feedback.py"


class ValidateFeedbackTests(unittest.TestCase):
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
        evidence_dir = self.root / "docs" / "evidence" / "tasks"
        evidence_dir.mkdir(parents=True)
        self.contract = self.root / "feedback.json"
        self.baseline = evidence_dir / "TASK-001-baseline.json"
        self.result = evidence_dir / "TASK-001-result.json"
        self.contract_data = {
            "schema_version": "1.0",
            "task_id": "TASK-001",
            "current_commit": self.commit,
            "environment": "test",
            "business_goal_refs": ["BIZ-001"],
            "target": "The completed order is observable in the business record",
            "observable_signals": [
                {"signal_id": "SIG-001", "source": "completed-order-record", "expected": "order completed"}
            ],
            "baseline": {
                "measured_at": self.now(-2),
                "commit": self.commit,
                "environment": "test",
                "evidence_paths": ["docs/evidence/tasks/TASK-001-baseline.json"],
            },
            "pass_fail_rules": [
                {"rule_id": "RULE-001", "signal_id": "SIG-001", "operator": "equals", "expected": "order completed"}
            ],
            "verification_commands": [["python3", "-c", "print('verify')"]],
            "evidence_paths": ["docs/evidence/tasks/TASK-001-result.json"],
            "rollback_method": "Revert the task commit and rerun the full verification suite",
        }
        self.write_files()

    def tearDown(self):
        self.tmp.cleanup()

    def now(self, minutes):
        return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()

    def evidence_object(self, *, phase, passed=True, commit=None, environment="test", age_minutes=1):
        return {
            "schema_version": "1.0",
            "task_id": "TASK-001",
            "phase": phase,
            "commit": commit or self.commit,
            "environment": environment,
            "captured_at": self.now(-age_minutes),
            "status": "pass" if passed else ("expected_fail" if phase == "baseline" else "fail"),
            "verification": {
                "command": ["python3", "-c", "print('verify')"] if phase == "result" else ["python3", "capture-baseline.py"],
                "exit_code": 0 if passed else 1,
            },
            "observations": [
                {
                    "signal_id": "SIG-001",
                    "source": "completed-order-record",
                    "expected": "order completed",
                    "observed": "order completed" if passed else "order pending",
                    "passed": passed,
                }
            ],
        }

    def write_files(self):
        self.contract.write_text(json.dumps(self.contract_data), encoding="utf-8")
        self.baseline.write_text(json.dumps(self.evidence_object(phase="baseline")), encoding="utf-8")
        self.result.write_text(json.dumps(self.evidence_object(phase="result")), encoding="utf-8")

    def run_validator(self, *extra):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(self.root),
                "--feedback",
                str(self.contract),
                "--environment",
                "test",
                *extra,
            ],
            capture_output=True,
            text=True,
        )

    def test_accepts_fresh_feedback_bound_to_current_commit(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_unknown_or_uncovered_signal_references(self):
        self.contract_data["pass_fail_rules"][0]["signal_id"] = "SIG-INVENTED"
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown observable signal", result.stderr)
        self.assertIn("has no pass/fail rule", result.stderr)

    def test_rejects_non_array_commands_and_placeholder_rollback(self):
        self.contract_data["verification_commands"] = ["python3 test.py"]
        self.contract_data["rollback_method"] = "__ROLLBACK_METHOD__"
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("argument arrays", result.stderr)
        self.assertIn("placeholder", result.stderr)

    def test_enforces_published_schema_additional_properties(self):
        self.contract_data["implementation_agent_says"] = "trust me"
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed by the published schema", result.stderr)

    def test_rejects_placeholder_evidence_values(self):
        evidence = self.evidence_object(phase="result")
        evidence["observations"][0]["observed"] = "__OBSERVED_VALUE__"
        self.result.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("placeholder", result.stderr.lower())

    def test_rejects_outside_or_missing_evidence_paths(self):
        self.contract_data["evidence_paths"] = ["../outside.json"]
        self.contract_data["baseline"]["evidence_paths"] = ["docs/evidence/tasks/missing.json"]
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("project-relative path", result.stderr)
        self.assertIn("does not exist", result.stderr)

    def test_rejects_stale_failed_or_wrong_binding_result_evidence(self):
        self.result.write_text(
            json.dumps(self.evidence_object(phase="result", passed=False, commit="deadbeef", environment="staging", age_minutes=120)),
            encoding="utf-8",
        )
        result = self.run_validator("--max-age-minutes", "60")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale", result.stderr)
        self.assertIn("contracted result commit", result.stderr)
        self.assertIn("environment must be test", result.stderr)
        self.assertIn("status must be pass", result.stderr)

    def test_rejects_declaration_only_evidence(self):
        self.result.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("task_id", result.stderr)
        self.assertIn("observations", result.stderr)

    def test_rejects_result_evidence_from_an_uncontracted_command(self):
        evidence = self.evidence_object(phase="result")
        evidence["verification"]["command"] = ["python3", "different-check.py"]
        self.result.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must match a contracted verification command", result.stderr)

    def test_rejects_contract_or_baseline_not_bound_to_current_commit_and_environment(self):
        self.contract_data["current_commit"] = "deadbeef"
        self.contract_data["environment"] = "staging"
        self.contract_data["baseline"]["commit"] = "deadbeef"
        self.contract_data["baseline"]["environment"] = "staging"
        self.write_files()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("feedback.current_commit must match", result.stderr)
        self.assertIn("feedback.environment must be test", result.stderr)
        self.assertIn("baseline.commit must resolve", result.stderr)

    def test_rejects_stale_baseline_measurement(self):
        self.contract_data["baseline"]["measured_at"] = self.now(-120)
        self.write_files()
        result = self.run_validator("--max-age-minutes", "60")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("feedback.baseline.measured_at is stale", result.stderr)

    def test_rejects_observation_without_business_signal_pass(self):
        evidence = self.evidence_object(phase="result")
        evidence["observations"][0]["source"] = "different-source"
        evidence["observations"][0]["passed"] = False
        self.result.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source must match", result.stderr)
        self.assertIn("validator-computed result", result.stderr)

    def test_computes_rule_instead_of_trusting_passed_true(self):
        evidence = self.evidence_object(phase="result")
        evidence["observations"][0].update(observed="order pending", passed=True)
        self.result.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("validator-computed result", result.stderr)

    def test_accepts_failing_pre_change_baseline_and_passing_result_commit(self):
        baseline_commit = self.commit
        (self.root / "seed.txt").write_text("implemented\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "implement task"], cwd=self.root, check=True)
        self.commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout.strip()
        self.contract_data["current_commit"] = self.commit
        self.contract_data["baseline"]["commit"] = baseline_commit
        self.contract.write_text(json.dumps(self.contract_data), encoding="utf-8")
        self.baseline.write_text(
            json.dumps(self.evidence_object(phase="baseline", passed=False, commit=baseline_commit)),
            encoding="utf-8",
        )
        self.result.write_text(json.dumps(self.evidence_object(phase="result")), encoding="utf-8")
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
