import json
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_ROOT))
sys.path.insert(0, str(TEST_ROOT.parent / "scripts"))
from test_validate_project import ProjectFixture, sha256
from test_run_project_checks import assert_matches_schema
from validate_delivery import pr_matches_origin


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "validate_delivery.py"
REVIEW_SCHEMA = SKILL_ROOT / "assets/schemas/review-evidence.schema.json"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


class ValidateDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ProjectFixture().__enter__()
        self.root = self.fixture.root
        self.remote = self.fixture.remote
        self.baseline = self.fixture.baseline
        self.project = self.root / "PROJECT.yaml"
        self.evidence = self.root / "evidence.json"
        self.review_evidence = self.root / "review-evidence.json"
        self.spec = self.root / "docs/superpowers/specs/current-spec.json"
        self.traceability = self.root / "traceability.json"
        self.business_evidence = self.root / "docs/evidence/BIZ-001.json"
        self.review_dir = self.root / "docs/evidence/review"

        spec = json.loads(self.spec.read_text(encoding="utf-8"))
        spec["validation_plan"]["scenario_coverage"][0]["automation_plan_status"] = "verified"
        scenario = spec["business_success_scenarios"][0]
        coverage = spec["validation_plan"]["scenario_coverage"][0]
        self.scenario_id = scenario["scenario_id"]
        self.signals = scenario["success_signals"]
        self.expected_business_outcome = scenario["expected_business_outcome"]
        self.expected_final_state = scenario["expected_final_state"]
        coverage.update(
            qa_case_refs=[f"QA-{self.scenario_id}"],
            automated_test_refs=[f"E2E-{self.scenario_id}"],
            evaluation_asset_refs=[f"EVAL-{self.scenario_id}"],
        )
        self.spec.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")

        self.project_data = self.fixture.contract()
        self.commands = self.project_data["commands"]
        self.project_data["artifacts"]["spec_sha256"] = sha256(self.spec)
        self.project_data["delivery"].update(
            collaboration="multi_person", change_size="large", mode="pull_request", requires_pr=True
        )
        self.traceability.write_text(json.dumps({
            "$schema": "skills/vibe-coding/assets/schemas/traceability.schema.json",
            "schema_version": "1.0", "mappings": [{
                "scenario_id": self.scenario_id, "qa_case_refs": coverage["qa_case_refs"],
                "automated_test_refs": coverage["automated_test_refs"],
                "evaluation_asset_refs": coverage["evaluation_asset_refs"],
                "business_signal_refs": self.signals,
                "business_signal_rules": [
                    {"signal_id": signal, "source": "test-observation", "operator": "equals", "expected": "success"}
                    for signal in self.signals
                ],
                "business_owner_approval": {
                    "approved_by": scenario["business_owner"],
                    "confirmed_version": scenario["confirmation"]["confirmed_version"],
                },
                "verification_commands": [self.commands["business_e2e"]],
                "evidence_paths": ["docs/evidence/BIZ-001.json"],
            }],
        }, ensure_ascii=False), encoding="utf-8")
        (self.root / ".gitignore").write_text(
            "docs/evidence/\n/evidence.json\n/review-evidence.json\n", encoding="utf-8"
        )
        self.project.write_text(json.dumps(self.project_data, indent=2, ensure_ascii=False), encoding="utf-8")
        git(self.root, "add", "PROJECT.yaml", str(self.spec.relative_to(self.root)), "traceability.json", ".gitignore")
        git(self.root, "commit", "-qm", "complete delivery contract")
        self.head = git(self.root, "rev-parse", "HEAD")
        git(self.root, "push", "-q", "origin", "codex/feature")
        self.business_evidence.parent.mkdir(parents=True, exist_ok=True)
        self.review_dir.mkdir(parents=True, exist_ok=True)
        for name in ("spec-review.json", "code-review.json", "test-review.json", "attestation.json"):
            (self.review_dir / name).write_text('{"verified": true}\n', encoding="utf-8")

    def tearDown(self):
        self.fixture.__exit__(None, None, None)

    def reviewed_artifacts(self):
        artifacts = self.project_data["artifacts"]
        return [
            artifacts["spec"], artifacts["design"], artifacts["plan"],
            f"git:diff:{self.baseline}..{self.head}",
        ]

    def write_evidence(self, age_minutes: int = 1, eval_exit: int = 0, pr_url: str | None = "https://github.com/example/project/pull/1"):
        now = datetime.now(timezone.utc)
        started = (now - timedelta(minutes=age_minutes + 1)).isoformat()
        finished = (now - timedelta(minutes=age_minutes)).isoformat()
        checks = []
        for name in self.project_data["verification"]["check_inventory"]:
            command = self.commands[name]
            checks.append({
                "name": name, "command": command, "timeout_seconds": 300,
                "started_at": started, "finished_at": finished,
                "status": "failed" if name == "eval_full" and eval_exit else "passed",
                "exit_code": eval_exit if name == "eval_full" else 0,
                "stdout": {"byte_count": 6, "sha256": "a" * 64, "summary": "[redacted: non-empty output]"},
                "stderr": {"byte_count": 0, "sha256": "b" * 64, "summary": "[no output]"},
            })
        self.evidence.write_text(json.dumps({
            "$schema": "skills/vibe-coding/assets/schemas/evidence-manifest.schema.json",
            "schema_version": "1.0", "run_id": "11111111-1111-4111-8111-111111111111",
            "phase": "full", "project_root": str(self.root.resolve()),
            "git": {"branch": "codex/feature", "commit": self.head, "clean": True},
            "started_at": started, "finished_at": finished, "checks": checks,
        }), encoding="utf-8")
        independent_manifest = self.review_dir / "independent-full.json"
        independent_payload = json.loads(self.evidence.read_text(encoding="utf-8"))
        independent_payload["run_id"] = "22222222-2222-4222-8222-222222222222"
        independent_manifest.write_text(json.dumps(independent_payload), encoding="utf-8")
        independent_sha = sha256(independent_manifest)
        primary_sha = sha256(self.evidence)
        self.write_business_evidence()
        review_types = (("spec", "spec-agent", "spec-run", "spec-review.json"),
                        ("code_quality", "code-agent", "code-run", "code-review.json"),
                        ("independent_test", "test-agent", "test-run", "test-review.json"))
        self.review_evidence.write_text(json.dumps({
            "$schema": "skills/vibe-coding/assets/schemas/review-evidence.schema.json",
            "schema_version": "1.0", "commit": self.head, "author_agent_id": "implementation-agent",
            "status": "pass",
            "reviews": [{
                "review_type": kind, "reviewer_id": reviewer, "execution_context_id": context,
                "reviewed_artifacts": self.reviewed_artifacts(), "status": "pass",
                "findings_count": 0, "blocking_findings": 0,
                "evidence_uri": f"docs/evidence/review/{filename}",
            } for kind, reviewer, context, filename in review_types],
            "independent_verification": {"commit": self.head, "checks": [
                {"name": name, "command": self.commands[name], "exit_code": 0, "captured_at": finished,
                 "evidence_manifest": "docs/evidence/review/independent-full.json", "evidence_sha256": independent_sha}
                for name in ("test_full", "eval_full")
            ]},
            "runtime_evidence": {
                "health_endpoint": {"check_name": "health_check", "evidence_manifest": "evidence.json", "evidence_sha256": primary_sha, "observed": "HTTP 200"},
                "smoke_result": {"check_name": "smoke", "evidence_manifest": "evidence.json", "evidence_sha256": primary_sha, "observed": "pass"},
            },
            "attestation": {"provider": "test-runtime", "run_id": "review-run-001", "artifact_uri": "docs/evidence/review/attestation.json"},
            "reviewed_at": finished, "pull_request_url": pr_url,
        }), encoding="utf-8")

    def write_business_evidence(self, *, status: str = "pass"):
        self.business_evidence.write_text(json.dumps({
            "$schema": "skills/vibe-coding/assets/schemas/business-evidence.schema.json",
            "schema_version": "1.0", "scenario_id": self.scenario_id, "commit": self.head,
            "environment": "test", "captured_at": datetime.now(timezone.utc).isoformat(),
            "status": status, "business_passed": status == "pass",
            "expected_business_outcome": self.expected_business_outcome,
            "expected_final_state": self.expected_final_state,
            "runner_check_name": "business_e2e", "evidence_manifest": "evidence.json",
            "evidence_sha256": sha256(self.evidence),
            "business_observations": [{
                "signal_id": signal, "source": "test-observation", "expected": "success",
                "observed": "success" if status == "pass" else "failure", "passed": status == "pass",
            } for signal in self.signals],
        }, ensure_ascii=False), encoding="utf-8")

    def run_validator(self, max_age: int = 60):
        return subprocess.run([
            sys.executable, str(SCRIPT), "--project", str(self.project),
            "--evidence", str(self.evidence), "--review-evidence", str(self.review_evidence),
            "--traceability", str(self.traceability), "--environment", "test",
            "--max-age-minutes", str(max_age),
        ], capture_output=True, text=True)

    def test_accepts_evidence_bound_to_exact_git_remote_and_commands(self):
        self.write_evidence()
        schema = json.loads(REVIEW_SCHEMA.read_text(encoding="utf-8"))
        assert_matches_schema(self, json.loads(self.review_evidence.read_text()), schema, schema)
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_wrong_project_root_command_branch_or_commit(self):
        self.write_evidence()
        evidence = json.loads(self.evidence.read_text())
        evidence["project_root"] = str(self.root.parent)
        evidence["git"]["branch"] = "other"
        evidence["git"]["commit"] = self.baseline
        evidence["checks"][0]["command"] = ["true"]
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("project_root", result.stderr)
        self.assertIn("branch", result.stderr)
        self.assertIn("current HEAD", result.stderr)
        self.assertIn("exactly match PROJECT.yaml", result.stderr)

    def test_rejects_remote_revision_not_equal_to_delivery_commit(self):
        self.write_evidence()
        subprocess.run(["git", "push", "-q", "--force", "origin", f"{self.baseline}:refs/heads/codex/feature"], cwd=self.root, check=True)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("remote branch revision", result.stderr)

    def test_rejects_dirty_state_and_missing_pr_url(self):
        self.write_evidence(pr_url=None)
        (self.root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("working tree", result.stderr)
        self.assertIn("pull_request_url", result.stderr)

    def test_requires_inventory_and_runtime_business_evidence(self):
        self.write_evidence()
        evidence = json.loads(self.evidence.read_text())
        evidence["checks"] = [check for check in evidence["checks"] if check["name"] not in {"eval_full", "health_check", "business_e2e"}]
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        review = json.loads(self.review_evidence.read_text())
        del review["runtime_evidence"]["health_endpoint"]
        self.review_evidence.write_text(json.dumps(review), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("eval_full", result.stderr)
        self.assertIn("health_check", result.stderr)
        self.assertIn("business_e2e", result.stderr)
        self.assertIn("runtime_evidence.health_endpoint", result.stderr)

    def test_rejects_failed_or_stale_evidence(self):
        self.write_evidence(age_minutes=120, eval_exit=2)
        result = self.run_validator(max_age=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("eval_full", result.stderr)
        self.assertIn("stale", result.stderr)

    def test_rejects_failed_business_traceability_evidence(self):
        self.write_evidence()
        self.write_business_evidence(status="fail")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("business traceability validation failed", result.stderr)

    def test_rejects_self_attested_or_incomplete_review(self):
        self.write_evidence()
        review = json.loads(self.review_evidence.read_text())
        review["reviews"][0]["reviewer_id"] = review["author_agent_id"]
        review["reviews"][1]["reviewed_artifacts"] = [self.project_data["artifacts"]["spec"]]
        review["independent_verification"]["checks"][0]["command"] = ["true"]
        review["runtime_evidence"]["smoke_result"] = "agent says pass"
        self.review_evidence.write_text(json.dumps(review), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("independent from the author", result.stderr)
        self.assertIn("Spec, Design, Plan", result.stderr)
        self.assertIn("exact project command", result.stderr)
        self.assertIn("review evidence schema", result.stderr)

    def test_delivery_reuses_full_project_and_spec_gate(self):
        self.write_evidence()
        project = json.loads(self.project.read_text())
        del project["owners"]
        self.project.write_text(json.dumps(project), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("project contract validation failed", result.stderr)

    def test_pr_url_matches_https_ssh_and_scp_origin_identity(self):
        pr = "https://github.com/stardustai/example/pull/42"
        self.assertTrue(pr_matches_origin(pr, "https://github.com/stardustai/example.git"))
        self.assertTrue(pr_matches_origin(pr, "ssh://git@github.com/stardustai/example.git"))
        self.assertTrue(pr_matches_origin(pr, "git@github.com:stardustai/example.git"))
        self.assertFalse(pr_matches_origin(pr, "git@github.com:other/example.git"))
        self.assertFalse(pr_matches_origin("https://github.com/stardustai/example/issues/42", "git@github.com:stardustai/example.git"))
        self.assertFalse(pr_matches_origin("https://github.com/stardustai/example/not-a-pr", "git@github.com:stardustai/example.git"))

    def test_rejects_copied_primary_manifest_as_independent_execution(self):
        self.write_evidence()
        copied = self.review_dir / "independent-full.json"
        copied.write_bytes(self.evidence.read_bytes())
        copied_sha = sha256(copied)
        review = json.loads(self.review_evidence.read_text())
        for check in review["independent_verification"]["checks"]:
            check["evidence_sha256"] = copied_sha
        self.review_evidence.write_text(json.dumps(review), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("digest must differ from the primary run", result.stderr)
        self.assertIn("distinct runner run_id", result.stderr)

    def test_rejects_fresh_review_wrapper_around_stale_independent_manifest(self):
        self.write_evidence()
        manifest_path = self.review_dir / "independent-full.json"
        manifest = json.loads(manifest_path.read_text())
        stale = "2020-01-01T00:00:00+00:00"
        manifest["started_at"] = stale
        manifest["finished_at"] = stale
        for check in manifest["checks"]:
            check["started_at"] = stale
            check["finished_at"] = stale
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        manifest_sha = sha256(manifest_path)
        review = json.loads(self.review_evidence.read_text())
        for check in review["independent_verification"]["checks"]:
            check["evidence_sha256"] = manifest_sha
        self.review_evidence.write_text(json.dumps(review), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence_manifest is stale", result.stderr)


if __name__ == "__main__":
    unittest.main()
