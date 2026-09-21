#!/usr/bin/env python3
"""Write auditable, read-only USPTO Trademark Search query receipts.

This tool records search results; it does not determine trademark availability,
likelihood of confusion, or legal clearance.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from json import dumps as json_dumps
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ENDPOINT = "https://tmsearch.uspto.gov/prod-stage-v1-0-0/tmsearch"
CONTROL_MARK = "EVOLIA"
CONTROL_REGISTRATION = "7781800"
MULTIWORD_CONTROL_MARK = "STAR TREK"
CLASS_FILTER = '(internationalClass:"IC 009" OR internationalClass:"IC 042")'
PAGE_SIZE = 400
MAX_PAGE_COUNT = 25
MAX_RESULT_COUNT = 10_000
TIMEOUT_SECONDS = 40
MIN_REQUEST_INTERVAL_SECONDS = 0.25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; read-only trademark query receipts)",
    "Content-Type": "application/json",
    "Origin": "https://tmsearch.uspto.gov",
    "Referer": "https://tmsearch.uspto.gov/",
}


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def escape_term(value: str) -> str:
    reserved = set('+-!(){}[]^"~*?:\\/')
    return "".join("\\" + char if char in reserved else char for char in value.strip().upper())


def quoted_wordmark(value: str) -> str:
    return f'wordmark:"{escape_term(value)}"'


def all_class_query(term: str) -> str:
    return quoted_wordmark(term)


def priority_class_query(term: str) -> str:
    return f"{quoted_wordmark(term)} AND {CLASS_FILTER}"


def contains_query(term: str) -> str:
    words = [word for word in term.strip().split() if word]
    if len(words) == 1:
        return f"wordmark:*{escape_term(words[0])}*"
    clauses = " AND ".join(f"wordmark:*{escape_term(word)}*" for word in words)
    return f"({clauses})"


def fuzzy_query(term: str) -> str | None:
    words = [word for word in term.strip().upper().split() if word]
    return f"wordmark:{escape_term(words[0])}~2" if len(words) == 1 else None


def validate_candidate(candidate: object) -> dict:
    if not isinstance(candidate, dict):
        raise ValueError("each candidate must be a JSON object")
    name = candidate.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("each candidate needs a non-empty string name")
    normalized = {"name": name.strip()}
    for field in ("variants", "meanings"):
        values = candidate.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(f"{field} must be a list of non-empty strings")
        normalized[field] = [value.strip() for value in values]
    return normalized


def coverage_for(candidate: dict) -> dict:
    missing = [field for field in ("variants", "meanings") if not candidate[field]]
    return {
        "explicit_variants": "PROVIDED" if candidate["variants"] else "MISSING",
        "explicit_meanings": "PROVIDED" if candidate["meanings"] else "MISSING",
        "coverage_missing": missing,
    }


def _control_for(value: str, builder) -> tuple[str | None, str | None, str | None]:
    word_count = len(value.strip().split())
    if word_count == 1:
        mark, registration = CONTROL_MARK, CONTROL_REGISTRATION
    elif word_count == 2:
        mark, registration = MULTIWORD_CONTROL_MARK, None
    else:
        return None, None, None
    return mark, builder(mark), registration


def _query_entry(channel: str, value: str, query: str | None, scope: str, builder) -> dict:
    control_mark, control_query, control_registration = _control_for(value, builder)
    if channel == "fuzzy" and len(value.strip().split()) != 1:
        query = None
        control_mark, control_query, control_registration = None, None, None
        unsupported_reason = "multiword fuzzy matching is not issued without a validated distinct-token positive control"
    elif control_query is None:
        unsupported_reason = "three-or-more-word query has no verified positive control; candidate request not issued"
    else:
        unsupported_reason = None
    return {
        "channel": channel,
        "term": value,
        "query": query,
        "control_query": control_query,
        "control_mark": control_mark,
        "control_registration": control_registration,
        "supported": query is not None and control_query is not None,
        "unsupported_reason": unsupported_reason,
        "scope": scope,
    }


def build_query_plan(candidate: dict) -> list[dict]:
    candidate = validate_candidate(candidate)
    name = candidate["name"]
    entries = [
        _query_entry("exact", name, priority_class_query(name), "priority_IC_009_042", priority_class_query),
        _query_entry("contain", name, contains_query(name), "all_classes_explicit_components", contains_query),
        _query_entry("fuzzy", name, fuzzy_query(name), "single_word_only", fuzzy_query),
        _query_entry("all_classes_exact", name, all_class_query(name), "all_classes", all_class_query),
    ]

    for variant in candidate["variants"]:
        entries.append(_query_entry(
            "variant_exact", variant, priority_class_query(variant), "priority_IC_009_042_supplementary", priority_class_query,
        ))
        entries.append(_query_entry(
            "variant_all_classes_exact", variant, all_class_query(variant), "all_classes_mandatory", all_class_query,
        ))
        if any(char.isspace() for char in variant) and " ".join(variant.split()).casefold() != " ".join(name.split()).casefold():
            spaced = " ".join(variant.split())
            entries.append(_query_entry(
                "spaced", spaced, all_class_query(spaced), "all_classes_mandatory", all_class_query,
            ))

    for meaning in candidate["meanings"]:
        entries.append(_query_entry(
            "meaning", meaning, contains_query(meaning), "all_classes_explicit_meaning", contains_query,
        ))
    return entries


def _total_and_relation(hits: dict) -> tuple[int | None, str | None]:
    if "totalValue" in hits:
        total = hits.get("totalValue")
        relation = hits.get("totalRelation")
    else:
        total_info = hits.get("total")
        if isinstance(total_info, dict):
            total = total_info.get("value")
            relation = total_info.get("relation")
        else:
            total = total_info
            relation = None
    if isinstance(total, bool) or not isinstance(total, int):
        return None, relation if isinstance(relation, str) else None
    return total, relation if isinstance(relation, str) else None


def _source_from_hit(hit: object) -> dict | None:
    if not isinstance(hit, dict):
        return None
    source = hit.get("source")
    if source is None:
        source = hit.get("_source")
    return source if isinstance(source, dict) else None


def _has_nonblank_string_values(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _normalized_record(source: dict) -> dict:
    record = dict(source)
    alive = source.get("alive")
    record["alive_state"] = "ALIVE" if alive is True else "DEAD" if alive is False else "UNKNOWN"
    serial = source.get("id") or source.get("serialNumber")
    record["serial_number"] = str(serial) if serial is not None else None
    if serial:
        record["tsdr_url"] = (
            "https://tsdr.uspto.gov/#caseNumber=" + str(serial)
            + "&caseSearchType=US_APPLICATION&caseType=DEFAULT&searchType=statusSearch"
        )
    missing = []
    if not isinstance(source.get("wordmark"), str) or not source.get("wordmark", "").strip():
        missing.append("wordmark")
    if serial is None or not str(serial).strip():
        missing.append("serial")
    if not isinstance(alive, bool):
        missing.append("alive")
    if not isinstance(source.get("registered"), bool):
        missing.append("registered")
    for field in ("goodsAndServices", "ownerName", "ownerFullText"):
        if not _has_nonblank_string_values(source.get(field)):
            missing.append(field)
    record["_receipt_validation"] = {"complete": not missing, "missing_fields": missing}
    return record


def parse_response(
    payload: object,
    *,
    http_status: int | None,
    endpoint: str,
    retry_after: str | None = None,
    error: str | None = None,
) -> dict:
    receipt = {
        "endpoint": endpoint,
        "checked_at": stamp(),
        "HTTP": http_status,
        "status": "UNKNOWN",
        "total": None,
        "returned": 0,
    }
    if retry_after is not None:
        receipt["retry_after"] = retry_after
    if error:
        receipt["error"] = error
    if http_status != 200:
        receipt["error"] = receipt.get("error") or (f"HTTP {http_status}" if http_status is not None else "request failed")
        return receipt
    if not isinstance(payload, dict):
        receipt["error"] = receipt.get("error") or "response JSON is not an object"
        return receipt
    hits = payload.get("hits")
    if not isinstance(hits, dict) or not isinstance(hits.get("hits"), list):
        receipt["error"] = "response is missing the expected hits object/list"
        return receipt

    rows = hits["hits"]
    total, relation = _total_and_relation(hits)
    records = []
    invalid_records = []
    for index, hit in enumerate(rows):
        source = _source_from_hit(hit)
        if source is None:
            invalid_records.append({
                "index": index,
                "serial_number": None,
                "missing_fields": ["source"],
            })
            continue
        record = _normalized_record(source)
        records.append(record)
        if not record["_receipt_validation"]["complete"]:
            invalid_records.append({
                "index": index,
                "serial_number": record["serial_number"],
                "missing_fields": record["_receipt_validation"]["missing_fields"],
            })
    receipt.update(total=total, returned=len(rows), records=records)
    if invalid_records or len(records) != len(rows):
        receipt["invalid_records"] = invalid_records
    receipt["total_relation"] = relation
    failed_shards = payload.get("shardsFailed", 0)
    shard_info = payload.get("_shards")
    if isinstance(shard_info, dict):
        failed_shards = shard_info.get("failed", failed_shards)
    if payload.get("timedOut") is True or failed_shards not in (0, None):
        receipt["status"] = "INCOMPLETE"
        receipt["error"] = "search timed out or one or more shards failed"
    elif (
        total is not None
        and relation == "eq"
        and total == len(rows)
        and len(records) == len(rows)
        and not invalid_records
    ):
        receipt["status"] = "COMPLETE"
    else:
        receipt["status"] = "INCOMPLETE"
        receipt["error"] = "result count or required source fields are not proven complete"
    return receipt


class ApiResponse:
    def __init__(self, status_code: int | None, headers: object, body: bytes, error: str | None = None):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.error = error

    def json(self) -> object:
        return json.loads(self.body.decode("utf-8"))


class UrllibSession:
    def post(self, endpoint: str, *, headers: dict, json: dict, timeout: int) -> ApiResponse:
        request = Request(
            endpoint,
            data=json_dumps(json).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            response = urlopen(request, timeout=timeout)
            return ApiResponse(response.status, response.headers, response.read())
        except HTTPError as error:
            return ApiResponse(error.code, error.headers, error.read())
        except (URLError, TimeoutError, OSError) as error:
            return ApiResponse(None, {}, b"", f"{type(error).__name__}: {error}")


def _header(response: object, name: str) -> str | None:
    headers = getattr(response, "headers", {})
    if isinstance(headers, dict):
        value = headers.get(name) or headers.get(name.lower())
    else:
        value = headers.get(name) if hasattr(headers, "get") else None
    return str(value) if value is not None else None


def query_receipt(session: object, query: str, *, endpoint: str = ENDPOINT) -> dict:
    checked_at = stamp()
    receipt = {
        "endpoint": endpoint,
        "checked_at": checked_at,
        "HTTP": None,
        "status": "UNKNOWN",
        "total": None,
        "total_relation": None,
        "returned": 0,
        "unique_records": 0,
        "serial_gaps": 0,
        "records": [],
        "pages": [],
    }
    expected_total = None
    serials = set()
    duplicate_serials = set()
    expected_page_count = None

    for page_index in range(MAX_PAGE_COUNT):
        offset = page_index * PAGE_SIZE
        if page_index:
            _wait_for_next_request()
        page_checked_at = stamp()
        request_payload = {
            "query": {"query_string": {"query": query}},
            "size": PAGE_SIZE,
            "from": offset,
            "sort": [{"id": {"order": "asc"}}],
        }
        try:
            response = session.post(
                endpoint,
                headers=HEADERS,
                json=request_payload,
                timeout=TIMEOUT_SECONDS,
            )
        except (URLError, TimeoutError, OSError) as error:
            page_receipt = parse_response(
                None,
                http_status=None,
                endpoint=endpoint,
                error=f"{type(error).__name__}: {error}",
            )
            page_receipt.update(
                checked_at=page_checked_at,
                page=page_index + 1,
                **{"from": offset},
                size=PAGE_SIZE,
                request_payload=request_payload,
            )
            page_receipt["raw_payload"] = None
            page_receipt["raw_response"] = None
            receipt["pages"].append(page_receipt)
            receipt.update(
                HTTP=None,
                status="UNKNOWN",
                unique_records=len(serials),
                error=page_receipt["error"],
            )
            return receipt

        http_status = getattr(response, "status_code", None)
        retry_after = _header(response, "Retry-After")
        error = getattr(response, "error", None)
        try:
            payload = response.json()
        except (ValueError, TypeError, UnicodeDecodeError) as parse_error:
            payload = None
            error = error or f"invalid JSON response: {parse_error}"

        page_receipt = parse_response(
            payload,
            http_status=http_status,
            endpoint=endpoint,
            retry_after=retry_after,
            error=error,
        )
        page_receipt.update(
            checked_at=page_checked_at,
            page=page_index + 1,
            **{"from": offset},
            size=PAGE_SIZE,
            request_payload=request_payload,
        )
        page_receipt["raw_payload"] = payload
        page_receipt["raw_response"] = None
        body = getattr(response, "body", None)
        if isinstance(body, bytes):
            page_receipt["raw_response"] = body.decode("utf-8", errors="replace")
        elif isinstance(body, str):
            page_receipt["raw_response"] = body
        receipt["pages"].append(page_receipt)

        receipt["HTTP"] = http_status
        if retry_after is not None:
            receipt["retry_after"] = retry_after
        if page_index == 0:
            receipt["raw_payload"] = payload
            if "raw_response" in page_receipt:
                receipt["raw_response"] = page_receipt["raw_response"]

        if http_status != 200:
            receipt.update(status=page_receipt["status"], error=page_receipt.get("error", "request failed"))
            return receipt
        if page_receipt["status"] == "UNKNOWN":
            receipt.update(
                status="UNKNOWN",
                unique_records=len(serials),
                error=page_receipt.get("error", "response could not be parsed"),
            )
            return receipt
        if page_receipt.get("error") == "search timed out or one or more shards failed":
            receipt.update(status="INCOMPLETE", error=page_receipt["error"])
            return receipt

        total = page_receipt.get("total")
        relation = page_receipt.get("total_relation")
        if total is None or relation != "eq":
            receipt.update(
                total=total,
                total_relation=relation,
                status="INCOMPLETE",
                error="result total is not a stable exact count",
            )
            return receipt

        if expected_total is None:
            expected_total = total
            expected_page_count = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
            receipt.update(total=total, total_relation=relation)
            if total > MAX_RESULT_COUNT:
                receipt.update(
                    status="INCOMPLETE",
                    error=f"result total exceeds safe cap of {MAX_RESULT_COUNT}",
                )
                return receipt
            if expected_page_count > MAX_PAGE_COUNT:
                receipt.update(
                    status="INCOMPLETE",
                    error=f"result requires more than {MAX_PAGE_COUNT} pages",
                )
                return receipt
        elif total != expected_total or relation != "eq":
            receipt.update(
                status="INCOMPLETE",
                error=f"result total changed between pages ({expected_total} to {total})",
            )
            return receipt

        hits = payload["hits"]["hits"]
        expected_page_size = min(PAGE_SIZE, expected_total - offset)
        if len(hits) != expected_page_size:
            receipt.update(
                status="INCOMPLETE",
                error=(
                    f"page {page_index + 1} returned {len(hits)} records; "
                    f"expected {expected_page_size} at offset {offset}"
                ),
            )
            return receipt

        page_records = page_receipt.get("records", [])
        page_invalid_records = page_receipt.get("invalid_records", [])
        if page_invalid_records:
            receipt.setdefault("invalid_records", []).extend(
                {
                    **invalid,
                    "page": page_index + 1,
                    "from": offset,
                    "global_index": offset + invalid["index"],
                }
                for invalid in page_invalid_records
            )
            receipt["serial_gaps"] += sum(
                invalid.get("serial_number") is None
                or not str(invalid.get("serial_number")).strip()
                for invalid in page_invalid_records
            )

        receipt["records"].extend(page_records)
        receipt["returned"] += len(hits)
        for record in page_records:
            serial = record.get("serial_number")
            if serial is None or not str(serial).strip():
                continue
            if serial in serials:
                duplicate_serials.add(serial)
            else:
                serials.add(serial)
        receipt["unique_records"] = len(serials)

        if duplicate_serials:
            duplicates = sorted(duplicate_serials)
            receipt["duplicate_serials"] = duplicates
            receipt.update(
                status="INCOMPLETE",
                error="duplicate serial numbers across returned pages: " + ", ".join(duplicates),
            )
            return receipt

        if page_index + 1 == expected_page_count:
            if (
                not receipt.get("invalid_records")
                and receipt["serial_gaps"] == 0
                and len(serials) == expected_total
                and receipt["returned"] == expected_total
            ):
                receipt["status"] = "COMPLETE"
                receipt["unique_records"] = len(serials)
                return receipt
            if receipt.get("invalid_records") or receipt["serial_gaps"]:
                receipt.update(
                    status="INCOMPLETE",
                    error="one or more returned records lack required source fields",
                )
                return receipt
            receipt.update(
                status="INCOMPLETE",
                unique_records=len(serials),
                error=(
                    f"unique record count {len(serials)} does not equal reported total {expected_total}"
                ),
            )
            return receipt

    receipt.update(
        status="INCOMPLETE",
        unique_records=len(serials),
        error=f"pagination exceeded the maximum of {MAX_PAGE_COUNT} pages",
    )
    return receipt


def has_known_positive(receipt: dict, mark: str = CONTROL_MARK, registration: str | None = CONTROL_REGISTRATION) -> bool:
    for record in receipt.get("records", []):
        if (
            str(record.get("wordmark", "")).casefold() == mark.casefold()
            and record.get("alive") is True
            and record.get("registered") is True
            and (str(record.get("registrationId", "")) == registration if registration else bool(record.get("registrationId")))
        ):
            return True
    return False


def unknown_not_queried(query: str | None, *, error: str) -> dict:
    return {
        "endpoint": ENDPOINT,
        "checked_at": stamp(),
        "HTTP": None,
        "status": "UNKNOWN",
        "total": None,
        "total_relation": None,
        "returned": 0,
        "records": [],
        "error": error,
        "query": query,
    }


def run_controlled_query(
    session: object,
    *,
    name: str,
    channel: str,
    query: str,
    control_query: str,
    control_mark: str,
    control_registration: str | None,
) -> dict:
    control = query_receipt(session, control_query)
    control["query"] = control_query
    control["name"] = control_mark
    control["channel"] = channel
    control["known_record_found"] = has_known_positive(control, control_mark, control_registration)
    control["passed"] = control["status"] == "COMPLETE" and control["known_record_found"]

    if control["passed"]:
        receipt = query_receipt(session, query)
    else:
        receipt = unknown_not_queried(query, error="positive control failed; candidate query was not issued")
    receipt.update(name=name, channel=channel, query=query)
    receipt["control"] = control
    receipt["control_passed"] = control["passed"]
    return receipt


def write_json_line(handle, value: dict) -> None:
    handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    handle.flush()


def load_input(path: Path) -> list[dict]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("candidates"), list):
        raise ValueError("input JSON must be an object with a candidates list")
    return [validate_candidate(candidate) for candidate in value["candidates"]]


def _wait_for_next_request() -> None:
    time.sleep(MIN_REQUEST_INTERVAL_SECONDS)


def run_candidates(candidates: list[dict], output) -> int:
    session = UrllibSession()
    first_request = True
    incomplete = not candidates
    for candidate in candidates:
        coverage = coverage_for(candidate)
        incomplete = incomplete or bool(coverage["coverage_missing"])
        for item in build_query_plan(candidate):
            if not item["supported"]:
                incomplete = True
                row = unknown_not_queried(item["query"], error=item["unsupported_reason"])
                row.update(name=candidate["name"], channel=item["channel"])
                row["control"] = {
                    "name": item["control_mark"],
                    "query": item["control_query"],
                    "HTTP": None,
                    "status": "UNKNOWN",
                    "passed": False,
                    "known_record_found": False,
                }
                row["control_passed"] = False
                row["scope"] = item["scope"]
                row["coverage"] = coverage
                row["error"] = item["unsupported_reason"]
                write_json_line(output, row)
                print(f"{candidate['name']} {item['channel']} UNKNOWN candidate query not issued", flush=True)
                continue
            if not first_request:
                _wait_for_next_request()
            first_request = False
            row = run_controlled_query(
                session,
                name=candidate["name"],
                channel=item["channel"],
                query=item["query"],
                control_query=item["control_query"],
                control_mark=item["control_mark"],
                control_registration=item["control_registration"],
            )
            row["scope"] = item["scope"]
            row["coverage"] = coverage
            write_json_line(output, row)
            incomplete = incomplete or row["status"] != "COMPLETE"
            if row.get("HTTP") == 429 or row.get("control", {}).get("HTTP") == 429:
                print(
                    "USPTO returned HTTP 429; stopped without further requests. "
                    f"Honor Retry-After={row.get('retry_after') or row.get('control', {}).get('retry_after')} before a later run.",
                    file=sys.stderr,
                )
                return 2
            print(
                f"{candidate['name']} {item['channel']} {row['status']} "
                f"total={row.get('total')} returned={row.get('returned')} control={row['control']['passed']}",
                flush=True,
            )
    return 2 if incomplete else 0


def run_preflight(output) -> int:
    session = UrllibSession()
    query = all_class_query(CONTROL_MARK)
    receipt = query_receipt(session, query)
    receipt.update(
        name=CONTROL_MARK,
        channel="positive_control_preflight",
        query=query,
        known_record_found=has_known_positive(receipt),
    )
    receipt["passed"] = receipt["status"] == "COMPLETE" and receipt["known_record_found"]
    write_json_line(output, receipt)
    print(
        f"USPTO positive control: {receipt['status']} known_record_found={receipt['known_record_found']}",
        flush=True,
    )
    return 0 if receipt["passed"] else 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="JSON file with a candidates array")
    parser.add_argument("--output", required=True, help="New output path; existing files are never overwritten")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run only the EVOLIA positive control; do not read or query candidates",
    )
    args = parser.parse_args(argv)
    if args.preflight_only and args.input:
        parser.error("--preflight-only cannot be combined with --input")
    if not args.preflight_only and not args.input:
        parser.error("--input is required unless --preflight-only is set")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        candidates = None if args.preflight_only else load_input(Path(args.input))
        with output_path.open("x", encoding="utf-8") as output:
            if args.preflight_only:
                return run_preflight(output)
            return run_candidates(candidates, output)
    except (FileExistsError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"us_trademark_screen: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
