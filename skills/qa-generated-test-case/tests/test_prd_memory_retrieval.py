import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "prd_memory_retrieval.py"


class PrdMemoryRetrievalTest(unittest.TestCase):
    def test_build_search_and_validate_external_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            source.mkdir()
            (source / "rosetta-task-list.md").write_text(
                """---
product_line: Rosetta
module: 任务列表
requirement_title: 任务列表筛选导出
version: v2
date: 2026-06-02
page_or_api: /tasks
role: 项目经理
tags: 筛选,导出,跨页
---
# 任务列表筛选导出

筛选条件使用 AND 关系。导出选中任务时需要保持跨页选中范围，并校验权限。
""",
                encoding="utf-8",
            )
            (source / "phoenix-license.md").write_text(
                """---
product_line: Phoenix
module: license管理
requirement_title: license生成
tags: 私有化,权限
---
# license生成

Admin 可以生成私有化 license，普通用户无入口。
""",
                encoding="utf-8",
            )
            index = base / "index.jsonl"
            csv_path = base / "index.csv"

            build = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "build-index",
                    "--source-dir",
                    str(source),
                    "--out-index",
                    str(index),
                    "--out-csv",
                    str(csv_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("records=2", build.stdout)
            self.assertTrue(index.exists())
            self.assertTrue(csv_path.exists())

            search = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "search-memory",
                    "--index",
                    str(index),
                    "--module",
                    "任务列表",
                    "--tags",
                    "筛选,导出",
                    "--query",
                    "跨页选中 导出",
                    "--format",
                    "json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            results = json.loads(search.stdout)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["requirement_title"], "任务列表筛选导出")
            self.assertIn("跨页选中", results[0]["content"])

            queries = base / "queries.jsonl"
            queries.write_text(
                json.dumps(
                    {
                        "module": "任务列表",
                        "tags": "筛选",
                        "query": "跨页选中",
                        "top_n": 3,
                        "min_results": 1,
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            validate = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "validate-retrieval",
                    "--index",
                    str(index),
                    "--queries-jsonl",
                    str(queries),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("validation=ok", validate.stdout)


if __name__ == "__main__":
    unittest.main()
