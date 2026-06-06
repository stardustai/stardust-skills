#!/usr/bin/env python3
import argparse
import csv
import json
import pathlib
import re
from collections import Counter, defaultdict


OUTPUT_DIR = pathlib.Path.home() / "Documents" / "memory" / "钉钉知识库"
CSV_HEADERS = [
    "workspace_name",
    "file_path",
    "size_mb",
    "file_type",
    "source_url",
    "modified_time",
    "proposed_category",
    "name_based_confidence",
    "needs_content_review",
    "review_reason",
    "content_summary",
    "duplicate_group",
    "proposed_action",
    "rename_to",
    "move_to",
    "admin_decision",
    "notes",
]
GENERIC_NAMES = {
    "test",
    "资料",
    "模板",
    "文档",
    "说明",
    "版本1",
    "版本2",
    "副本",
    "新建文档",
    "untitled",
    "draft",
    "temp",
    "tmp",
}
DELETE_TOKENS = {"test", "tmp", "temp", "copy", "backup"}
DELETE_SUBSTRINGS = ("副本", "备份", "废弃")


def load_inventory(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_existing_rows(path):
    if not path:
        return {}
    rows = {}
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows[row["file_path"]] = row
    return rows


def normalize_name(name):
    stem = name.rsplit(".", 1)[0].strip().lower()
    stem = re.sub(r"\(\d+\)$", "", stem)
    stem = re.sub(r"[_\-\s]+", " ", stem)
    return stem.strip()


def top_level_category(path):
    cleaned = path.lstrip()
    if "/" not in cleaned:
        return "(root)"
    return cleaned.split("/", 1)[0]


def is_archived_path(path):
    top = top_level_category(path)
    return top.startswith("待归档") or top.startswith("100-归档")


def infer_file_type(item):
    ext = (item.get("extension") or "").strip().lower()
    if ext:
        return ext
    node_category = item.get("node_category") or item.get("category") or ""
    return node_category.lower() or "unknown"


def infer_category(path, file_type):
    lowered = path.lower()
    top = top_level_category(path)

    if is_archived_path(path):
        return "归档"

    if top == "0_Strategy":
        return "战略"
    if top.startswith("0.品牌营销部-周报"):
        return "管理"
    if top.startswith("1. Onboarding"):
        return "Onboarding"
    if top.startswith("1. 新人必看"):
        return "Onboarding"
    if top.startswith("2. Global BD Steps"):
        return "流程/SOP"
    if top.startswith("2. 销售部流程规范"):
        return "流程/SOP"
    if top.startswith("3. Training"):
        return "培训"
    if top.startswith("3. 部门日常管理"):
        return "管理"
    if top.startswith("4. Management"):
        return "管理"
    if top.startswith("4. 行业调研"):
        return "研究"
    if top.startswith("5. Research"):
        return "研究"
    if top.startswith("5.投标知识库"):
        return "项目"
    if top.startswith("6. Channels"):
        return "渠道"
    if top.startswith("6. 培训"):
        return "培训"
    if top.startswith("7. Materials"):
        return "对外材料"
    if top.startswith("7.客户/Client"):
        return "项目"
    if top.startswith("8. Projects"):
        return "项目"
    if top.startswith("8. 客户大模型研究"):
        return "研究"
    if top.startswith("9. Cross-department Communication"):
        return "跨部门协作"
    if top.startswith("渠道产品合作"):
        return "渠道"
    if top.startswith("数据统计"):
        return "管理"
    if top.startswith("学习思考+资料分享"):
        return "培训"
    if top.startswith("公司/产品介绍材料"):
        return "对外材料"
    if top.startswith("跨部门协作材料"):
        return "跨部门协作"
    if top.startswith("飞书—历史文档"):
        return "归档"
    if top.startswith("98-复盘基地"):
        return "管理"
    if top.startswith("99-个人中心/Personal Doc"):
        return "待整理"
    if top.startswith("10. BD"):
        return "BD"
    if "hiring" in lowered or "招聘" in lowered or "面试" in lowered:
        return "招聘"
    if "legal" in lowered or "法务" in lowered or "contract" in lowered or "合同" in lowered:
        return "法务合同"
    if "okr" in lowered or "绩效" in lowered or "management" in lowered:
        return "管理"
    if "template" in lowered or "模板" in lowered:
        return "模板"
    if "invoice" in lowered or "财务" in lowered or "付款" in lowered:
        return "财务"
    if "channel" in lowered or "渠道" in lowered:
        return "渠道"
    if "project" in lowered or "项目" in lowered:
        return "项目"
    if "research" in lowered or "调研" in lowered:
        return "研究"
    if file_type in {"jpg", "jpeg", "png", "svg"}:
        return "图片素材"
    if file_type in {"mp4", "mov"}:
        return "视频素材"
    return "待整理"


def infer_confidence(path, proposed_category, duplicate_group):
    if is_archived_path(path):
        return 0.99
    score = 0.92
    cleaned = path.lstrip()
    basename = cleaned.rsplit("/", 1)[-1]
    normalized = normalize_name(basename)
    top = top_level_category(cleaned)

    if top in {"(root)"} or proposed_category == "待整理":
        score -= 0.30
    if any(token in normalized for token in GENERIC_NAMES):
        score -= 0.28
    if re.search(r"\b(v\d+|final|new|updated?)\b", normalized):
        score -= 0.10
    if duplicate_group:
        score -= 0.18
    if len(normalized) <= 4:
        score -= 0.12
    return max(0.35, min(0.98, round(score, 2)))


def infer_action(path, proposed_category, duplicate_group):
    lowered = path.lower()
    top = top_level_category(path)
    basename = path.lstrip().rsplit("/", 1)[-1]
    normalized = normalize_name(basename)
    tokens = set(normalized.split())

    if is_archived_path(path):
        return "keep", ""

    if tokens.intersection(DELETE_TOKENS) or any(token in basename for token in DELETE_SUBSTRINGS):
        return "move_to_待归档", "待归档"
    if duplicate_group:
        return "duplicate_candidate", ""
    if top == "(root)":
        return "move", f"{proposed_category}/"
    if top.startswith("11. Personal") and proposed_category == "待整理":
        return "move_to_待归档", "待归档"
    if top.startswith("99-个人中心/Personal Doc"):
        return "move_to_待归档", "100-归档材料"
    if top.startswith("飞书—历史文档"):
        return "move_to_待归档", "100-归档材料"
    return "keep", ""


def build_review_reason(path, confidence, duplicate_group):
    reasons = []
    basename = path.lstrip().rsplit("/", 1)[-1]
    normalized = normalize_name(basename)
    if top_level_category(path) == "(root)":
        reasons.append("位于根目录")
    if any(token in normalized for token in GENERIC_NAMES):
        reasons.append("文件名过于通用")
    if confidence < 0.60 and not reasons:
        reasons.append("仅靠名称和路径无法稳定判断")
    return "；".join(reasons)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-json", required=True)
    parser.add_argument("--existing-csv")
    parser.add_argument("--output-csv")
    args = parser.parse_args()

    inventory = load_inventory(args.inventory_json)
    existing = load_existing_rows(args.existing_csv)
    files = inventory["files"]

    name_counts = Counter(
        normalize_name(item["name"])
        for item in files
        if item.get("name") and not is_archived_path(item["path"].lstrip())
    )
    duplicate_ids = {}
    group_index = 1
    normalized_group_ids = {}
    for item in files:
        normalized = normalize_name(item["name"])
        if is_archived_path(item["path"].lstrip()):
            continue
        if name_counts[normalized] < 2:
            continue
        if normalized not in normalized_group_ids:
            normalized_group_ids[normalized] = f"DUP-{group_index:04d}"
            group_index += 1
        duplicate_ids[item["path"]] = normalized_group_ids[normalized]

    rows = []
    uncertain_count = 0
    for item in files:
        path = item["path"].lstrip()
        file_type = infer_file_type(item)
        duplicate_group = duplicate_ids.get(item["path"], "")
        proposed_category = infer_category(path, file_type)
        confidence = infer_confidence(path, proposed_category, duplicate_group)
        proposed_action, move_to = infer_action(path, proposed_category, duplicate_group)
        review_reason = build_review_reason(path, confidence, duplicate_group)
        needs_review = "yes" if review_reason else "no"
        if needs_review == "yes":
            uncertain_count += 1

        row = {
            "workspace_name": inventory["workspace"]["name"],
            "file_path": path,
            "size_mb": "",
            "file_type": file_type,
            "source_url": item.get("url") or "",
            "modified_time": item.get("modified_time") or item.get("modifiedTime") or "",
            "proposed_category": proposed_category,
            "name_based_confidence": f"{confidence:.2f}",
            "needs_content_review": needs_review,
            "review_reason": review_reason,
            "content_summary": "",
            "duplicate_group": duplicate_group,
            "proposed_action": proposed_action,
            "rename_to": "",
            "move_to": move_to,
            "admin_decision": "",
            "notes": "",
        }

        if path in existing:
            prior = existing[path]
            row["admin_decision"] = prior.get("admin_decision", "")
            row["notes"] = prior.get("notes", "")
            if prior.get("content_summary"):
                row["content_summary"] = prior["content_summary"]
            if prior.get("needs_content_review"):
                row["needs_content_review"] = prior["needs_content_review"]
            if prior.get("review_reason"):
                row["review_reason"] = prior["review_reason"]
        rows.append(row)

    rows.sort(key=lambda row: row["file_path"].lower())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.output_csv:
        output_csv = pathlib.Path(args.output_csv)
    else:
        safe_name = inventory["workspace"]["name"].replace("/", " ").strip()
        output_csv = OUTPUT_DIR / f"{safe_name}-整改台账初版.csv"

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(
        json.dumps(
            {
                "workspace": inventory["workspace"]["name"],
                "rows": len(rows),
                "needs_content_review": uncertain_count,
                "output_csv": str(output_csv),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
