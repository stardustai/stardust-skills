# AI Services

One FastAPI + MCP service in front of three backends, modelled on
`video-transcribe-service`:

| Capability | Backend | Endpoint used |
| --- | --- | --- |
| OCR, `engine=rapidocr` (default) | `ocr-provider` (`127.0.0.1:7998`) | `POST /v1/ocr` |
| OCR, `engine=qwen` (tables, complex layouts) | gpu4 LiteLLM gateway (`127.0.0.1:8900`, `qwen3.8-27b` vision) | `POST /v1/chat/completions` |
| ASR (audio → text) | gpu4 LiteLLM gateway (`127.0.0.1:8900`, `qwen3-asr`) | `POST /v1/audio/transcriptions` |
| TTS (text → audio) | gpu4 LiteLLM gateway (`127.0.0.1:8900`, `qwen3-tts-1.7b-customvoice`) | `POST /v1/audio/speech` |

The service holds no models. Like `video-transcribe-service`, it has no auth of its
own: bind it to loopback and put Cloudflare Access (or equivalent) in front of any
public route.

## MCP tools (`/mcp`, streamable HTTP, stateless)

- `health`: configured backends.
- `ocr_document(filename, data_base64, mime_type?, page_numbers?, languages?, engine?)`:
  `engine="rapidocr"` (default) returns fast plain text. `engine="qwen"` is for tables,
  forms and complex layouts: PDF pages are rendered to images, a vision model reads
  each page and returns Markdown (tables as Markdown/HTML), and the response lists
  per-page text. It is slower, ignores `languages`, and reads at most 20 pages per
  call (use `page_numbers`). The response carries the `engine` that produced it.
- `transcribe_audio(filename, audio_base64, language?)`: text plus `segments`.
- `synthesize_speech(text, voice?, instructions?, model?)`: text up to 3000 characters;
  returns MP3 as `audio_base64` plus `format`, `media_type`, `size_bytes`. Voices:
  `Vivian` (default), `Serena`, `Uncle_Fu`, `Dylan`, `Eric`, `Ryan`, `Aiden`,
  `Ono_Anna`, `Sohee`; `instructions` steers tone, emotion and pacing.

## REST

- `GET /health`
- `POST /ocr`: multipart `file`, optional `page_numbers` (`1,3`), `languages` (`ch_sim,en`), `engine` (`rapidocr` | `qwen`)
- `POST /asr`: multipart `file`, optional `language`
- `POST /tts`: JSON `{"text": "...", "voice": "Vivian", "instructions": "温暖、自然"}`;
  responds with raw MP3 bytes.

```bash
curl -sS -X POST localhost:8920/ocr -F file=@page.png
curl -sS -X POST localhost:8920/asr -F file=@clip.mp3
curl -sS -X POST localhost:8920/tts -H 'Content-Type: application/json' \
  -d '{"text":"你好"}' -o out.mp3
```

Backend failures return `502`, bad input `400`.

## Configuration

Read from `.env` / the environment; see [.env.example](.env.example).

| Variable | Default |
| --- | --- |
| `AI_SERVICES_HOST` / `_PORT` / `_MCP_PATH` | `127.0.0.1` / `8920` / `/mcp` |
| `AI_SERVICES_MCP_ALLOWED_HOSTS` | loopback; add the public hostname when exposed |
| `AI_SERVICES_OCR_BASE_URL` / `_MODEL` / `_API_KEY` / `_TIMEOUT_SECONDS` | `http://127.0.0.1:7998/v1` / provider default / empty / `300` |
| `AI_SERVICES_OCR_QWEN_BASE_URL` / `_MODEL` / `_API_KEY` | `http://127.0.0.1:8900/v1` / `qwen3.8-27b` / empty |
| `AI_SERVICES_OCR_QWEN_REASONING_EFFORT` / `_MAX_OUTPUT_TOKENS` / `_TIMEOUT_SECONDS` | `low` / `8192` / `600` |
| `AI_SERVICES_OCR_QWEN_PDF_DPI` / `_MAX_PAGES` / `_CONCURRENCY` | `150` / `20` / `3` |
| `AI_SERVICES_ASR_BASE_URL` / `_MODEL` / `_API_KEY` / `_LANGUAGE` / `_TIMEOUT_SECONDS` | `http://127.0.0.1:8900/v1` / `qwen3-asr` / empty / auto / `1800` |
| `AI_SERVICES_TTS_BASE_URL` / `_MODEL` / `_VOICE` / `_API_KEY` / `_TIMEOUT_SECONDS` | `http://127.0.0.1:8900/v1` / `qwen3-tts-1.7b-customvoice` / `Vivian` / empty / `300` |

`AI_SERVICES_TTS_API_KEY` must be a LiteLLM virtual key scoped to the TTS model; the
chat and ASR keys cannot reach `/v1/audio/speech`. The gateway always returns MP3, and
a cold start takes about a minute (the model unloads after 5 idle minutes).
Audio above 24 MB is re-encoded to a 48 kbps mp3 before ASR upload when `ffmpeg` is
available (gateway limit is 100 MiB).

## Development and deployment

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env   # fill in keys
.venv/bin/pytest -q && .venv/bin/ruff check .
.venv/bin/uvicorn ai_services.app:app --port 8920
```

Systemd user unit: [deploy/ai-services.service](deploy/ai-services.service) (copy to
`~/.config/systemd/user/`, then `systemctl --user enable --now ai-services`). Codex MCP
config once exposed:

```toml
[mcp_servers.ai_services]
enabled = true
url = "http://127.0.0.1:8920/mcp"
```
