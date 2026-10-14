import base64

from fastapi.testclient import TestClient

from ai_services import app as app_module
from ai_services.app import app, streamable_mcp
from ai_services.config import Settings, get_settings
from ai_services.schemas import AsrResponse, OcrResponse


def override_settings():
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)


def test_health_lists_all_backends():
    override_settings()
    try:
        body = TestClient(app).get("/health").json()
    finally:
        app.dependency_overrides.clear()
    assert body["status"] == "ok"
    assert set(body["backends"]) == {"ocr", "asr", "tts"}


def test_ocr_endpoint(monkeypatch):
    seen = {}

    def fake(filename, data, settings, **kwargs):
        seen.update(filename=filename, data=data, **kwargs)
        return OcrResponse(filename=filename, model="m", text="t")

    override_settings()
    monkeypatch.setattr(app_module, "run_ocr", fake)
    try:
        response = TestClient(app).post(
            "/ocr",
            files={"file": ("a.png", b"png", "image/png")},
            data={"page_numbers": "1, 3", "languages": "en", "engine": "qwen"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200 and response.json()["text"] == "t"
    assert seen["page_numbers"] == [1, 3] and seen["languages"] == ["en"]
    assert seen["engine"] == "qwen"


def test_asr_endpoint_maps_backend_error(monkeypatch):
    from ai_services.backends import BackendError

    def fake(*args, **kwargs):
        raise BackendError("ASR", "HTTP 503: down", 503)

    override_settings()
    monkeypatch.setattr(app_module, "run_asr", fake)
    try:
        response = TestClient(app).post("/asr", files={"file": ("a.mp3", b"x")})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502 and "ASR backend" in response.json()["detail"]


def test_tts_endpoint_returns_audio(monkeypatch):
    from ai_services.schemas import TtsResponse

    def fake(request, settings):
        return b"AUDIO", TtsResponse(
            model="m", voice="Vivian", format="mp3", media_type="audio/mpeg",
            size_bytes=5, audio_base64=""
        )

    override_settings()
    monkeypatch.setattr(app_module, "run_tts", fake)
    try:
        response = TestClient(app).post("/tts", json={"text": "hi"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.content == b"AUDIO" and response.headers["content-type"] == "audio/mpeg"


def test_tts_rejects_empty_text():
    assert TestClient(app).post("/tts", json={"text": ""}).status_code == 422
    assert TestClient(app).post("/tts", json={"text": "x" * 3001}).status_code == 422


def test_mcp_tools_and_calls(monkeypatch):
    import asyncio

    assert streamable_mcp is not None
    tools = asyncio.run(streamable_mcp.list_tools())
    assert {t.name for t in tools} == {
        "health", "ocr_document", "transcribe_audio", "synthesize_speech"
    }

    monkeypatch.setattr(
        app_module, "run_asr",
        lambda filename, data, settings, **kw: AsrResponse(
            filename=filename, model="m", text=data.decode()
        ),
    )
    _, structured = asyncio.run(
        streamable_mcp.call_tool(
            "transcribe_audio",
            {"filename": "a.mp3", "audio_base64": base64.b64encode(b"words").decode()},
        )
    )
    assert structured["text"] == "words"


def test_mcp_endpoint_serves_without_redirect():
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert response.status_code == 200
    names = {t["name"] for t in response.json()["result"]["tools"]}
    assert "synthesize_speech" in names
