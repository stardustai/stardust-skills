import importlib.util
import io
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "us_trademark_screen.py"
spec = importlib.util.spec_from_file_location("us_trademark_screen", SCRIPT)
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


def valid_source(**overrides):
    source = {
        "id": "12345678",
        "wordmark": "EXAMPLE",
        "alive": True,
        "registered": True,
        "goodsAndServices": ["IC 009: Computer software"],
        "ownerName": ["Example Corporation (CORPORATION; USA)"],
        "ownerFullText": ["(APPLICANT) Example Corporation (CORPORATION; USA); Example address"],
    }
    source.update(overrides)
    return source


class TrademarkScreenTests(unittest.TestCase):
    def test_query_plan_uses_only_explicit_variants_and_meanings(self):
        candidate = {
            "name": "Clearpath",
            "variants": ["Clear Path", "CLEARPATH"],
            "meanings": ["context memory"],
        }

        plan = screen.build_query_plan(candidate)
        channels = [item["channel"] for item in plan]

        self.assertEqual(channels[:4], ["exact", "contain", "fuzzy", "all_classes_exact"])
        self.assertIn("spaced", channels)
        self.assertEqual(channels.count("variant_exact"), 2)
        self.assertEqual(channels.count("variant_all_classes_exact"), 2)
        self.assertIn("meaning", channels)
        self.assertTrue(all("assistant" not in item["query"].lower() for item in plan))
        spaced = next(item for item in plan if item["channel"] == "spaced")
        self.assertIn('wordmark:"CLEAR PATH"', spaced["query"])
        self.assertEqual(spaced["control_mark"], "STAR TREK")

    def test_two_word_contains_uses_and_and_verified_distinct_control_terms(self):
        plan = screen.build_query_plan({"name": "Clear Path"})
        contains = next(item for item in plan if item["channel"] == "contain")

        self.assertEqual(contains["query"], "(wordmark:*CLEAR* AND wordmark:*PATH*)")
        self.assertEqual(contains["control_query"], "(wordmark:*STAR* AND wordmark:*TREK*)")
        self.assertEqual(contains["control_mark"], "STAR TREK")
        self.assertTrue(contains["supported"])

    def test_unsupported_word_count_does_not_create_candidate_query(self):
        plan = screen.build_query_plan({"name": "Clear Open Path"})
        contain = next(item for item in plan if item["channel"] == "contain")
        fuzzy = next(item for item in plan if item["channel"] == "fuzzy")

        self.assertFalse(contain["supported"])
        self.assertIsNone(contain["control_query"])
        self.assertIn("no verified positive control", contain["unsupported_reason"])
        self.assertFalse(fuzzy["supported"])
        self.assertIsNone(fuzzy["query"])
        self.assertIn("fuzzy", fuzzy["unsupported_reason"])


    def test_parse_response_preserves_dead_records_and_adds_tsdr_link(self):
        payload = {
            "hits": {
                "totalValue": 2,
                "totalRelation": "eq",
                "hits": [
                    {
                        "_source": {
                            "id": "12345678",
                            "wordmark": "CLEARPATH",
                            "alive": True,
                            "registered": True,
                            "registrationId": "7654321",
                            "goodsAndServices": ["SaaS for business management"],
                            "ownerName": ["Example Corporation (CORPORATION; USA)"],
                            "ownerFullText": ["(REGISTRANT) Example Corporation (CORPORATION; USA); Example address"],
                        }
                    },
                    {
                        "source": {
                            "id": "87654321",
                            "wordmark": "CLEAR PATH",
                            "alive": False,
                            "registered": False,
                            "registrationId": None,
                            "statusDescription": "ABANDONED",
                            "goodsAndServices": ["Downloadable software"],
                            "ownerName": ["Example Holdings LLC (LIMITED LIABILITY COMPANY; USA)"],
                            "ownerFullText": ["(LAST LISTED OWNER) Example Holdings LLC (LIMITED LIABILITY COMPANY; USA); Example address"],
                        }
                    },
                ]
            }
        }

        receipt = screen.parse_response(payload, http_status=200, endpoint="https://example.test")

        self.assertEqual(receipt["status"], "COMPLETE")
        self.assertEqual(receipt["total"], 2)
        self.assertEqual(receipt["returned"], 2)
        self.assertEqual(len(receipt["records"]), 2)
        self.assertIs(receipt["records"][1]["alive"], False)
        self.assertEqual(receipt["records"][1]["alive_state"], "DEAD")
        self.assertTrue(receipt["records"][0]["tsdr_url"].startswith("https://tsdr.uspto.gov/#caseNumber=12345678"))
        self.assertEqual(receipt["records"][1]["goodsAndServices"], ["Downloadable software"])

    def test_empty_source_record_cannot_be_reported_complete(self):
        payload = {
            "hits": {
                "totalValue": 1,
                "totalRelation": "eq",
                "hits": [{"source": {}}],
            }
        }

        receipt = screen.parse_response(payload, http_status=200, endpoint="https://example.test")

        self.assertEqual(receipt["status"], "INCOMPLETE")
        self.assertEqual(receipt["invalid_records"][0]["missing_fields"], [
            "wordmark", "serial", "alive", "registered", "goodsAndServices", "ownerName", "ownerFullText",
        ])

    def test_goods_and_services_must_be_a_nonempty_array_of_nonblank_strings(self):
        invalid_values = {
            "missing": None,
            "empty": [],
            "blank": ["", "   "],
            "malformed_item": ["IC 009: Software", None],
            "non_string_item": ["IC 009: Software", 42],
            "scalar": "IC 009: Software",
        }

        for label, value in invalid_values.items():
            with self.subTest(label=label):
                source = valid_source()
                if label == "missing":
                    del source["goodsAndServices"]
                else:
                    source["goodsAndServices"] = value
                payload = {"hits": {"totalValue": 1, "totalRelation": "eq", "hits": [{"source": source}]}}

                receipt = screen.parse_response(payload, http_status=200, endpoint="https://example.test")

                self.assertEqual(receipt["status"], "INCOMPLETE")
                self.assertIn("goodsAndServices", receipt["invalid_records"][0]["missing_fields"])

    def test_owner_fields_must_be_nonempty_arrays_of_nonblank_strings(self):
        invalid_values = {
            "missing": None,
            "empty": [],
            "blank": ["", "   "],
            "malformed_item": ["Example Corporation", None],
            "non_string_item": ["Example Corporation", 42],
            "scalar": "Example Corporation",
        }

        for field in ("ownerName", "ownerFullText"):
            for label, value in invalid_values.items():
                with self.subTest(field=field, label=label):
                    source = valid_source()
                    if label == "missing":
                        del source[field]
                    else:
                        source[field] = value
                    payload = {"hits": {"totalValue": 1, "totalRelation": "eq", "hits": [{"source": source}]}}

                    receipt = screen.parse_response(payload, http_status=200, endpoint="https://example.test")

                    self.assertEqual(receipt["status"], "INCOMPLETE")
                    self.assertIn(field, receipt["invalid_records"][0]["missing_fields"])

    def test_all_owner_and_goods_service_values_are_preserved(self):
        owners = ["Original Owner Inc. (CORPORATION; USA)", "Current Owner LLC (LIMITED LIABILITY COMPANY; USA)"]
        owner_history = [
            "(ORIGINAL REGISTRANT) Original Owner Inc. (CORPORATION; USA); Original address",
            "(LAST LISTED OWNER) Current Owner LLC (LIMITED LIABILITY COMPANY; USA); Current address",
        ]
        goods = ["IC 009: Software", "IC 042: Software as a service"]
        source = valid_source(ownerName=owners, ownerFullText=owner_history, goodsAndServices=goods)
        payload = {"hits": {"totalValue": 1, "totalRelation": "eq", "hits": [{"source": source}]}}

        receipt = screen.parse_response(payload, http_status=200, endpoint="https://example.test")

        self.assertEqual(receipt["status"], "COMPLETE")
        self.assertEqual(receipt["records"][0]["ownerName"], owners)
        self.assertEqual(receipt["records"][0]["ownerFullText"], owner_history)
        self.assertEqual(receipt["records"][0]["goodsAndServices"], goods)


    def test_parse_response_marks_total_greater_than_returned_incomplete(self):
        payload = {
            "hits": {
                "total": {"value": 401, "relation": "gte"},
                "hits": [{"source": valid_source(id="1", wordmark="EVOLIA")}],
            }
        }

        receipt = screen.parse_response(payload, http_status=200, endpoint="https://example.test")

        self.assertEqual(receipt["status"], "INCOMPLETE")
        self.assertEqual(receipt["total"], 401)
        self.assertEqual(receipt["returned"], 1)


    def test_parse_response_marks_http_429_unknown_and_keeps_retry_after(self):
        receipt = screen.parse_response(
            {"error": "rate limited"},
            http_status=429,
            endpoint="https://example.test",
            retry_after="17",
        )

        self.assertEqual(receipt["status"], "UNKNOWN")
        self.assertEqual(receipt["HTTP"], 429)
        self.assertEqual(receipt["retry_after"], "17")
        self.assertNotIn("records", receipt)

    def test_invalid_json_and_missing_count_relation_are_not_complete(self):
        invalid = screen.parse_response(None, http_status=200, endpoint="https://example.test", error="invalid JSON")
        unproven = screen.parse_response(
            {"hits": {"total": 1, "hits": [{"source": valid_source(id="1", wordmark="X")}]}},
            http_status=200,
            endpoint="https://example.test",
        )

        self.assertEqual(invalid["status"], "UNKNOWN")
        self.assertEqual(unproven["status"], "INCOMPLETE")


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        return self.responses.pop(0)


class ControlledQueryTests(unittest.TestCase):
    def test_unsupported_run_exits_nonzero_and_keeps_unknown_receipts(self):
        output = io.StringIO()
        status = screen.run_candidates([{
            "name": "Clear Open Path", "variants": ["Clearer Open Path"],
            "meanings": ["Wide Open Road"],
        }], output)
        self.assertEqual(status, 2)
        self.assertIn('"status":"UNKNOWN"', output.getvalue())

    def test_query_keeps_raw_body_even_when_json_is_invalid(self):
        response = screen.ApiResponse(403, {"Retry-After": "60"}, b'<html>Access denied</html>')
        result = screen.query_receipt(FakeSession(response), 'wordmark:"EXAMPLE"')
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["raw_response"], '<html>Access denied</html>')

    def test_query_preserves_original_json_envelope(self):
        payload = {"hits": {"totalValue": 0, "totalRelation": "eq", "hits": []}, "diagnostic": "fixture"}
        result = screen.query_receipt(FakeSession(FakeResponse(payload)), 'wordmark:"EXAMPLE"')
        self.assertEqual(result["raw_payload"], payload)

    def test_run_query_requires_positive_complete_control_before_channel(self):
        good = {
            "hits": {
                "totalValue": 1,
                "totalRelation": "eq",
                "hits": [{"source": {
                    "id": "97721070",
                    "wordmark": "EVOLIA",
                    "alive": True,
                    "registered": True,
                    "registrationId": "7781800",
                    "goodsAndServices": ["Software"],
                    "ownerName": ["Example Corporation (CORPORATION; USA)"],
                    "ownerFullText": ["(REGISTRANT) Example Corporation (CORPORATION; USA); Example address"],
                }}],
            }
        }
        session = FakeSession(FakeResponse(good), FakeResponse(good))

        result = screen.run_controlled_query(
            session,
            name="Clearpath",
            channel="exact",
            query='wordmark:"CLEARPATH" AND (internationalClass:"IC 009" OR internationalClass:"IC 042")',
            control_query='wordmark:"EVOLIA" AND (internationalClass:"IC 009" OR internationalClass:"IC 042")',
            control_mark="EVOLIA",
            control_registration="7781800",
        )

        self.assertEqual(result["control"]["status"], "COMPLETE")
        self.assertTrue(result["control"]["known_record_found"])
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["HTTP"], 200)
        self.assertTrue(result["control_passed"])
        self.assertEqual(len(session.calls), 2)

    def test_two_word_control_uses_real_phrase_with_registered_record(self):
        control_source = {
            "id": "97254052",
            "wordmark": "STAR TREK",
            "alive": True,
            "registered": True,
            "registrationId": "7444105",
            "internationalClass": ["IC 042"],
            "goodsAndServices": ["Computer software"],
            "ownerName": ["Example Corporation (CORPORATION; USA)"],
            "ownerFullText": ["(REGISTRANT) Example Corporation (CORPORATION; USA); Example address"],
        }
        payload = {
            "hits": {
                "totalValue": 1,
                "totalRelation": "eq",
                "hits": [{"source": control_source}],
            }
        }
        session = FakeSession(FakeResponse(payload), FakeResponse(payload))

        result = screen.run_controlled_query(
            session,
            name="Clear Path",
            channel="contain",
            query="(wordmark:*CLEAR* AND wordmark:*PATH*)",
            control_query="(wordmark:*STAR* AND wordmark:*TREK*)",
            control_mark="STAR TREK",
            control_registration=None,
        )

        self.assertTrue(result["control"]["known_record_found"])
        self.assertTrue(result["control_passed"])
        self.assertEqual(len(session.calls), 2)

    def test_failed_control_invalidates_candidate_channel_without_candidate_request(self):
        miss = {"hits": {"totalValue": 0, "totalRelation": "eq", "hits": []}}
        session = FakeSession(FakeResponse(miss))

        result = screen.run_controlled_query(
            session,
            name="Clearpath",
            channel="meaning",
            query="wordmark:*CONTEXT*",
            control_query="wordmark:*EVOLIA*",
            control_mark="EVOLIA",
            control_registration="7781800",
        )

        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["control"]["passed"])
        self.assertIn("was not issued", result["error"])
        self.assertEqual(len(session.calls), 1)


if __name__ == "__main__":
    unittest.main()
