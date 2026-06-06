#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import urllib.parse
import urllib.request


CONFIG_PATH = os.path.expanduser("~/.dingtalk-skills/config")


def load_config():
    cfg = {}
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            cfg[key] = value
    return cfg


def request_json(url, method="GET", body=None, token=None):
    headers = {}
    payload = None
    if token:
        headers["x-acs-dingtalk-access-token"] = token
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def fetch_access_token(cfg):
    data = request_json(
        "https://api.dingtalk.com/v1.0/oauth2/accessToken",
        method="POST",
        body={
            "appKey": cfg["DINGTALK_APP_KEY"],
            "appSecret": cfg["DINGTALK_APP_SECRET"],
        },
    )
    return data["accessToken"]


def read_inventory(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return {item["path"].lstrip(): item for item in data["files"]}


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def extract_doc_summary(token, operator_id, doc_key):
    url = (
        "https://api.dingtalk.com/v1.0/doc/suites/documents/"
        + urllib.parse.quote(doc_key)
        + "/blocks?"
        + urllib.parse.urlencode({"operatorId": operator_id})
    )
    data = request_json(url, token=token)
    blocks = (data.get("result") or {}).get("data") or []
    parts = []
    for block in blocks[:20]:
        block_type = block.get("blockType")
        if block_type == "heading":
            text = ((block.get("heading") or {}).get("text") or "").strip()
        elif block_type == "paragraph":
            text = ((block.get("paragraph") or {}).get("text") or "").strip()
        elif block_type == "unorderedList":
            text = ((block.get("unorderedList") or {}).get("text") or "").strip()
        elif block_type == "orderedList":
            text = ((block.get("orderedList") or {}).get("text") or "").strip()
        elif block_type == "blockquote":
            text = ((block.get("blockquote") or {}).get("text") or "").strip()
        else:
            text = ""
        if text:
            parts.append(text)
        joined = " ".join(parts)
        if len(joined) >= 500:
            break
    return " ".join(parts)[:500]


def classify_from_text(text):
    lowered = text.lower()
    if any(token in lowered for token in ["okr", "performance", "考核", "周报", "月报", "workshop", "review", "1:1"]):
        return "管理", "keep", ""
    if any(token in lowered for token in ["onboarding", "new hire", "新人", "入职", "考试", "培训", "single choice question", "questions"]):
        return "Onboarding", "keep", ""
    if any(token in lowered for token in ["nda", "agreement", "contract", "保密协议", "合同", "consent", "guarantee"]):
        return "法务合同", "keep", ""
    if any(token in lowered for token in ["rfq", "quotation", "quote", "proposal", "报价", "投标", "招标", "sow", "po"]):
        return "项目", "keep", ""
    if any(token in lowered for token in ["pitch", "intro", "company introduction", "case study", "方案", "介绍"]):
        return "对外材料", "keep", ""
    if any(token in lowered for token in ["template", "outreach", "subject:", "email draft"]):
        return "模板", "keep", ""
    if any(token in lowered for token in ["sop", "process", "workflow", "指南", "交接", "手册", "流程"]):
        return "流程/SOP", "keep", ""
    if any(token in lowered for token in ["flight", "hotel", "receipt", "invoice", "trip", "报销", "机票", "住宿"]):
        return "待整理", "move_to_待归档", "待归档"
    return "", "", ""


def classify_from_filename(path, file_type):
    lowered = path.lower()
    basename = path.rsplit("/", 1)[-1]
    if "/4. management/" in f"/{lowered}":
        return "管理", "keep", "", "跟随管理目录归类"
    if "/6. channels/" in f"/{lowered}":
        return "渠道", "keep", "", "跟随渠道目录归类"
    if "/3. training/" in f"/{lowered}" or "/1. onboarding/" in f"/{lowered}":
        return "培训", "keep", "", "跟随培训目录归类"
    if "/8. projects/" in f"/{lowered}" or "mary china labeling factory" in lowered or "mary-大项目" in lowered:
        return "项目", "keep", "", "跟随项目目录归类"
    if any(token in lowered for token in ["flight", "hotel", "receipt", "invoice", "trip", "报销", "机票", "回程机票"]):
        return "待整理", "move_to_待归档", "待归档", "文件名明显为差旅报销材料"
    if file_type == "json" and any(token in lowered for token in ["/delivery/label/", "/label/"]):
        return "项目", "keep", "", "路径明显为项目交付标注结果"
    if any(token in lowered for token in ["nda", "agreement", "contract", "保密协议", "合同", "consent", "guarantee", "dpa"]):
        return "法务合同", "keep", "", "文件名明显为合同或法务材料"
    if any(token in lowered for token in ["rfq", "quotation", "quote", "proposal", "报价", "投标", "招标", "sow", "po", "offer", "supplier form", "requirements questionnaire", "questionnaire", "q&a", "需求说明", "需求文档", "规则文档", "api test", "疑问解答", "标书", "供应商信息变更表"]):
        return "项目", "keep", "", "文件名明显为项目商务文件"
    if any(token in lowered for token in ["okr", "performance", "考核", "周报", "月报", "workshop", "review"]):
        return "管理", "keep", "", "文件名明显为管理材料"
    if any(token in lowered for token in ["guide", "manual", "sop", "workflow", "流程", "交接", "指南", "手册"]):
        return "流程/SOP", "keep", "", "文件名明显为流程文档"
    if any(token in lowered for token in ["case study", "pitch", "intro", "company introduction", "介绍", "solution", "approach", "员工简介"]) and file_type in {"adoc", "pdf", "pptx", "docx"}:
        return "对外材料", "keep", "", "文件名明显为对外介绍或案例材料"
    if any(token in lowered for token in ["template", "email templates", "draft", "ppt rules"]) and file_type in {"adoc", "pdf", "pptx", "docx", "xlsx", "axls", "wps"}:
        return "模板", "keep", "", "文件名明显为模板类材料"
    if any(token in lowered for token in ["crm", "lead", "channel", "客户"]) and file_type in {"xlsx", "axls", "adoc"}:
        return "渠道", "keep", "", "文件名明显为渠道或客户管理材料"
    return "", "", "", ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-json", required=True)
    parser.add_argument("--csv-path", required=True)
    args = parser.parse_args()

    fieldnames, rows = read_csv(args.csv_path)
    inventory = read_inventory(args.inventory_json)
    cfg = load_config()
    token = fetch_access_token(cfg)
    operator_id = cfg["DINGTALK_OPERATOR_ID"]

    updated = 0
    deep_read = 0
    unresolved = 0

    for row in rows:
        if row.get("needs_content_review") != "yes":
            continue
        path = row["file_path"]
        file_type = row["file_type"]

        proposed_category, proposed_action, move_to, reason = classify_from_filename(path, file_type)
        if proposed_category:
            row["proposed_category"] = proposed_category
            row["proposed_action"] = proposed_action
            row["move_to"] = move_to
            row["review_reason"] = reason
            row["needs_content_review"] = "no"
            row["notes"] = (row.get("notes") or "").strip()
            updated += 1
            continue

        if row.get("proposed_action") == "duplicate_candidate" and row.get("proposed_category") not in {"待整理", ""}:
            row["needs_content_review"] = "no"
            row["review_reason"] = "疑似重复版本，待管理员确认是否保留"
            updated += 1
            continue

        if file_type == "adoc":
            item = inventory.get(path)
            if item and item.get("node_id"):
                try:
                    summary = extract_doc_summary(token, operator_id, item["node_id"])
                except Exception as exc:
                    row["notes"] = (row.get("notes") or "") + f" API正文读取失败: {exc}"
                    unresolved += 1
                    continue
                deep_read += 1
                row["content_summary"] = summary
                proposed_category, proposed_action, move_to = classify_from_text(summary)
                if proposed_category:
                    row["proposed_category"] = proposed_category
                    row["proposed_action"] = proposed_action
                    row["move_to"] = move_to
                    row["review_reason"] = "已基于正文开头重判"
                    row["needs_content_review"] = "no"
                    updated += 1
                else:
                    row["review_reason"] = "已读取正文开头，仍需人工判断"
                    unresolved += 1
                continue

        unresolved += 1

    write_csv(args.csv_path, fieldnames, rows)
    print(
        json.dumps(
            {
                "csv_path": args.csv_path,
                "updated_rows": updated,
                "deep_read_adoc": deep_read,
                "still_unresolved": unresolved,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
