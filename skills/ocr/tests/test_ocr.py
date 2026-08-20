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


def test_call_ocr_sends_shared_access_headers(monkeypatch) -> None:
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
        auth_headers={"Authorization": "Bearer access-token"},
        payload={"inputs": []},
        timeout=12,
    )

    assert result["object"] == "list"
    assert captured["url"] == "https://ocr.example/v1/ocr"
    assert captured["headers"]["Authorization"] == "Bearer access-token"
    assert "X-API-Key" not in captured["headers"]
    assert captured["timeout"] == 12


def test_resolve_auth_headers_delegates_to_shared_client(monkeypatch) -> None:
    monkeypatch.setattr(ocr, "auth_headers", lambda url: {"Authorization": url})

    assert ocr.resolve_auth_headers("https://ocr.example/v1") == {
        "Authorization": "https://ocr.example/v1"
    }


def test_auth_status_and_logout_are_origin_scoped(monkeypatch, capsys) -> None:
    monkeypatch.delenv("CF_ACCESS_CLIENT_ID", raising=False)
    monkeypatch.delenv("CF_ACCESS_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(ocr, "session_status", lambda url: url.endswith("/v1"))

    assert (
        ocr.main(
            ["--base-url", "https://ocr.example/v1", "--auth-status"]
        )
        == 0
    )
    assert "session active" in capsys.readouterr().out

    monkeypatch.setattr(ocr, "logout", lambda url: url.endswith("/v1"))
    assert ocr.main(["--base-url", "https://ocr.example/v1", "--logout"]) == 0
    assert "Removed" in capsys.readouterr().out


def test_auth_status_reports_complete_service_token_without_session_lookup(
    monkeypatch, capsys
) -> None:
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "id")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "secret")

    def fail_session_lookup(_url):
        raise AssertionError("session_status must not run in service-token mode")

    monkeypatch.setattr(ocr, "session_status", fail_session_lookup)

    assert ocr.main(["--auth-status"]) == 0
    assert "service token configured" in capsys.readouterr().out


def test_auth_status_rejects_partial_service_token(monkeypatch, capsys) -> None:
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "id")
    monkeypatch.delenv("CF_ACCESS_CLIENT_SECRET", raising=False)

    assert ocr.main(["--auth-status"]) == 1
    assert "Set both CF_ACCESS_CLIENT_ID" in capsys.readouterr().err


def test_legacy_ocr_api_key_resolution_is_absent() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "DOCUMENT_OCR_API_KEY" not in source
    assert 'profile.get("api_key")' not in source


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
