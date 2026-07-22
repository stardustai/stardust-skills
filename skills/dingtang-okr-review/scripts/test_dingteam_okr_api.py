#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


PATH = Path(__file__).resolve().parent / "dingteam_okr_api.py"
SPEC = importlib.util.spec_from_file_location("dingteam_okr_api_under_test", PATH)
api = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(api)


class DingteamOkrApiTest(unittest.TestCase):
    def test_rating_list_body_is_parameterized(self) -> None:
        body = api.rating_list_body("period-1", user_ids=["user-1"], page_size=37)
        self.assertEqual(body["okrId"], "period-1")
        self.assertEqual(body["userIds"], ["user-1"])
        self.assertEqual(body["pageSize"], 37)
        self.assertEqual(body["reportType"], "rating")

    def test_get_rating_list_rejects_unread_pages(self) -> None:
        with patch.object(api, "call", return_value={"list": [], "totalPages": 2}):
            with self.assertRaisesRegex(RuntimeError, "increase --page-size"):
                api.get_rating_list("period-1", allow_browser=False)

    def test_resolve_score_batch_prefers_current(self) -> None:
        cells = [
            {"batchId": "old", "isCurrent": False},
            {"batchId": "current", "isCurrent": True},
        ]
        with patch.object(api, "get_score_batch", return_value={"cells": cells}):
            self.assertEqual(api.resolve_score_batch_id("period-1"), "current")

    def test_read_client_reuses_headers(self) -> None:
        with (
            patch.object(api.browser, "get_headers", return_value={"Authorization": "secret"}) as headers,
            patch.object(api.direct, "_post", return_value={"data": {"value": 1}}),
            patch.object(api.direct, "_unwrap", side_effect=lambda payload: payload["data"]),
        ):
            client = api.ReadClient(allow_browser=False)
            client.call("period.list", {})
            client.call("score.batch", {})
        headers.assert_called_once_with(allow_browser=False)


if __name__ == "__main__":
    unittest.main()
