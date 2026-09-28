"""本地材料采集的范围、时间证据与提取上限测试。"""

import os
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from work_summary import local_source
from work_summary.common import CommandResult


class LocalSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="work-summary-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        now = datetime.now(timezone.utc)
        self.window = {"start": (now - timedelta(hours=1)).isoformat(),
                       "end": (now + timedelta(hours=1)).isoformat(),
                       "timezone": "UTC", "observed_at": now.isoformat()}
        self.config = {"local": {"roots": [{"path": str(self.root), "project": "测试项目", "mode": "workspace"}]},
                       "limits": {"timeout_seconds": 30, "max_content_chars": 20000}}

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def collect(self):
        return local_source.collect(self.config, self.window)

    def docx(self, name="方案.docx", extra_text=""):
        path = self.root / name
        body = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body><w:p><w:r><w:t>方案第一段 First paragraph</w:t></w:r></w:p>
          <w:tbl><w:tr><w:tc><w:p><w:r><w:t>任务</w:t></w:r></w:p></w:tc>
          <w:tc><w:p><w:r><w:t>完成</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
          <w:p><w:r><w:t>''' + extra_text + '''</w:t></w:r></w:p></w:body></w:document>'''
        core = '''<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
          xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/">
          <dc:creator>另一位作者</dc:creator><dcterms:created>2020-01-01T00:00:00Z</dcterms:created>
          <dcterms:modified>2020-02-01T00:00:00Z</dcterms:modified></cp:coreProperties>'''
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", body)
            archive.writestr("docProps/core.xml", core)
        return path

    def test_utf8_chinese_english_and_supported_text_formats(self):
        values = {"会议.md": "# 项目会议\n完成 English 内容", "plain.txt": "纯文本", "data.csv": "任务,状态\n联调,完成",
                  "data.json": '{"任务":"已完成"}', "data.xml": "<任务>已完成</任务>",
                  "页面.html": "<h1>方案</h1><script>hidden()</script><p>Hello &amp; 工作</p>"}
        for name, content in values.items():
            self.write(name, content)
        result = self.collect()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["items"]), 6)
        items = {item["title"]: item for item in result["items"]}
        self.assertEqual(items["会议.md"]["content"], values["会议.md"])
        self.assertIn("Hello & 工作", items["页面.html"]["content"])
        self.assertNotIn("hidden", items["页面.html"]["content"])
        for item in result["items"]:
            self.assertEqual(item["project"], "测试项目")
            self.assertIsNone(item["event_time"])
            self.assertEqual(item["attribution"], "unknown")
            self.assertEqual(item["verification"], "record_only")
            self.assertEqual(item["time_basis"], "filesystem_mtime_candidate")
            self.assertEqual(len(item["metadata"]["sha256"]), 64)

    def test_docx_paragraphs_tables_core_properties_are_evidence_only(self):
        path = self.docx()
        before = path.read_bytes()
        result = self.collect()
        self.assertEqual(result["status"], "complete")
        item = result["items"][0]
        self.assertIn("方案第一段 First paragraph", item["content"])
        self.assertIn("任务\t完成", item["content"])
        self.assertEqual(item["metadata"]["document_properties"]["creator"], "另一位作者")
        self.assertEqual(item["metadata"]["document_properties"]["modified"], "2020-02-01T00:00:00Z")
        self.assertIsNone(item["event_time"])
        self.assertEqual(item["attribution"], "unknown")
        self.assertTrue(any("不能证明" in warning for warning in item["warnings"]))
        self.assertEqual(path.read_bytes(), before)

    def test_today_ctime_old_mtime_remains_candidate_only(self):
        path = self.write("旧文档.md", "几年前已完成的工作")
        old_time = datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()
        os.utime(path, (old_time, old_time))
        item = self.collect()["items"][0]
        self.assertEqual(item["metadata"]["candidate_time_fields"], ["ctime"])
        self.assertIsNone(item["event_time"])
        self.assertEqual(item["attribution"], "unknown")

    def test_outside_window_is_not_read(self):
        self.write("旧材料.md", "不应读取")
        self.window.update(start="2000-01-01T00:00:00+00:00", end="2000-01-02T00:00:00+00:00")
        with patch.object(local_source, "_extract_file", side_effect=AssertionError("不应提取")):
            result = self.collect()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["items"], [])

    def test_mixed_filters_relative_names_before_reading_body(self):
        self.write("私人日记.md", "公司 Alpha 项目，仅正文命中不应读取")
        self.write("Alpha/记录.md", "授权公司工作")
        self.write("ALPHA-方案.txt", "授权项目方案")
        self.config["local"]["roots"][0].update(mode="mixed", keywords=["alpha"])
        with patch.object(local_source, "_extract_file", wraps=local_source._extract_file) as extract:
            result = self.collect()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(extract.call_count, 2)
        self.assertNotIn("私人日记.md", [call.args[0].name for call in extract.call_args_list])

    def test_mixed_without_keywords_is_unavailable(self):
        self.config["local"]["roots"][0].update(mode="mixed", keywords=[])
        self.write("材料.txt", "不应读取")
        with patch.object(local_source, "_extract_file", side_effect=AssertionError("不应提取")):
            result = self.collect()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["items"], [])

    def test_root_home_and_symlink_roots_are_refused(self):
        alias = self.root / "alias"
        target = self.root / "target"
        target.mkdir()
        alias.symlink_to(target, target_is_directory=True)
        for path in [Path("/"), Path.home(), alias]:
            with self.subTest(path=path):
                self.config["local"]["roots"][0]["path"] = str(path)
                result = self.collect()
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["items"], [])

    def test_symlink_escape_never_reads_target(self):
        outside = tempfile.TemporaryDirectory(prefix="outside-work-summary-")
        self.addCleanup(outside.cleanup)
        foreign = Path(outside.name) / "foreign.txt"
        foreign.write_text("不在授权范围", encoding="utf-8")
        (self.root / "escape.txt").symlink_to(foreign)
        (self.root / "escape-directory").symlink_to(Path(outside.name), target_is_directory=True)
        self.write("safe.md", "授权范围内容")
        result = self.collect()
        self.assertEqual(result["status"], "complete")
        self.assertEqual([item["title"] for item in result["items"]], ["safe.md"])

    @unittest.skipUnless(os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"), "需要支持目录句柄的系统")
    def test_directory_replaced_by_symlink_during_collection_cannot_escape(self):
        outside = tempfile.TemporaryDirectory(prefix="outside-work-summary-")
        self.addCleanup(outside.cleanup)
        foreign = Path(outside.name).resolve()
        (foreign / "note.md").write_text("私密范围外正文", encoding="utf-8")
        candidate = self.write("team/note.md", "范围内正文")
        original = local_source._extract_file

        def replace_then_extract(path, *args):
            candidate.parent.rename(self.root / "moved")
            candidate.parent.symlink_to(foreign, target_is_directory=True)
            return original(path, *args)

        with patch.object(local_source, "_extract_file", side_effect=replace_then_extract):
            result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0]["content"], "")
        self.assertNotIn("私密范围外正文", str(result))

    def test_single_file_extraction_rejects_symlink_itself(self):
        target = self.write("target.md", "不可沿链接读取")
        link = self.root / "linked.md"
        link.symlink_to(target)
        extracted = local_source.extract_file(link)
        self.assertFalse(extracted["metadata"]["complete"])
        self.assertEqual(extracted["content"], "")

    def test_secret_names_and_private_directories_are_skipped_before_read(self):
        names = [".env", ".env.example", "private.key", "server.pem", "api-key.json", "tokens.txt",
                 "credentials.json", ".ssh/config", ".git/notes.md", "node_modules/notes.txt",
                 "secrets/notes.md", "key/notes.md", ".aws/config", ".netrc"]
        for name in names:
            self.write(name, "不应进入采集结果")
        self.write("ordinary.md", "项目进展")
        with patch.object(local_source, "_extract_file", wraps=local_source._extract_file) as extract:
            result = self.collect()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(extract.call_count, 1)
        self.assertEqual(result["items"][0]["title"], "ordinary.md")

    def test_duplicate_content_preserves_all_paths_and_projects(self):
        first = self.write("one.md", "相同材料")
        second = self.write("team/two.md", "相同材料")
        self.config["local"]["roots"].append({"path": str(second.parent), "project": "第二项目", "mode": "workspace"})
        result = self.collect()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(set(item["metadata"]["paths"]), {str(first), str(second)})
        self.assertEqual(set(item["metadata"]["projects"]), {"测试项目", "第二项目"})
        self.assertEqual(item["id"], self.collect()["items"][0]["id"])

    def test_duplicate_unsupported_name_does_not_hide_readable_content(self):
        self.write("same.unknown", "同一文本材料")
        self.write("same.md", "同一文本材料")
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["content"], "同一文本材料")
        self.assertEqual(len(result["items"][0]["metadata"]["paths"]), 2)

    def test_globs_include_root_level_files_and_exclude_directories(self):
        self.write("root.md", "根文件")
        self.write("team/nested.md", "嵌套文件")
        self.write("team/ignore.txt", "非目标格式")
        self.write("excluded/a.md", "排除目录")
        self.config["local"].update(include_globs=["**/*.md"], exclude_globs=["excluded/**"])
        result = self.collect()
        self.assertEqual(result["status"], "complete")
        self.assertEqual({item["title"] for item in result["items"]}, {"root.md", "nested.md"})

    def test_zip_declared_uncompressed_size_is_limited(self):
        self.docx(extra_text="材料" * 1000)
        self.config["local"]["max_docx_uncompressed_bytes"] = 1024
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0]["content"], "")
        self.assertTrue(any("解压大小" in warning for warning in result["items"][0]["warnings"]))

    def test_zip_excessive_compression_ratio_is_rejected(self):
        self.docx(extra_text="A" * (2 * 1024 * 1024))
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertTrue(any("压缩比" in warning for warning in result["items"][0]["warnings"]))

    def test_unsupported_attachments_are_retained_and_make_partial(self):
        for index, suffix in enumerate(["png", "pptx", "xlsx", "unknown"]):
            self.write("attachment." + suffix, b"not parsed " + str(index).encode())
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["items"]), 4)
        for item in result["items"]:
            self.assertFalse(item["metadata"]["complete"])
            self.assertIn(item["metadata"]["extraction"], {"requires_skill", "unsupported"})
            self.assertEqual(item["content"], "")

    def test_invalid_utf8_json_xml_and_docx_are_retained(self):
        for name, content in {"bad.txt": b"\xff\xfe", "bad.json": b"{", "bad.xml": b"<unclosed>",
                              "bad.docx": b"not a zip"}.items():
            self.write(name, content)
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["items"]), 4)
        self.assertTrue(all(item["metadata"]["extraction"] == "parse_error" for item in result["items"]))

    def test_xml_entity_declaration_is_not_expanded(self):
        self.write("entity.xml", '<!DOCTYPE r [<!ENTITY v "不应展开">]><r>&v;</r>')
        item = self.collect()["items"][0]
        self.assertEqual(item["content"], "")
        self.assertEqual(item["metadata"]["extraction"], "parse_error")

    def test_docx_utf16_entity_declaration_is_not_expanded(self):
        body = '<?xml version="1.0" encoding="utf-16"?><!DOCTYPE r [<!ENTITY v "不应展开">]><r>&v;</r>'
        path = self.root / "entity.docx"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", body.encode("utf-16"))
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0]["content"], "")

    def test_file_count_cap_is_partial(self):
        self.write("one.md", "内容一")
        self.write("two.md", "内容二")
        self.config["local"]["max_files"] = 1
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["items"]), 1)
        self.assertTrue(any("数量超过" in gap for gap in result["gaps"]))

    def test_exact_file_count_cap_does_not_claim_missing_files(self):
        self.write("one.md", "唯一材料")
        self.config["local"]["max_files"] = 1
        self.assertEqual(self.collect()["status"], "complete")

    def test_file_size_cap_retains_metadata_without_content(self):
        path = self.write("large.md", "X" * 30)
        self.config["local"]["max_file_bytes"] = 10
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        item = result["items"][0]
        self.assertEqual(item["metadata"]["extraction"], "size_limit")
        self.assertEqual(item["metadata"]["size_bytes"], 30)
        self.assertIsNone(item["metadata"]["sha256"])
        self.assertEqual(item["locator"], str(path))

    def test_content_cap_is_partial(self):
        self.write("long.md", "中文和 English 内容" * 10)
        self.config["limits"]["max_content_chars"] = 12
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["items"][0]["content"]), 12)
        self.assertTrue(result["items"][0]["metadata"]["content_truncated"])

    def test_depth_cap_reports_unscanned_directory(self):
        self.write("one/visible.md", "可读取")
        self.write("one/two/hidden.md", "未遍历")
        self.config["local"]["max_depth"] = 1
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual([item["title"] for item in result["items"]], ["visible.md"])
        self.assertTrue(any("深度上限" in gap for gap in result["gaps"]))

    def test_timeout_is_partial(self):
        self.write("material.txt", "工作材料")
        with patch.object(local_source.time, "monotonic", side_effect=[0, 100, 100, 100]):
            result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"], [])
        self.assertTrue(any("时间上限" in gap for gap in result["gaps"]))

    def test_permission_failures_are_reported_without_raw_error(self):
        self.write("material.md", "工作材料")
        with patch.object(local_source, "_read_file", side_effect=PermissionError("sensitive diagnostic")):
            result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0]["metadata"]["extraction"], "read_error")
        self.assertNotIn("sensitive diagnostic", str(result))
        with patch.object(local_source.os, "scandir", side_effect=PermissionError("private reason")):
            result = self.collect()
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("private reason", str(result))

    def test_pdf_without_optional_tool_is_explicitly_unsupported(self):
        self.write("report.pdf", b"%PDF-example")
        with patch.object(local_source.shutil, "which", return_value=None):
            result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0]["metadata"]["extraction"], "unsupported")

    def test_pdf_tool_uses_argument_array_and_private_copy(self):
        path = self.write("report.pdf", b"%PDF-example")
        with patch.object(local_source.shutil, "which", return_value="/usr/bin/pdftotext"), \
                patch.object(local_source, "run", return_value=CommandResult(0, "PDF 中文正文", "", False)) as run_tool:
            extracted = local_source.extract_file(path)
        self.assertEqual(extracted["content"], "PDF 中文正文")
        self.assertTrue(extracted["metadata"]["complete"])
        args = run_tool.call_args.args[0]
        self.assertIsInstance(args, list)
        self.assertNotIn(str(path), args)
        self.assertEqual(args[-1], "-")
        self.assertEqual(path.read_bytes(), b"%PDF-example")

    def test_empty_pdf_requires_ocr_or_skill(self):
        path = self.write("scanned.pdf", b"%PDF-example")
        with patch.object(local_source.shutil, "which", return_value="pdftotext"), \
                patch.object(local_source, "run", return_value=CommandResult(0, "\n", "", False)):
            extracted = local_source.extract_file(str(path))
        self.assertFalse(extracted["metadata"]["complete"])
        self.assertEqual(extracted["metadata"]["extraction"], "requires_skill")

    def test_extraction_redacts_credentials_in_otherwise_authorized_text(self):
        path = self.write("meeting.md", "工作备注 api_key=some-confidential-value")
        extracted = local_source.extract_file(path)
        self.assertNotIn("some-confidential-value", extracted["content"])
        self.assertIn("[REDACTED]", extracted["content"])

    def test_no_config_and_invalid_window(self):
        self.assertEqual(local_source.collect({}, self.window)["status"], "not_configured")
        result = local_source.collect(self.config, {"start": "invalid", "end": "invalid"})
        self.assertEqual(result["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
