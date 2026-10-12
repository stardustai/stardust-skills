"""真实离线命令行流程，以及时间、隐私和报告输入边界。"""

import copy
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from work_summary import common, config, report


WINDOW = {"start": "2024-06-01T00:00:00+08:00", "end": "2024-06-02T00:00:00+08:00",
          "timezone": "Asia/Shanghai", "observed_at": "2024-06-02T12:00:00+08:00"}


def evidence_bundle():
    item = {"id": "git-commit-example", "source": "git", "kind": "commit", "project": "示例项目",
            "title": "实现检查", "locator": "/example/repository@123", "event_time": "2024-06-01T12:00:00+08:00",
            "time_basis": "author_time", "attribution": "author", "content": "仅供核查的实现证据",
            "verification": "record_only", "warnings": [], "metadata": {}}
    return {"schema_version": 1, "company": "示例公司", "window": copy.deepcopy(WINDOW),
            "sources": [{"source": name, "status": "complete", "scope": ["授权示例范围"],
                         "items": [item] if name == "git" else [], "gaps": []}
                        for name in ("git", "dingtalk", "local")]}


def findings(identifier="git-commit-example"):
    return {"items": [{"project": "示例项目", "title": "实现检查", "action": "补充实现",
                        "result": "等待业务验证", "status": "进行中", "attribution": "本人编写",
                        "evidence_ids": [identifier], "time_scope": "in_period",
                        "event_time": "2024-06-01T12:00:00+08:00", "risks": [], "next_steps": []}]}


class WorkflowCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="summary-workflow-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.state = self.base / "state"
        self.repository = self.base / "company-repository"
        self.workspace = self.base / "company-materials"
        self.repository.mkdir()
        self.workspace.mkdir()
        self.config_path = self.state / "config.json"
        self.environment = {key: value for key, value in os.environ.items()
                            if key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL")}
        self.environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                                 "GIT_TERMINAL_PROMPT": "0"})
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "author@example.invalid")
        self.git("config", "user.name", "Example Author")
        self.git("config", "commit.gpgsign", "false")
        (self.repository / "component.txt").write_text("implemented synthetic feature\n", encoding="utf-8")
        self.git("add", "component.txt")
        dates = dict(self.environment, GIT_AUTHOR_DATE="2024-06-01T12:00:00+08:00",
                     GIT_COMMITTER_DATE="2024-06-01T12:00:00+08:00")
        self.git("commit", "-q", "-m", "补充示例功能", environment=dates)
        material = self.workspace / "设计说明.md"
        material.write_text("# 示例公司项目\n完成设计草案，待评审。\n", encoding="utf-8")
        timestamp = datetime(2024, 6, 1, 13, tzinfo=timezone.utc).timestamp()
        os.utime(material, (timestamp, timestamp))

    def git(self, *arguments, environment=None):
        return subprocess.run(["git", *arguments], cwd=str(self.repository), env=environment or self.environment,
                              text=True, encoding="utf-8", capture_output=True, check=True)

    def cli(self, *arguments):
        return subprocess.run([sys.executable, str(ROOT / "scripts/daily_summary.py"), *map(str, arguments)],
                              cwd=str(ROOT), env=self.environment, text=True, encoding="utf-8",
                              capture_output=True, timeout=20)

    def initialize(self):
        result = self.cli("init", "--config", self.config_path, "--company", "示例公司", "--name", "Example Author")
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def configure(self):
        value = self.initialize()
        value["identity"]["git_emails"] = ["author@example.invalid"]
        value["git"]["repositories"] = [{"name": "示例项目", "path": str(self.repository)}]
        value["local"]["roots"] = [{"path": str(self.workspace), "mode": "workspace", "project": "示例项目"}]
        value["dingtalk"]["enabled"] = False
        self.config_path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return value

    def collect_offline(self, name="run"):
        destination = self.state / name
        result = self.cli("collect", "--config", self.config_path, "--start", "2024-06-01", "--end", "2024-06-01",
                          "--output-dir", destination, "--offline")
        return result, destination

    def test_init_private_config_and_no_overwrite(self):
        config_value = self.initialize()
        self.assertEqual("示例公司", config_value["company"]["name"])
        self.assertEqual([], config_value["git"]["repositories"])
        self.assertEqual(0o600, stat.S_IMODE(self.config_path.stat().st_mode))
        self.assertEqual(0o700, stat.S_IMODE(self.state.stat().st_mode))
        before = self.config_path.read_bytes()
        second = self.cli("init", "--config", self.config_path, "--company", "另一公司")
        self.assertEqual(1, second.returncode)
        self.assertEqual(before, self.config_path.read_bytes())

    def test_doctor_with_disabled_dingtalk_requires_no_network(self):
        self.configure()
        result = self.cli("doctor", "--config", self.config_path)
        self.assertEqual(0, result.returncode, result.stderr)
        checks = json.loads(result.stdout)["checks"]
        self.assertTrue(all(check["ok"] for check in checks if not check.get("optional")))

    def test_offline_collect_returns_partial_exit_and_keeps_private_artifacts(self):
        self.configure()
        result, destination = self.collect_offline()
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertEqual(0o700, stat.S_IMODE(destination.stat().st_mode))
        self.assertEqual({"evidence.json", "draft.md", "manifest.json"}, {path.name for path in destination.iterdir()})
        for path in destination.iterdir():
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
        bundle = json.loads((destination / "evidence.json").read_text(encoding="utf-8"))
        sources = {source["source"]: source for source in bundle["sources"]}
        self.assertEqual("unavailable", sources["dingtalk"]["status"])
        self.assertTrue(sources["dingtalk"]["gaps"])
        self.assertEqual(1, len(sources["git"]["items"]))
        self.assertIn("implemented synthetic feature", sources["git"]["items"][0]["content"])
        self.assertEqual(1, len(sources["local"]["items"]))
        self.assertIsNone(sources["local"]["items"][0]["event_time"])
        self.assertEqual("unknown", sources["local"]["items"][0]["attribution"])
        self.assertEqual(str(destination), json.loads(result.stdout)["output_dir"])
        self.assertEqual([], list(self.repository.glob("evidence.json")))
        self.assertEqual(0, self.cli("check", "--bundle", destination / "evidence.json").returncode)

    def test_collect_will_not_overwrite_or_write_inside_sources(self):
        self.configure()
        first, destination = self.collect_offline()
        self.assertEqual(2, first.returncode, first.stderr)
        before = {path.name: path.read_bytes() for path in destination.iterdir()}
        repeated, _ = self.collect_offline()
        self.assertEqual(1, repeated.returncode)
        self.assertEqual(before, {path.name: path.read_bytes() for path in destination.iterdir()})
        for location in (self.workspace / "summary", self.repository / "summary"):
            result = self.cli("collect", "--config", self.config_path, "--start", "2024-06-01", "--end", "2024-06-01",
                              "--offline", "--output-dir", location)
            self.assertEqual(1, result.returncode)
            self.assertFalse(location.exists())

    def test_render_and_check_real_collected_evidence(self):
        self.configure()
        result, destination = self.collect_offline()
        self.assertEqual(2, result.returncode, result.stderr)
        bundle_path = destination / "evidence.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        identifier = next(source for source in bundle["sources"] if source["source"] == "git")["items"][0]["id"]
        findings_path = self.state / "findings.json"
        findings_path.write_text(json.dumps(findings(identifier)), encoding="utf-8")
        report_path = self.state / "report.md"
        result = self.cli("render", "--bundle", bundle_path, "--findings", findings_path, "--output", report_path)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(0o600, stat.S_IMODE(report_path.stat().st_mode))
        before = report_path.read_bytes()
        self.assertIn(identifier, before.decode("utf-8"))
        repeated = self.cli("render", "--bundle", bundle_path, "--findings", findings_path, "--output", report_path)
        self.assertEqual(1, repeated.returncode)
        self.assertEqual(before, report_path.read_bytes())
        invalid = findings("forged-evidence-id")
        findings_path.write_text(json.dumps(invalid), encoding="utf-8")
        self.assertEqual(1, self.cli("check", "--bundle", bundle_path, "--findings", findings_path).returncode)
        invalid = findings(identifier)
        invalid["items"][0]["event_time"] = WINDOW["end"]
        findings_path.write_text(json.dumps(invalid), encoding="utf-8")
        self.assertEqual(1, self.cli("check", "--bundle", bundle_path, "--findings", findings_path).returncode)

    def test_invalid_configuration_exits_cleanly_before_creating_output(self):
        self.configure()
        value = json.loads(self.config_path.read_text(encoding="utf-8"))
        value["local"]["roots"][0]["path"] = "/"
        self.config_path.write_text(json.dumps(value), encoding="utf-8")
        result, destination = self.collect_offline()
        self.assertEqual(1, result.returncode)
        self.assertFalse(destination.exists())
        self.assertNotIn("Traceback", result.stderr)

    def test_init_refuses_any_git_worktree(self):
        target = self.repository / "personal-config.json"
        result = self.cli("init", "--config", target, "--company", "示例公司")
        self.assertEqual(1, result.returncode)
        self.assertFalse(target.exists())


class CommonBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="summary-common-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def test_window_date_end_is_inclusive_but_iso_end_is_exclusive(self):
        now = datetime(2024, 6, 4, tzinfo=timezone.utc)
        day = common.make_window("2024-06-01", "2024-06-02", "Asia/Shanghai", now=now)
        self.assertEqual("2024-06-03T00:00:00+08:00", day["end"])
        self.assertTrue(common.in_window("2024-06-01T00:00:00+08:00", day))
        self.assertFalse(common.in_window(day["end"], day))
        exact = common.make_window("2024-06-01", "2024-06-02T00:00:00+08:00", "Asia/Shanghai", now=now)
        self.assertEqual("2024-06-02T00:00:00+08:00", exact["end"])
        self.assertFalse(common.in_window("2024-06-02T00:00:00+08:00", exact))

    def test_future_end_is_capped_at_observation_and_future_start_rejected(self):
        now = datetime(2024, 6, 1, 6, 30, tzinfo=timezone.utc)
        window = common.make_window("2024-06-01", "2024-06-03", now=now)
        self.assertEqual(now, common.parse_time(window["end"]))
        self.assertTrue(window["capped_at_now"])
        with self.assertRaises(ValueError):
            common.make_window("2024-06-02", "2024-06-03", now=now)
        with self.assertRaises(ValueError):
            common.make_window("2024-06-01T00:00:00", now=now)

    def test_dst_days_use_real_23_and_25_hour_intervals(self):
        now = datetime(2024, 12, 1, tzinfo=timezone.utc)
        for day, hours in (("2024-03-10", 23), ("2024-11-03", 25)):
            window = common.make_window(day, day, "America/New_York", now=now)
            elapsed = common.parse_time(window["end"]) - common.parse_time(window["start"])
            self.assertEqual(hours * 3600, elapsed.total_seconds())

    def test_dst_repeated_hour_compares_instants_not_wall_clock(self):
        now = common.parse_time("2024-11-03T01:15:00-05:00")
        window = common.make_window("2024-11-03T01:30:00-04:00", "2024-11-03T02:00:00-05:00",
                                    "America/New_York", now=now)
        self.assertEqual(45 * 60, (common.parse_time(window["end"]) - common.parse_time(window["start"])).total_seconds())
        self.assertTrue(window["capped_at_now"])
        earlier_end = common.make_window("2024-11-03T01:30:00-04:00", "2024-11-03T01:40:00-04:00",
                                         "America/New_York", now=now)
        self.assertFalse(earlier_end["capped_at_now"])
        self.assertEqual(10 * 60, (common.parse_time(earlier_end["end"]) - common.parse_time(earlier_end["start"])).total_seconds())

    def test_naive_times_are_rejected_and_numeric_timestamps_agree(self):
        self.assertIsNone(common.parse_time("2024-06-01T12:00:00"))
        self.assertIsNone(common.parse_time(datetime(2024, 6, 1)))
        self.assertEqual(common.parse_time(1717200000), common.parse_time(1717200000000))
        self.assertIsNone(common.parse_time(float("inf")))

    def test_run_filters_environment_and_does_not_interpret_shell_text(self):
        code = "import json, os, sys; print(json.dumps({'secret': os.getenv('SUMMARY_TEST_SECRET'), 'git_dir': os.getenv('GIT_DIR'), 'path': bool(os.getenv('PATH')), 'argument': sys.argv[1]}))"
        argument = "$(touch should-not-exist); echo example"
        with patch.dict(os.environ, {"SUMMARY_TEST_SECRET": "synthetic-private-value", "GIT_DIR": "/outside-repository"}):
            result = common.run([sys.executable, "-c", code, argument], cwd=str(self.root))
        self.assertEqual(0, result.returncode)
        actual = json.loads(result.stdout)
        self.assertIsNone(actual["secret"])
        self.assertIsNone(actual["git_dir"])
        self.assertTrue(actual["path"])
        self.assertEqual(argument, actual["argument"])
        self.assertFalse((self.root / "should-not-exist").exists())

    def test_run_caps_combined_output_and_reports_truncation(self):
        code = "import sys; sys.stdout.write('x' * 3000); sys.stdout.flush(); sys.stderr.write('y' * 3000)"
        result = common.run([sys.executable, "-c", code], timeout=5, max_output_bytes=4096)
        self.assertTrue(result.truncated)
        self.assertLessEqual(len(result.stdout.encode()) + len(result.stderr.encode()), 4096)

    def test_run_timeout_is_bounded_and_does_not_echo_program_output(self):
        started = time.monotonic()
        with self.assertRaises(RuntimeError) as context:
            common.run([sys.executable, "-c", "import time; print('PRIVATE_SYNTHETIC_TEXT', flush=True); time.sleep(2)"], timeout=0.1)
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertNotIn("PRIVATE_SYNTHETIC_TEXT", str(context.exception))

    def test_timeout_stops_children_even_when_original_parent_exited(self):
        marker = self.root / "child-survived.txt"
        child = "import time; from pathlib import Path; time.sleep(0.6); Path(" + repr(str(marker)) + ").write_text('survived')"
        parent = "import subprocess, sys; subprocess.Popen([sys.executable, '-c', " + repr(child) + "])"
        with self.assertRaises(RuntimeError):
            common.run([sys.executable, "-c", parent], timeout=0.2)
        time.sleep(0.7)
        self.assertFalse(marker.exists(), "超时后仍有派生进程写入，进程组未被完整终止")

    def test_private_write_permissions_no_overwrite_and_no_symlink_following(self):
        target = self.root / "private" / "evidence.json"
        common.private_write(target, "original")
        self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))
        self.assertEqual(0o700, stat.S_IMODE(target.parent.stat().st_mode))
        with self.assertRaises(FileExistsError):
            common.private_write(target, "replacement")
        self.assertEqual("original", target.read_text())
        link = target.parent / "alias.json"
        link.symlink_to(target)
        with self.assertRaises(OSError):
            common.private_write(link, "replacement")
        self.assertEqual("original", target.read_text())

    def test_common_credential_patterns_are_removed_recursively(self):
        values = {"api": "api_key=private-example", "url": "https://example.invalid/x?token=private-example",
                  "nested": ["Authorization: Bearer private-example"], "key": "-----BEGIN " + "PRIVATE KEY-----\nprivate-example\n-----END " + "PRIVATE KEY-----"}
        text = common.json_text(values)
        self.assertNotIn("private-example", text)
        self.assertIn("REDACTED", text)


class ReportAndConfigTests(unittest.TestCase):
    def test_default_configuration_requires_explicit_company(self):
        with self.assertRaises(ValueError):
            config.validate_config({})
        valid = config.validate_config({"company": {"name": "示例公司"}})
        self.assertEqual([], valid["git"]["repositories"])
        self.assertEqual([], valid["local"]["roots"])

    def test_invalid_configuration_never_silently_expands_scope(self):
        invalid_values = [
            {"unknown": True}, {"git": {"unknown": True}}, {"git": {"max_commits": 0}},
            {"git": {"max_commits": True}}, {"limits": {"timeout_seconds": 121}},
            {"local": {"max_depth": 33}}, {"identity": {"git_emails": "me@example.invalid"}},
            {"local": {"roots": [{"path": "/", "mode": "workspace"}]}},
            {"git": {"repositories": [{"path": str(Path.home())}]}},
            {"git": {"repositories": [{"path": "relative-project"}]}},
            {"local": {"roots": [{"path": "/example/project", "mode": "mixed", "keywords": []}]}},
            {"dingtalk": {"enabled": "false"}}, {"dingtalk": {"page_size": 31}},
        ]
        for invalid in invalid_values:
            with self.subTest(invalid=invalid):
                value = {"company": {"name": "示例公司"}, **invalid}
                with self.assertRaises(ValueError):
                    config.validate_config(value)

    def test_findings_reject_forged_evidence_and_cross_period_or_naive_dates(self):
        bundle = evidence_bundle()
        with self.assertRaises(ValueError):
            report.validate_findings(findings("forged"), bundle)
        for event_time in ("2024-05-31T23:59:59+08:00", WINDOW["end"], "2024-06-01T12:00:00", None):
            value = findings()
            value["items"][0]["event_time"] = event_time
            with self.subTest(event_time=event_time), self.assertRaises(ValueError):
                report.validate_findings(value, bundle)
        uncertain = findings()
        uncertain["items"][0]["time_scope"] = "uncertain"
        uncertain["items"][0]["event_time"] = None
        self.assertIs(uncertain, report.validate_findings(uncertain, bundle))

    def test_findings_date_precision_preserves_real_day_without_inventing_time(self):
        bundle = evidence_bundle()
        value = findings()
        value["items"][0].pop("event_time")
        value["items"][0]["event_date"] = "2024-06-01"
        self.assertIs(value, report.validate_findings(value, bundle))
        self.assertNotIn("event_time", value["items"][0])
        for bad_day in ("2024-05-31", "2024-06-02", "2024-06-01T12:00:00+08:00", "invalid", 1):
            value["items"][0]["event_date"] = bad_day
            with self.subTest(event_date=bad_day), self.assertRaises(ValueError):
                report.validate_findings(value, bundle)
        value["items"][0]["event_date"] = "2024-06-01"
        value["items"][0]["event_time"] = "2024-05-31T12:00:00+08:00"
        with self.assertRaises(ValueError):
            report.validate_findings(value, bundle)

    def test_findings_event_date_uses_configured_timezone(self):
        bundle = evidence_bundle()
        bundle["window"].update(start="2024-05-31T17:00:00+00:00", end="2024-05-31T18:00:00+00:00")
        value = findings()
        value["items"][0].pop("event_time")
        value["items"][0]["event_date"] = "2024-06-01"
        self.assertIs(value, report.validate_findings(value, bundle))
        value["items"][0]["event_date"] = "2024-05-31"
        with self.assertRaises(ValueError):
            report.validate_findings(value, bundle)

    def test_bundle_rejects_duplicate_ids_source_mismatch_and_hidden_gaps(self):
        for change in ("duplicate", "mismatch", "hidden_gap", "source_duplicate"):
            bundle = evidence_bundle()
            if change == "duplicate":
                bundle["sources"][0]["items"].append(copy.deepcopy(bundle["sources"][0]["items"][0]))
            elif change == "mismatch":
                bundle["sources"][0]["items"][0]["source"] = "local"
            elif change == "hidden_gap":
                bundle["sources"][0]["gaps"] = ["实际上未完成"]
            else:
                bundle["sources"][1]["source"] = "git"
            with self.subTest(change=change), self.assertRaises(ValueError):
                report.validate_bundle(bundle)

    def test_bundle_rejects_missing_naive_and_reversed_windows(self):
        for change in ("missing", "naive", "reversed"):
            bundle = evidence_bundle()
            if change == "missing":
                del bundle["window"]
            elif change == "naive":
                bundle["window"]["start"] = "2024-06-01T00:00:00"
            else:
                bundle["window"]["start"], bundle["window"]["end"] = bundle["window"]["end"], bundle["window"]["start"]
            with self.subTest(change=change), self.assertRaises(ValueError):
                report.validate_bundle(bundle)

    def test_bundle_rejects_malformed_source_and_evidence_shapes_cleanly(self):
        for change in ("source", "item"):
            bundle = evidence_bundle()
            if change == "source":
                bundle["sources"][0] = "not an object"
            else:
                bundle["sources"][0]["items"] = [None]
            with self.subTest(change=change), self.assertRaises(ValueError):
                report.validate_bundle(bundle)

    def test_report_displays_untrusted_markdown_as_text(self):
        bundle = evidence_bundle()
        malicious = "![tracker](https://example.invalid/image) [click](javascript:alert(1)) <script>evil()</script> | extra\r\n# forged-heading"
        bundle["company"] = malicious
        item = bundle["sources"][0]["items"][0]
        for key in ("title", "project", "locator"):
            item[key] = malicious
        result = report.render(bundle)
        self.assertNotIn("![tracker](", result)
        self.assertNotIn("[click](javascript:", result)
        self.assertNotIn("<script>", result)
        self.assertNotIn("\n# forged-heading", result)
        self.assertNotIn("\r", result)
        self.assertIn("git-commit-example", result)
        self.assertIn("tracker", result)

    def test_markdown_escape_preserves_original_text_after_display_decoding(self):
        original = r"[方括号](括号) !图片 #标题 *强调* _下划线_ `代码` {对象} \路径 |表格 &实体"
        self.assertEqual(original, html.unescape(report.cell(original)))

    def test_report_does_not_promote_raw_evidence_to_completion(self):
        bundle = evidence_bundle()
        raw = report.render(bundle)
        self.assertNotIn("## 本期工作", raw)
        self.assertNotIn(bundle["sources"][0]["items"][0]["content"], raw)
        mixed = findings()
        historical = copy.deepcopy(mixed["items"][0])
        historical.update(time_scope="historical", event_time="2023-06-01T00:00:00+08:00", title="历史事项")
        mixed["items"].append(historical)
        result = report.render(bundle, mixed)
        self.assertLess(result.index("## 本期工作"), result.index("历史事项"))
        self.assertIn("历史背景", result)


if __name__ == "__main__":
    unittest.main()
