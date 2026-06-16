#!/usr/bin/env python3
"""Create and sync CaseForge requirement memory entries."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import date
from pathlib import Path


COMMON_RADAR = """## 通用漏测雷达

1. 权限：页面入口、按钮操作、后端接口都要考虑。
2. 状态：开始、处理中、报错、完成、已过期、恢复等状态要明确触发条件。
3. 导出：旧格式兼容、字段顺序、特殊字符、大数据量、权限越权。
4. 统计：时间范围、分母为0、历史数据、重复计数、四舍五入、动态列。
5. 工作池：上游/下游展示、当前池报错、上游报错残留、强弱校验优先级。
6. 私有化：Admin 与普通用户差异、授权到期拦截、恢复后回归、环境隔离。
7. 任务列表：筛选 AND/OR 口径、筛选命中总量、跨页选中状态、导出选中范围、首次分配时间不覆盖。
8. 历史版本：一期/二期/三期/V3.x/废弃/待讨论/未实现只能作为版本关系线索，不能不加判断地当作当前规则。
"""


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def slugify(value: str) -> str:
    text = value.strip().lower()
    replacements = {
        "任务列表": "task-list",
        "license": "license",
        "数据快照": "data-snapshot",
        "项目进度": "project-progress",
        "算法池": "algorithm-pool",
        "供应商": "supplier",
        "强校验": "validation-type",
        "弱校验": "validation-type",
    }
    for source, target in replacements.items():
        if source in text:
            return target
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text).strip("-")
    return text[:60] or "requirement"


def strip_heading_number(value: str) -> str:
    return re.sub(r"^#+\s*\d*(?:\.\d+)*\s*", "", value).strip()


def extract_section(text: str, heading_keyword: str) -> str:
    lines = text.splitlines()
    start = None
    level = None
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("#"):
            continue
        title = strip_heading_number(line)
        if heading_keyword in title:
            start = index + 1
            level = len(line) - len(line.lstrip("#"))
            break
    if start is None:
        return ""
    collected = []
    for line in lines[start:]:
        if line.lstrip().startswith("#"):
            current_level = len(line) - len(line.lstrip("#"))
            if level is not None and current_level <= level:
                break
        collected.append(line)
    return "\n".join(collected).strip()


def extract_first_paragraph(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("|") and not re.match(r"^\d+\.", stripped):
            return stripped
    return fallback


def extract_numbered_items(text: str, limit: int = 20) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^(?:\d+\.|-)\s*(.+)", stripped)
        if not match:
            continue
        item = match.group(1).strip()
        if not item or item.startswith("---") or item in items:
            continue
        items.append(item)
        if len(items) >= limit:
            break
    return items


def infer_keywords(requirement_name: str, normalized: str, design: str) -> str:
    candidates = [
        "任务列表",
        "筛选",
        "导出",
        "跨页选中",
        "分配时间",
        "更新时间",
        "license",
        "私有化",
        "算法池",
        "上游报错",
        "强校验",
        "弱校验",
        "数据快照",
        "完成池",
        "项目统计",
        "供应商",
        "权限",
        "状态流转",
        "数据集",
        "标注工具",
    ]
    haystack = f"{requirement_name}\n{normalized}\n{design}"
    found = [keyword for keyword in candidates if keyword in haystack]
    return "、".join(found[:12]) or requirement_name


def build_entry(
    requirement_name: str,
    source_file: str,
    normalized: str,
    design: str,
) -> str:
    objective = extract_first_paragraph(extract_section(normalized, "背景与目标"), f"沉淀 {requirement_name} 的业务规则。")
    key_source = "\n".join(
        [
            extract_section(normalized, "功能范围"),
            extract_section(normalized, "业务规则"),
            extract_section(normalized, "字段"),
            extract_section(normalized, "测试假设"),
        ]
    )
    rules = extract_numbered_items(key_source, 25)
    if not rules:
        rules = extract_numbered_items(normalized, 25)
    risks = extract_numbered_items(extract_section(design, "高风险点"), 20)
    if not risks:
        risks = extract_numbered_items(extract_section(design, "待确认问题"), 12)

    rule_lines = "\n".join(f"{index}. {item}" for index, item in enumerate(rules, 1)) or "1. 待补充稳定业务规则。"
    risk_lines = "\n".join(f"{index}. {item}" for index, item in enumerate(risks, 1)) or "1. 待补充测试风险。"

    return f"""# 需求记忆：{requirement_name}

## 来源

需求文档：`{source_file or requirement_name}`

## 核心业务目标

{objective}

## 关键业务规则

{rule_lines}

## 测试风险沉淀

{risk_lines}
"""


def ensure_index(memory_dir: Path) -> Path:
    index_path = memory_dir / "requirements-index.md"
    if index_path.exists():
        return index_path
    write_text(
        index_path,
        "# 已沉淀需求索引\n\n| 需求日期 | 需求标题 | 主题关键词 | 对应记忆条目 |\n| --- | --- | --- | --- |\n",
    )
    return index_path


def append_index_row(index_path: Path, requirement_date: str, requirement_name: str, keywords: str, entry_file: str) -> bool:
    text = read_text(index_path)
    entry_ref = f"`entries/{entry_file}`"
    if entry_ref in text or f"| {requirement_date} | {requirement_name} |" in text:
        return False
    if not text.endswith("\n"):
        text += "\n"
    text += f"| {requirement_date} | {requirement_name} | {keywords} | {entry_ref} |\n"
    write_text(index_path, text)
    return True


def sync_skill(memory_dir: Path, skill_dir: Path) -> None:
    references = skill_dir / "references"
    references.mkdir(parents=True, exist_ok=True)

    business_memory = memory_dir / "product-business-memory.md"
    if business_memory.exists():
        shutil.copyfile(business_memory, references / "business-memory.md")

    index_path = memory_dir / "requirements-index.md"
    if index_path.exists():
        index_text = read_text(index_path).strip()
        write_text(references / "requirement-memory-index.md", f"{index_text}\n\n{COMMON_RADAR}".strip() + "\n")

    entries_dir = memory_dir / "entries"
    entry_files = sorted(entries_dir.glob("*.md")) if entries_dir.exists() else []
    combined = [
        "# 需求记忆条目全集",
        "",
        "说明：本文件由 `scripts/requirement_memory_tools.py sync-skill` 从项目 `memory/entries/*.md` 同步生成。",
        "",
    ]
    for entry in entry_files:
        combined.extend([f"<!-- source: {entry.name} -->", read_text(entry).strip(), ""])
    write_text(references / "requirement-memory-entries.md", "\n".join(combined).strip() + "\n")

    archive = memory_dir / "historical-prd-archive"
    archive_mapping = {
        "source-file-digests.md": "historical-prd-source-digests.md",
        "source-file-index.csv": "historical-prd-source-index.csv",
        "module-knowledge-map.md": "historical-prd-module-knowledge-map.md",
        "evolution-groups.md": "historical-prd-evolution-groups-full.md",
    }
    if archive.exists():
        for source_name, target_name in archive_mapping.items():
            source = archive / source_name
            if source.exists():
                shutil.copyfile(source, references / target_name)


def create_from_run(args: argparse.Namespace) -> int:
    run_dir = args.run_dir
    memory_dir = args.memory_dir
    entries_dir = memory_dir / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)

    normalized = read_text(run_dir / "01-normalized-prd.md")
    design = read_text(run_dir / "02-test-design.md")
    if not normalized:
        raise SystemExit(f"Missing normalized PRD: {run_dir / '01-normalized-prd.md'}")

    requirement_date = args.date or date.today().isoformat()
    requirement_name = args.requirement_name or infer_requirement_name(normalized, run_dir)
    source_file = args.source_file or infer_source_file(run_dir)
    keywords = args.keywords or infer_keywords(requirement_name, normalized, design)
    slug = args.slug or slugify(requirement_name)
    entry_file = f"{requirement_date}-{slug}.md"
    entry_path = entries_dir / entry_file

    if entry_path.exists() and not args.force:
        print(f"entry_exists={entry_path}")
    else:
        write_text(entry_path, build_entry(requirement_name, source_file, normalized, design))
        print(f"entry={entry_path}")

    index_path = ensure_index(memory_dir)
    appended = append_index_row(index_path, requirement_date, requirement_name, keywords, entry_file)
    print(f"index={index_path}")
    print(f"index_appended={str(appended).lower()}")

    if args.skill_dir:
        sync_skill(memory_dir, args.skill_dir)
        print(f"skill_synced={args.skill_dir}")
    return 0


def infer_requirement_name(normalized: str, run_dir: Path) -> str:
    for line in normalized.splitlines()[:20]:
        stripped = line.strip("# ").strip()
        if stripped.startswith("标准化 PRD："):
            return stripped.split("：", 1)[1].strip()
    return run_dir.name


def infer_source_file(run_dir: Path) -> str:
    extracted = read_text(run_dir / "00-extracted-prd.txt")
    for line in extracted.splitlines()[:10]:
        stripped = line.strip()
        if stripped:
            return stripped
    return run_dir.name


def command_sync_skill(args: argparse.Namespace) -> int:
    sync_skill(args.memory_dir, args.skill_dir)
    print(f"skill_synced={args.skill_dir}")
    print(f"memory_dir={args.memory_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and sync CaseForge requirement memories.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-from-run", help="Create a memory entry from a CaseForge run directory")
    create.add_argument("--run-dir", type=Path, required=True)
    create.add_argument("--memory-dir", type=Path, required=True)
    create.add_argument("--skill-dir", type=Path)
    create.add_argument("--requirement-name")
    create.add_argument("--source-file")
    create.add_argument("--date")
    create.add_argument("--keywords")
    create.add_argument("--slug")
    create.add_argument("--force", action="store_true")
    create.set_defaults(func=create_from_run)

    sync = subparsers.add_parser("sync-skill", help="Sync project memories into the skill references")
    sync.add_argument("--memory-dir", type=Path, required=True)
    sync.add_argument("--skill-dir", type=Path, required=True)
    sync.set_defaults(func=command_sync_skill)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
