"""Offline regressions for the read-only npm text-search receipt helper."""

import importlib.util
import json
from pathlib import Path

import pytest
import requests


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "public_catalog_capture.py"
spec = importlib.util.spec_from_file_location("public_catalog_capture_test", SCRIPT)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def npm_page(names, total):
    return {
        "objects": [{"package": {"name": name, "version": "1.0.0"}} for name in names],
        "total": total,
        "time": "2026-09-14T00:00:00.000Z",
    }


class RawHeaders:
    def __init__(self, pairs):
        self.pairs = list(pairs)

    def iteritems(self):
        return iter(self.pairs)


class Response:
    def __init__(self, status, payload=None, body=None, headers=None):
        self.status_code = status
        self.content = body if body is not None else json.dumps(payload).encode("utf-8")
        self.headers = dict(headers or {"Content-Type": "application/json", "X-Fixture": "kept"})
        self.raw = type("Raw", (), {"headers": RawHeaders(self.headers.items())})()
        self.url = "https://registry.npmjs.org/-/v1/search"

    def json(self):
        return json.loads(self.content)


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("unexpected additional HTTP request")
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def test_first_429_stops_before_any_next_page_or_control(tmp_path):
    session = Session(Response(429, body=b"rate limited", headers={"Retry-After": "0"}))

    receipt = capture.capture_query(session, "Rummage Rocket", tmp_path / "capture", page_size=2)

    assert len(session.calls) == 1
    assert receipt["pagination_status"] == "INCOMPLETE"
    assert receipt["control_status"] == "NOT_RUN"
    page = receipt["pages"][0]
    assert page["http_status"] == 429
    assert (tmp_path / "capture" / page["body_file"]).read_bytes() == b"rate limited"
    header_rows = json.loads((tmp_path / "capture" / page["headers_file"]).read_text())
    assert ["Retry-After", "0"] in header_rows


@pytest.mark.parametrize("status", [302, 403, 429, 500, 503])
def test_non_200_first_page_never_starts_control_or_retry(tmp_path, status):
    session = Session(Response(status, body=b"blocked"))

    receipt = capture.capture_query(session, "exact query", tmp_path / f"capture-{status}")

    assert len(session.calls) == 1
    assert session.calls[0][1]["allow_redirects"] is False
    assert receipt["pagination_status"] == "INCOMPLETE"
    assert receipt["control_status"] == "NOT_RUN"


def test_second_page_failure_stops_before_control_and_keeps_both_raw_receipts(tmp_path):
    first = Response(200, npm_page([f"pkg-{i}" for i in range(100)], 150))
    second = Response(503, body=b"temporarily unavailable")
    session = Session(first, second)

    receipt = capture.capture_query(session, "spaced user query", tmp_path / "capture")

    assert len(session.calls) == 2
    assert [call[1]["params"]["from"] for call in session.calls] == [0, 100]
    assert receipt["pagination_status"] == "INCOMPLETE"
    assert receipt["control_status"] == "NOT_RUN"
    assert len(receipt["pages"]) == 2
    assert (tmp_path / "capture" / receipt["pages"][0]["body_file"]).read_bytes() == first.content
    assert (tmp_path / "capture" / receipt["pages"][1]["body_file"]).read_bytes() == b"temporarily unavailable"


def test_complete_pages_keep_exact_query_raw_bodies_headers_unique_names_and_control(tmp_path):
    first = Response(200, npm_page(["one", "two"], 3), headers={"Content-Type": "application/json", "X-Page": "one"})
    second = Response(200, npm_page(["three"], 3), headers={"Content-Type": "application/json", "X-Page": "two"})
    control = Response(200, npm_page(["react"], 1), headers={"Content-Type": "application/json", "X-Control": "kept"})
    session = Session(first, second, control)
    query = "  Rummage Rocket  "

    receipt = capture.capture_query(
        session,
        query,
        tmp_path / "capture",
        page_size=2,
        max_pages=3,
    )

    assert [call[1]["params"]["text"] for call in session.calls] == [query, query, "react"]
    assert [call[1]["params"]["from"] for call in session.calls] == [0, 2, 0]
    assert receipt["query"] == query
    assert receipt["pagination_status"] == "COMPLETE"
    assert receipt["control_status"] == "MATCHED"
    assert receipt["reported_total"] == receipt["returned_rows"] == receipt["unique_names"] == 3
    assert receipt["package_names"] == ["one", "two", "three"]
    assert len(receipt["pages"]) == 2
    for page, response in zip(receipt["pages"], (first, second)):
        assert (tmp_path / "capture" / page["body_file"]).read_bytes() == response.content
        headers = json.loads((tmp_path / "capture" / page["headers_file"]).read_text())
        assert ["X-Page", "one" if response is first else "two"] in headers
    assert (tmp_path / "capture" / receipt["control"]["body_file"]).read_bytes() == control.content


def test_changing_total_stops_before_another_page_or_control(tmp_path):
    session = Session(
        Response(200, npm_page(["one", "two"], 3)),
        Response(200, npm_page(["three", "four"], 4)),
    )

    receipt = capture.capture_query(session, "query", tmp_path / "capture", page_size=2)

    assert len(session.calls) == 2
    assert receipt["pagination_status"] == "INCOMPLETE"
    assert receipt["control_status"] == "NOT_RUN"
    assert "total" in receipt["error"].lower()


def test_duplicate_names_stop_before_control(tmp_path):
    session = Session(
        Response(200, npm_page(["one", "two"], 4)),
        Response(200, npm_page(["two", "three"], 4)),
    )

    receipt = capture.capture_query(session, "query", tmp_path / "capture", page_size=2)

    assert len(session.calls) == 2
    assert receipt["pagination_status"] == "INCOMPLETE"
    assert receipt["control_status"] == "NOT_RUN"
    assert "duplicate" in receipt["error"].lower()


def test_configured_page_cap_stops_without_running_control(tmp_path):
    session = Session(
        Response(200, npm_page(["one", "two"], 5)),
        Response(200, npm_page(["three", "four"], 5)),
    )

    receipt = capture.capture_query(
        session,
        "query",
        tmp_path / "capture",
        page_size=2,
        max_pages=2,
    )

    assert len(session.calls) == 2
    assert receipt["pagination_status"] == "INCOMPLETE"
    assert receipt["control_status"] == "NOT_RUN"
    assert "cap" in receipt["error"].lower()


def test_existing_output_directory_is_never_overwritten(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("existing user data")
    session = Session(Response(200, npm_page(["react"], 1)))

    with pytest.raises(FileExistsError):
        capture.capture_query(session, "query", output)

    assert session.calls == []
    assert sentinel.read_text() == "existing user data"


def test_candidate_transport_exception_stops_without_control(tmp_path):
    session = Session(requests.ConnectionError("offline fixture"))

    receipt = capture.capture_query(session, "query", tmp_path / "candidate-transport")

    assert len(session.calls) == 1
    assert receipt["pagination_status"] == "UNKNOWN"
    assert receipt["control_status"] == "NOT_RUN"
    assert receipt["pages"][0]["http_status"] is None
    assert "ConnectionError" in receipt["pages"][0]["error"]


def test_control_transport_exception_keeps_candidate_complete_but_incomplete_capture(tmp_path):
    session = Session(
        Response(200, npm_page(["candidate"], 1)),
        requests.Timeout("control timeout fixture"),
    )

    receipt = capture.capture_query(session, "query", tmp_path / "control-transport")

    assert len(session.calls) == 2
    assert receipt["pagination_status"] == "COMPLETE"
    assert receipt["control_status"] == "UNKNOWN"
    assert receipt["capture_status"] == "INCOMPLETE"
    assert receipt["control"] is None


@pytest.mark.parametrize(
    "response",
    [
        Response(200, body=b"{"),
        Response(200, payload=[]),
        Response(200, payload={"total": 1, "objects": {}}),
        Response(200, payload={"total": "1", "objects": []}),
    ],
    ids=["invalid-json", "non-object-json", "objects-not-list", "total-not-integer"],
)
def test_malformed_json_or_wrong_candidate_shape_stops_without_control(tmp_path, response):
    session = Session(response)

    receipt = capture.capture_query(session, "query", tmp_path / "bad-candidate-shape")

    assert len(session.calls) == 1
    assert receipt["pagination_status"] == "INCOMPLETE"
    assert receipt["control_status"] == "NOT_RUN"
    page = receipt["pages"][0]
    assert (tmp_path / "bad-candidate-shape" / page["body_file"]).exists()
    assert (tmp_path / "bad-candidate-shape" / page["headers_file"]).exists()


@pytest.mark.parametrize(
    "names,total",
    [([], 2), (["one"], 3)],
    ids=["empty-page-with-positive-total", "short-page"],
)
def test_empty_or_short_candidate_page_stops_before_control(tmp_path, names, total):
    session = Session(Response(200, npm_page(names, total)))

    receipt = capture.capture_query(
        session,
        "query",
        tmp_path / "short-candidate-page",
        page_size=2,
    )

    assert len(session.calls) == 1
    assert receipt["pagination_status"] == "INCOMPLETE"
    assert receipt["control_status"] == "NOT_RUN"
    assert "returned" in receipt["error"]


def test_non_200_control_is_unknown_and_never_retried(tmp_path):
    session = Session(
        Response(200, npm_page(["candidate"], 1)),
        Response(503, body=b"control unavailable"),
    )

    receipt = capture.capture_query(session, "query", tmp_path / "control-http-failure")

    assert len(session.calls) == 2
    assert receipt["pagination_status"] == "COMPLETE"
    assert receipt["control_status"] == "UNKNOWN"
    assert receipt["capture_status"] == "INCOMPLETE"
    control = receipt["control"]
    assert control["http_status"] == 503
    assert (tmp_path / "control-http-failure" / control["body_file"]).read_bytes() == b"control unavailable"


def test_wrong_control_identity_is_not_accepted(tmp_path):
    session = Session(
        Response(200, npm_page(["candidate"], 1)),
        Response(200, npm_page(["not-react"], 1)),
    )

    receipt = capture.capture_query(session, "query", tmp_path / "control-wrong-identity")

    assert len(session.calls) == 2
    assert receipt["pagination_status"] == "COMPLETE"
    assert receipt["control_status"] == "NOT_CONFIRMED"
    assert receipt["capture_status"] == "INCOMPLETE"


@pytest.mark.parametrize(
    "control_names,control_total",
    [
        (["react"], 0),
        (["react"], 2),
        (["react", "react"], 2),
    ],
    ids=["rows-when-total-zero", "short-control-page", "duplicate-control-names"],
)
def test_control_requires_expected_rows_and_unique_names(tmp_path, control_names, control_total):
    session = Session(
        Response(200, npm_page(["candidate"], 1)),
        Response(200, npm_page(control_names, control_total)),
    )

    receipt = capture.capture_query(session, "query", tmp_path / "bad-control-page", page_size=2)

    assert len(session.calls) == 2
    assert receipt["pagination_status"] == "COMPLETE"
    assert receipt["control_status"] == "UNKNOWN"
    assert receipt["capture_status"] == "INCOMPLETE"
    assert receipt["control"]["reported_total"] == control_total
    assert receipt["control"]["returned_rows"] == len(control_names)
