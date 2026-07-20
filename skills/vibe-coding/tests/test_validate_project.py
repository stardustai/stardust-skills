import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "validate_project.py"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from validate_project import DOCUMENT_TOPICS, reviewed_section, validate_url
SPEC_SKILL = SKILL_ROOT.parent / "spec-intake"
EXAMPLE_SPEC = SPEC_SKILL / "examples" / "insurance-broker-proposal.spec.json"
EXAMPLE_WIREFRAME = SPEC_SKILL / "examples" / "insurance-broker-workspace-wireframe.svg"


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def engineering_spec(risk_tier: str = "R1") -> dict:
    spec = json.loads(EXAMPLE_SPEC.read_text(encoding="utf-8"))
    spec["stage_gate"].update(
        current_stage="engineering_delivery",
        readiness_label="engineering_ready",
        decision="ready_for_engineering",
    )
    spec["stage_gate"]["stage_exit_check"]["next_stage"] = "engineering_delivery"
    spec["opportunity_assessment"]["priority_decision"].update(
        recommendation="top_8", missing_evidence=[]
    )
    spec["owners"].update(
        product_owner="product@example.com",
        engineering_owner="engineering@example.com",
        qa_owner="qa@example.com",
        devops_owner="devops@example.com",
    )
    spec["business_success_scenarios"][0]["business_owner"] = spec["owners"]["business_owner"]
    spec["business_success_scenarios"][0]["confirmation"]["confirmed_by"] = spec["owners"]["business_owner"]
    spec["delivery_risk_profile"]["risk_tier"] = risk_tier
    spec["delivery_risk_profile"]["dimensions"] = {
        "user_exposure": "internal_single_team",
        "data_sensitivity": "internal" if risk_tier != "R0" else "synthetic",
        "write_impact": "read_only" if risk_tier != "R0" else "none",
        "integrations_and_permissions": "approved_internal" if risk_tier != "R0" else "none",
        "reversibility": "easy",
        "business_impact": "low" if risk_tier != "R0" else "demo",
    }
    spec["ui_requirements"]["wireframe_status"] = "reviewed"
    for asset in spec["validation_plan"]["evaluation_assets"]:
        asset.update(status="available", path_or_link=f"fixtures/{asset['asset_id']}.json", version="1.0")
    spec["validation_plan"]["poc_design_ready"].update(status="ready", blockers=[])
    spec["validation_plan"]["poc_execution_ready"].update(status="ready", blockers=[])
    coverage = spec["validation_plan"]["scenario_coverage"][0]
    coverage.update(qa_status="approved", automation_plan_status="planned")
    implementation = spec["implementation_mapping"]
    implementation["engineering_review_type"] = "technical_design"
    for capability in implementation["capabilities"]:
        if capability["support_status"] in {"missing", "unknown"}:
            capability["support_status"] = "partial"
    implementation["source_code_review"].update(status="completed", unread_required_paths=[])
    implementation["technical_design_assessment"] = {
        "design_summary": "Validated design uses existing repository contracts.",
        "ai_score": 4,
        "scoring_dimensions": [
            {"dimension": name, "score": 4, "rationale": "Validated against the project contract."}
            for name in ("architecture_fit", "code_reuse", "integration_complexity", "testability", "delivery_risk")
        ],
        "score_rationale": "All required design dimensions are independently reviewable.",
        "ai_engineer_confirmation": "confirmed",
    }
    spec["missing_fields"] = []
    return spec


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProjectFixture:
    DOCUMENT_PATHS = {
        "business_goal": "docs/business-goal.md",
        "system_architecture": "docs/system-architecture.md",
        "runtime_constraints": "docs/runtime-constraints.md",
        "test_plan": "docs/test-plan.md",
        "traceability": "docs/traceability.md",
        "eval_plan": "docs/eval-plan.md",
        "runbook": "docs/runbook.md",
        "technical_debt_register": "docs/technical-debt-register.md",
        "agent_rules_audit": "docs/agent-rules-audit.md",
        "qa_normalized_spec": "docs/qa/01-normalized-spec.md",
        "qa_test_design": "docs/qa/02-test-design.md",
        "qa_test_cases": "docs/qa/03-testcases.md",
    }

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "project"
        self.remote = self.base / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(self.remote)], check=True)
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True)
        run_git(self.root, "config", "user.email", "tests@example.com")
        run_git(self.root, "config", "user.name", "Vibe Tests")
        run_git(self.root, "remote", "add", "origin", self.remote.as_uri())

        spec_path = self.root / "docs/superpowers/specs/current-spec.json"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(json.dumps(engineering_spec(), ensure_ascii=False), encoding="utf-8")
        shutil.copy2(EXAMPLE_WIREFRAME, spec_path.parent / EXAMPLE_WIREFRAME.name)
        for rel in [
            "docs/superpowers/specs/current-design.md",
            "docs/superpowers/plans/current.md", "docs/business-goal.md",
            "docs/system-architecture.md", "docs/runtime-constraints.md",
            "docs/test-plan.md", "docs/traceability.md", "docs/eval-plan.md",
            "docs/runbook.md", "docs/technical-debt-register.md", "docs/agent-rules-audit.md",
            "docs/qa/01-normalized-spec.md", "docs/qa/02-test-design.md", "docs/qa/03-testcases.md",
            "docs/ui-spec.md",
        ]:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            responsibility = next(
                (key for key, value in self.DOCUMENT_PATHS.items() if value == rel),
                "ui_spec" if rel == "docs/ui-spec.md" else None,
            )
            coverage = ""
            if responsibility:
                coverage = "\n".join(
                    f"## {topic}\n\nCoverage: {topic}. The approved contract contains concrete reviewed details.\n"
                    for topic in DOCUMENT_TOPICS[responsibility]
                )
            path.write_text(
                f"# Approved {rel}\n\nStatus: approved\nOwner: test-owner\n\n{coverage}",
                encoding="utf-8",
            )
        documentation = {
            "organization": "standard",
            "paths": dict(self.DOCUMENT_PATHS),
            "conditional_paths": {"algorithm_design": None, "ui_spec": "docs/ui-spec.md"},
            "content_review": "docs/documentation-review.json",
        }
        self.write_documentation_review(documentation)
        self.write_readme(documentation)
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-qm", "baseline")
        self.baseline = run_git(self.root, "rev-parse", "HEAD")
        run_git(self.root, "push", "-q", "-u", "origin", "main")
        run_git(self.root, "switch", "-qc", "codex/feature")
        self.write_project(self.contract())
        run_git(self.root, "add", "PROJECT.yaml")
        run_git(self.root, "commit", "-qm", "add project contract")
        self.head = run_git(self.root, "rev-parse", "HEAD")
        run_git(self.root, "push", "-q", "-u", "origin", "codex/feature")
        return self

    def contract(self, risk_tier: str = "R1") -> dict:
        return {
            "$schema": "skills/vibe-coding/assets/schemas/project.schema.json",
            "schema_version": "1.0", "project_id": "PROJ-001", "name": "Example", "status": "implementation",
            "repository": {
                "remote_url": self.remote.as_uri(), "default_branch": "main", "feature_branch": "codex/feature",
                "baseline_commit": self.baseline, "last_green_commit": self.baseline,
                "working_tree": "clean", "known_dirty_paths": [],
            },
            "artifacts": {
                "spec": "docs/superpowers/specs/current-spec.json", "spec_sha256": sha256(self.root / "docs/superpowers/specs/current-spec.json"),
                "design": "docs/superpowers/specs/current-design.md", "plan": "docs/superpowers/plans/current.md",
            },
            "documentation": {
                "organization": "standard",
                "paths": dict(self.DOCUMENT_PATHS),
                "conditional_paths": {"algorithm_design": None, "ui_spec": "docs/ui-spec.md"},
                "content_review": "docs/documentation-review.json",
            },
            "risk": {"tier": risk_tier, "source": "docs/superpowers/specs/current-spec.json#/delivery_risk_profile"},
            "owners": {"business": "示例业务 owner", "product": "product@example.com", "engineering": "engineering@example.com", "qa": "qa@example.com", "decision": "PMF owner"},
            "commands": {
                name: [sys.executable, "-c", f"print('{name}')"]
                for name in ("install", "start", "stop", "build", "pre_commit_full", "test_full", "eval_full", "smoke", "health_check", "business_e2e")
            },
            "command_timeouts_seconds": {"default": 300, **{name: 300 for name in ("install", "start", "stop", "build", "pre_commit_full", "test_full", "eval_full", "smoke", "health_check", "business_e2e")}},
            "verification": {
                "check_inventory": ["build", "pre_commit_full", "test_full", "eval_full", "start", "health_check", "smoke", "stop", "business_e2e"],
                "runtime": {"check_names": ["start", "health_check", "smoke", "stop"], "required_evidence_fields": ["health_endpoint", "smoke_result"]},
                "business": {"check_names": ["business_e2e"], "required_evidence_fields": ["scenario_results", "observable_signals"]},
                "applicability": {
                    name: {"status": "required", "reason": "Required by the approved test plan.", "evidence": "docs/test-plan.md", "approved_by": "qa@example.com"}
                    for name in ("format_static_type", "unit", "integration", "business_e2e", "permissions", "ui_accessibility", "performance_cost", "recovery_rollback", "eval")
                },
            },
            "features": {"algorithmic": False, "business_ui": True},
            "technical_debt": {"strategy": "minimum_safe", "approved_by": "PMF owner", "decision_record": "docs/technical-debt-register.md", "excluded_debt_ids": ["TD-001"], "excluded_paths": ["legacy/"]},
            "pre_commit": {"hook_path": ".githooks/pre-commit", "full_suite": True},
            "delivery": {
                "collaboration": "single_owner", "change_size": "small", "direct_push_permitted": True,
                "explicit_pr_required": False, "change_dimensions": {name: False for name in (
                    "architecture", "public_api", "data_schema", "permissions", "dependency_or_integration",
                    "migration_or_bulk_write", "technical_debt_or_refactor", "material_spec_or_plan", "critical_runtime")},
                "mode": "direct_push", "requires_pr": False,
            },
            "deployment": {"required": False, "sre_skill": "production-devops-sre", "target_environment": None, "lifecycle_status": "not_started"},
        }

    def write_project(self, data: dict) -> None:
        (self.root / "PROJECT.yaml").write_text(json.dumps(data, indent=2), encoding="utf-8")

    def write_documentation_review(self, documentation: dict) -> None:
        mapped = dict(documentation["paths"])
        mapped.update({key: value for key, value in documentation["conditional_paths"].items() if value})
        documents = []
        for responsibility, relative in mapped.items():
            path = self.root / relative
            content = path.read_text(encoding="utf-8")
            coverage = []
            for topic in DOCUMENT_TOPICS[responsibility]:
                locator = f"## {topic}"
                section = reviewed_section(content, locator)
                if section is None:
                    raise AssertionError(f"fixture locator is not unique: {relative} {locator}")
                coverage.append({
                    "topic": topic,
                    "locator": locator,
                    "section_sha256": hashlib.sha256(section.encode("utf-8")).hexdigest(),
                })
            documents.append({
                "responsibility": responsibility,
                "path": relative,
                "sha256": sha256(path),
                "coverage": coverage,
            })
        review = {
            "schema_version": "1.0",
            "author_agent_id": "initialization-agent",
            "author_execution_context_id": "33333333-3333-4333-8333-333333333333",
            "reviewer_id": "independent-documentation-review-agent",
            "execution_context_id": "44444444-4444-4444-8444-444444444444",
            "reviewed_at": "2026-07-20T12:00:00+00:00",
            "status": "pass",
            "documents": documents,
        }
        path = self.root / documentation["content_review"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")

    def write_readme(self, documentation: dict) -> None:
        entries = {
            "organization": documentation["organization"],
            "spec": "docs/superpowers/specs/current-spec.json",
            "design": "docs/superpowers/specs/current-design.md",
            "plan": "docs/superpowers/plans/current.md",
            **documentation["paths"],
            **{key: value for key, value in documentation["conditional_paths"].items() if value},
            "content_review": documentation["content_review"],
        }
        (self.root / "README.md").write_text(
            "# Example project\n\n## Documentation organization\n\n"
            + "\n".join(f"- `{key}`: `{value}`" for key, value in entries.items())
            + "\n",
            encoding="utf-8",
        )

    def commit_project(self) -> None:
        run_git(self.root, "add", "PROJECT.yaml")
        run_git(self.root, "commit", "-qm", "update project contract")
        self.head = run_git(self.root, "rev-parse", "HEAD")

    def run(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--project-root", str(self.root)], capture_output=True, text=True)

    def __exit__(self, *_):
        self.tmp.cleanup()


class ValidateProjectTests(unittest.TestCase):
    def test_accepts_valid_engineering_ready_project_and_git_state(self):
        with ProjectFixture() as fx:
            self.assertEqual(fx.run().returncode, 0, fx.run().stderr)

    def test_accepts_existing_document_structure_when_mapped_in_readme(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            adapted_paths = {
                key: f"handbook/{Path(path).name}"
                for key, path in fx.DOCUMENT_PATHS.items()
            }
            adapted_ui = "product/ui/states.md"
            for key, source in fx.DOCUMENT_PATHS.items():
                target = adapted_paths[key]
                target_path = fx.root / target
                target_path.parent.mkdir(parents=True, exist_ok=True)
                (fx.root / source).rename(target_path)
            ui_target = fx.root / adapted_ui
            ui_target.parent.mkdir(parents=True, exist_ok=True)
            (fx.root / "docs/ui-spec.md").rename(ui_target)
            project["documentation"] = {
                "organization": "adapt_existing",
                "paths": adapted_paths,
                "conditional_paths": {"algorithm_design": None, "ui_spec": adapted_ui},
                "content_review": "docs/documentation-review.json",
            }
            project["technical_debt"]["decision_record"] = adapted_paths["technical_debt_register"]
            for policy in project["verification"]["applicability"].values():
                policy["evidence"] = adapted_paths["test_plan"]
            project["verification"]["applicability"]["eval"]["evidence"] = adapted_paths["eval_plan"]
            fx.write_documentation_review(project["documentation"])
            fx.write_readme(project["documentation"])
            fx.write_project(project)
            run_git(fx.root, "add", ".")
            run_git(fx.root, "commit", "-qm", "adapt existing documentation structure")

            result = fx.run()
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_adapted_structure_missing_readme_mapping(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            project["documentation"]["organization"] = "adapt_existing"
            (fx.root / "README.md").write_text(
                "# Existing project\n\nDocumentation is stored somewhere in this repository.\n",
                encoding="utf-8",
            )
            project["repository"].update(
                working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml", "README.md"]
            )
            fx.write_project(project)

            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("README documentation map", result.stderr)

    def test_rejects_long_document_without_required_semantic_coverage(self):
        with ProjectFixture() as fx:
            architecture = fx.root / "docs/system-architecture.md"
            architecture.write_text(
                "# Existing notes\n\nThis document is long enough to pass a superficial length check, "
                "but it contains no reviewed system boundaries, components, data flow, authorization, "
                "observability, or recovery contract.\n",
                encoding="utf-8",
            )
            project = fx.contract()
            project["repository"].update(
                working_tree="known_dirty",
                known_dirty_paths=[
                    "PROJECT.yaml", "docs/documentation-review.json", "docs/system-architecture.md"
                ],
            )
            review_path = fx.root / project["documentation"]["content_review"]
            review = json.loads(review_path.read_text(encoding="utf-8"))
            for document in review["documents"]:
                if document["responsibility"] == "system_architecture":
                    document["sha256"] = sha256(architecture)
            review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
            fx.write_project(project)

            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("documentation content review", result.stderr)

    def test_rejects_reused_generic_documentation_locator(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            review_path = fx.root / project["documentation"]["content_review"]
            review = json.loads(review_path.read_text(encoding="utf-8"))
            for document in review["documents"]:
                for coverage in document["coverage"]:
                    coverage["locator"] = "Status: approved"
            review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
            project["repository"].update(
                working_tree="known_dirty",
                known_dirty_paths=["PROJECT.yaml", "docs/documentation-review.json"],
            )
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unique full-line locator", result.stderr)

    def test_rejects_declared_self_review_identity_variants(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            review_path = fx.root / project["documentation"]["content_review"]
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["reviewer_id"] = " INITIALIZATION-AGENT "
            review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
            project["repository"].update(
                working_tree="known_dirty",
                known_dirty_paths=["PROJECT.yaml", "docs/documentation-review.json"],
            )
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("reviewer must differ", result.stderr)

    def test_requires_qa_documentation_contract(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            del project["documentation"]["paths"]["qa_test_cases"]
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml"])
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("qa_test_cases", result.stderr)

    def test_rejects_readme_path_prefix_or_backup_suffix_as_a_mapping(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            project["documentation"]["organization"] = "adapt_existing"
            mapped = list(project["documentation"]["paths"].values())
            mapped.extend(value for value in project["documentation"]["conditional_paths"].values() if value)
            mapped.extend(project["artifacts"][key] for key in ("spec", "design", "plan"))
            mapped.append(project["documentation"]["content_review"])
            (fx.root / "README.md").write_text(
                "# Misleading map\n\n" + "\n".join(f"- `{path}.bak`" for path in mapped) + "\n",
                encoding="utf-8",
            )
            project["repository"].update(
                working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml", "README.md"]
            )
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("README documentation map", result.stderr)

    def test_rejects_absolute_document_path_even_inside_checkout(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            project["documentation"]["organization"] = "adapt_existing"
            project["documentation"]["paths"]["business_goal"] = str(
                (fx.root / "docs/business-goal.md").resolve()
            )
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml"])
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("project-relative", result.stderr)

    def test_standard_structure_rejects_nonstandard_conditional_and_artifact_paths(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            project["documentation"]["conditional_paths"]["ui_spec"] = "product/custom-ui.md"
            project["artifacts"]["plan"] = "docs/test-plan.md"
            target = fx.root / "product/custom-ui.md"
            target.parent.mkdir(parents=True)
            (fx.root / "docs/ui-spec.md").rename(target)
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("standard structure", result.stderr)
            self.assertIn("Superpowers", result.stderr)

    def test_rejects_technical_debt_exclusion_outside_project(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            project["technical_debt"]["excluded_paths"] = ["../../outside"]
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml"])
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("technical_debt.excluded_paths", result.stderr)

    def test_invokes_authoritative_spec_validator(self):
        with ProjectFixture() as fx:
            spec_path = fx.root / "docs/superpowers/specs/current-spec.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            del spec["business_success_scenarios"][0]["title"]
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            project = fx.contract()
            project["artifacts"]["spec_sha256"] = sha256(spec_path)
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml", "docs/superpowers/specs/current-spec.json"])
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("spec-intake validation failed", result.stderr)
            self.assertIn("title", result.stderr)

    def test_rejects_spec_checksum_drift(self):
        with ProjectFixture() as fx:
            spec_path = fx.root / "docs/superpowers/specs/current-spec.json"
            spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            project = json.loads((fx.root / "PROJECT.yaml").read_text(encoding="utf-8"))
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml", "docs/superpowers/specs/current-spec.json"])
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("spec_sha256", result.stderr)

    def test_rejects_wrong_branch_unknown_commit_and_unexpected_dirty_state(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            project["repository"]["feature_branch"] = "codex/other"
            project["repository"]["last_green_commit"] = "f" * 40
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("current Git branch", result.stderr)
            self.assertIn("last_green_commit", result.stderr)
            self.assertIn("working tree", result.stderr)

    def test_derives_pr_for_multi_person_large_or_structural_change(self):
        with ProjectFixture() as fx:
            for mutate in ("multi_large", "architecture"):
                project = fx.contract()
                if mutate == "multi_large":
                    project["delivery"].update(collaboration="multi_person", change_size="large")
                else:
                    project["delivery"]["change_dimensions"]["architecture"] = True
                project["delivery"].update(mode="direct_push", requires_pr=False)
                fx.write_project(project)
                result = fx.run()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("derived PR policy", result.stderr)

    def test_allows_multi_person_small_direct_push_but_r2_forces_pr(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            project["delivery"].update(collaboration="multi_person", change_size="small")
            fx.write_project(project)
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml"])
            fx.write_project(project)
            self.assertEqual(fx.run().returncode, 0, fx.run().stderr)

            project = fx.contract("R2")
            project["delivery"].update(mode="direct_push", requires_pr=False)
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml"])
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("derived PR policy", result.stderr)

    def test_requires_deterministic_deployment_adapter_fields(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            project["deployment"].update(sre_skill="other", lifecycle_status="done")
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml"])
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("production-devops-sre", result.stderr)
            self.assertIn("lifecycle_status", result.stderr)

    def test_accepts_production_rollout_as_an_observed_intermediate_state(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            project["deployment"].update(
                required=True, target_environment="production", lifecycle_status="production_rollout"
            )
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml"])
            fx.write_project(project)
            result = fx.run()
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_placeholder_documents_and_ui_flag_drift(self):
        with ProjectFixture() as fx:
            (fx.root / "docs/runbook.md").write_text("# ready\n", encoding="utf-8")
            project = fx.contract()
            project["features"]["business_ui"] = False
            project["repository"].update(
                working_tree="known_dirty",
                known_dirty_paths=["PROJECT.yaml", "docs/runbook.md"],
            )
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("docs/runbook.md", result.stderr)
            self.assertIn("ui_requirements.has_ui", result.stderr)

    def test_requires_pre_commit_full_and_per_command_timeouts(self):
        with ProjectFixture() as fx:
            project = fx.contract()
            del project["commands"]["pre_commit_full"]
            del project["command_timeouts_seconds"]["eval_full"]
            project["command_timeouts_seconds"]["default"] = 0
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml"])
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("commands.pre_commit_full", result.stderr)
            self.assertIn("command_timeouts_seconds.eval_full", result.stderr)
            self.assertIn("command_timeouts_seconds.default", result.stderr)

    def test_rejects_unapproved_or_forbidden_test_exemptions(self):
        with ProjectFixture() as fx:
            project = fx.contract("R2")
            project["verification"]["applicability"]["eval"].update(
                status="not_applicable", approved_by="engineering@example.com"
            )
            project["verification"]["applicability"]["permissions"].update(
                status="not_applicable", approved_by="engineering@example.com"
            )
            project["repository"].update(working_tree="known_dirty", known_dirty_paths=["PROJECT.yaml"])
            fx.write_project(project)
            result = fx.run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("verification.applicability.eval", result.stderr)
            self.assertIn("verification.applicability.permissions", result.stderr)

    def test_accepts_common_scp_style_ssh_remote_url(self):
        errors = []
        validate_url("git@github.com:stardustai/example.git", errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
