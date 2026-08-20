from __future__ import annotations

import importlib.util
import io
import json
import urllib.error
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "video_transcribe.py"
SPEC = importlib.util.spec_from_file_location("video_transcribe_client", SCRIPT)
assert SPEC and SPEC.loader
video = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(video)


def test_build_payload_preserves_service_contract() -> None:
    assert video.build_payload(
        "https://www.youtube.com/watch?v=abc",
        prefer_subtitles=True,
        langs=["zh.*", "en.*"],
        combine_subtitles=False,
        keep_workdir=False,
    ) == {
        "url": "https://www.youtube.com/watch?v=abc",
        "prefer_subtitles": True,
        "langs": ["zh.*", "en.*"],
        "combine_subtitles": False,
        "keep_workdir": False,
    }


def test_call_transcribe_sends_access_headers(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(
                {
                    "url": "https://www.youtube.com/watch?v=abc",
                    "source": "subtitles",
                    "text": "hello",
                }
            ).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(video.urllib.request, "urlopen", fake_urlopen)

    response = video.call_transcribe(
        base_url="https://video.example",
        auth_headers={"Authorization": "Bearer token"},
        payload={"url": "https://example/video"},
        timeout=30,
    )

    assert captured["url"] == "https://video.example/transcribe"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["headers"]["Content-type"] == "application/json"
    assert "X-API-Key" not in captured["headers"]
    assert captured["payload"] == {"url": "https://example/video"}
    assert captured["timeout"] == 30
    assert response["text"] == "hello"


def test_render_text_requires_text_field() -> None:
    with pytest.raises(ValueError, match="text"):
        video.render({"source": "subtitles"}, "text")


def test_render_json_preserves_full_response() -> None:
    response = {"url": "https://example/video", "source": "funasr", "text": "hi"}

    assert json.loads(video.render(response, "json")) == response


def test_invalid_non_http_video_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="HTTP"):
        video.validate_video_url("file:///tmp/video.mp4")


def test_auth_headers_delegate_to_shared_client(monkeypatch) -> None:
    monkeypatch.setattr(video, "auth_headers", lambda url: {"Authorization": url})

    assert video.resolve_auth_headers("https://video.example") == {
        "Authorization": "https://video.example"
    }


def test_auth_status_and_logout_are_origin_scoped(monkeypatch, capsys) -> None:
    monkeypatch.delenv("CF_ACCESS_CLIENT_ID", raising=False)
    monkeypatch.delenv("CF_ACCESS_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(video, "session_status", lambda url: url == "https://video.example")

    assert (
        video.main(
            ["--base-url", "https://video.example", "--auth-status"]
        )
        == 0
    )
    assert "session active" in capsys.readouterr().out

    monkeypatch.setattr(video, "logout", lambda url: url == "https://video.example")
    assert video.main(["--base-url", "https://video.example", "--logout"]) == 0
    assert "Removed" in capsys.readouterr().out


def test_auth_status_reports_complete_service_token_without_session_lookup(
    monkeypatch, capsys
) -> None:
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "id")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "secret")

    def fail_session_lookup(_url):
        raise AssertionError("session_status must not run in service-token mode")

    monkeypatch.setattr(video, "session_status", fail_session_lookup)

    assert video.main(["--auth-status"]) == 0
    assert "service token configured" in capsys.readouterr().out


def test_auth_status_rejects_partial_service_token(monkeypatch, capsys) -> None:
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "id")
    monkeypatch.delenv("CF_ACCESS_CLIENT_SECRET", raising=False)

    assert video.main(["--auth-status"]) == 1
    assert "Set both CF_ACCESS_CLIENT_ID" in capsys.readouterr().err


def test_http_errors_do_not_echo_authorization_header(monkeypatch) -> None:
    error = urllib.error.HTTPError(
        "https://video.example/transcribe",
        403,
        "Forbidden",
        {},
        io.BytesIO(b"denied"),
    )

    def fail_urlopen(_request, timeout):
        raise error

    monkeypatch.setattr(video.urllib.request, "urlopen", fail_urlopen)

    with pytest.raises(RuntimeError) as caught:
        video.call_transcribe(
            base_url="https://video.example",
            auth_headers={"Authorization": "Bearer secret-value"},
            payload={"url": "https://example/video"},
            timeout=30,
        )

    assert "secret-value" not in str(caught.value)
    assert "HTTP 403" in str(caught.value)


def test_http_errors_redact_auth_value_echoed_by_upstream(monkeypatch) -> None:
    error = urllib.error.HTTPError(
        "https://video.example/transcribe",
        500,
        "Internal Server Error",
        {},
        io.BytesIO(b"debug authorization=Bearer REVIEW_SECRET"),
    )

    def fail_urlopen(_request, timeout):
        raise error

    monkeypatch.setattr(video.urllib.request, "urlopen", fail_urlopen)

    with pytest.raises(RuntimeError) as caught:
        video.call_transcribe(
            base_url="https://video.example",
            auth_headers={"Authorization": "Bearer REVIEW_SECRET"},
            payload={"url": "https://example/video"},
            timeout=30,
        )

    assert "REVIEW_SECRET" not in str(caught.value)
    assert "HTTP 500" in str(caught.value)


def test_cloudflare_1010_is_not_reported_as_bad_login(monkeypatch) -> None:
    error = urllib.error.HTTPError(
        "https://video.example/transcribe",
        403,
        "Forbidden",
        {},
        io.BytesIO(b"error code: 1010"),
    )

    def fail_urlopen(_request, timeout):
        raise error

    monkeypatch.setattr(video.urllib.request, "urlopen", fail_urlopen)

    with pytest.raises(RuntimeError, match="before Access saw"):
        video.call_transcribe(
            base_url="https://video.example",
            auth_headers={"Authorization": "Bearer token"},
            payload={"url": "https://example/video"},
            timeout=30,
        )
