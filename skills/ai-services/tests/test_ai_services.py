from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "scripts" / "ai_services.py"
SPEC = importlib.util.spec_from_file_location("ai_services_client", SCRIPT)
assert SPEC and SPEC.loader
client = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(client)


class Recorder(BaseHTTPRequestHandler):
    calls: list[dict] = []
    responses: list[tuple[int, bytes, str]] = []

    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        type(self).calls.append(
            {
                "method": self.command,
                "path": self.path,
                "content_type": self.headers.get("Content-Type", ""),
                "body": body,
            }
        )
        status, payload, ctype = type(self).responses.pop(0)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = _handle

    def log_message(self, *args) -> None:  # silence test output
        pass


class PureFunctionTests(unittest.TestCase):
    def test_parse_pages(self):
        self.assertEqual([1, 3, 4, 5], client.parse_pages("1,3-5"))
        self.assertIsNone(client.parse_pages(None))
        for bad in ("0", "5-3", "a"):
            with self.assertRaises(ValueError):
                client.parse_pages(bad)

    def test_tts_text_rules(self):
        self.assertEqual("你好", client.resolve_text("  你好 ", None))
        with self.assertRaisesRegex(ValueError, "3001 characters"):
            client.resolve_text("x" * 3001, None)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            client.resolve_text(None, None)
        with self.assertRaisesRegex(ValueError, "must end in .mp3"):
            client.validate_mp3_path(Path("speech.wav"))

    def test_multipart_carries_fields_and_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scan.png"
            path.write_bytes(b"\x89PNGdata")
            body, ctype = client.encode_multipart({"engine": "qwen"}, "file", path)
        boundary = ctype.split("boundary=")[1]
        self.assertIn(f"--{boundary}--".encode(), body)
        self.assertIn(b'name="engine"\r\n\r\nqwen', body)
        self.assertIn(b'filename="scan.png"', body)
        self.assertIn(b"Content-Type: image/png", body)
        self.assertIn(b"\x89PNGdata", body)

    def test_format_ocr_markdown_lists_pages_and_warnings(self):
        out = client.format_ocr(
            {
                "filename": "d.pdf", "engine": "qwen", "model": "m", "text": "ignored",
                "warnings": ["page 2 returned no text"],
                "pages": [{"page_number": 1, "text": "| a |"}, {"page_number": 2, "text": ""}],
            },
            "markdown",
        )
        self.assertIn("## Page 1", out)
        self.assertIn("| a |", out)
        self.assertIn("> warning: page 2 returned no text", out)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Recorder)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        Recorder.calls = []
        Recorder.responses = []
        patcher = patch.object(client, "auth_headers", return_value={"X-Test-Auth": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = client.main(["--base-url", self.base, *argv])
        return code, out.getvalue(), err.getvalue()

    def test_ocr_posts_engine_and_pages_and_prints_text(self):
        Recorder.responses = [
            (200, json.dumps({"filename": "t.png", "engine": "qwen", "model": "m",
                              "text": "| a | b |"}).encode(), "application/json")
        ]
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "t.png"
            image.write_bytes(b"png")
            code, out, _ = self.run_cli(
                "ocr", str(image), "--engine", "qwen", "--pages", "1,3", "--format", "text"
            )
        self.assertEqual(0, code)
        self.assertEqual("| a | b |\n", out)
        call = Recorder.calls[0]
        self.assertEqual("/ocr", call["path"])
        self.assertIn(b'name="engine"\r\n\r\nqwen', call["body"])
        self.assertIn(b'name="page_numbers"\r\n\r\n1,3', call["body"])

    def test_asr_prints_transcript(self):
        Recorder.responses = [
            (200, json.dumps({"filename": "a.mp3", "model": "m", "text": "你好",
                              "segments": []}).encode(), "application/json")
        ]
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "a.mp3"
            audio.write_bytes(b"ID3")
            code, out, _ = self.run_cli("asr", str(audio), "--language", "zh")
        self.assertEqual((0, "你好\n"), (code, out))
        self.assertIn(b'name="language"\r\n\r\nzh', Recorder.calls[0]["body"])

    def test_tts_writes_mp3_and_sends_json(self):
        Recorder.responses = [(200, b"ID3audio", "audio/mpeg")]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp3"
            code, out, _ = self.run_cli(
                "tts", "你好", "--output", str(target), "--voice", "Serena",
                "--instructions", "温暖",
            )
            self.assertEqual(0, code)
            self.assertEqual(b"ID3audio", target.read_bytes())
        self.assertEqual(
            {"text": "你好", "voice": "Serena", "instructions": "温暖"},
            json.loads(Recorder.calls[0]["body"]),
        )
        self.assertEqual("application/json", Recorder.calls[0]["content_type"])

    def test_tts_retries_once_on_gateway_timeout(self):
        Recorder.responses = [(524, b"timeout", "text/plain"), (200, b"ID3ok", "audio/mpeg")]
        with tempfile.TemporaryDirectory() as directory, patch.object(client.time, "sleep"):
            target = Path(directory) / "out.mp3"
            code, _, _ = self.run_cli("tts", "hi", "--output", str(target))
            self.assertEqual(0, code)
            self.assertEqual(b"ID3ok", target.read_bytes())
        self.assertEqual(2, len(Recorder.calls))

    def test_errors_are_reported_without_traceback(self):
        Recorder.responses = [(502, b'{"detail":"OCR backend: HTTP 503"}', "application/json")]
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "t.png"
            image.write_bytes(b"png")
            code, _, err = self.run_cli("ocr", str(image))
        self.assertEqual(1, code)
        self.assertIn("HTTP 502", err)
        self.assertNotIn("Traceback", err)

    def test_tts_rejects_long_text_before_any_request(self):
        with tempfile.TemporaryDirectory() as directory:
            code, _, err = self.run_cli(
                "tts", "x" * 3001, "--output", str(Path(directory) / "o.mp3")
            )
        self.assertEqual(1, code)
        self.assertIn("3001 characters", err)
        self.assertEqual([], Recorder.calls)

    def test_health(self):
        Recorder.responses = [(200, b'{"status":"ok"}', "application/json")]
        code, out, _ = self.run_cli("health")
        self.assertEqual((0, '{"status":"ok"}\n'), (code, out))
        self.assertEqual("GET", Recorder.calls[0]["method"])


if __name__ == "__main__":
    unittest.main()
