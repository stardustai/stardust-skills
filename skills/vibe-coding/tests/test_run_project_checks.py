import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "run_project_checks.py"
INSTALL_HOOK = SKILL_ROOT / "scripts" / "install_pre_commit.py"
EVIDENCE_SCHEMA = SKILL_ROOT / "assets" / "schemas" / "evidence-manifest.schema.json"


def assert_matches_schema(testcase, value, schema, root_schema, path="$"):
    if "$ref" in schema:
        target = root_schema
        for component in schema["$ref"].removeprefix("#/").split("/"):
            target = target[component]
        return assert_matches_schema(testcase, value, target, root_schema, path)
    if "const" in schema:
        testcase.assertEqual(value, schema["const"], path)
    if "enum" in schema:
        testcase.assertIn(value, schema["enum"], path)
    expected_types = schema.get("type")
    if isinstance(expected_types, str):
        expected_types = [expected_types]
    if expected_types:
        matches = {
            "object": lambda item: isinstance(item, dict),
            "array": lambda item: isinstance(item, list),
            "string": lambda item: isinstance(item, str),
            "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
            "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
            "boolean": lambda item: isinstance(item, bool),
            "null": lambda item: item is None,
        }
        testcase.assertTrue(any(matches[name](value) for name in expected_types), f"{path}: wrong type")
    if isinstance(value, dict):
        required = set(schema.get("required", []))
        testcase.assertFalse(required - set(value), f"{path}: missing required properties")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            testcase.assertFalse(set(value) - set(properties), f"{path}: unexpected properties")
        for key, item in value.items():
            if key in properties:
                assert_matches_schema(testcase, item, properties[key], root_schema, f"{path}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            assert_matches_schema(testcase, item, schema["items"], root_schema, f"{path}[{index}]")
    if isinstance(value, str):
        testcase.assertGreaterEqual(len(value), schema.get("minLength", 0), path)
        if "pattern" in schema:
            testcase.assertIsNotNone(re.fullmatch(schema["pattern"], value), path)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema:
            testcase.assertGreaterEqual(value, schema["minimum"], path)
        if "exclusiveMinimum" in schema:
            testcase.assertGreater(value, schema["exclusiveMinimum"], path)


class RunProjectChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        self.root.mkdir()
        self.evidence = self.root / "docs/evidence/full-latest.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write_project(self, test_command, eval_command=None):
        commands = {"test_full": test_command}
        if eval_command is not None:
            commands["eval_full"] = eval_command
        data = {"commands": commands}
        (self.root / "PROJECT.yaml").write_text(json.dumps(data), encoding="utf-8")

    def init_git(self):
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "PROJECT.yaml"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.root, check=True)

    def run_checks(self, *extra_args, checks=("test_full", "eval_full"), evidence=None):
        evidence = evidence or self.evidence
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(self.root),
                "--checks",
                *checks,
                "--evidence",
                str(evidence),
                *extra_args,
            ],
            capture_output=True,
            text=True,
        )

    def test_records_reproducible_context_without_persisting_raw_output(self):
        secret = "super-secret-value-that-must-not-be-persisted"
        output = (secret + "\n") * 20_000
        code = (
            "import sys; "
            "value=''.join(map(chr,[115,117,112,101,114,45,115,101,99,114,101,116,45,118,97,108,117,101,45,116,104,97,116,45,109,117,115,116,45,110,111,116,45,98,101,45,112,101,114,115,105,115,116,101,100])); "
            "sys.stdout.write((value+'\\n')*20000)"
        )
        self.write_project(
            [sys.executable, "-c", code],
            [sys.executable, "-c", "print('eval-pass')"],
        )
        self.init_git()

        result = self.run_checks("--default-timeout", "5")

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence_text = self.evidence.read_text(encoding="utf-8")
        self.assertNotIn(secret, evidence_text)
        self.assertLess(len(evidence_text), 20_000)
        evidence = json.loads(evidence_text)
        self.assertEqual(evidence["phase"], "full")
        self.assertRegex(evidence["run_id"], r"^[0-9a-f-]{36}$")
        self.assertEqual(evidence["project_root"], str(self.root.resolve()))
        self.assertEqual(evidence["git"]["branch"], "main")
        self.assertTrue(evidence["git"]["clean"])
        self.assertRegex(evidence["git"]["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual([item["name"] for item in evidence["checks"]], ["test_full", "eval_full"])
        first = evidence["checks"][0]
        self.assertEqual(first["command"], [sys.executable, "-c", code])
        self.assertEqual(first["timeout_seconds"], 5.0)
        self.assertEqual(first["stdout"]["byte_count"], len(output.encode()))
        self.assertEqual(first["stdout"]["sha256"], hashlib.sha256(output.encode()).hexdigest())
        self.assertEqual(first["stdout"]["summary"], "[redacted: non-empty output]")
        self.assertEqual(first["stderr"]["summary"], "[no output]")
        self.assertIn("started_at", first)
        self.assertIn("finished_at", first)
        self.assertIn("started_at", evidence)
        self.assertIn("finished_at", evidence)

    def test_per_command_timeout_kills_the_process_group_and_finalizes_evidence(self):
        late_file = self.root / "late-child-output"
        parent_code = (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable, '-c', "
            "'import pathlib,signal,sys,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(0.5); pathlib.Path(sys.argv[1]).write_text(\"late\")', "
            "sys.argv[1]]); time.sleep(10)"
        )
        self.write_project([sys.executable, "-c", parent_code, str(late_file)])

        result = self.run_checks(
            "--default-timeout",
            "2",
            "--timeout",
            "test_full=0.1",
            checks=("test_full",),
        )

        self.assertNotEqual(result.returncode, 0)
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        check = evidence["checks"][0]
        self.assertEqual(check["status"], "timed_out")
        self.assertEqual(check["exit_code"], 124)
        self.assertEqual(check["timeout_seconds"], 0.1)
        self.assertIsNotNone(evidence["finished_at"])
        time.sleep(0.7)
        self.assertFalse(late_file.exists(), "child process survived timeout")

    def test_missing_executable_is_a_finalized_failure_manifest(self):
        self.write_project(["definitely-not-a-real-vibe-coding-executable"])

        result = self.run_checks(checks=("test_full",))

        self.assertNotEqual(result.returncode, 0)
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        check = evidence["checks"][0]
        self.assertEqual(check["status"], "start_failed")
        self.assertEqual(check["exit_code"], 127)
        self.assertEqual(check["error_type"], "FileNotFoundError")
        self.assertIsNotNone(check["finished_at"])
        self.assertIsNotNone(evidence["finished_at"])

    def test_evidence_path_must_resolve_inside_project_root(self):
        self.write_project([sys.executable, "-c", "print('ok')"])
        outside = self.root.parent / "escaped-evidence.json"

        result = self.run_checks(checks=("test_full",), evidence=outside)

        self.assertEqual(result.returncode, 2)
        self.assertIn("inside the project root", result.stderr)
        self.assertFalse(outside.exists())

    def test_failed_command_blocks_later_checks(self):
        self.write_project(
            [sys.executable, "-c", "import sys; sys.exit(7)"],
            [sys.executable, "-c", "print('must-not-run')"],
        )

        result = self.run_checks()

        self.assertNotEqual(result.returncode, 0)
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        self.assertEqual(len(evidence["checks"]), 1)
        self.assertEqual(evidence["checks"][0]["exit_code"], 7)
        self.assertEqual(evidence["checks"][0]["status"], "failed")

    def test_rejects_invalid_timeout_configuration_before_running(self):
        marker = self.root / "must-not-run"
        self.write_project([sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()", str(marker)])

        result = self.run_checks("--timeout", "unknown=2", checks=("test_full",))

        self.assertEqual(result.returncode, 2)
        self.assertIn("not one of the requested checks", result.stderr)
        self.assertFalse(marker.exists())

    def test_project_timeout_uses_per_command_then_project_default(self):
        data = {
            "commands": {
                "test_full": [sys.executable, "-c", "print('test')"],
                "eval_full": [sys.executable, "-c", "print('eval')"],
            },
            "command_timeouts_seconds": {"default": 11, "test_full": 7},
        }
        (self.root / "PROJECT.yaml").write_text(json.dumps(data), encoding="utf-8")

        result = self.run_checks()

        self.assertEqual(result.returncode, 0, result.stderr)
        checks = json.loads(self.evidence.read_text(encoding="utf-8"))["checks"]
        self.assertEqual(checks[0]["timeout_seconds"], 7.0)
        self.assertEqual(checks[1]["timeout_seconds"], 11.0)

    def test_generated_manifest_matches_the_published_evidence_schema(self):
        self.write_project([sys.executable, "-c", "print('pass')"])
        self.init_git()

        result = self.run_checks(checks=("test_full",))

        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(self.evidence.read_text(encoding="utf-8"))
        schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
        assert_matches_schema(self, manifest, schema, schema)

    def test_omitted_checks_runs_the_project_verification_inventory_in_order(self):
        names = ["test_full", "start", "health_check", "smoke", "stop", "eval_full", "business_e2e"]
        data = {
            "commands": {name: [sys.executable, "-c", f"print('{name}')"] for name in names},
            "verification": {"check_inventory": names},
        }
        (self.root / "PROJECT.yaml").write_text(json.dumps(data), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(self.root),
                "--evidence",
                str(self.evidence),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        self.assertEqual(evidence["phase"], "full")
        self.assertEqual([check["name"] for check in evidence["checks"]], names)


class InstallPreCommitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True)
        data = {
            "commands": {
                "pre_commit_full": [sys.executable, "-c", "print('full-suite')"],
            },
            "pre_commit": {"hook_path": ".githooks/pre-commit", "full_suite": True},
        }
        (self.root / "PROJECT.yaml").write_text(json.dumps(data), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def install(self):
        return subprocess.run(
            [sys.executable, str(INSTALL_HOOK), "--project-root", str(self.root)],
            capture_output=True,
            text=True,
        )

    def test_installs_portable_versioned_full_suite_hook_and_local_runner(self):
        result = self.install()

        self.assertEqual(result.returncode, 0, result.stderr)
        hook = self.root / ".githooks/pre-commit"
        runner = self.root / "scripts/vibe-coding/run_project_checks.py"
        hook_text = hook.read_text(encoding="utf-8")
        self.assertTrue(runner.exists())
        self.assertIn("vibe-coding-pre-commit version 2.0", hook_text)
        self.assertIn("git rev-parse --show-toplevel", hook_text)
        self.assertIn("scripts/vibe-coding/run_project_checks.py", hook_text)
        self.assertNotIn(str(SKILL_ROOT), hook_text)
        self.assertNotIn(str(self.root), hook_text)
        hooks_path = subprocess.run(
            ["git", "config", "--worktree", "core.hooksPath"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(hooks_path.stdout.strip(), ".githooks")

        moved = self.root.parent / "moved-project"
        shutil.move(self.root, moved)
        self.root = moved
        hook_result = subprocess.run([str(moved / ".githooks/pre-commit")], cwd=moved, capture_output=True, text=True)
        self.assertEqual(hook_result.returncode, 0, hook_result.stderr)
        evidence = json.loads((moved / "docs/evidence/pre-commit-latest.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["phase"], "pre_commit")
        self.assertEqual([item["name"] for item in evidence["checks"]], ["pre_commit_full"])

    def test_refuses_to_overwrite_a_conflicting_hook(self):
        hook = self.root / ".githooks/pre-commit"
        hook.parent.mkdir(parents=True)
        original = "#!/bin/sh\necho user-hook\n"
        hook.write_text(original, encoding="utf-8")

        result = self.install()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(hook.read_text(encoding="utf-8"), original)
        self.assertFalse((self.root / "scripts/vibe-coding/run_project_checks.py").exists())
        hooks_path = subprocess.run(
            ["git", "config", "core.hooksPath"], cwd=self.root, capture_output=True, text=True, check=False
        )
        self.assertEqual(hooks_path.stdout.strip(), "")

    def test_refuses_to_overwrite_a_conflicting_project_runner(self):
        runner = self.root / "scripts/vibe-coding/run_project_checks.py"
        runner.parent.mkdir(parents=True)
        runner.write_text("# user-owned runner\n", encoding="utf-8")

        result = self.install()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(runner.read_text(encoding="utf-8"), "# user-owned runner\n")
        self.assertFalse((self.root / ".githooks/pre-commit").exists())


if __name__ == "__main__":
    unittest.main()
