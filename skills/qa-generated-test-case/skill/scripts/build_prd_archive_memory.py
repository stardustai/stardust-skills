#!/usr/bin/env python3
"""Build a reusable CaseForge memory map from a historical PRD folder."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from xml.etree import ElementTree as ET


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SUPPORTED_SUFFIXES = {".md", ".txt", ".docx", ".doc"}
KEYWORDS = [
    "权限",
    "角色",
    "状态",
    "流转",
    "筛选",
    "搜索",
    "导出",
    "导入",
    "统计",
    "时间",
    "校验",
    "失败",
    "异常",
    "默认",
    "只读",
    "不可",
    "支持",
    "新增",
    "删除",
    "编辑",
    "查看",
    "分配",
    "退回",
    "驳回",
    "完成",
    "标注池",
    "检查池",
    "抽查池",
    "完成池",
    "算法",
    "数据集",
    "工作流",
    "工作池",
    "分页",
    "跨页",
    "置灰",
    "提示",
    "兼容",
    "历史",
]
TAG_RULES = {
    "权限": ["权限", "角色", "可见", "不可见", "越权", "管理员", "普通用户", "团队"],
    "状态流转": ["状态", "流转", "标注池", "检查池", "抽查池", "完成池", "退回", "驳回", "回收", "暂停", "释放"],
    "筛选搜索": ["筛选", "搜索", "查询", "过滤", "条件"],
    "导入导出": ["导出", "导入", "下载", "上传", "Excel", "jsonl", "zip"],
    "统计": ["统计", "指标", "通过率", "进度", "成本", "数量", "总量", "计数"],
    "算法": ["算法", "模型", "辅助标注", "交互式", "非交互式", "调用"],
    "标注工具": ["操作项", "标注工具", "画布", "属性", "实例", "快捷键", "多边形", "矩形", "点云", "语义分割"],
    "数据管理": ["数据集", "数据源", "版本", "切片", "送标", "数据流", "元数据"],
    "安全": ["水印", "审计", "黑白名单", "加密", "token", "登录", "注册", "认证"],
    "SaaS": ["SaaS", "租户", "组织", "订阅", "免费", "资源"],
    "兼容历史": ["历史", "一期", "二期", "三期", "V", "v", "废弃", "待讨论", "未实现"],
}


@dataclass
class FileDigest:
    relative_path: str
    module_path: str
    title: str
    suffix: str
    char_count: int
    date_markers: str
    version_markers: str
    status_markers: str
    tags: str
    headings: str
    key_rules: str


def clean_text(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", text)
    text = re.sub(r"\[[^\]]+]\((?:https?://|file:)[^)]+\)", " ", text)
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
    lines = []
    for line in text.splitlines():
        stripped = re.sub(r"\s+", " ", line).strip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


def extract_docx_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    parts = []
    for paragraph in root.findall(".//w:p", WORD_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)).strip()
        if text:
            parts.append(text)
    return clean_text("\n".join(parts))


def extract_doc_with_textutil(path: Path) -> str:
    result = subprocess.run(
        ["textutil", "-stdout", "-convert", "txt", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return clean_text(result.stdout)


def read_file_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return clean_text(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".docx":
        return extract_docx_xml(path)
    if suffix == ".doc":
        return extract_doc_with_textutil(path)
    return ""


def first_title(path: Path, text: str) -> str:
    for line in text.splitlines()[:80]:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
    for line in text.splitlines()[:20]:
        if line.strip() and not line.strip().startswith("|"):
            return line.strip()[:80]
    return path.stem


def module_path(root: Path, path: Path) -> str:
    parts = path.relative_to(root).parts[:-1]
    return "/".join(parts[:3]) if parts else "根目录"


def extract_markers(text: str, pattern: str, limit: int = 8) -> str:
    found = []
    for item in re.findall(pattern, text, flags=re.IGNORECASE):
        value = item if isinstance(item, str) else "".join(item)
        if value not in found:
            found.append(value)
    return "；".join(found[:limit])


def extract_headings(text: str, limit: int = 10) -> str:
    headings = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title and title not in headings:
                headings.append(title)
        elif re.match(r"^(\d+(\.\d+)*|[一二三四五六七八九十]+[、.])", stripped):
            headings.append(stripped[:80])
        if len(headings) >= limit:
            break
    return "；".join(headings)


def extract_key_rules(text: str, limit: int = 12) -> str:
    rules = []
    for line in text.splitlines():
        stripped = line.strip()
        if len(stripped) < 6 or stripped.startswith("| ---"):
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            continue
        if re.fullmatch(r"[-|:：\s]+", stripped):
            continue
        score = sum(1 for keyword in KEYWORDS if keyword in stripped)
        if score == 0:
            continue
        if re.search(r"(背景|目录|版本信息|更新记录|负责人|创建日期)", stripped) and score < 2:
            continue
        normalized = stripped[:160]
        if normalized not in rules:
            rules.append(normalized)
        if len(rules) >= limit:
            break
    return "；".join(rules)


def infer_tags(text: str, relative_path: str) -> str:
    haystack = f"{relative_path}\n{text[:12000]}"
    tags = []
    for tag, words in TAG_RULES.items():
        if any(word in haystack for word in words):
            tags.append(tag)
    return "；".join(tags)


def digest_file(root: Path, path: Path) -> FileDigest | None:
    text = read_file_text(path)
    if not text:
        return None
    relative = path.relative_to(root).as_posix()
    return FileDigest(
        relative_path=relative,
        module_path=module_path(root, path),
        title=first_title(path, text),
        suffix=path.suffix.lower() or "<none>",
        char_count=len(text),
        date_markers=extract_markers(relative + "\n" + text[:2000], r"(20\d{2}[.\-/年]\d{1,2}(?:[.\-/月]\d{1,2})?)"),
        version_markers=extract_markers(relative + "\n" + text[:3000], r"((?:V|v)?\d+(?:\.\d+){0,3}|一期|二期|三期|四期|第一期|第二期|第三期|第四期)"),
        status_markers=extract_markers(relative + "\n" + text[:3000], r"(已评审|待讨论|未实现|废弃|仅限SaaS|SaaS|私有化|一期|二期|三期)"),
        tags=infer_tags(text, relative),
        headings=extract_headings(text),
        key_rules=extract_key_rules(text),
    )


def write_csv(path: Path, digests: list[FileDigest]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(digests[0]).keys()) if digests else [field.name for field in FileDigest.__dataclass_fields__.values()]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for digest in digests:
            writer.writerow(asdict(digest))


def build_digest_markdown(root: Path, digests: list[FileDigest]) -> str:
    lines = [
        "# 历史 PRD 逐文件知识索引",
        "",
        f"来源目录：`{root}`",
        f"已处理文件数：{len(digests)}",
        "",
        "说明：每个文件保留标题、模块、标签、阶段版本和关键规则摘录，用于后续生成测试用例时快速定位历史业务逻辑。",
        "",
    ]
    for index, digest in enumerate(digests, 1):
        lines.extend(
            [
                f"## {index}. {digest.title}",
                "",
                f"- 路径：`{digest.relative_path}`",
                f"- 模块：{digest.module_path}",
                f"- 标签：{digest.tags or '-'}",
                f"- 日期：{digest.date_markers or '-'}",
                f"- 版本/阶段：{digest.version_markers or '-'}",
                f"- 状态：{digest.status_markers or '-'}",
                f"- 章节：{digest.headings or '-'}",
                f"- 关键规则摘录：{digest.key_rules or '-'}",
                "",
            ]
        )
    return "\n".join(lines)


def build_module_map(root: Path, digests: list[FileDigest]) -> str:
    by_top: dict[str, list[FileDigest]] = defaultdict(list)
    for digest in digests:
        top = digest.relative_path.split("/", 1)[0]
        by_top[top].append(digest)

    lines = [
        "# 历史 PRD 模块知识图谱",
        "",
        f"来源目录：`{root}`",
        f"已处理文件数：{len(digests)}",
        "",
        "## 模块分布",
        "",
        "| 模块 | 文件数 | 高频标签 | 典型业务焦点 |",
        "| --- | ---: | --- | --- |",
    ]
    for module, items in sorted(by_top.items(), key=lambda pair: len(pair[1]), reverse=True):
        tag_counter: Counter[str] = Counter()
        rule_counter: Counter[str] = Counter()
        for item in items:
            for tag in item.tags.split("；"):
                if tag:
                    tag_counter[tag] += 1
            for rule in item.key_rules.split("；"):
                if rule:
                    rule_counter[rule[:60]] += 1
        tags = "、".join(tag for tag, _ in tag_counter.most_common(6)) or "-"
        sample_rules = "；".join(rule for rule, _ in rule_counter.most_common(3)) or "-"
        lines.append(f"| {module} | {len(items)} | {tags} | {sample_rules} |")

    lines.extend(["", "## 可复用业务规则", ""])
    lines.extend(
        [
            "1. Rosetta 人类反馈引擎是标注生产主域，历史 PRD 高频覆盖工作流、工作池、标注工具、点云/CV/文本/音频标注、任务流转、抽检包和项目统计。",
            "2. 多模态数据管理与数据探索是数据资产主域，后续用例需默认关注数据集、数据源、版本、切片、送标、数据流、权限隔离、导入导出和格式校验。",
            "3. 组织管理、登录注册和数据安全需求必须默认覆盖角色权限、SaaS/私有化差异、租户/组织隔离、用户状态、认证安全和审计记录。",
            "4. 算法接入需求必须默认覆盖算法创建/编辑/配置、交互式与非交互式调用、操作项映射、Query 参数、调用日志、算法结果写入和失败处理。",
            "5. 标注工具类需求必须覆盖标注池、检查池、抽查池、完成池，以及实例展示、属性、快捷键、画布、映射、错标、撤销/重做、连续帧、多视图和导出结果。",
            "6. 任务列表、统计和导出类需求必须覆盖筛选条件组合、分页/跨页选择、数据总量、导出字段顺序、权限越权、空数据、大数据量、异步处理和页面数据一致性。",
            "7. 出现“一期/二期/三期/V3.x/废弃/待讨论/未实现”等标记时，生成用例必须优先识别版本覆盖关系，不要把废弃或未实现规则直接当成当前规则。",
        ]
    )
    return "\n".join(lines)


def build_evolution_groups(digests: list[FileDigest]) -> str:
    groups: dict[str, list[FileDigest]] = defaultdict(list)
    for digest in digests:
        path = Path(digest.relative_path)
        if path.name in {"_index.md", "历史PRD.md", "验收报告.md", "验收问题.md"}:
            continue
        if path.stem in {"_index", "历史PRD", "验收报告", "验收问题", "无标题文档"}:
            continue
        stem = re.sub(r"^20\d{2}[.\-/]?\d{0,2}[.\-/]?\d{0,2}\s*", "", path.stem)
        stem = re.sub(r"(V|v)?\d+(\.\d+)*|一期|二期|三期|四期|第一期|第二期|第三期|第四期|需求|PRD|prd", "", stem)
        stem = re.sub(r"[\s_（）()【】\[\]、，,：:;；-]+", "", stem)
        key = stem[:18] or path.parent.name
        groups[key].append(digest)

    lines = ["# 历史 PRD 版本/阶段关系候选", "", "说明：这是基于文件名和路径自动识别的候选关系，用于提醒生成用例时检查一期、二期、后续修改和废弃规则。", ""]
    index = 1
    for key, items in sorted(groups.items(), key=lambda pair: len(pair[1]), reverse=True):
        if len(items) < 2:
            continue
        markers = "；".join(sorted({item.version_markers for item in items if item.version_markers})[:5])
        lines.append(f"## {index}. {key}")
        lines.append("")
        lines.append(f"- 候选阶段/版本：{markers or '-'}")
        for item in sorted(items, key=lambda x: x.relative_path):
            lines.append(f"- `{item.relative_path}` | {item.title} | {item.status_markers or '-'}")
        lines.append("")
        index += 1
        if index > 120:
            break
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build historical PRD memory artifacts.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    root = args.source
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)
    digests: list[FileDigest] = []
    failures: list[dict[str, str]] = []

    for path in files:
        try:
            digest = digest_file(root, path)
            if digest:
                digests.append(digest)
        except Exception as exc:  # noqa: BLE001
            failures.append({"path": path.relative_to(root).as_posix(), "error": str(exc)})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "source-file-index.csv", digests)
    (args.out_dir / "source-file-digests.md").write_text(build_digest_markdown(root, digests), encoding="utf-8")
    (args.out_dir / "module-knowledge-map.md").write_text(build_module_map(root, digests), encoding="utf-8")
    (args.out_dir / "evolution-groups.md").write_text(build_evolution_groups(digests), encoding="utf-8")
    (args.out_dir / "build-report.json").write_text(
        json.dumps(
            {
                "source": str(root),
                "discovered_supported_files": len(files),
                "processed_files": len(digests),
                "failures": failures,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"supported_files={len(files)}")
    print(f"processed_files={len(digests)}")
    print(f"failures={len(failures)}")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
