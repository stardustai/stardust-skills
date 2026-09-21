"""Extra pagination integrity checks for the USPTO receipt tool."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "us_trademark_screen.py"
spec = importlib.util.spec_from_file_location("us_pagination_extra", SCRIPT)
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


class Response:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")

    def json(self):
        return json.loads(self.body)


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, endpoint, **kwargs):
        self.calls.append(kwargs["json"])
        return self.response


def test_failed_shards_never_become_complete_even_with_all_hits():
    payload = {
        "hits": {
            "totalValue": 1,
            "totalRelation": "eq",
            "hits": [{"source": source(1)}],
        },
        "_shards": {"failed": 1},
    }
    session = Session(Response(payload))

    result = screen.query_receipt(session, "wordmark:FIXTURE")

    assert result["status"] == "INCOMPLETE"
    assert "shards failed" in result["error"]
    assert len(session.calls) == 1
    assert result["pages"][0]["raw_payload"] == payload
    assert result["pages"][0]["raw_response"] == json.dumps(payload)


def test_result_cap_stops_before_following_pages():
    payload = {
        "hits": {
            "totalValue": 2,
            "totalRelation": "eq",
            "hits": [{"source": source(1)}, {"source": source(2)}],
        }
    }
    session = Session(Response(payload))

    with patch.object(screen, "PAGE_SIZE", 2), patch.object(screen, "MAX_RESULT_COUNT", 1):
        result = screen.query_receipt(session, "wordmark:FIXTURE")

    assert result["status"] == "INCOMPLETE"
    assert "safe cap" in result["error"]
    assert len(session.calls) == 1
    assert session.calls[0]["from"] == 0
