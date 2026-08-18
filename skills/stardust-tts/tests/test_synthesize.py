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

AUTH_SCRIPT = Path(__file__).parents[1] / "scripts" / "access_oauth.py"
AUTH_SPEC = importlib.util.spec_from_file_location("stardust_tts_oauth", AUTH_SCRIPT)
assert AUTH_SPEC and AUTH_SPEC.loader
oauth = importlib.util.module_from_spec(AUTH_SPEC)
AUTH_SPEC.loader.exec_module(oauth)


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


class OAuthTests(unittest.TestCase):
    def test_keychain_secret_is_sent_on_stdin_not_argv(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0, stdout="")

        with patch.object(oauth.platform, "system", return_value="Darwin"), patch.object(
            oauth.subprocess, "run", side_effect=fake_run
        ):
            oauth.keychain_store({"client_id": "public-id", "refresh_token": "secret"})

        argv, options = calls[0]
        self.assertNotIn("secret", " ".join(argv))
        self.assertIn("secret", options["input"])

    def test_non_macos_has_no_plaintext_token_fallback(self):
        with patch.object(oauth.platform, "system", return_value="Linux"):
            with self.assertRaisesRegex(RuntimeError, "macOS Keychain"):
                oauth.keychain_store({"refresh_token": "secret"})

    def test_discovery_follows_protected_resource_to_authorization_server(self):
        responses = {
            "https://tts-api.preseen.ai/.well-known/cloudflare-access-protected-resource/": {
                "resource": "https://tts-api.preseen.ai",
                "authorization_servers": ["https://stardust.cloudflareaccess.com"],
            },
            "https://stardust.cloudflareaccess.com/.well-known/oauth-authorization-server": {
                "authorization_endpoint": "https://stardust.cloudflareaccess.com/authorize",
                "token_endpoint": "https://stardust.cloudflareaccess.com/token",
                "registration_endpoint": "https://stardust.cloudflareaccess.com/register",
            },
        }
        with patch.object(oauth, "request_json", side_effect=lambda url, **_: responses[url]):
            metadata = oauth.discover("https://tts-api.preseen.ai/v1")

        self.assertEqual("https://tts-api.preseen.ai", metadata["resource"])
        self.assertEqual(
            "https://stardust.cloudflareaccess.com/register",
            metadata["registration_endpoint"],
        )


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
