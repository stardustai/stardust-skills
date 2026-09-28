"""脱敏 DWS v1.0.58 契约、分页、权限和正文读取回归测试。"""

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from work_summary import dingtalk_source as source
from work_summary.common import CommandResult


COMPANY = "示例公司"
PROFILE = "example-corp:example-user"
WINDOW = {"start": "2026-09-28T00:00:00+08:00", "end": "2026-09-29T00:00:00+08:00",
          "timezone": "Asia/Shanghai", "observed_at": "2026-09-29T00:00:00+08:00"}
CONFIG = {"company": {"name": COMPANY},
          "local": {"max_file_bytes": 3000000},
          "dingtalk": {"enabled": True, "profile": "", "queries": ["示例项目"], "nodes": [],
                       "max_pages": 10, "max_documents": 50, "page_size": 20},
          "limits": {"timeout_seconds": 30, "max_content_chars": 20000}}


def profiles(**changes):
    profile = {"profile": PROFILE, "corpName": COMPANY, "corpId": "example-corp", "userId": "example-user",
               "status": "active", "isCurrent": True, "isOrgCurrent": True}
    profile.update(changes)
    return {"success": True, "currentProfile": PROFILE, "profiles": [profile]}


def search(ids=("node-one",), more=False, cursor=""):
    return {"ok": True, "outcome": "success", "data": {
        "count": len(ids), "files": [{"creatorId": "example-author", "fileSize": 0,
                                       "name": "搜索摘要不能当正文", "nodeId": node, "type": "ALIDOC"} for node in ids],
        "hasMore": more, "nextCursor": cursor}}


def inspect(node="node-one", extension="adoc", size=0):
    return {"ok": True, "outcome": "success", "data": {"complete": True, "status": "success", "data": {"file": {
        "fileId": node, "name": "示例项目需求", "extension": extension, "fileSize": size,
        "modifyTime": 1790560800000, "docUrl": "https://alidocs.dingtalk.com/i/nodes/" + node + "?signature=private",
        "status": "NORMAL", "type": "ALIDOC"}}, "steps": [{"status": "success", "tool": "drive.info"}]}}


def fetch(node="node-one", text="完成接口验证，尚未上线。"):
    return {"complete": True, "status": "success", "content": {
        "nodeId": node, "title": "示例项目验证记录", "revision": "2", "success": True,
        "jsonml": json.dumps(["root", {"internal-attribute": "secret-never-output"},
                              ["h1", {}, ["span", {}, "验证记录"]], ["p", {}, ["span", {}, text]]], ensure_ascii=False)},
        "contractVersion": "2026-09-example", "target": {"canonicalId": node, "product": "doc"}}


def output(payload, code=0, truncated=False):
    return CommandResult(code, json.dumps(payload, ensure_ascii=False), "private-stderr", truncated)


class DingtalkSourceTest(unittest.TestCase):
    def setUp(self):
        self.config = copy.deepcopy(CONFIG)
        self.calls = []

    def run_mock(self, args, **kwargs):
        self.calls.append((args, kwargs))
        route = args[1:3]
        if route == ["profile", "list"]:
            return output(profiles())
        self.assertEqual(args[args.index("--profile") + 1], PROFILE)
        self.assertEqual(args[-2:], ["--format", "json"])
        if route == ["drive", "+search"]:
            return output(search())
        node = args[args.index("--node") + 1]
        if route == ["drive", "+inspect"]:
            return output(inspect(node))
        if route == ["doc", "+fetch"]:
            return output(fetch(node))
        self.fail("unexpected read route: " + str(route))

    def collect(self, handler=None):
        with patch.object(source, "run", side_effect=handler or self.run_mock):
            return source.collect(self.config, WINDOW)

    def test_actual_envelopes_read_jsonml_not_search_snippet(self):
        result = self.collect()
        self.assertEqual(result["status"], "complete")
        item = result["items"][0]
        self.assertEqual(item["content"], "验证记录\n完成接口验证，尚未上线。")
        self.assertNotIn("secret-never-output", json.dumps(result))
        self.assertNotIn("signature", item["locator"])
        self.assertNotIn("搜索摘要", item["content"])
        self.assertIsNone(item["event_time"])
        self.assertEqual(item["attribution"], "unknown")
        self.assertEqual(item["metadata"]["revision"], "2")
        args = next(args for args, _ in self.calls if args[1:3] == ["drive", "+search"])
        self.assertEqual(args[args.index("--modified-from") + 1], "1790524800000")
        self.assertEqual(args[args.index("--modified-to") + 1], "1790611199999")

    def test_disabled_and_unconfigured_do_not_call_cli(self):
        with patch.object(source, "run") as run:
            self.config["dingtalk"]["enabled"] = False
            self.assertEqual(source.collect(self.config, WINDOW)["status"], "not_configured")
            self.config["dingtalk"]["enabled"] = True
            self.config["dingtalk"]["queries"] = []
            self.assertEqual(source.collect(self.config, WINDOW)["status"], "not_configured")
            run.assert_not_called()

    def test_profile_mismatch_stops_before_business_calls(self):
        self.config["company"]["name"] = "其他公司"
        result = self.collect()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(len(self.calls), 1)

    def test_missing_org_default_does_not_choose_first(self):
        result = self.collect(lambda args, **kw: output(profiles(isOrgCurrent=False)))
        self.assertEqual(result["status"], "unavailable")

    def test_explicit_profile_is_company_checked(self):
        self.config["dingtalk"]["profile"] = PROFILE
        def handler(args, **kw):
            if args[1:3] == ["profile", "list"]:
                return output(profiles(isOrgCurrent=False))
            return self.run_mock(args, **kw)
        self.assertEqual(self.collect(handler)["status"], "complete")
        self.config["dingtalk"]["profile"] = "other-corp:other-user"
        self.assertEqual(self.collect(handler)["status"], "unavailable")

    def test_two_pages_deduplicate_and_pin_profile(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+search"]:
                self.calls.append((args, kw))
                self.assertEqual(args[args.index("--profile") + 1], PROFILE)
                return output(search(("node-one", "node-two")) if "--cursor" in args else search(more=True, cursor="next-one"))
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["items"]), 2)
        searches = [args for args, _ in self.calls if args[1:3] == ["drive", "+search"]]
        self.assertEqual(len(searches), 2)
        self.assertEqual(searches[1][searches[1].index("--cursor") + 1], "next-one")

    def test_repeated_cursor_is_partial_and_bounded(self):
        searches = []
        def handler(args, **kw):
            if args[1:3] == ["drive", "+search"]:
                searches.append(args)
                return output(search(more=True, cursor="same-cursor"))
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(searches), 2)
        self.assertTrue(any("游标重复" in gap for gap in result["gaps"]))

    def test_page_cap_and_document_cap_are_explicit(self):
        self.config["dingtalk"].update(max_pages=1, max_documents=1, page_size=100)
        def handler(args, **kw):
            if args[1:3] == ["drive", "+search"]:
                self.assertEqual(args[args.index("--limit") + 1], "30")
                return output(search(("node-one", "node-two"), True, "next"))
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(len(result["items"]), 1)
        self.assertTrue(any("max_pages" in gap for gap in result["gaps"]))
        self.assertTrue(any("max_documents" in gap for gap in result["gaps"]))

    def test_403_stops_source_without_retry_or_raw_error(self):
        searches = []
        self.config["dingtalk"]["queries"] += ["另一个主题"]
        def handler(args, **kw):
            if args[1:3] == ["drive", "+search"]:
                searches.append(args)
                return output({"ok": False, "outcome": "error", "error": {"code": "403", "message": "token=SECRET"}}, 1)
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(len(searches), 1)
        self.assertNotIn("SECRET", json.dumps(result))

    def test_timeout_reports_gap_not_zero_work(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+search"]:
                raise RuntimeError("工具执行超时：dws")
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(any("超时" in gap for gap in result["gaps"]))

    def test_fetch_partial_keeps_content_with_gap(self):
        def handler(args, **kw):
            if args[1:3] == ["doc", "+fetch"]:
                value = fetch()
                value.update(complete=False, status="partial_success")
                return output(value)
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "partial")
        self.assertIn("接口验证", result["items"][0]["content"])
        self.assertFalse(result["items"][0]["metadata"]["body_complete"])

    def test_process_truncation_not_parsed_as_complete(self):
        def handler(args, **kw):
            if args[1:3] == ["doc", "+fetch"]:
                return output(fetch(), truncated=True)
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0]["content"], "")
        self.assertTrue(any("截断" in gap for gap in result["gaps"]))

    def test_character_cap_retains_partial_body(self):
        self.config["limits"]["max_content_chars"] = 6
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["items"][0]["content"]), 6)

    def test_online_sheet_is_not_fetched_as_adoc(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+inspect"]:
                return output(inspect(extension="axls"))
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0]["metadata"]["extension"], "axls")
        self.assertFalse(any(args[1:3] == ["doc", "+fetch"] for args, _ in self.calls))

    def test_native_markdown_reads_own_content_route(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+inspect"]:
                return output(inspect(extension="md"))
            if args[1:3] == ["markdown", "fetch"]:
                return output({"success": True, "content": "# 本期记录\n完成需求分析", "nodeId": "node-one"})
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "complete")
        self.assertIn("完成需求分析", result["items"][0]["content"])

    def test_explicit_node_url_dedup_and_no_time_inference(self):
        self.config["dingtalk"].update(queries=[], nodes=["node-one", "https://alidocs.dingtalk.com/i/nodes/node-one?signature=SECRET"])
        result = self.collect()
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["status"], "complete")
        self.assertIsNone(result["items"][0]["event_time"])
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertFalse(any(args[1:3] == ["drive", "+search"] for args, _ in self.calls))

    def test_shared_shortlink_rejected_without_browser(self):
        self.config["dingtalk"].update(queries=[], nodes=["https://alidocs.dingtalk.com/i/p/shared/docs/example"])
        result = self.collect()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(len(self.calls), 1)

    def test_unknown_search_schema_is_not_zero_hits(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+search"]:
                return output({"ok": True, "outcome": "success", "data": {"unexpected": []}})
            return self.run_mock(args, **kw)
        self.assertEqual(self.collect(handler)["status"], "unavailable")

    def test_missing_pagination_marker_is_partial(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+search"]:
                return output({"ok": True, "outcome": "success", "data": {"files": []}})
            return self.run_mock(args, **kw)
        self.assertEqual(self.collect(handler)["status"], "partial")

    def test_confirmed_zero_results_is_complete(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+search"]:
                return output(search(()))
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["items"], [])

    def test_attachment_download_relative_private_temp_and_verify(self):
        directories = []
        def handler(args, **kw):
            if args[1:3] == ["drive", "+inspect"]:
                return output(inspect(extension="txt", size=30))
            if args[1:3] == ["drive", "+download"]:
                directories.append(Path(kw["cwd"]))
                self.assertEqual(Path(kw["cwd"]).stat().st_mode & 0o777, 0o700)
                target = args[args.index("--output") + 1]
                self.assertFalse(Path(target).is_absolute())
                (Path(kw["cwd"]) / target).write_text("已核对接口边界", encoding="utf-8")
                return output({"ok": True, "outcome": "success", "data": {"sizeBytes": 21}})
            return self.run_mock(args, **kw)
        with patch("work_summary.local_source.extract_file", return_value={"content": "已核对接口边界", "warnings": [],
                                                                             "metadata": {"extraction": "text", "complete": True}}):
            result = self.collect(handler)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["items"][0]["content"], "已核对接口边界")
        self.assertTrue(all(not directory.exists() for directory in directories))

    def test_attachment_unknown_size_does_not_download(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+inspect"]:
                return output(inspect(extension="pdf", size=None))
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "partial")
        self.assertFalse(any(args[1:3] == ["drive", "+download"] for args, _ in self.calls))

    def test_jsonml_nontext_is_explicit_gap(self):
        text, warnings = source._jsonml_text(["root", {}, ["p", {}, "正文"], ["image", {"src": "private-url"}]])
        self.assertEqual(text, "正文")
        self.assertTrue(warnings)
        self.assertNotIn("private-url", text)

    def test_fractional_time_bounds_keep_exclusive_end(self):
        window = dict(WINDOW, start="2026-09-28T00:00:00.000500+08:00", end="2026-09-28T00:00:00.001500+08:00")
        with patch.object(source, "run", side_effect=self.run_mock):
            source.collect(self.config, window)
        args = next(args for args, _ in self.calls if args[1:3] == ["drive", "+search"])
        self.assertEqual(args[args.index("--modified-from") + 1], "1790524800001")
        self.assertEqual(args[args.index("--modified-to") + 1], "1790524800001")

    def test_permission_reason_without_code_is_fatal(self):
        self.config["dingtalk"]["queries"] += ["不得继续读取"]
        searches = []
        def handler(args, **kw):
            if args[1:3] == ["drive", "+search"]:
                searches.append(args)
                return output({"success": False, "reason": "permission_denied"}, 1)
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(len(searches), 1)

    def test_attachment_respects_local_file_byte_limit(self):
        self.config["local"]["max_file_bytes"] = 10
        self.config["limits"]["max_file_bytes"] = 999999  # 旧位置不能覆盖真实配置。
        def handler(args, **kw):
            if args[1:3] == ["drive", "+inspect"]:
                return output(inspect(extension="txt", size=30))
            self.assertNotEqual(args[1:3], ["drive", "+download"])
            return self.run_mock(args, **kw)
        result = self.collect(handler)
        self.assertEqual(result["status"], "partial")
        self.assertTrue(any("超限" in gap for gap in result["gaps"]))

    def test_attachment_information_warning_is_not_coverage_gap(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+inspect"]:
                return output(inspect(extension="docx", size=6))
            if args[1:3] == ["drive", "+download"]:
                (Path(kw["cwd"]) / "document.docx").write_bytes(b"sample")
                return output({"ok": True, "outcome": "success", "data": {"sizeBytes": 6}})
            return self.run_mock(args, **kw)
        with patch("work_summary.local_source.extract_file", return_value={
                "content": "设计方案已整理", "warnings": ["文档作者为自报信息"],
                "metadata": {"extraction": "docx", "complete": True, "sha256": "example-hash"}}) as extract:
            result = self.collect(handler)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["gaps"], [])
        self.assertTrue(result["items"][0]["warnings"])
        self.assertTrue(result["items"][0]["metadata"]["body_complete"])
        self.assertEqual(extract.call_args.kwargs["max_file_bytes"], 3000000)

    def test_failed_attachment_extraction_is_not_body_read(self):
        def handler(args, **kw):
            if args[1:3] == ["drive", "+inspect"]:
                return output(inspect(extension="pdf", size=6))
            if args[1:3] == ["drive", "+download"]:
                (Path(kw["cwd"]) / "document.pdf").write_bytes(b"sample")
                return output({"ok": True, "outcome": "success", "data": {"sizeBytes": 6}})
            return self.run_mock(args, **kw)
        with patch("work_summary.local_source.extract_file", return_value={
                "content": "", "warnings": ["需要 OCR"], "metadata": {"extraction": "requires_skill", "complete": False}}):
            result = self.collect(handler)
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["items"][0]["metadata"]["body_read"])


if __name__ == "__main__":
    unittest.main()
