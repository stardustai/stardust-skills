#!/usr/bin/env python3
"""Create a Markdown draft from inventory and grep-rule JSON outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


CATEGORIES = [
    "登录认证",
    "权限控制",
    "安全审计",
    "数据安全",
    "接口安全",
    "传输安全",
    "运维暴露面",
    "备份恢复",
    "发布变更",
    "文档材料",
]

SEVERITIES = ["高危", "中危", "低危", "待确认"]


def load_json(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def md_escape(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", help="inventory.py JSON output")
    parser.add_argument("--findings", help="grep_rules.py JSON output")
    parser.add_argument("--output", "-o", required=True, help="Markdown report output path")
    parser.add_argument("--project-name", default="", help="Project display name")
    parser.add_argument("--public-facing", choices=["是", "否", "待确认"], default="待确认")
    args = parser.parse_args()

    inventory = load_json(args.inventory)
    scan = load_json(args.findings)
    findings = scan.get("findings", [])

    severity_counts = Counter(item.get("severity", "待确认") for item in findings)
    category_counts = Counter(item.get("category", "待确认") for item in findings)
    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in findings:
        by_category[item.get("category", "待确认")].append(item)

    project_name = args.project_name or Path(inventory.get("root") or ".").name
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    tech = ", ".join(inventory.get("detected_technologies", [])) or "待确认"
    root = inventory.get("root", "待确认")

    lines: list[str] = []
    lines.append("# 等保代码安全检测报告")
    lines.append("")
    lines.append("## 1. 检测概览")
    lines.append("")
    lines.append(f"- 项目名称：{project_name}")
    lines.append(f"- 检测时间：{now}")
    lines.append(f"- 检测范围：{root}")
    lines.append(f"- 技术栈：{tech}")
    lines.append(f"- 是否面向公网：{args.public_facing}")
    lines.append("- 检测方式：源码审查、配置审查、部署文件审查、文档材料审查、规则扫描")
    lines.append("- 总体结论：本报告为规则扫描初稿，需结合源码语义复核后形成最终结论。")
    lines.append("")
    lines.append("## 2. 风险统计")
    lines.append("")
    lines.append("| 风险等级 | 数量 |")
    lines.append("| --- | ---: |")
    for severity in SEVERITIES:
        lines.append(f"| {severity} | {severity_counts.get(severity, 0)} |")
    lines.append("")
    lines.append("## 3. 重点结论")
    lines.append("")
    if findings:
        for index, item in enumerate(findings[:10], 1):
            lines.append(f"{index}. [{item.get('severity')}] {item.get('title')}（{item.get('file')}:{item.get('line')}）")
    else:
        lines.append("暂未通过规则扫描发现明确问题；仍需人工复核认证、权限、审计、数据流和部署边界。")
    lines.append("")
    lines.append("## 4. 详细问题清单")
    lines.append("")
    if findings:
        for index, item in enumerate(findings, 1):
            lines.append(f"### DBCA-{index:03d} {item.get('title')}")
            lines.append("")
            lines.append(f"- 风险等级：{item.get('severity')}")
            lines.append(f"- 检查分类：{item.get('category')}")
            lines.append(f"- 证据位置：`{item.get('file')}:{item.get('line')}`")
            lines.append(f"- 证据片段：`{md_escape(item.get('evidence', ''))}`")
            lines.append(f"- 问题描述：{item.get('description')}")
            lines.append("- 影响分析：需结合调用链、部署环境和输入来源确认实际影响。")
            lines.append(f"- 整改建议：{item.get('recommendation')}")
            lines.append("- 验收标准：完成整改后重新扫描，并补充接口/权限/部署验证记录。")
            lines.append("")
    else:
        lines.append("无规则扫描命中项。")
        lines.append("")
    lines.append("## 5. 等保检查点覆盖情况")
    lines.append("")
    lines.append("| 检查项 | 结论 | 说明 |")
    lines.append("| --- | --- | --- |")
    for category in CATEGORIES:
        count = category_counts.get(category, 0)
        if count:
            conclusion = "不通过/需整改"
            note = f"规则扫描发现 {count} 个线索，需人工确认。"
        else:
            conclusion = "待确认"
            note = "未发现规则命中，不代表已满足要求。"
        lines.append(f"| {category} | {conclusion} | {note} |")
    lines.append("")
    lines.append("## 6. 整改路线图")
    lines.append("")
    lines.append("### 立即整改")
    lines.append("")
    lines.append("- 优先处理高危问题、外网暴露面、认证权限绕过、敏感数据泄露和硬编码凭据。")
    lines.append("")
    lines.append("### 近期整改")
    lines.append("")
    lines.append("- 处理中危问题，补齐审计日志、输入校验、传输安全、备份恢复和发布回滚能力。")
    lines.append("")
    lines.append("### 持续治理")
    lines.append("")
    lines.append("- 建立安全检查进入 CI、发布准入、账号权限定期复核和等保材料持续维护机制。")
    lines.append("")
    lines.append("## 7. 未覆盖范围与待补充材料")
    lines.append("")
    lines.append("- 线上网络拓扑、边界防护策略和证书有效期。")
    lines.append("- 生产资产清单、账号清单、离职账号回收记录。")
    lines.append("- 备份恢复演练记录、发布审批记录、应急演练记录。")
    lines.append("- 云厂商等保证明和安全责任边界材料。")
    lines.append("")
    lines.append("## 8. 附录")
    lines.append("")
    lines.append(f"- 扫描文件数：{inventory.get('file_count', '待确认')}")
    lines.append(f"- 规则扫描文件数：{scan.get('scanned_files', '待确认')}")
    if inventory.get("deployment_files"):
        lines.append("- 发现的部署相关文件：")
        for file in inventory.get("deployment_files", [])[:30]:
            lines.append(f"  - `{file}`")
    if inventory.get("documentation_files"):
        lines.append("- 发现的文档相关文件：")
        for file in inventory.get("documentation_files", [])[:30]:
            lines.append(f"  - `{file}`")
    lines.append("")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
