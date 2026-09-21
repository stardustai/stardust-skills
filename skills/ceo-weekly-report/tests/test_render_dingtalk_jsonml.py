import unittest

from scripts.render_dingtalk_jsonml import render_document


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "ceo_judgment": [
                {"text": "Friday上线标准需要闭环", "status": "⚠️"}
            ],
            "company_metrics": [
                {
                    "name": "新签订单",
                    "target": "5000万",
                    "previous": "无数据",
                    "current": "无数据",
                    "change": "无数据",
                    "status": "❓",
                    "data_date": "2026-09-13",
                    "definition_evidence": "CRM，口径待财务确认",
                    "decision_critical": True,
                    "responsible_user_id": "finance123",
                    "responsible_name": "张丽丽(Lily)",
                    "next_checkpoint": "2026-09-11 18:00",
                }
            ],
            "issues": [
                {
                    "id": "FRI-003",
                    "question": "Friday上线标准是否已共同验收？",
                    "current_root_cause": "业务Eval与通用Eval尚未共同验收",
                    "prior_state": "上线标准未统一",
                    "new_evidence": "测试周报",
                    "status_icon": "⚠️",
                    "weeks_open": 2,
                    "next_checkpoint": "2026-09-11",
                    "owner": {"name": "王靖", "user_id": "u123"},
                    "closure_standard": "两类Eval通过并保留Gate记录",
                }
            ],
            "cockpit": [],
            "business_lines": {
                "MorningStar": self.business_line(
                    "规划缺少未来市场机会验证",
                    "source-ms",
                    [
                        "span",
                        {"data-type": "text"},
                        [
                            "span",
                            {"data-type": "leaf", "bold": True},
                            "完整内容",
                        ],
                    ],
                ),
                "Friday": self.business_line(
                    "产品与技术里程碑待对齐",
                    "source-fri",
                    [
                        "a",
                        {"href": "https://example.com/friday"},
                        "Friday原始周报",
                    ],
                ),
                "International": self.business_line(
                    "无数据", "source-intl", "完整内容"
                ),
                "WorldModel": self.business_line(
                    "无数据", "source-wm", "完整内容"
                ),
            },
            "root_causes": [],
            "discussion": [],
        }
        self.before = [
            "root",
            {},
            ["p", {"uuid": "preface"}, "保留的会议信息"],
            ["h1", {"uuid": "anchor"}, "第一部分：指标"],
            ["p", {"uuid": "old"}, "旧内容"],
        ]

    @staticmethod
    def business_line(summary, source_id, source_child):
        return {
            "summary": summary,
            "core_metrics": "无数据",
            "milestone_deviation": "无数据",
            "largest_risk": "无数据",
            "management_decision": "无",
            "metrics": [],
            "milestones": [
                {
                    "date": "2026-09-11",
                    "owner": {"name": "王靖", "user_id": "u123"},
                    "name": "数字分身上线Gate",
                    "deliverable_evidence": "上线Gate记录",
                    "progress": "业务与通用Eval待共同验收",
                    "status": "⌛",
                }
            ],
            "full_report_jsonml": [
                ["p", {"uuid": source_id}, source_child]
            ],
        }

    def render(self):
        return render_document(
            self.before, self.report, "第一部分：指标"
        )

    def test_preserves_content_before_managed_anchor(self):
        self.assertEqual(
            self.render()[2],
            ["p", {"uuid": "preface"}, "保留的会议信息"],
        )

    def test_removes_content_after_managed_anchor(self):
        self.assertNotIn("旧内容", str(self.render()))

    def test_uses_native_mention_node(self):
        rendered = str(self.render())
        self.assertIn("'data-type': 'mention'", rendered)
        self.assertIn("'id': 'u123'", rendered)
        self.assertIn("'name': '王靖'", rendered)

    def test_missing_metric_renders_native_owner_and_checkpoint(self):
        rendered = str(self.render())
        self.assertIn("'id': 'finance123'", rendered)
        self.assertIn("'name': '张丽丽(Lily)'", rendered)
        self.assertIn("下次检查：2026-09-11 18:00", rendered)

    def test_business_line_full_report_is_folded(self):
        rendered = str(self.render())
        self.assertIn("'fold': True", rendered)
        self.assertIn("MorningStar完整周报", rendered)

    def test_output_contains_no_literal_markdown_bold(self):
        self.assertNotIn("**", str(self.render()))

    def test_preserves_source_report_rich_text_and_links(self):
        rendered = str(self.render())
        self.assertIn("'bold': True", rendered)
        self.assertIn("https://example.com/friday", rendered)

    def test_missing_managed_anchor_blocks_render(self):
        with self.assertRaisesRegex(ValueError, "managed anchor not found"):
            render_document(self.before, self.report, "不存在的标题")

    def test_business_line_summary_and_metrics_tables_exist(self):
        rendered = str(self.render())
        self.assertIn("本周经营结论", rendered)
        self.assertIn("里程碑偏差", rendered)
        self.assertIn("口径与证据", rendered)

    def test_business_line_milestone_table_uses_native_owner(self):
        rendered = str(self.render())
        self.assertIn("交付物和验收证据", rendered)
        self.assertIn("数字分身上线Gate", rendered)
        self.assertIn("上线Gate记录", rendered)
        self.assertIn("'id': 'u123'", rendered)


if __name__ == "__main__":
    unittest.main()
