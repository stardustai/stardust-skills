# Stardust AI Services Skill

OCR, speech-to-text and text-to-speech through the shared Stardust AI Services
endpoint (`https://ai-services.preseen.ai`), as a bundled command-line client
or through the MCP server.

The MCP server source is in [`mcp/ai-services`](../../mcp/ai-services) at the
repository root; its tools are `health`, `ocr_document`, `transcribe_audio` and
`synthesize_speech`.

## Setup

Nothing to install beyond Python 3. On first use the client opens a browser;
sign in with an `@stardust.ai` mailbox. The flow is the shared Stardust
Cloudflare Access client (OAuth with PKCE and a loopback redirect), so the
browser must run on the same machine. Over SSH the sign-in URL is printed.

Headless workloads use their own Cloudflare service token via
`CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET`. Never commit credentials.

## Use

```bash
S="$HOME/.agents/skills/ai-services/scripts/ai_services.py"
python3 "$S" health
python3 "$S" ocr page.png                       # RapidOCR
python3 "$S" ocr table.pdf --engine qwen        # tables / complex layouts, Markdown
python3 "$S" asr meeting.mp3 --language zh
python3 "$S" tts "你好" --voice Vivian --output hello.mp3
```

## Tests

```bash
python3 -m unittest skills/ai-services/tests/test_ai_services.py
```
