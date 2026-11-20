import base64
import json

import httpx
import pytest

from ai_services.asr import parse_transcription, transcribe_audio
from ai_services.backends import BackendError
from ai_services.config import Settings
from ai_services.ocr import guess_mime_type, ocr_document
from ai_services.schemas import TtsRequest
from ai_services.tts import synthesize_speech


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_ocr_maps_provider_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "rapidocr:ch_sim+en",
                "data": [
                    {
                        "source_id": "a.png",
                        "text": "你好",
                        "confidence": 0.9,
                        "pages": [{"page_number": 1, "text": "你好", "confidence": 0.9}],
                    }
                ],
            },
        )

    result = ocr_document(
        "dir/a.png", b"png", settings(), languages=["ch_sim"], transport=httpx.MockTransport(handler)
    )
    assert seen["url"] == "http://127.0.0.1:7998/v1/ocr"
    item = seen["body"]["inputs"][0]
    assert item["source_id"] == "a.png" and item["mime_type"] == "image/png"
    assert base64.b64decode(item["data_base64"]) == b"png"
    assert seen["body"]["languages"] == ["ch_sim"]
    assert result.text == "你好" and result.pages[0].page_number == 1


def test_ocr_rejects_unsupported_type():
    with pytest.raises(ValueError):
        guess_mime_type("notes.txt")


def test_ocr_backend_error_is_wrapped():
    transport = httpx.MockTransport(lambda r: httpx.Response(503, text="busy"))
    with pytest.raises(BackendError, match="HTTP 503"):
        ocr_document("a.png", b"x", settings(), transport=transport)


def _chat_reply(text, finish="stop"):
    return {"choices": [{"message": {"content": text}, "finish_reason": finish}]}


def test_ocr_qwen_reads_image_as_markdown():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_chat_reply("```markdown\n| a | b |\n|---|---|\n```"))

    result = ocr_document(
        "t.png", b"png", settings(ocr_qwen_api_key="k"), engine="qwen",
        transport=httpx.MockTransport(handler),
    )
    assert seen["url"] == "http://127.0.0.1:8900/v1/chat/completions"
    assert seen["auth"] == "Bearer k"
    body = seen["body"]
    assert body["model"] == "qwen3.8-27b" and body["reasoning_effort"] == "low"
    image, prompt = body["messages"][0]["content"]
    assert image["image_url"]["url"].startswith("data:image/png;base64,")
    assert prompt["type"] == "text"
    assert result.engine == "qwen" and result.text == "| a | b |\n|---|---|"
    assert result.pages == []


def _pdf(pages: int) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    for n in range(pages):
        doc.new_page().insert_text((72, 72), f"page {n + 1}")
    return doc.tobytes()


def test_ocr_qwen_renders_pdf_pages_in_order():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = json.loads(request.content)["messages"][0]["content"][0]["image_url"]["url"]
        assert url.startswith("data:image/png;base64,")
        calls.append(url)
        return httpx.Response(200, json=_chat_reply(f"text {len(calls)}"))

    result = ocr_document(
        "doc.pdf", _pdf(3), settings(ocr_qwen_concurrency=1), engine="qwen",
        page_numbers=[3, 1], transport=httpx.MockTransport(handler),
    )
    assert len(calls) == 2
    assert [p.page_number for p in result.pages] == [3, 1]
    assert result.text == "text 1\n\ntext 2"


def test_ocr_qwen_validates_pages():
    with pytest.raises(ValueError, match="out of range"):
        ocr_document("d.pdf", _pdf(1), settings(), engine="qwen", page_numbers=[2])
    with pytest.raises(ValueError, match="at most 2"):
        ocr_document("d.pdf", _pdf(3), settings(ocr_qwen_max_pages=2), engine="qwen")


def test_ocr_qwen_flags_truncation_and_empty_pages():
    replies = iter([_chat_reply("cut", "length"), _chat_reply("")])
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=next(replies)))
    result = ocr_document(
        "d.pdf", _pdf(2), settings(ocr_qwen_concurrency=1), engine="qwen", transport=transport
    )
    assert "truncated" in result.pages[0].text
    assert result.warnings == ["page 2 returned no text"]


def test_ocr_rejects_unknown_engine():
    with pytest.raises(ValueError, match="engine"):
        ocr_document("a.png", b"x", settings(), engine="tesseract")


def test_parse_transcription_falls_back_to_text():
    text, segments = parse_transcription({"text": " hi ", "segments": []})
    assert text == "hi" and [s.text for s in segments] == ["hi"]


def test_asr_uploads_to_gateway():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = request.content
        return httpx.Response(
            200, json={"text": "hello", "segments": [{"start": 0, "end": 1.5, "text": "hello"}]}
        )

    result = transcribe_audio(
        "clip.mp3", b"audio-bytes", settings(asr_api_key="k"), language="en",
        transport=httpx.MockTransport(handler),
    )
    assert seen["url"] == "http://127.0.0.1:8900/v1/audio/transcriptions"
    assert seen["auth"] == "Bearer k"
    assert b"qwen3-asr" in seen["body"] and b"verbose_json" in seen["body"]
    assert b'name="language"' in seen["body"] and b"audio-bytes" in seen["body"]
    assert result.text == "hello" and result.segments[0].end == 1.5


def test_tts_returns_mp3_and_metadata():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=b"ID3audio")

    audio, result = synthesize_speech(
        TtsRequest(text="你好", voice="Serena", instructions="温暖"),
        settings(tts_api_key="k"),
        transport=httpx.MockTransport(handler),
    )
    assert audio == b"ID3audio"
    assert seen["url"] == "http://127.0.0.1:8900/v1/audio/speech"
    assert seen["auth"] == "Bearer k"
    assert seen["body"] == {
        "model": "qwen3-tts-1.7b-customvoice",
        "input": "你好",
        "voice": "Serena",
        "response_format": "mp3",
        "instructions": "温暖",
    }
    assert result.media_type == "audio/mpeg" and base64.b64decode(result.audio_base64) == audio


def test_tts_defaults_voice_and_surfaces_gateway_errors():
    bodies = []

    def ok(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, content=b"x")

    synthesize_speech(TtsRequest(text="hi"), settings(), transport=httpx.MockTransport(ok))
    assert bodies[0]["voice"] == "Vivian" and "instructions" not in bodies[0]

    denied = httpx.MockTransport(lambda r: httpx.Response(401, text="key not allowed"))
    with pytest.raises(BackendError, match="HTTP 401"):
        synthesize_speech(TtsRequest(text="hi"), settings(), transport=denied)
