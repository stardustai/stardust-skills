"""用一次性真实 Git 仓库验证采集范围、归属和保守的完成状态。"""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from work_summary import git_source
from work_summary.common import CommandResult


WINDOW = {"start": "2026-09-28T00:00:00+08:00", "end": "2026-09-29T00:00:00+08:00",
          "timezone": "Asia/Shanghai", "observed_at": "2026-09-28T22:00:00+08:00"}
TODAY = "2026-09-28T10:00:00+08:00"
BEFORE = "2026-09-20T10:00:00+08:00"
SELF = "me@example.invalid"
COLLEAGUE = "colleague@example.invalid"


class GitSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="work-summary-git-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "project"
        self.repo.mkdir()
        self.environment = {key: value for key, value in os.environ.items()
                            if key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL")}
        self.environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                                 "GIT_TERMINAL_PROMPT": "0"})
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Example User")
        self.git("config", "user.email", SELF)
        self.git("config", "commit.gpgsign", "false")
        self.config = {
            "company": {"name": "Example"}, "identity": {"name": "Example User", "git_emails": [SELF]},
            "git": {"repositories": [{"name": "project", "path": str(self.repo)}],
                    "max_commits": 500, "include_worktree": True},
            "limits": {"timeout_seconds": 10, "max_content_chars": 20_000},
        }

    def git(self, *arguments, cwd=None, environment=None):
        result = subprocess.run(["git", *arguments], cwd=str(cwd or self.repo),
                                env=environment or self.environment, capture_output=True, text=True,
                                encoding="utf-8", check=True)
        return result.stdout.strip()

    def commit(self, message="example change", filename="main.txt", content="example\n",
               authored_at=TODAY, committed_at=TODAY, author=SELF, committer=SELF, cwd=None):
        root = Path(cwd or self.repo)
        target = root / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self.git("add", "--", filename, cwd=root)
        environment = dict(self.environment, GIT_AUTHOR_NAME="Author", GIT_AUTHOR_EMAIL=author,
                           GIT_COMMITTER_NAME="Committer", GIT_COMMITTER_EMAIL=committer,
                           GIT_AUTHOR_DATE=authored_at, GIT_COMMITTER_DATE=committed_at)
        self.git("-c", "commit.gpgsign=false", "commit", "-q", "-m", message, cwd=root,
                 environment=environment)
        return self.git("rev-parse", "HEAD", cwd=root)

    def collect(self, config=None):
        return git_source.collect(config or self.config, WINDOW)

    @staticmethod
    def commits(result):
        return [item for item in result["items"] if item["kind"] == "commit"]

    def test_not_configured_and_empty_repository(self):
        self.assertEqual("not_configured", git_source.collect({}, WINDOW)["status"])
        result = self.collect()
        self.assertEqual("complete", result["status"], result)
        self.assertEqual([], result["items"])
        self.assertIn("本地快照", result["scope"][0])

    def test_missing_and_non_git_paths_are_unavailable(self):
        for path in (self.base / "missing", self.base):
            config = copy.deepcopy(self.config)
            config["git"]["repositories"][0]["path"] = str(path)
            result = self.collect(config)
            self.assertEqual("unavailable", result["status"], result)
            self.assertTrue(result["gaps"])

    def test_repository_subdirectory_cannot_expand_authorization(self):
        self.commit()
        subdirectory = self.repo / "subdirectory"
        subdirectory.mkdir()
        self.config["git"]["repositories"][0]["path"] = str(subdirectory)
        result = self.collect()
        self.assertEqual("unavailable", result["status"], result)
        self.assertEqual([], result["items"])
        self.assertTrue(any("父级仓库" in gap for gap in result["gaps"]))

    def test_commit_contains_real_diff_and_stable_identifier(self):
        revision = self.commit(message="实现中文文件", filename="中文 空格.txt", content="actual-diff-content\n")
        first = self.collect()
        second = self.collect()
        item = self.commits(first)[0]
        self.assertEqual("complete", first["status"], first)
        self.assertEqual("author", item["attribution"])
        self.assertEqual("author_time", item["time_basis"])
        self.assertEqual("record_only", item["verification"])
        self.assertEqual(revision, item["metadata"]["commit"])
        self.assertEqual("中文 空格.txt", item["metadata"]["files"][0]["path"])
        self.assertIn("+actual-diff-content", item["content"])
        self.assertEqual(item["id"], self.commits(second)[0]["id"])

    def test_time_window_includes_start_and_excludes_end(self):
        self.commit(content="old\n", authored_at=BEFORE, committed_at=BEFORE)
        start = self.commit(content="start\n", authored_at=WINDOW["start"], committed_at=WINDOW["start"])
        self.commit(content="end\n", authored_at=WINDOW["end"], committed_at=WINDOW["end"])
        result = self.collect()
        self.assertEqual([start], [item["metadata"]["commit"] for item in self.commits(result)])

    def test_historical_author_current_committer_is_not_today_development(self):
        self.commit(authored_at=BEFORE, committed_at=TODAY)
        item = self.commits(self.collect())[0]
        self.assertEqual("committer_time", item["time_basis"])
        self.assertEqual(TODAY, item["event_time"])
        self.assertFalse(item["metadata"]["author_in_window"])
        self.assertTrue(any("历史创作" in warning for warning in item["warnings"]))

    def test_unordered_dates_do_not_prune_author_time_candidates(self):
        expected = self.commit(authored_at=TODAY, committed_at=BEFORE, content="today author\n")
        self.commit(authored_at=BEFORE, committed_at=BEFORE, content="old head\n")
        result = self.collect()
        self.assertEqual([expected], [item["metadata"]["commit"] for item in self.commits(result)])
        self.assertEqual("author_time", self.commits(result)[0]["time_basis"])

    def test_colleague_authorship_with_own_committer_is_not_claimed_as_own_code(self):
        self.commit(author=COLLEAGUE, committer=SELF)
        item = self.commits(self.collect())[0]
        self.assertEqual("committer", item["attribution"])
        self.assertIn("不能据此认定为本人开发", item["content"])
        self.assertEqual("committer_time", item["time_basis"])

    def test_own_old_committer_current_colleague_author_is_not_today_action(self):
        self.commit(author=COLLEAGUE, committer=SELF, authored_at=TODAY, committed_at=BEFORE)
        item = self.commits(self.collect())[0]
        self.assertEqual("committer", item["attribution"])
        self.assertEqual("author_time", item["time_basis"])
        self.assertTrue(any("不可算为本人当天提交" in warning for warning in item["warnings"]))

    def test_coauthor_and_no_identity_match(self):
        self.commit(author=COLLEAGUE, committer=COLLEAGUE,
                    message="共同完成\n\nCo-authored-by: Example User <ME@example.invalid>")
        result = self.collect()
        self.assertEqual("coauthor", self.commits(result)[0]["attribution"])
        self.config["identity"]["git_emails"] = ["other@example.invalid"]
        result = self.collect()
        self.assertEqual("complete", result["status"])
        self.assertEqual([], self.commits(result))

    def test_multiple_refs_and_duplicate_repositories_deduplicate_hash(self):
        revision = self.commit()
        self.git("branch", "another")
        self.git("tag", "sample")
        self.git("update-ref", "refs/remotes/origin/main", revision)
        self.config["git"]["repositories"].append({"name": "same path", "path": str(self.repo)})
        result = self.collect()
        self.assertEqual(1, len(self.commits(result)))
        self.assertEqual(1, len(result["scope"]))

    def test_remote_tracking_only_commit_is_scanned_without_fetching(self):
        initial = self.commit(authored_at=BEFORE, committed_at=BEFORE)
        target = self.commit(content="remote\n")
        self.git("update-ref", "refs/remotes/origin/main", target)
        self.git("checkout", "--detach", initial)
        self.git("branch", "-f", "main", initial)
        result = self.collect()
        self.assertEqual([target], [item["metadata"]["commit"] for item in self.commits(result)])

    def test_detached_head_is_scanned(self):
        initial = self.commit(authored_at=BEFORE, committed_at=BEFORE)
        self.git("checkout", "--detach", initial)
        target = self.commit(content="detached\n")
        result = self.collect()
        self.assertEqual([target], [item["metadata"]["commit"] for item in self.commits(result)])

    def test_merge_warns_diff_is_first_parent_and_can_include_colleague_code(self):
        self.commit(authored_at=BEFORE, committed_at=BEFORE)
        self.git("checkout", "-b", "feature")
        self.commit(filename="feature.txt", content="colleague implementation\n", author=COLLEAGUE,
                    committer=COLLEAGUE, authored_at=BEFORE, committed_at=BEFORE)
        self.git("checkout", "main")
        environment = dict(self.environment, GIT_AUTHOR_NAME="Example User", GIT_AUTHOR_EMAIL=SELF,
                           GIT_COMMITTER_NAME="Example User", GIT_COMMITTER_EMAIL=SELF,
                           GIT_AUTHOR_DATE=TODAY, GIT_COMMITTER_DATE=TODAY)
        self.git("merge", "--no-ff", "feature", "-m", "合入同事变更", environment=environment)
        item = self.commits(self.collect())[0]
        self.assertTrue(item["metadata"]["is_merge"])
        self.assertIn("+colleague implementation", item["content"])
        self.assertTrue(any("第一父提交" in warning for warning in item["warnings"]))

    def test_worktree_date_and_authorship_remain_unknown(self):
        self.commit(authored_at=BEFORE, committed_at=BEFORE)
        (self.repo / "main.txt").write_text("staged content\n", encoding="utf-8")
        self.git("add", "main.txt")
        (self.repo / "main.txt").write_text("unstaged content\n", encoding="utf-8")
        (self.repo / "未跟踪.txt").write_text("untracked bytes must not be read", encoding="utf-8")
        before = self.git("status", "--porcelain=v1")
        result = self.collect()
        after = self.git("status", "--porcelain=v1")
        item = result["items"][0]
        self.assertEqual("worktree", item["kind"])
        self.assertIsNone(item["event_time"])
        self.assertEqual("unknown", item["attribution"])
        self.assertEqual("unknown", item["time_basis"])
        self.assertIn("+staged content", item["content"])
        self.assertIn("+unstaged content", item["content"])
        self.assertNotIn("untracked bytes must not be read", json.dumps(result))
        self.assertEqual(before, after)
        self.assertEqual("complete", result["status"], result)

    def test_sensitive_files_have_no_diff_content_and_report_gap(self):
        secret = "DO_NOT_READ_THIS_SECRET_CONTENT"
        for name in (".env", "keys.pem", "config/credentials.json", "api-token.txt"):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(secret, encoding="utf-8")
        self.git("add", ".")
        self.commit(filename="normal.txt", content="ordinary bytes\n")
        result = self.collect()
        item = self.commits(result)[0]
        self.assertEqual("partial", result["status"], result)
        self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(4, len(item["metadata"]["filtered_files"]))
        self.assertIn("+ordinary bytes", item["content"])
        self.assertTrue(any("过滤敏感" in gap for gap in result["gaps"]))

    def test_sensitive_uncommitted_files_are_not_read(self):
        self.commit(filename=".env", content="initial secret", authored_at=BEFORE, committed_at=BEFORE)
        (self.repo / ".env").write_text("UNCOMMITTED_SECRET", encoding="utf-8")
        result = self.collect()
        self.assertNotIn("UNCOMMITTED_SECRET", json.dumps(result))
        self.assertEqual([".env"], result["items"][0]["metadata"]["filtered_files"])

    def test_external_worktree_is_not_read_until_explicitly_configured(self):
        self.commit(authored_at=BEFORE, committed_at=BEFORE)
        external = self.base / "external"
        self.git("worktree", "add", "--detach", str(external), "HEAD")
        target = self.commit(cwd=external, content="external detached\n")
        (external / "main.txt").write_text("outside modified", encoding="utf-8")
        observed_paths = []
        real_run = git_source.run
        def capture(arguments, **kwargs):
            observed_paths.append(Path(kwargs["cwd"]))
            return real_run(arguments, **kwargs)
        with patch.object(git_source, "run", side_effect=capture):
            result = self.collect()
        self.assertNotIn(external, observed_paths)
        self.assertEqual([], result["items"])
        self.assertEqual("partial", result["status"])
        self.assertTrue(any("配置路径外" in gap for gap in result["gaps"]))
        self.config["git"]["repositories"].append({"name": "external", "path": str(external)})
        allowed = self.collect()
        self.assertEqual("complete", allowed["status"], allowed)
        self.assertEqual([target], [item["metadata"]["commit"] for item in self.commits(allowed)])
        self.assertTrue(any(item["locator"] == str(external.resolve()) for item in allowed["items"]
                            if item["kind"] == "worktree"))

    def test_authorized_nested_worktree_is_scanned(self):
        self.commit(authored_at=BEFORE, committed_at=BEFORE)
        nested = self.repo / "nested-worktree"
        self.git("worktree", "add", "--detach", str(nested), "HEAD")
        target = self.commit(cwd=nested, content="nested detached\n")
        self.config["git"]["include_worktree"] = False
        result = self.collect()
        self.assertEqual("complete", result["status"], result)
        self.assertEqual([target], [item["metadata"]["commit"] for item in self.commits(result)])

    def test_history_scan_cap_is_partial_even_if_no_identity_matches(self):
        for index in range(3):
            self.commit(content=str(index), authored_at=BEFORE, committed_at=BEFORE)
        self.config["git"]["max_commits"] = 2
        self.config["identity"]["git_emails"] = ["nobody@example.invalid"]
        result = self.collect()
        self.assertEqual("partial", result["status"])
        self.assertEqual([], result["items"])
        self.assertTrue(any("max_commits=2" in gap for gap in result["gaps"]))

    def test_content_limit_is_explicit_and_marks_partial(self):
        self.commit(content="long content\n" * 100)
        self.config["limits"]["max_content_chars"] = 100
        result = self.collect()
        item = self.commits(result)[0]
        self.assertLessEqual(len(item["content"]), 100)
        self.assertTrue(any("max_content_chars" in warning for warning in item["warnings"]))
        self.assertEqual("partial", result["status"])

    def test_process_output_truncation_preserves_complete_records_and_marks_partial(self):
        self.commit()
        real_run = git_source.run
        def truncate(arguments, **kwargs):
            result = real_run(arguments, **kwargs)
            if "log" in arguments:
                return CommandResult(-9, result.stdout, "", True)
            return result
        with patch.object(git_source, "run", side_effect=truncate):
            result = self.collect()
        self.assertEqual("partial", result["status"], result)
        self.assertEqual(1, len(self.commits(result)))
        self.assertTrue(any("历史输出达到上限" in gap for gap in result["gaps"]))

    def test_actual_diff_output_cap_reports_truncation(self):
        self.commit(content="large patch\n" * 5000)
        self.config["limits"]["max_content_chars"] = 2000
        result = self.collect()
        self.assertEqual("partial", result["status"])
        self.assertTrue(any("实际 diff 输出达到上限" in warning
                            for warning in self.commits(result)[0]["warnings"]))

    def test_timeout_is_safe_and_unavailable(self):
        with patch.object(git_source, "run", side_effect=RuntimeError("DO_NOT_EXPOSE_INTERNAL_ERROR")):
            result = self.collect()
        self.assertEqual("unavailable", result["status"])
        self.assertNotIn("DO_NOT_EXPOSE_INTERNAL_ERROR", json.dumps(result))
        self.assertTrue(any("超时" in gap for gap in result["gaps"]))

    def test_diff_timeout_does_not_discard_other_commits(self):
        earlier = self.commit(content="first\n")
        later = self.commit(content="second\n")
        real_run = git_source.run
        def timeout(arguments, **kwargs):
            if later in arguments and "--name-status" in arguments:
                raise RuntimeError("safe timeout")
            return real_run(arguments, **kwargs)
        with patch.object(git_source, "run", side_effect=timeout):
            result = self.collect()
        self.assertEqual("partial", result["status"])
        self.assertEqual([earlier], [item["metadata"]["commit"] for item in self.commits(result)])

    def test_bare_repository_can_supply_commit_records(self):
        target = self.commit()
        bare = self.base / "bare.git"
        self.git("clone", "--bare", "--quiet", str(self.repo), str(bare))
        self.config["git"]["repositories"] = [{"name": "bare", "path": str(bare)}]
        result = self.collect()
        self.assertEqual("complete", result["status"], result)
        self.assertEqual([target], [item["metadata"]["commit"] for item in self.commits(result)])

    def test_empty_repository_staged_work_is_still_observed(self):
        (self.repo / "draft.txt").write_text("unfinished draft\n", encoding="utf-8")
        self.git("add", "draft.txt")
        result = self.collect()
        self.assertEqual("complete", result["status"], result)
        self.assertEqual("worktree", result["items"][0]["kind"])
        self.assertIn("+unfinished draft", result["items"][0]["content"])

    def test_missing_identity_is_an_explicit_gap(self):
        self.commit()
        self.config["identity"]["git_emails"] = []
        result = self.collect()
        self.assertEqual("partial", result["status"])
        self.assertEqual([], self.commits(result))
        self.assertTrue(any("identity.git_emails" in gap for gap in result["gaps"]))

    def test_incomplete_history_record_is_not_mistaken_for_full_evidence(self):
        self.commit()
        real_run = git_source.run
        def truncate(arguments, **kwargs):
            result = real_run(arguments, **kwargs)
            if "log" in arguments:
                return CommandResult(-9, result.stdout[:-4], "", True)
            return result
        with patch.object(git_source, "run", side_effect=truncate):
            result = self.collect()
        self.assertEqual("partial", result["status"])
        self.assertEqual([], self.commits(result))

    def test_repository_diff_drivers_are_not_executed(self):
        (self.repo / ".gitattributes").write_text("*.txt diff=custom\n", encoding="utf-8")
        self.git("config", "diff.custom.command", "does-not-exist-custom-diff")
        self.git("config", "diff.custom.textconv", "does-not-exist-textconv")
        self.git("add", ".gitattributes")
        self.commit(content="ordinary content\n")
        result = self.collect()
        self.assertEqual("complete", result["status"], result)
        self.assertIn("+ordinary content", self.commits(result)[0]["content"])


if __name__ == "__main__":
    unittest.main()
