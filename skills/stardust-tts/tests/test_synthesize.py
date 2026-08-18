from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "synthesize.py"
SPEC = importlib.util.spec_from_file_location("stardust_tts_client", SCRIPT)
assert SPEC and SPEC.loader
tts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tts)


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

    def test_credentials_require_dedicated_tts_key(self):
        with patch.dict(
            tts.os.environ,
            {"LITELLM_API_KEY": "broad-key"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "STARDUST_TTS_API_KEY"):
                tts.resolve_api_key()

        with patch.dict(
            tts.os.environ,
            {
                "STARDUST_TTS_API_KEY": "scoped-key",
                "LITELLM_API_KEY": "broad-key",
            },
            clear=True,
        ):
            self.assertEqual("scoped-key", tts.resolve_api_key())


class ServiceClientTests(unittest.TestCase):
    def test_call_speech_sends_bearer_and_requires_real_mp3(self):
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
                api_key="secret-value",
                payload={"response_format": "mp3"},
                timeout=12,
            )

        self.assertTrue(tts.is_mp3(result))
        self.assertEqual("https://tts.example/v1/audio/speech", captured["url"])
        self.assertEqual("Bearer secret-value", captured["headers"]["Authorization"])
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
                    api_key="secret-value",
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
