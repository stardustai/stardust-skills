import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import testcase_table_tools  # noqa: E402


VALID_MARKDOWN = """
| 用例名称 | 所属模块 | 前置条件 | 步骤描述 | 预期结果 | 用例等级 | 编辑模式 |
| --- | --- | --- | --- | --- | --- | --- |
| 筛选任务-按状态筛选成功 | /任务列表筛选 | 用户有任务列表查看权限 | [1]进入任务列表；[2]选择状态筛选条件并查询 | [1]任务列表页面打开；[2]列表只展示符合状态条件的数据 | P0 | STEP |
| 导出任务-跨页选中范围正确 | /任务列表筛选 | 用户有任务列表导出权限且存在多页数据 | [1]跨页选中任务；[2]点击导出 | [1]已选数量保持正确；[2]导出文件只包含已选任务 | P1 | STEP |
"""


class TestcaseTableToolsTest(unittest.TestCase):
    def test_parse_validate_and_export_xlsx(self):
        rows = testcase_table_tools.parse_markdown_table(VALID_MARKDOWN)
        self.assertEqual(len(rows), 2)
        self.assertEqual(testcase_table_tools.validate_rows(rows, "/任务列表筛选"), [])

        with tempfile.TemporaryDirectory() as temp_dir:
            xlsx = Path(temp_dir) / "cases.xlsx"
            testcase_table_tools.build_xlsx(xlsx, rows)
            with zipfile.ZipFile(xlsx) as archive:
                self.assertIsNone(archive.testzip())

    def test_validate_detects_step_number_mismatch(self):
        rows = testcase_table_tools.parse_markdown_table(
            VALID_MARKDOWN.replace("[1]已选数量保持正确；[2]导出文件只包含已选任务", "[1]已选数量保持正确")
        )
        errors = testcase_table_tools.validate_rows(rows, "/任务列表筛选")
        self.assertTrue(any("step numbers" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
