import argparse
import json
from pathlib import Path

from scripts.report_contract import (
    BUSINESS_LINES,
    validate_claim,
    validate_issue,
    validate_issue_continuity,
    validate_manifest,
    validate_metric,
    validate_privacy,
)


FIXED_METRICS = (
    "new_signed_orders",
    "recognized_revenue",
    "payment_collected",
    "gross_margin",
    "overdue_receivables",
    "weighted_pipeline",
    "opportunities_advanced",
    "friday_ka_poc_orders",
    "friday_smb_wau_paid_conversion",
    "morningstar_orders_margin_new_opportunities",
    "international_pipeline_paid_poc",
    "worldmodel_validated_demand_paid_poc",
)
REQUIRED_REPORT_KEYS = (
    "ceo_judgment",
    "company_metrics",
    "issues",
    "cockpit",
    "business_lines",
    "root_causes",
    "discussion",
)
REQUIRED_BUSINESS_LINE_KEYS = (
    "summary",
    "core_metrics",
    "milestone_deviation",
    "largest_risk",
    "management_decision",
    "metrics",
    "milestones",
    "full_report_jsonml",
)
RENDERED_METRIC_KEYS = (
    "name",
    "target",
    "current",
    "status",
    "data_date",
    "definition_evidence",
)


def validate_rendered_metric(metric: dict) -> list[str]:
    key = metric.get("key", metric.get("name", "<missing>"))
    return [
        f"{key} is missing rendered field {field}"
        for field in RENDERED_METRIC_KEYS
        if field not in metric
    ]


def validate_run(
    manifest: dict, report: dict, previous_issues: list[dict]
) -> dict:
    errors = validate_manifest(manifest)

    for key in REQUIRED_REPORT_KEYS:
        if key not in report:
            errors.append(f"report section {key} is missing")

    metrics = report.get("company_metrics", [])
    metric_by_key = {item.get("key"): item for item in metrics}
    if len(metric_by_key) != len(metrics):
        errors.append("company report has duplicate metric keys")
    for key in FIXED_METRICS:
        if key not in metric_by_key:
            errors.append(f"fixed metric {key} is missing")
        else:
            errors.extend(validate_metric(metric_by_key[key]))
    exception_count = len(set(metric_by_key) - set(FIXED_METRICS))
    if exception_count > 3:
        errors.append("company report has more than 3 exception metrics")

    claims = report.get("claims", [])
    validated_claim_texts = set()
    for claim in claims:
        errors.extend(validate_claim(claim))
        if not validate_claim(claim):
            validated_claim_texts.add(claim.get("text"))
    for section, records in (
        ("CEO judgment", report.get("ceo_judgment", [])),
        ("root cause", report.get("root_causes", [])),
    ):
        for record in records:
            if record.get("text") not in validated_claim_texts:
                errors.append(
                    f"{section} '{record.get('text', '<missing>')}' has no matching validated claim"
                )
    for metric in metrics:
        errors.extend(validate_rendered_metric(metric))
    for issue in report.get("issues", []):
        errors.extend(validate_issue(issue))
    errors.extend(
        validate_issue_continuity(
            previous_issues, report.get("issues", [])
        )
    )

    business_lines = report.get("business_lines", {})
    for line_name in BUSINESS_LINES:
        if line_name not in business_lines:
            errors.append(f"business line {line_name} is missing from report")
            continue
        line = business_lines[line_name]
        for key in REQUIRED_BUSINESS_LINE_KEYS:
            if key not in line:
                errors.append(
                    f"business line {line_name} is missing field {key}"
                )
        for metric in line.get("metrics", []):
            errors.extend(validate_metric(metric))
            errors.extend(validate_rendered_metric(metric))

    errors.extend(validate_privacy(report.get("private", {})))
    unique_errors = list(dict.fromkeys(errors))
    return {"publishable": not unique_errors, "errors": unique_errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--previous-issues", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    def load(path: str):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    result = validate_run(
        load(args.manifest),
        load(args.report),
        load(args.previous_issues),
    )
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["publishable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
