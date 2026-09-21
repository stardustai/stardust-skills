"""Metadata gaps must stay incomplete without hiding later paged evidence."""

import importlib.util
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "us_trademark_screen.py"
spec = importlib.util.spec_from_file_location("us_pagination_metadata", SCRIPT)
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


def source(serial=None, *, wordmark=True):
    record = {
        "alive": True,
        "registered": True,
        "registrationId": str(serial) if serial is not None else None,
        "goodsAndServices": ["Software"],
        "ownerName": ["Fixture Corporation (CORPORATION; USA)"],
        "ownerFullText": ["(APPLICANT) Fixture Corporation (CORPORATION; USA); Fixture address"],
    }
    if serial is not None:
        record["id"] = str(serial)
    if wordmark:
        record["wordmark"] = f"FIXTURE {serial}"
    return record


def page(records, total):
    return {
        "hits": {
            "totalValue": total,
            "totalRelation": "eq",
            "hits": [{"source": record} for record in records],
        }
    }


class Response:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, endpoint, **kwargs):
        self.calls.append(kwargs["json"])
        return self.responses.pop(0)


def test_missing_wordmark_keeps_three_pages_and_marks_record_gap_incomplete():
    session = Session(
        Response(page([source(1), source(2)], 5)),
        Response(page([source(3, wordmark=False), source(4)], 5)),
        Response(page([source(5)], 5)),
    )

    with patch.object(screen, "PAGE_SIZE", 2):
        result = screen.query_receipt(session, "wordmark:FIXTURE")

    assert result["status"] == "INCOMPLETE"
    assert len(session.calls) == len(result["pages"]) == 3
    assert result["returned"] == result["total"] == 5
    assert result["unique_records"] == 5
    assert len(result["records"]) == 5
    assert result["pages"][1]["invalid_records"] == [
        {"index": 0, "serial_number": "3", "missing_fields": ["wordmark"]},
    ]


def test_missing_serial_does_not_become_a_duplicate_none_or_fake_unique():
    session = Session(
        Response(page([source(1), source(wordmark=True)], 4)),
        Response(page([source("   "), source(3)], 4)),
    )

    with patch.object(screen, "PAGE_SIZE", 2):
        result = screen.query_receipt(session, "wordmark:FIXTURE")

    assert result["status"] == "INCOMPLETE"
    assert len(session.calls) == len(result["pages"]) == 2
    assert result["returned"] == result["total"] == 4
    assert result["unique_records"] == 2
    assert result["serial_gaps"] == 2
    assert "duplicate_serials" not in result
    assert result["pages"][0]["invalid_records"] == [
        {"index": 1, "serial_number": None, "missing_fields": ["serial"]},
    ]
    assert result["pages"][1]["invalid_records"] == [
        {"index": 0, "serial_number": "   ", "missing_fields": ["serial"]},
    ]
