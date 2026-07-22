#!/usr/bin/env python3
"""Read-only Dingteam OKR API client backed by the headless auth profile."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


_BROWSER_PATH = Path(__file__).resolve().parent / "dingteam_okr_browser_source.py"
_spec = importlib.util.spec_from_file_location("dingteam_okr_browser_source", _BROWSER_PATH)
browser = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(browser)
direct = browser.direct


READ_ENDPOINTS = {
    "period.list": "/data/okr/person/period/list",
    "objective.list": "/data/okr/objective/showListView/v2",
    "score.batch": "/data/okr/objective/getObjectiveScoreBatch",
    "score.detail": "/data/okr/objective/getScoreDetail",
    "rating.list": "/data/okr/cockpit/detail/list",
    "rating.reports": "/data/okr/cockpit/reports",
    "rating.detailReports": "/data/okr/cockpit/detail/reports",
}


class ReadClient:
    """Reuse one in-memory header set for a read-only audit run."""

    def __init__(self, *, allow_browser: bool = True) -> None:
        self.allow_browser = allow_browser
        self._headers: dict[str, str] | None = None

    def call(self, alias: str, body: dict[str, Any]) -> Any:
        if alias not in READ_ENDPOINTS:
            raise ValueError(f"unsupported read endpoint alias: {alias}")
        if self._headers is None:
            self._headers = browser.get_headers(allow_browser=self.allow_browser)
        payload = direct._post(READ_ENDPOINTS[alias], body, self._headers)
        return direct._unwrap(payload)

    def get_score_batch(self, okr_id: str) -> dict[str, Any]:
        data = self.call("score.batch", {"okrId": okr_id})
        if not isinstance(data, dict):
            raise RuntimeError(f"unexpected score.batch response: {data!r}")
        return data

    def resolve_score_batch_id(self, okr_id: str) -> str:
        return score_batch_id(self.get_score_batch(okr_id), okr_id)

    def get_score_detail(self, objective_id: str, batch_id: str) -> dict[str, Any]:
        data = self.call(
            "score.detail", {"objectiveId": objective_id, "batchId": batch_id}
        )
        if not isinstance(data, dict) or data.get("objectiveId") != objective_id:
            raise RuntimeError(
                f"unexpected score.detail response for {objective_id}: {data!r}"
            )
        return data


def call(alias: str, body: dict[str, Any], *, allow_browser: bool = True) -> Any:
    """Call one approved read-only endpoint without exposing auth headers."""
    return ReadClient(allow_browser=allow_browser).call(alias, body)


def rating_list_body(
    okr_id: str,
    *,
    user_ids: list[str] | None = None,
    page_no: int = 1,
    page_size: int = 1000,
    search_type: str = "byObj",
) -> dict[str, Any]:
    return {
        "searchName": "",
        "objectiveType": 0,
        "objectiveStatus": "",
        "progress": 0,
        "confidence": 0,
        "deptIds": [],
        "userIds": user_ids or [],
        "krOwnerIds": [],
        "objOwnerIds": [],
        "taskOwnerIds": [],
        "dateRange": None,
        "taskType": "total",
        "pieChartSearchType": 0,
        "pageNo": page_no,
        "pageSize": page_size,
        "reportType": "rating",
        "okrId": okr_id,
        "key": "",
        "isAsc": False,
        "searchType": search_type,
        "batchId": "",
    }


def get_rating_list(
    okr_id: str,
    *,
    user_ids: list[str] | None = None,
    page_size: int = 1000,
    allow_browser: bool = True,
) -> dict[str, Any]:
    data = call(
        "rating.list",
        rating_list_body(okr_id, user_ids=user_ids, page_size=page_size),
        allow_browser=allow_browser,
    )
    if not isinstance(data, dict) or not isinstance(data.get("list"), list):
        raise RuntimeError(f"unexpected rating.list response: {data!r}")
    if data.get("totalPages", 1) not in (0, 1):
        raise RuntimeError(
            f"rating archive has {data['totalPages']} pages; increase --page-size"
        )
    return data


def get_score_batch(okr_id: str, *, allow_browser: bool = True) -> dict[str, Any]:
    data = call("score.batch", {"okrId": okr_id}, allow_browser=allow_browser)
    if not isinstance(data, dict):
        raise RuntimeError(f"unexpected score.batch response: {data!r}")
    return data


def score_batch_id(data: dict[str, Any], okr_id: str = "<unknown>") -> str:
    cells = data.get("cells") if isinstance(data.get("cells"), list) else []
    current = [cell for cell in cells if cell.get("isCurrent")]
    candidates = current or cells
    if len(candidates) != 1 or not candidates[0].get("batchId"):
        raise RuntimeError(f"could not resolve one score batch for {okr_id}: {cells!r}")
    return str(candidates[0]["batchId"])


def resolve_score_batch_id(okr_id: str, *, allow_browser: bool = True) -> str:
    return score_batch_id(get_score_batch(okr_id, allow_browser=allow_browser), okr_id)


def get_score_detail(
    objective_id: str,
    batch_id: str,
    *,
    allow_browser: bool = True,
) -> dict[str, Any]:
    data = call(
        "score.detail",
        {"objectiveId": objective_id, "batchId": batch_id},
        allow_browser=allow_browser,
    )
    if not isinstance(data, dict) or data.get("objectiveId") != objective_id:
        raise RuntimeError(f"unexpected score.detail response for {objective_id}: {data!r}")
    return data


def parse_body(args: argparse.Namespace) -> dict[str, Any]:
    if args.body_file:
        return json.loads(Path(args.body_file).read_text(encoding="utf-8"))
    return json.loads(args.body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    call_parser = subparsers.add_parser("call", help="call an approved read endpoint")
    call_parser.add_argument("--alias", choices=sorted(READ_ENDPOINTS), required=True)
    call_body = call_parser.add_mutually_exclusive_group(required=True)
    call_body.add_argument("--body")
    call_body.add_argument("--body-file")

    rating_parser = subparsers.add_parser("rating-list", help="read rating archive")
    rating_parser.add_argument("--okr-id", required=True)
    rating_parser.add_argument("--user-id", action="append", default=[])
    rating_parser.add_argument("--page-size", type=int, default=1000)

    batch_parser = subparsers.add_parser("score-batch", help="read score batch")
    batch_parser.add_argument("--okr-id", required=True)

    detail_parser = subparsers.add_parser("score-detail", help="read one objective score")
    detail_parser.add_argument("--objective-id", required=True)
    detail_parser.add_argument("--batch-id", required=True)

    args = parser.parse_args()
    allow_browser = not args.no_browser
    if args.command == "call":
        data = call(args.alias, parse_body(args), allow_browser=allow_browser)
    elif args.command == "rating-list":
        data = get_rating_list(
            args.okr_id,
            user_ids=args.user_id,
            page_size=args.page_size,
            allow_browser=allow_browser,
        )
    elif args.command == "score-batch":
        data = get_score_batch(args.okr_id, allow_browser=allow_browser)
    else:
        data = get_score_detail(
            args.objective_id,
            args.batch_id,
            allow_browser=allow_browser,
        )
    print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
