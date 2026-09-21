"""Regression for stable ordering across USPTO offset-paginated pages."""

import importlib.util
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "us_trademark_screen.py"
spec = importlib.util.spec_from_file_location("us_pagination_sort", SCRIPT)
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


def source(serial):
    return {
        "id": str(serial),
        "wordmark": f"FIXTURE {serial}",
        "alive": True,
        "registered": True,
        "registrationId": str(serial),
        "goodsAndServices": ["Software"],
        "ownerName": ["Fixture Corporation (CORPORATION; USA)"],
        "ownerFullText": ["(APPLICANT) Fixture Corporation (CORPORATION; USA); Fixture address"],
    }


def page(serials, total):
    return {
        "hits": {
            "totalValue": total,
            "totalRelation": "eq",
            "hits": [{"source": source(serial)} for serial in serials],
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


def test_each_offset_page_uses_the_same_ascending_serial_sort():
    session = Session(Response(page([1, 2], 3)), Response(page([3], 3)))

    with patch.object(screen, "PAGE_SIZE", 2):
        result = screen.query_receipt(session, "wordmark:FIXTURE")

    assert result["status"] == "COMPLETE"
    assert [call["from"] for call in session.calls] == [0, 2]
    assert [call.get("sort") for call in session.calls] == [
        [{"id": {"order": "asc"}}],
        [{"id": {"order": "asc"}}],
    ]
    assert [page["request_payload"] for page in result["pages"]] == session.calls
