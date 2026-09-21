import csv
import importlib.util
import json
import sys
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests


SCRIPT = Path(__file__).parents[1] / "scripts" / "brand_domain_scan.py"
spec = importlib.util.spec_from_file_location("brand_domain_scan", SCRIPT)
scan = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class Response:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self._payload


class FixtureSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        for key, response in self.responses.items():
            if key in url:
                if isinstance(response, Exception):
                    raise response
                return response
        raise AssertionError(f"unexpected request: {url}")


def bootstrap_payload(*tlds):
    return {"services": [[[tld], [f"https://rdap.{tld}.test/"]] for tld in tlds]}


def test_rdap_404_is_unknown_without_a_positive_registered_control():
    session = FixtureSession({"/domain/novel.ai": Response(404, {"errorCode": 404, "title": "Not Found"})})
    result = scan.probe_domain(
        session,
        "novel.ai",
        "https://rdap.ai.test/",
        timeout=1,
        control_registered=False,
        retries=0,
    )

    assert result.registry_status == "UNKNOWN"
    assert result.http_status == 404
    assert result.error == "control_unverified"


def test_rdap_404_is_no_registry_record_only_after_control_is_registered():
    session = FixtureSession({"/domain/novel.ai": Response(404, {"errorCode": 404, "title": "Not Found"})})
    result = scan.probe_domain(
        session,
        "novel.ai",
        "https://rdap.ai.test/",
        timeout=1,
        control_registered=True,
        retries=0,
    )

    assert result.registry_status == "NO_REGISTRY_RECORD"
    assert result.error == ""
    assert result.raw_response


@pytest.mark.parametrize("payload", [{}, {"errorCode": "404"}, {"errorCode": 500, "title": "bad gateway"}])
def test_rdap_404_requires_a_structured_404_error_body(payload):
    session = FixtureSession({"/domain/novel.ai": Response(404, payload)})
    result = scan.probe_domain(
        session,
        "novel.ai",
        "https://rdap.ai.test/",
        timeout=1,
        control_registered=True,
        retries=0,
    )

    assert result.registry_status == "UNKNOWN"
    assert result.error == "invalid_rdap_not_found"


@pytest.mark.parametrize(
    "payload",
    [
        {"objectClassName": "error", "ldhName": "novel.ai"},
        {"objectClassName": "domain"},
        {"objectClassName": "domain", "ldhName": "other.ai"},
    ],
)
def test_success_http_status_requires_a_valid_registered_domain_object(payload):
    session = FixtureSession({"/domain/novel.ai": Response(200, payload)})
    result = scan.probe_domain(
        session,
        "novel.ai",
        "https://rdap.ai.test/",
        timeout=1,
        control_registered=True,
        retries=0,
    )

    assert result.registry_status == "UNKNOWN"
    assert result.error == "invalid_rdap_domain_object"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Domain not found.\n", 404),
        ("prefix contains domain not found but is not a response\n", None),
        ("Domain Name: other.io\n", None),
        ("Domain Name: google.io\nRegistrar: Example\n", 200),
    ],
)
def test_io_whois_requires_a_well_formed_exact_domain_response(monkeypatch, body, expected):
    monkeypatch.setattr(
        scan.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=body, stderr="", returncode=0),
    )

    code, source = scan.check_via_io_whois("google.io", timeout=1, retries=0)

    assert code == expected
    assert source == "whois://whois.nic.io"


def test_retry_after_is_bounded_and_retryable_errors_remain_query_errors(monkeypatch):
    session = FixtureSession({"/domain/novel.ai": Response(429, headers={"Retry-After": "9999"})})
    waits = []
    monkeypatch.setattr(scan.time, "sleep", waits.append)
    result = scan.probe_domain(
        session,
        "novel.ai",
        "https://rdap.ai.test/",
        timeout=1,
        control_registered=True,
        retries=2,
    )

    assert result.registry_status == "UNKNOWN"
    assert result.error == "http_429_retry_after_exceeds_bound"
    assert len(session.calls) == 1
    assert waits == []


def test_timeout_remains_query_unknown_with_distinct_error():
    session = FixtureSession({"/domain/novel.ai": requests.Timeout("offline")})
    evidence = scan.probe_domain(
        session,
        "novel.ai",
        "https://rdap.ai.test/",
        timeout=1,
        control_registered=True,
        retries=0,
    )

    assert evidence.registry_status == "UNKNOWN"
    assert evidence.error == "timeout"


def test_cache_is_keyed_by_full_domain_and_stale_or_error_records_are_not_reused(tmp_path):
    checked = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    stale = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
    path = tmp_path / "cache.jsonl"
    records = [
        {"domain": "alpha.ai", "registry_status": "REGISTERED", "checked_at": checked, "error": "", "source": "rdap", "raw_response": "{\"objectClassName\":\"domain\",\"ldhName\":\"alpha.ai\"}"},
        {"domain": "alpha.com", "registry_status": "NO_REGISTRY_RECORD", "checked_at": stale, "error": "", "source": "rdap", "control_status": "REGISTERED", "control_domain": "control.com", "raw_response": "{\"errorCode\":404}"},
        {"domain": "beta.ai", "registry_status": "UNKNOWN", "checked_at": checked, "error": "timeout", "raw_response": ""},
    ]
    path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")

    cache = scan.load_jsonl_cache(path, ttl_hours=24)

    assert set(cache) == {"alpha.ai"}
    assert cache["alpha.ai"]["registry_status"] == "REGISTERED"


def test_jsonl_cache_ignores_non_object_records_and_naive_timestamps(tmp_path):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    path = tmp_path / "cache.jsonl"
    path.write_text(
        "null\n[]\n"
        + json.dumps({"domain": "naive.ai", "registry_status": "REGISTERED", "checked_at": now.replace("Z", ""), "raw_response": "{}"})
        + "\n"
        + json.dumps({"domain": "valid.ai", "registry_status": "REGISTERED", "source": "rdap", "checked_at": now, "raw_response": "{\"objectClassName\":\"domain\",\"ldhName\":\"valid.ai\"}"})
        + "\n",
        encoding="utf-8",
    )

    cache = scan.load_jsonl_cache(path, ttl_hours=24)

    assert set(cache) == {"valid.ai"}


def test_legacy_yes_no_csv_is_not_an_availability_cache(tmp_path):
    path = tmp_path / "legacy.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=scan.OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerow({"域名": "Alpha.ai", "是否available": "yes", "分数": "9.0"})

    assert scan.load_legacy_history(path) == {}


def test_candidate_metadata_is_taken_from_current_input_when_domain_evidence_is_cached():
    item = scan.Candidate(
        candidate="Alpha",
        theme="new-theme",
        brand_score_10="",
        what_works="new rationale",
        concern="new concern",
        root_a="new-root",
        root_b="",
        seed_meaning="new meaning",
        generation_priority="8.2",
    )
    row = scan.build_live_row(
        item,
        {"ai": {"registry_status": "NO_REGISTRY_RECORD", "evidence": "cached"}},
        ["ai"],
    )

    assert row["思路"] == "new-theme"
    assert row["分数"] == ""
    assert row["是否available"] == "pending"


def test_tld_and_candidate_inputs_are_normalized_and_deduplicated_without_aliasing_invalid_names():
    assert scan.normalize_tlds([".AI", "ai", " COM "]) == ["ai", "com"]
    with pytest.raises(ValueError):
        scan.normalize_tlds(["..ai"])
    assert scan.normalize_candidate("  Alpha-1 ") == "alpha-1"
    with pytest.raises(ValueError):
        scan.normalize_candidate("Alpha!")


def test_controls_require_registered_control_per_tld_and_bootstrap_failures_are_not_unsupported():
    session = FixtureSession({"dns.json": Response(200, bootstrap_payload("ai"))})
    assert scan.build_bootstrap_index(session, 1) == {"ai": "https://rdap.ai.test/"}

    broken = FixtureSession({"dns.json": requests.Timeout("offline")})
    with pytest.raises(requests.RequestException):
        scan.build_bootstrap_index(broken, 1, retries=0)


@pytest.mark.parametrize(
    ("control_response", "expected_status"),
    [
        (Response(200, {"objectClassName": "domain", "ldhName": "control.ai"}), "pending"),
        (Response(200, {"errorCode": 404, "title": "Domain not found"}), "unknown"),
        (Response(200, {"objectClassName": "domain"}), "unknown"),
        (Response(503), "unknown"),
    ],
)
def test_cli_keeps_ten_csv_columns_and_only_accepts_absence_after_control(
    tmp_path, monkeypatch, control_response, expected_status
):
    responses = {
        "dns.json": Response(200, bootstrap_payload("ai")),
        "/domain/control.ai": control_response,
        "/domain/novel.ai": Response(404, {"errorCode": 404, "title": "Not Found"}),
    }

    class Session(FixtureSession):
        def __init__(self):
            super().__init__(responses)

    monkeypatch.setattr(scan.requests, "Session", Session)
    source = tmp_path / "candidates.csv"
    source.write_text(
        "candidate,theme,brand_score_10,what_works,concern,root_a,root_b,seed_meaning\n"
        "Novel,new-theme,9.5,new rationale,new concern,new-root,,new meaning\n",
        encoding="utf-8",
    )
    output_all = tmp_path / "all.csv"
    output_shortlist = tmp_path / "short.csv"
    evidence_path = tmp_path / "evidence.jsonl"
    cache_path = tmp_path / "cache.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brand_domain_scan.py",
            "--input", str(source),
            "--output-all", str(output_all),
            "--output-shortlist", str(output_shortlist),
            "--output-evidence", str(evidence_path),
            "--cache-jsonl", str(cache_path),
            "--tlds", ".AI,ai",
            "--retries", "0",
            "--controls-json", str(_write_controls(tmp_path)),
        ],
    )

    assert scan.main() == 0

    with output_all.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert len(reader.fieldnames) == 10
        row = next(reader)
    assert row["是否available"] == expected_status
    assert row["思路"] == "new-theme"
    assert row["分数"] == "9.5"
    records = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()]
    candidate_record = next(item for item in records if item["domain"] == "novel.ai")
    assert candidate_record["registry_status"] == ("NO_REGISTRY_RECORD" if expected_status == "pending" else "UNKNOWN")
    if expected_status == "unknown":
        assert candidate_record["error"] == "control_unverified"
        assert not cache_path.exists()
    else:
        assert candidate_record["error"] == ""
        assert "novel.ai" in cache_path.read_text(encoding="utf-8")


def test_cli_rejects_output_collision_before_network_or_writes(tmp_path, monkeypatch):
    source = tmp_path / "candidates.csv"
    source.write_text("candidate\nNovel\n", encoding="utf-8")
    monkeypatch.setattr(scan.requests, "Session", lambda: (_ for _ in ()).throw(AssertionError("network must not start")))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brand_domain_scan.py",
            "--input", str(source),
            "--output-all", str(source),
            "--output-shortlist", str(tmp_path / "short.csv"),
            "--cache-jsonl", str(tmp_path / "cache.jsonl"),
            "--tlds", "ai",
        ],
    )

    with pytest.raises(SystemExit, match="must not overlap"):
        scan.main()
    assert source.read_text(encoding="utf-8") == "candidate\nNovel\n"


def test_cli_reuses_only_complete_cached_receipt_and_preserves_original_time(tmp_path, monkeypatch):
    checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    raw_response = '{"objectClassName":"domain","ldhName":"novel.ai"}'
    cache_path = tmp_path / "cache.jsonl"
    cache_path.write_text(
        json.dumps({
            "domain": "novel.ai",
            "registry_status": "REGISTERED",
            "http_status": 200,
            "source": "rdap",
            "endpoint": "https://rdap.ai.test/domain/novel.ai",
            "checked_at": checked_at,
            "error": "",
            "control_status": "REGISTERED",
            "control_domain": "control.ai",
            "raw_response": raw_response,
        }) + "\n",
        encoding="utf-8",
    )
    call_lists = []
    responses = {
        "dns.json": Response(200, bootstrap_payload("ai")),
        "/domain/control.ai": Response(200, {"objectClassName": "domain", "ldhName": "control.ai"}),
    }

    class Session(FixtureSession):
        def __init__(self):
            super().__init__(responses)
            call_lists.append(self.calls)

    monkeypatch.setattr(scan.requests, "Session", Session)
    source = tmp_path / "candidates.csv"
    source.write_text("candidate,theme\nNovel,current-theme\n", encoding="utf-8")
    output_all = tmp_path / "all.csv"
    evidence_path = tmp_path / "evidence.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brand_domain_scan.py",
            "--input", str(source),
            "--output-all", str(output_all),
            "--output-shortlist", str(tmp_path / "short.csv"),
            "--output-evidence", str(evidence_path),
            "--cache-jsonl", str(cache_path),
            "--tlds", "ai",
            "--retries", "0",
            "--controls-json", str(_write_controls(tmp_path)),
        ],
    )

    assert scan.main() == 0

    requested_urls = [url for calls in call_lists for url, _kwargs in calls]
    assert not any("/domain/novel.ai" in url for url in requested_urls)
    candidate_record = next(
        record for record in map(json.loads, evidence_path.read_text(encoding="utf-8").splitlines())
        if record.get("domain") == "novel.ai"
    )
    assert candidate_record["checked_at"] == checked_at
    assert candidate_record["raw_response"] == raw_response
    assert candidate_record["cache_hit"] is True
    assert len(cache_path.read_text(encoding="utf-8").splitlines()) == 1


def test_cli_rejects_existing_output_before_network_without_overwriting(tmp_path, monkeypatch):
    source = tmp_path / "candidates.csv"
    source.write_text("candidate\nNovel\n", encoding="utf-8")
    existing_output = tmp_path / "all.csv"
    existing_output.write_text("keep\n", encoding="utf-8")
    monkeypatch.setattr(scan.requests, "Session", lambda: (_ for _ in ()).throw(AssertionError("network must not start")))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brand_domain_scan.py",
            "--input", str(source),
            "--output-all", str(existing_output),
            "--output-shortlist", str(tmp_path / "short.csv"),
            "--cache-jsonl", str(tmp_path / "cache.jsonl"),
            "--tlds", "ai",
        ],
    )

    with pytest.raises(SystemExit, match="already exists"):
        scan.main()
    assert existing_output.read_text(encoding="utf-8") == "keep\n"


def test_cli_rejects_cache_alias_to_input_before_network(tmp_path, monkeypatch):
    source = tmp_path / "candidates.csv"
    source.write_text("candidate\nNovel\n", encoding="utf-8")
    monkeypatch.setattr(scan.requests, "Session", lambda: (_ for _ in ()).throw(AssertionError("network must not start")))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "brand_domain_scan.py",
            "--input", str(source),
            "--output-all", str(tmp_path / "all.csv"),
            "--output-shortlist", str(tmp_path / "short.csv"),
            "--cache-jsonl", str(source),
            "--tlds", "ai",
        ],
    )

    with pytest.raises(SystemExit, match="must not overlap"):
        scan.main()


def test_unsupported_tld_produces_explicit_status():
    result = scan.unsupported_result("alpha.xyz", "xyz")
    assert result.registry_status == "UNSUPPORTED"
    assert result.error == "unsupported_tld"


def test_only_successful_bootstrap_absence_is_unsupported_not_network_failure():
    unsupported = scan._probe_one(
        FixtureSession({}),
        "alpha.xyz",
        "xyz",
        {},
        timeout=1,
        retries=0,
        controls={},
        control_status={},
        bootstrap_ok=True,
    )
    unknown = scan._probe_one(
        FixtureSession({}),
        "alpha.ai",
        "ai",
        {},
        timeout=1,
        retries=0,
        controls={},
        control_status={},
        bootstrap_ok=False,
    )

    assert unsupported.registry_status == "UNSUPPORTED"
    assert unsupported.error == "unsupported_tld"
    assert unknown.registry_status == "UNKNOWN"
    assert unknown.error == "bootstrap_unavailable"


def test_check_domain_retains_historic_tuple_contract_and_routes_io_to_whois(monkeypatch):
    called = []

    def whois(domain, timeout, retries=2):
        called.append((domain, timeout, retries))
        return 200, "whois://whois.nic.io"

    monkeypatch.setattr(scan, "check_via_io_whois", whois)
    code, source = scan.check_domain(FixtureSession({}), {}, "alpha", "IO", 1)

    assert (code, source) == (200, "whois://whois.nic.io")
    assert called == [("alpha.io", 1, 2)]


def _write_controls(path):
    controls_path = path / "controls.json"
    controls_path.write_text(json.dumps({"ai": "control.ai"}), encoding="utf-8")
    return controls_path
