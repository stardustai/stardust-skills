"""私有整理模板与临时安装的发布边界测试；不访问真实 Skill 安装目录。"""

import copy
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def bundle():
    sources = []
    for name in ("git", "dingtalk", "local"):
        item = {"id": name + "-example", "source": name, "kind": "commit" if name == "git" else "document",
                "project": "合成项目", "title": "待核对记录", "locator": "/example/" + name,
                "event_time": None, "time_basis": "unknown", "attribution": "unknown",
                "content": "FULL_BODY_MUST_NOT_BECOME_A_FINDING", "verification": "record_only",
                "warnings": [], "metadata": {}}
        sources.append({"source": name, "status": "complete", "scope": ["合成范围"], "items": [item], "gaps": []})
    return {"schema_version": 1, "company": "示例公司", "sources": sources,
            "window": {"start": "2024-06-01T00:00:00+08:00", "end": "2024-06-02T00:00:00+08:00",
                       "observed_at": "2024-06-02T12:00:00+08:00", "timezone": "Asia/Shanghai"}}


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="summary-distribution-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.environment = {key: value for key, value in os.environ.items()
                            if key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL")}
        self.environment["PYTHONDONTWRITEBYTECODE"] = "1"
        self.bundle_path = self.base / "evidence.json"
        self.bundle_path.write_text(json.dumps(bundle(), ensure_ascii=False), encoding="utf-8")

    def program(self, script, *arguments):
        return subprocess.run([sys.executable, str(script), *map(str, arguments)], cwd=str(self.base),
                              env=self.environment, text=True, encoding="utf-8", capture_output=True, timeout=20)

    def cli(self, *arguments):
        return self.program(ROOT / "scripts/daily_summary.py", *arguments)

    def template(self):
        target = self.base / "private" / "findings.json"
        result = self.cli("prepare-review", "--bundle", self.bundle_path, "--output", target)
        self.assertEqual(0, result.returncode, result.stderr)
        return target, json.loads(target.read_text(encoding="utf-8"))

    def source_fixture(self, with_references=True):
        """仅复制当前发布源代码与公开规则，随后添加完全合成的禁入文件。"""
        source = self.base / "source"
        source.mkdir()
        for filename in ("SKILL.md", "README.md", "config.example.json", "agents/openai.yaml"):
            target = source / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / filename, target)
        for path in (ROOT / "scripts").rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            target = source / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        if with_references:
            (source / "references").mkdir()
            (source / "references/public.md").write_text("# 公开说明\n", encoding="utf-8")
        (source / "tests").mkdir()
        (source / "tests/test_example.py").write_text("# 公开测试占位\n", encoding="utf-8")
        return source

    def install(self, source=ROOT, destination=None):
        destination = destination or self.base / "skills"
        result = self.program(source / "scripts/install_skill.py", "--dest", destination)
        return result, destination / "daily-work-summary"

    def test_prepare_review_produces_private_uncertain_template_with_real_ids(self):
        target, findings = self.template()
        self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))
        self.assertEqual(0o700, stat.S_IMODE(target.parent.stat().st_mode))
        self.assertEqual({"git-example", "dingtalk-example", "local-example"},
                         {item["evidence_ids"][0] for item in findings["items"]})
        self.assertEqual(3, len(findings["items"]))
        for item in findings["items"]:
            self.assertEqual("", item["action"])
            self.assertEqual("", item["result"])
            self.assertEqual("uncertain", item["time_scope"])
            self.assertIsNone(item["event_time"])
            self.assertIsNone(item["event_date"])
        self.assertNotIn("FULL_BODY_MUST_NOT_BECOME_A_FINDING", target.read_text(encoding="utf-8"))

    def test_template_requires_action_and_result_before_check_can_pass(self):
        target, initial = self.template()
        result = self.cli("check", "--bundle", self.bundle_path, "--findings", target)
        self.assertEqual(1, result.returncode)
        for field in ("action", "result"):
            value = copy.deepcopy(initial)
            for item in value["items"]:
                item.update(action="核对材料", result="待业务确认")
            value["items"][0].pop(field)
            target.write_text(json.dumps(value), encoding="utf-8")
            result = self.cli("check", "--bundle", self.bundle_path, "--findings", target)
            self.assertEqual(1, result.returncode, field)
        for item in initial["items"]:
            item.update(action="核对材料", result="待业务确认")
        target.write_text(json.dumps(initial), encoding="utf-8")
        self.assertEqual(0, self.cli("check", "--bundle", self.bundle_path, "--findings", target).returncode)

    def test_prepare_review_does_not_overwrite_existing_template(self):
        target, _ = self.template()
        target.write_text("existing user review", encoding="utf-8")
        result = self.cli("prepare-review", "--bundle", self.bundle_path, "--output", target)
        self.assertEqual(1, result.returncode)
        self.assertEqual("existing user review", target.read_text(encoding="utf-8"))

    def test_prepare_review_requires_output_and_valid_bundle(self):
        missing_output = self.cli("prepare-review", "--bundle", self.bundle_path)
        self.assertEqual(1, missing_output.returncode)
        invalid = bundle()
        invalid["sources"][0]["items"][0]["id"] = "invalid id!"
        self.bundle_path.write_text(json.dumps(invalid), encoding="utf-8")
        target = self.base / "invalid-findings.json"
        result = self.cli("prepare-review", "--bundle", self.bundle_path, "--output", target)
        self.assertEqual(1, result.returncode)
        self.assertFalse(target.exists())

    def test_installed_cli_version_and_help_are_self_contained(self):
        result, target = self.install()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(0o700, stat.S_IMODE(target.stat().st_mode))
        for path in target.rglob("*"):
            if path.is_file():
                self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode), str(path))
        script = target / "scripts/daily_summary.py"
        version = self.program(script, "--version")
        self.assertEqual(0, version.returncode, version.stderr)
        self.assertRegex(version.stdout.strip(), r"^\d+\.\d+\.\d+")
        help_result = self.program(script, "--help")
        self.assertEqual(0, help_result.returncode, help_result.stderr)
        self.assertIn("prepare-review", help_result.stdout)
        self.assertIn("collect", help_result.stdout)
        self.assertTrue((target / "SKILL.md").is_file())
        self.assertTrue((target / "config.example.json").is_file())

    def test_same_name_installation_is_refused_without_mutation(self):
        source = self.source_fixture()
        first, target = self.install(source)
        self.assertEqual(0, first.returncode, first.stderr)
        marker = target / "owner-note.txt"
        marker.write_text("existing installation", encoding="utf-8")
        before = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
        second, _ = self.install(source)
        self.assertNotEqual(0, second.returncode)
        after = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_install_excludes_configuration_caches_logs_and_runtime_artifacts(self):
        source = self.source_fixture()
        forbidden = ["config.json", ".env", "evidence.json", "manifest.json", "activity.log",
                     "scripts/config.json", "scripts/.env", "scripts/activity.log", "scripts/local.pyc",
                     "scripts/__pycache__/cached.py", "scripts/__pycache__/cached.cpython-39.pyc",
                     "scripts/.cache/generated.py", "tests/fixtures/personal.json",
                     "references/evidence.json", "references/session.log", "references/draft.md",
                     "references/runs/report.md", "agents/private.yaml", "runs/evidence.json"]
        for relative in forbidden:
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("SYNTHETIC_PRIVATE_STATE", encoding="utf-8")
        result, target = self.install(source)
        self.assertEqual(0, result.returncode, result.stderr)
        copied_forbidden = [relative for relative in forbidden if (target / relative).exists()]
        self.assertEqual([], copied_forbidden)
        self.assertTrue((target / "scripts/work_summary/config.py").is_file())
        self.assertTrue((target / "references/public.md").is_file())
        self.assertTrue((target / "agents/openai.yaml").is_file())
        self.assertFalse(any("SYNTHETIC_PRIVATE_STATE" in path.read_text(encoding="utf-8")
                             for path in target.rglob("*") if path.is_file()))

    def test_install_does_not_follow_file_symlinks(self):
        source = self.source_fixture()
        outside = self.base / "outside-private.md"
        outside.write_text("outside private material", encoding="utf-8")
        (source / "references/alias.md").symlink_to(outside)
        result, target = self.install(source)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((target / "references/alias.md").exists())

    def test_install_does_not_follow_top_level_directory_symlinks(self):
        source = self.source_fixture(with_references=False)
        outside = self.base / "outside-references"
        outside.mkdir()
        (outside / "private.md").write_text("outside private material", encoding="utf-8")
        (source / "references").symlink_to(outside, target_is_directory=True)
        result, target = self.install(source)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(target.exists())
        self.assertFalse((target / "references/private.md").exists())

    def test_install_cannot_write_inside_source_distribution(self):
        source = self.source_fixture()
        result, target = self.install(source, destination=source)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
