from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "ocr.py"
SPEC = importlib.util.spec_from_file_location("ocr_skill_client", SCRIPT)
assert SPEC and SPEC.loader
ocr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ocr)


def test_parse_pages_expands_ranges_and_deduplicates() -> None:
    assert ocr.parse_pages("1,3-5,4") == [1, 3, 4, 5]


def test_build_payload_encodes_image(tmp_path: Path) -> None:
    image = tmp_path / "sample.png"
    image.write_bytes(b"png bytes")

    payload = ocr.build_payload(
        [image], model="rapidocr:ch_sim+en", languages=["ch_sim", "en"], page_numbers=None
    )

    assert payload["model"] == "rapidocr:ch_sim+en"
    assert payload["languages"] == ["ch_sim", "en"]
    assert payload["inputs"] == [
        {
            "source_id": "input-1:sample.png",
            "mime_type": "image/png",
            "data_base64": "cG5nIGJ5dGVz",
            "page_numbers": None,
        }
    ]


def test_call_ocr_sends_bearer_without_exposing_it(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps({"object": "list", "model": "m", "data": []}).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)

    result = ocr.call_ocr(
        base_url="https://ocr.example/v1",
        api_key="secret",
        payload={"inputs": []},
        timeout=12,
    )

    assert result["object"] == "list"
    assert captured["url"] == "https://ocr.example/v1/ocr"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["timeout"] == 12


def test_render_markdown_preserves_page_quality_signals() -> None:
    response = {
        "data": [
            {
                "source_id": "input-1:scan.pdf",
                "confidence": 0.91,
                "warnings": ["document warning"],
                "pages": [
                    {
                        "page_number": 2,
                        "text": "识别文本",
                        "confidence": 0.82,
                        "warnings": ["blurred"],
                    }
                ],
            }
        ]
    }

    output = ocr.render_markdown(response)

    assert "# input-1:scan.pdf" in output
    assert "## Page 2" in output
    assert "Confidence: 0.82" in output
    assert "Warnings: blurred" in output
    assert "识别文本" in output
