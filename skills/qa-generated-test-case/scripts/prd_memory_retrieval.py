#!/usr/bin/env python3
"""Build and search a private PRD memory index for QA testcase generation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SUPPORTED_SUFFIXES = {".md", ".txt", ".docx"}
FIELD_NAMES = [
    "id",
    "product_line",
    "module",
    "requirement_title",
    "version",
    "date",
    "page_or_api",
    "role",
    "tags",
    "source_path",
    "section",
    "content",
]
FILTER_FIELDS = [
    "product_line",
    "module",
    "requirement_title",
    "version",
    "date",
    "page_or_api",
    "role",
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


def clean_text(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
    lines = []
    for line in text.splitlines():
        stripped = re.sub(r"\s+", " ", line).strip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


def read_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    parts: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)).strip()
        if text:
            parts.append(text)
    return clean_text("\n".join(parts))


def read_source_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return clean_text(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".docx":
        return read_docx_text(path)
    return ""


def parse_front_matter(raw_text: str) -> tuple[dict[str, str], str]:
    lines = raw_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw_text

    end_index = None
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, raw_text

    metadata: dict[str, str] = {}
    for line in lines[1:end_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace("-", "_")
        metadata[normalized_key] = value.strip().strip('"').strip("'")
    return metadata, "\n".join(lines[end_index + 1 :]).strip()


def first_heading(path: Path, text: str) -> str:
    for line in text.splitlines()[:80]:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
    for line in text.splitlines()[:20]:
        stripped = line.strip()
        if stripped and not stripped.startswith("|"):
            return stripped[:80]
    return path.stem


def extract_first(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def normalize_tags(value: str | list[str]) -> str:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[,，;；|/]\s*", value)
    items: list[str] = []
    for item in raw_items:
        stripped = item.strip()
        if stripped and stripped not in items:
            items.append(stripped)
    return "；".join(items)


def infer_tags(text: str, relative_path: str) -> str:
    haystack = f"{relative_path}\n{text[:12000]}"
    tags = []
    for tag, words in TAG_RULES.items():
        if any(word in haystack for word in words):
            tags.append(tag)
    return "；".join(tags)


def infer_metadata(root: Path, path: Path, body: str, metadata: dict[str, str]) -> dict[str, str]:
    relative = path.relative_to(root).as_posix()
    parts = Path(relative).parts
    product_line = metadata.get("product_line") or metadata.get("product") or (parts[0] if len(parts) > 1 else "")
    module = metadata.get("module") or metadata.get("module_path") or ("/".join(parts[1:-1]) if len(parts) > 2 else "")
    title = metadata.get("requirement_title") or metadata.get("title") or first_heading(path, body)
    combined = f"{relative}\n{body[:3000]}"
    version = metadata.get("version") or extract_first(
        r"((?:V|v)?\d+(?:\.\d+){0,3}|一期|二期|三期|四期|第一期|第二期|第三期|第四期)",
        combined,
    )
    date = metadata.get("date") or extract_first(r"(20\d{2}[.\-/年]\d{1,2}(?:[.\-/月]\d{1,2})?)", combined)
    page_or_api = metadata.get("page_or_api") or metadata.get("page") or metadata.get("api") or ""
    role = metadata.get("role") or ""
    tags = metadata.get("tags") or infer_tags(body, relative)
    return {
        "product_line": product_line,
        "module": module,
        "requirement_title": title,
        "version": version,
        "date": date,
        "page_or_api": page_or_api,
        "role": role,
        "tags": normalize_tags(tags),
        "source_path": relative,
    }


def split_sections(text: str, max_chars: int) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = "正文"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        content = "\n".join(current_lines).strip()
        if content:
            sections.extend(chunk_section(current_title, content, max_chars))
        current_lines = []

    for line in text.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if heading:
            flush()
            current_title = heading.group(2).strip()
        else:
            current_lines.append(line)
    flush()

    if not sections and text.strip():
        sections.extend(chunk_section("正文", text.strip(), max_chars))
    return sections


def chunk_section(title: str, content: str, max_chars: int) -> list[tuple[str, str]]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", content) if paragraph.strip()]
    chunks: list[tuple[str, str]] = []
    current = ""
    for paragraph in paragraphs or [content]:
        if current and len(current) + len(paragraph) + 1 > max_chars:
            chunks.append((title, current.strip()))
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip() if current else paragraph
        while len(current) > max_chars:
            chunks.append((title, current[:max_chars].strip()))
            current = current[max_chars:].strip()
    if current:
        chunks.append((title, current.strip()))
    return chunks


def record_id(source_path: str, section: str, content: str) -> str:
    digest = hashlib.sha1(f"{source_path}\n{section}\n{content[:160]}".encode("utf-8")).hexdigest()
    return digest[:16]


def build_records(source_dir: Path, max_chars: int) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    files = sorted(path for path in source_dir.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)
    for path in files:
        raw_text = read_source_text(path)
        if not raw_text:
            continue
        metadata, body = parse_front_matter(raw_text)
        body = clean_text(body)
        inferred = infer_metadata(source_dir, path, body, metadata)
        for section, content in split_sections(body, max_chars):
            record = {field: "" for field in FIELD_NAMES}
            record.update(inferred)
            record["section"] = section
            record["content"] = content
            record["id"] = record_id(record["source_path"], section, content)
            records.append(record)
    return records


def write_jsonl(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELD_NAMES)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in FIELD_NAMES})


def load_index(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
            records.append({field: str(record.get(field, "")) for field in FIELD_NAMES})
    return records


def contains_filter(record_value: str, expected: str) -> bool:
    if not expected:
        return True
    return expected.casefold() in record_value.casefold()


def tag_filter(record_tags: str, expected_tags: str) -> bool:
    if not expected_tags:
        return True
    record_items = {item.casefold() for item in re.split(r"[,，;；|/]\s*", record_tags) if item.strip()}
    expected_items = [item.casefold() for item in re.split(r"[,，;；|/]\s*", expected_tags) if item.strip()]
    return all(any(expected in item for item in record_items) for expected in expected_items)


def matches_filters(record: dict[str, str], filters: dict[str, str]) -> bool:
    for field in FILTER_FIELDS:
        if not contains_filter(record.get(field, ""), filters.get(field, "")):
            return False
    return tag_filter(record.get("tags", ""), filters.get("tags", ""))


def query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for term in re.findall(r"[A-Za-z0-9_.:/-]+|[\u4e00-\u9fff]{2,}", query):
        normalized = term.casefold()
        if normalized and normalized not in terms:
            terms.append(normalized)
        if re.fullmatch(r"[\u4e00-\u9fff]{4,}", term):
            for index in range(len(term) - 1):
                bigram = term[index : index + 2].casefold()
                if bigram not in terms:
                    terms.append(bigram)
    return terms


def score_record(record: dict[str, str], query: str) -> int:
    terms = query_terms(query)
    if not terms:
        return 1
    score = 0
    weighted_fields = [
        ("requirement_title", 5),
        ("tags", 4),
        ("module", 3),
        ("page_or_api", 3),
        ("role", 2),
        ("section", 2),
        ("content", 1),
    ]
    for field, weight in weighted_fields:
        value = record.get(field, "").casefold()
        for term in terms:
            if term in value:
                score += weight
    return score


def search_records(
    records: list[dict[str, str]],
    filters: dict[str, str],
    query: str,
    top_n: int,
) -> list[tuple[int, dict[str, str]]]:
    candidates = [record for record in records if matches_filters(record, filters)]
    scored = [(score_record(record, query), record) for record in candidates]
    if query:
        scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[1].get("date", ""), item[1].get("source_path", "")))
    return scored[:top_n]


def format_markdown(results: list[tuple[int, dict[str, str]]], query: str, filters: dict[str, str]) -> str:
    lines = ["# PRD Memory Retrieval Results", ""]
    if query:
        lines.append(f"- query: `{query}`")
    active_filters = {key: value for key, value in filters.items() if value}
    if active_filters:
        lines.append(f"- filters: `{json.dumps(active_filters, ensure_ascii=False, sort_keys=True)}`")
    lines.append(f"- results: {len(results)}")
    lines.append("")

    for index, (score, record) in enumerate(results, 1):
        lines.extend(
            [
                f"## {index}. {record.get('requirement_title') or record.get('source_path')}",
                "",
                f"- score: {score}",
                f"- product_line: {record.get('product_line') or '-'}",
                f"- module: {record.get('module') or '-'}",
                f"- version: {record.get('version') or '-'}",
                f"- date: {record.get('date') or '-'}",
                f"- page_or_api: {record.get('page_or_api') or '-'}",
                f"- role: {record.get('role') or '-'}",
                f"- tags: {record.get('tags') or '-'}",
                f"- source_path: `{record.get('source_path')}`",
                f"- section: {record.get('section') or '-'}",
                "",
                record.get("content", ""),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def validate_records(records: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(records, 1):
        missing = [field for field in FIELD_NAMES if field not in record]
        if missing:
            errors.append(f"record {index}: missing fields {missing}")
        if not record.get("id"):
            errors.append(f"record {index}: empty id")
        if record.get("id") in seen_ids:
            errors.append(f"record {index}: duplicate id {record.get('id')}")
        seen_ids.add(record.get("id", ""))
        if not record.get("source_path"):
            errors.append(f"record {index}: empty source_path")
        if not record.get("content"):
            errors.append(f"record {index}: empty content")
    return errors


def command_build_index(args: argparse.Namespace) -> int:
    if not args.source_dir.exists():
        raise SystemExit(f"source_dir not found: {args.source_dir}")
    records = build_records(args.source_dir, args.max_chars)
    write_jsonl(args.out_index, records)
    if args.out_csv:
        write_csv(args.out_csv, records)
    print(f"records={len(records)}")
    print(f"index={args.out_index}")
    if args.out_csv:
        print(f"csv={args.out_csv}")
    return 0


def collect_filters(args: argparse.Namespace) -> dict[str, str]:
    filters = {field: getattr(args, field, "") or "" for field in FILTER_FIELDS}
    filters["tags"] = args.tags or ""
    return filters


def command_search_memory(args: argparse.Namespace) -> int:
    records = load_index(args.index)
    results = search_records(records, collect_filters(args), args.query or "", args.top_n)
    if args.format == "json":
        output = json.dumps(
            [{"score": score, **record} for score, record in results],
            ensure_ascii=False,
            indent=2,
        )
    else:
        output = format_markdown(results, args.query or "", collect_filters(args))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + ("" if output.endswith("\n") else "\n"), encoding="utf-8")
        print(f"out={args.out}")
    else:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def command_validate_retrieval(args: argparse.Namespace) -> int:
    records = load_index(args.index)
    errors = validate_records(records)
    checked_queries = 0
    if args.queries_jsonl:
        with args.queries_jsonl.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue
                spec = json.loads(line)
                checked_queries += 1
                filters = {field: str(spec.get(field, "")) for field in FILTER_FIELDS}
                filters["tags"] = str(spec.get("tags", ""))
                top_n = int(spec.get("top_n", args.top_n))
                results = search_records(records, filters, str(spec.get("query", "")), top_n)
                min_results = int(spec.get("min_results", 1))
                if len(results) < min_results:
                    errors.append(f"query {line_number}: expected at least {min_results} results, got {len(results)}")
                if len(results) > top_n:
                    errors.append(f"query {line_number}: returned {len(results)} results over top_n={top_n}")
    print(f"index_records={len(records)}")
    print(f"queries={checked_queries}")
    if errors:
        print("validation=failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print("validation=ok")
    return 0


def add_search_filters(parser: argparse.ArgumentParser) -> None:
    for field in FILTER_FIELDS:
        parser.add_argument(f"--{field.replace('_', '-')}", dest=field, default="")
    parser.add_argument("--tags", default="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and search an external PRD memory index.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_index = subparsers.add_parser("build-index", help="Build a JSONL index from a private PRD directory")
    build_index.add_argument("--source-dir", type=Path, required=True)
    build_index.add_argument("--out-index", type=Path, required=True)
    build_index.add_argument("--out-csv", type=Path)
    build_index.add_argument("--max-chars", type=int, default=1200)
    build_index.set_defaults(func=command_build_index)

    search = subparsers.add_parser("search-memory", help="Search an existing PRD memory index")
    search.add_argument("--index", type=Path, required=True)
    search.add_argument("--query", default="")
    search.add_argument("--top-n", type=int, default=5)
    search.add_argument("--format", choices=["markdown", "json"], default="markdown")
    search.add_argument("--out", type=Path)
    add_search_filters(search)
    search.set_defaults(func=command_search_memory)

    validate = subparsers.add_parser("validate-retrieval", help="Validate index schema and optional query specs")
    validate.add_argument("--index", type=Path, required=True)
    validate.add_argument("--queries-jsonl", type=Path)
    validate.add_argument("--top-n", type=int, default=5)
    validate.set_defaults(func=command_validate_retrieval)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001
        print(f"error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
