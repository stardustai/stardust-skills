from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "synthesize.py"
SPEC = importlib.util.spec_from_file_location("stardust_tts_client", SCRIPT)
assert SPEC and SPEC.loader
tts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tts)

AUTH_SCRIPT = Path(__file__).parents[3] / "lib" / "stardust_access" / "access_oauth.py"
AUTH_SPEC = importlib.util.spec_from_file_location("stardust_tts_access", AUTH_SCRIPT)
assert AUTH_SPEC and AUTH_SPEC.loader
access = importlib.util.module_from_spec(AUTH_SPEC)
AUTH_SPEC.loader.exec_module(access)


def _jwt(exp: float) -> str:
    import base64

    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": exp}).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"header.{payload}.signature"


class InputValidationTests(unittest.TestCase):
    def test_resolve_text_accepts_file_and_enforces_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text("  多行语音文本  ", encoding="utf-8")
            self.assertEqual("多行语音文本", tts.resolve_text(None, path))

        with self.assertRaisesRegex(ValueError, "3001 characters"):
            tts.resolve_text("x" * 3001, None)

    def test_output_must_be_mp3(self):
        with self.assertRaisesRegex(ValueError, "must end in .mp3"):
            tts.validate_output_path(Path("speech.wav"))

    def test_payload_uses_fixed_model_mp3_and_instructions(self):
        payload = tts.build_payload(
            "你好",
            voice="Vivian",
            instructions=" 温暖、自然 ",
        )
        self.assertEqual("qwen3-tts-1.7b-customvoice", payload["model"])
        self.assertEqual("Vivian", payload["voice"])
        self.assertEqual("mp3", payload["response_format"])
        self.assertEqual("温暖、自然", payload["instructions"])

    def test_payload_rejects_unknown_voice(self):
        with self.assertRaisesRegex(ValueError, "Unsupported voice"):
            tts.build_payload("hello", voice="unknown", instructions=None)

    def test_default_endpoint_is_the_access_protected_tts_api(self):
        self.assertEqual("https://tts-api.preseen.ai/v1", tts.DEFAULT_BASE_URL)

    def test_auth_headers_use_service_token_only_when_pair_is_complete(self):
        with patch.dict(
            tts.os.environ,
            {
                "CF_ACCESS_CLIENT_ID": "service-id",
                "CF_ACCESS_CLIENT_SECRET": "service-secret",
            },
            clear=True,
        ):
            self.assertEqual(
                {
                    "CF-Access-Client-Id": "service-id",
                    "CF-Access-Client-Secret": "service-secret",
                },
                tts.resolve_auth_headers("https://tts-api.preseen.ai/v1"),
            )

        with patch.dict(
            tts.os.environ,
            {"CF_ACCESS_CLIENT_ID": "service-id"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "both"):
                tts.resolve_auth_headers("https://tts-api.preseen.ai/v1")


class AccessOAuthTests(unittest.TestCase):
    """The skill runs the browser login itself; nothing else is installed."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self._token_file = Path(self._dir.name) / "oauth.json"
        patcher = patch.dict(
            access.os.environ,
            {"STARDUST_TTS_TOKEN_FILE": str(self._token_file)},
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_origin_is_derived_from_the_api_base_url(self):
        self.assertEqual(
            "https://tts-api.preseen.ai",
            access._origin("https://tts-api.preseen.ai/v1"),
        )

    def test_generic_token_file_override_precedes_legacy_override(self):
        with patch.dict(
            access.os.environ,
            {
                "STARDUST_ACCESS_TOKEN_FILE": "/tmp/generic.json",
                "STARDUST_TTS_TOKEN_FILE": "/tmp/legacy.json",
            },
            clear=True,
        ):
            self.assertEqual(Path("/tmp/generic.json"), access.token_path())

    def test_legacy_tts_token_file_override_remains_supported(self):
        with patch.dict(
            access.os.environ,
            {"STARDUST_TTS_TOKEN_FILE": "/tmp/legacy.json"},
            clear=True,
        ):
            self.assertEqual(Path("/tmp/legacy.json"), access.token_path())

    def test_shared_client_identity_is_service_neutral(self):
        self.assertEqual("stardust-access-client/1.0", access.USER_AGENT)
        self.assertEqual("Stardust Service Access", access.CLIENT_NAME)

    def test_missing_protected_resource_metadata_identifies_server_prerequisite(self):
        with patch.object(
            access,
            "request_json",
            side_effect=RuntimeError("OAuth endpoint returned HTTP 404"),
        ):
            with self.assertRaisesRegex(RuntimeError, "service-side Access"):
                access.discover("https://ocr.example/v1")

    def test_refresh_token_round_trips_and_is_owner_only(self):
        import os as _os
        import stat as _stat

        access.store_record({"client_id": "c", "refresh_token": "r"})
        self.assertEqual(
            {"client_id": "c", "refresh_token": "r"}, access.load_record()
        )
        mode = _stat.S_IMODE(_os.stat(self._token_file).st_mode)
        self.assertEqual(0o600, mode)

    def test_session_status_is_a_bool_so_the_exit_code_is_right(self):
        # It feeds `return 0 if active else 1`; a message string is always
        # truthy and would report "signed in" forever.
        self.assertIs(False, access.session_status("https://tts-api.preseen.ai/v1"))
        access.store_record({"client_id": "c", "refresh_token": "r"})
        self.assertIs(True, access.session_status("https://tts-api.preseen.ai/v1"))

    def test_logout_is_idempotent_and_account_scoped(self):
        access.store_record({"client_id": "c", "refresh_token": "r"})
        access.store_record(
            {"client_id": "o", "refresh_token": "r2"}, "https://other.example"
        )
        self.assertTrue(access.logout("https://tts-api.preseen.ai/v1"))
        self.assertFalse(access.logout("https://tts-api.preseen.ai/v1"))
        self.assertIsNotNone(access.load_record("https://other.example"))

    def test_corrupt_credential_file_says_what_to_do(self):
        self._token_file.write_text("{ not json", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "sign in again"):
            access.load_record()

    def test_pkce_challenge_is_sha256_of_the_verifier(self):
        import base64 as _b64
        import hashlib as _hashlib

        verifier, challenge = access._pkce()
        expected = (
            _b64.urlsafe_b64encode(_hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        self.assertEqual(expected, challenge)
        self.assertNotEqual(verifier, challenge)

    def test_service_token_env_bypasses_the_browser_entirely(self):
        with patch.dict(
            access.os.environ,
            {"CF_ACCESS_CLIENT_ID": "id", "CF_ACCESS_CLIENT_SECRET": "secret"},
        ):
            with patch.object(access, "oauth_access_token") as never:
                headers = access.auth_headers("https://tts-api.preseen.ai/v1")
        never.assert_not_called()
        self.assertEqual("id", headers["CF-Access-Client-Id"])
        self.assertEqual("secret", headers["CF-Access-Client-Secret"])

    def test_employee_headers_carry_a_bearer_access_token(self):
        with patch.dict(access.os.environ, {}, clear=False):
            access.os.environ.pop("CF_ACCESS_CLIENT_ID", None)
            access.os.environ.pop("CF_ACCESS_CLIENT_SECRET", None)
            with patch.object(access, "oauth_access_token", return_value="tok"):
                headers = access.auth_headers("https://tts-api.preseen.ai/v1")
        self.assertEqual("Bearer tok", headers["Authorization"])

    def test_a_stored_refresh_token_is_reused_instead_of_a_new_login(self):
        access.store_record({"client_id": "c", "refresh_token": "r"})
        metadata = {
            "token_endpoint": "https://issuer.example/token",
            "resource": "https://tts-api.preseen.ai",
        }
        with patch.object(access, "discover", return_value=metadata), patch.object(
            access, "_refresh", return_value={"access_token": "new", "refresh_token": "r2"}
        ), patch.object(access, "_interactive_tokens") as browser:
            token = access.oauth_access_token("https://tts-api.preseen.ai/v1")
        browser.assert_not_called()
        self.assertEqual("new", token)
        self.assertEqual("r2", access.load_record()["refresh_token"])

    def test_a_rejected_refresh_falls_back_to_the_browser(self):
        access.store_record({"client_id": "c", "refresh_token": "expired"})
        metadata = {
            "token_endpoint": "https://issuer.example/token",
            "resource": "https://tts-api.preseen.ai",
        }
        with patch.object(access, "discover", return_value=metadata), patch.object(
            access, "_refresh", side_effect=RuntimeError("invalid_grant")
        ), patch.object(
            access,
            "_interactive_tokens",
            return_value=("c2", {"access_token": "a", "refresh_token": "r3"}),
        ) as browser:
            token = access.oauth_access_token("https://tts-api.preseen.ai/v1")
        browser.assert_called_once()
        self.assertEqual("a", token)
        self.assertEqual("c2", access.load_record()["client_id"])


class SharedAcrossSkillsTests(unittest.TestCase):
    """One client, one credential file, many Access-protected services."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        patcher = patch.dict(
            access.os.environ,
            {"STARDUST_TTS_TOKEN_FILE": str(Path(self._dir.name) / "oauth.json")},
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_every_entry_point_takes_a_base_url(self):
        # This is what makes the client reusable: nothing is hard-coded to TTS.
        import inspect

        for fn in (access.auth_headers, access.oauth_access_token,
                   access.session_status, access.logout):
            self.assertIn(
                "base_url", inspect.signature(fn).parameters, f"{fn.__name__}"
            )

    def test_two_services_keep_separate_credentials_in_one_file(self):
        tts = "https://tts-api.preseen.ai/v1"
        ocr = "https://ocr-api.preseen.ai/v1"
        access.store_record({"client_id": "t", "refresh_token": "rt"}, access._origin(tts))
        access.store_record({"client_id": "o", "refresh_token": "ro"}, access._origin(ocr))

        self.assertTrue(access.session_status(tts))
        self.assertTrue(access.session_status(ocr))
        self.assertEqual("t", access.load_record(access._origin(tts))["client_id"])
        self.assertEqual("o", access.load_record(access._origin(ocr))["client_id"])

    def test_signing_out_of_one_service_leaves_the_other_signed_in(self):
        tts = "https://tts-api.preseen.ai/v1"
        ocr = "https://ocr-api.preseen.ai/v1"
        access.store_record({"client_id": "t", "refresh_token": "rt"}, access._origin(tts))
        access.store_record({"client_id": "o", "refresh_token": "ro"}, access._origin(ocr))

        self.assertTrue(access.logout(tts))
        self.assertFalse(access.session_status(tts))
        self.assertTrue(access.session_status(ocr))


class ServiceClientTests(unittest.TestCase):
    def test_call_speech_sends_auth_headers_and_requires_real_mp3(self):
        captured = {}

        class Response:
            headers = {"Content-Type": "audio/mpeg"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return b"ID3\x04\x00\x00test-mp3"

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data)
            captured["timeout"] = timeout
            return Response()

        with patch.object(tts.urllib.request, "urlopen", fake_urlopen):
            result = tts.call_speech(
                base_url="https://tts.example/v1",
                auth_headers={"Authorization": "Bearer opaque-token"},
                payload={"response_format": "mp3"},
                timeout=12,
            )

        self.assertTrue(tts.is_mp3(result))
        self.assertEqual("https://tts.example/v1/audio/speech", captured["url"])
        self.assertEqual("Bearer opaque-token", captured["headers"]["Authorization"])
        self.assertEqual("mp3", captured["payload"]["response_format"])
        self.assertEqual(12, captured["timeout"])

    def test_call_speech_rejects_mislabeled_wav(self):
        class Response:
            headers = {"Content-Type": "audio/mpeg"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return b"RIFF-not-mp3"

        with patch.object(tts.urllib.request, "urlopen", return_value=Response()):
            with self.assertRaisesRegex(RuntimeError, "bytes are not MP3"):
                tts.call_speech(
                    base_url="https://tts.example/v1",
                    auth_headers={"Authorization": "Bearer opaque-token"},
                    payload={"response_format": "mp3"},
                    timeout=12,
                )

    def test_write_mp3_replaces_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "speech.mp3"
            output.write_bytes(b"old")
            tts.write_mp3(output, b"ID3-new")
            self.assertEqual(b"ID3-new", output.read_bytes())


if __name__ == "__main__":
    unittest.main()
