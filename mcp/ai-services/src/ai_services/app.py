import asyncio
import base64
import binascii
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from starlette.types import ASGIApp, Receive, Scope, Send

from ai_services.asr import asr_runtime_status
from ai_services.asr import transcribe_audio as run_asr
from ai_services.backends import BackendError
from ai_services.config import Settings, get_settings
from ai_services.ocr import ocr_document as run_ocr
from ai_services.ocr import ocr_runtime_status
from ai_services.schemas import AsrResponse, HealthResponse, OcrResponse, TtsRequest, TtsResponse
from ai_services.tts import synthesize_speech as run_tts
from ai_services.tts import tts_runtime_status


class CanonicalMCPPathMiddleware:
    """Serve `/mcp` and `/mcp/` identically instead of redirecting."""

    def __init__(self, app: ASGIApp, mcp_path: str) -> None:
        self.app = app
        self.mcp_path = "/" + mcp_path.strip("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == self.mcp_path:
            scope = dict(scope)
            scope["path"] = self.mcp_path + "/"
            scope["raw_path"] = (self.mcp_path + "/").encode()
        await self.app(scope, receive, send)


def decode_base64(value: str, field: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except binascii.Error as exc:
        raise ValueError(f"{field} must be valid base64") from exc


def build_health(settings: Settings) -> HealthResponse:
    return HealthResponse(
        status="ok",
        backends={
            "ocr": ocr_runtime_status(settings),
            "asr": asr_runtime_status(settings),
            "tts": tts_runtime_status(settings),
        },
    )


def http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, BackendError):
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings

    streamable_mcp = FastMCP(
        name="ai-services",
        instructions=(
            "OCR (image/PDF to text), ASR (audio to text) and TTS (text to audio). "
            "Binary inputs and outputs are base64 strings."
        ),
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[h.strip() for h in get_settings().mcp_allowed_hosts.split(",") if h.strip()],
        ),
    )

    @streamable_mcp.tool(
        name="health",
        description="Report the configured OCR, ASR and TTS backends.",
        structured_output=True,
    )
    def mcp_health() -> HealthResponse:
        return build_health(get_settings())

    @streamable_mcp.tool(
        name="ocr_document",
        description=(
            "Extract text from an image (png, jpg, webp, ...) or a PDF. Pass the file "
            "contents as base64 in data_base64. engine='rapidocr' (default) is fast plain-text "
            "OCR for ordinary scans and screenshots. Use engine='qwen' for tables, forms or "
            "complex layouts: a vision model reads each page and returns Markdown (slower; "
            "languages is ignored). For PDFs, page_numbers (1-based) limits which pages are "
            "read; qwen mode accepts at most 20 pages per call."
        ),
        structured_output=True,
    )
    async def mcp_ocr_document(
        filename: str,
        data_base64: str,
        mime_type: str | None = None,
        page_numbers: list[int] | None = None,
        languages: list[str] | None = None,
        engine: str = "rapidocr",
    ) -> OcrResponse:
        data = decode_base64(data_base64, "data_base64")
        return await asyncio.to_thread(
            run_ocr, filename, data, get_settings(),
            mime_type=mime_type, page_numbers=page_numbers, languages=languages, engine=engine,
        )

    @streamable_mcp.tool(
        name="transcribe_audio",
        description=(
            "Transcribe an audio file to text (ASR) with optional segment timestamps. Pass "
            "the file contents as base64 in audio_base64; language (for example zh, en) is "
            "auto-detected when omitted."
        ),
        structured_output=True,
    )
    async def mcp_transcribe_audio(
        filename: str,
        audio_base64: str,
        language: str | None = None,
    ) -> AsrResponse:
        data = decode_base64(audio_base64, "audio_base64")
        return await asyncio.to_thread(run_asr, filename, data, get_settings(), language=language)

    @streamable_mcp.tool(
        name="synthesize_speech",
        description=(
            "Convert text (max 3000 characters) to speech with Qwen3-TTS. Returns MP3 as "
            "base64 in audio_base64. voice is one of Vivian, Serena, Uncle_Fu, Dylan, Eric, "
            "Ryan, Aiden, Ono_Anna, Sohee (default Vivian); instructions steers tone, "
            "emotion and pacing in plain language, e.g. '温暖、自然、语速稍慢'. A cold start "
            "can take about a minute."
        ),
        structured_output=True,
    )
    async def mcp_synthesize_speech(
        text: str,
        voice: str | None = None,
        instructions: str | None = None,
        model: str | None = None,
    ) -> TtsResponse:
        request = TtsRequest(text=text, voice=voice, instructions=instructions, model=model)
        _, result = await asyncio.to_thread(run_tts, request, get_settings())
        return result
except Exception:
    streamable_mcp = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if streamable_mcp is None:
        yield
        return

    async with streamable_mcp.session_manager.run():
        yield


app = FastAPI(
    title="AI Services",
    description="OCR, ASR and TTS behind one REST and MCP endpoint.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(CanonicalMCPPathMiddleware, mcp_path=get_settings().mcp_path)


@app.get("/health", response_model=HealthResponse, operation_id="health")
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return build_health(settings)


@app.post("/ocr", response_model=OcrResponse, operation_id="ocr_document")
async def ocr_file(
    file: UploadFile = File(..., description="Image or PDF to read."),
    page_numbers: str | None = Form(None, description="Comma-separated 1-based PDF pages."),
    languages: str | None = Form(None, description="Comma-separated OCR languages (rapidocr)."),
    engine: str = Form("rapidocr", description="'rapidocr' (default) or 'qwen' for tables/layouts."),
    settings: Settings = Depends(get_settings),
) -> OcrResponse:
    try:
        pages = [int(p) for p in page_numbers.split(",") if p.strip()] if page_numbers else None
        langs = [x.strip() for x in languages.split(",") if x.strip()] if languages else None
        return await asyncio.to_thread(
            run_ocr, file.filename or "document", await file.read(), settings,
            mime_type=file.content_type if file.content_type != "application/octet-stream" else None,
            page_numbers=pages, languages=langs, engine=engine,
        )
    except Exception as exc:
        raise http_error(exc) from exc


@app.post("/asr", response_model=AsrResponse, operation_id="transcribe_audio")
async def asr_file(
    file: UploadFile = File(..., description="Audio file to transcribe."),
    language: str | None = Form(None, description="Language code; auto-detected when empty."),
    settings: Settings = Depends(get_settings),
) -> AsrResponse:
    try:
        return await asyncio.to_thread(
            run_asr, file.filename or "audio", await file.read(), settings, language=language
        )
    except Exception as exc:
        raise http_error(exc) from exc


@app.post(
    "/tts",
    operation_id="synthesize_speech",
    response_class=Response,
    responses={200: {"content": {"audio/*": {}}, "description": "Synthesized audio bytes."}},
)
async def tts(request: TtsRequest, settings: Settings = Depends(get_settings)) -> Response:
    try:
        audio, result = await asyncio.to_thread(run_tts, request, settings)
    except Exception as exc:
        raise http_error(exc) from exc
    return Response(content=audio, media_type=result.media_type)


if streamable_mcp is not None:
    app.mount("/" + get_settings().mcp_path.strip("/"), streamable_mcp.streamable_http_app())
