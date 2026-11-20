# Registering ai-services in ChatGPT

**Status (done 2026-10-14):** Access app `Stardust AI Services API`
(`ai-services.preseen.ai`, Managed OAuth, redirect `https://chatgpt.com/connector/oauth/*`,
loopback only), tunnel ingress, proxied CNAME, and the ChatGPT plugin `ai-services`
(`https://ai-services.preseen.ai/mcp`, OAuth) are all in place. Verified from ChatGPT:
`health` and `ocr_document` (rapidocr) returned real results. Verified locally on the same
service: `engine=qwen` returns a Markdown table in ~2 s, TTS returns MP3, ASR round-trips
the synthesized speech.

ChatGPT needs a public HTTPS MCP URL with OAuth. The service has no auth of its own,
so it must only be exposed behind a Cloudflare Access application (Managed OAuth),
the same way `video-transcribe.preseen.ai` is. Follow
the internal Cloudflare Access reuse guide for background.

Origin: `http://127.0.0.1:8920` (systemd user unit `ai-services`, already running).

## 1. Cloudflare Access application (do this first)

Zero Trust -> Access -> Applications -> Add -> Self-hosted:

- Name: `Stardust AI Services API`; hostname: `ai-services.preseen.ai`
- Policy: the reusable `Stardust employees` policy (emails ending in `@stardust.ai`)
- Identity provider: One-time PIN; session 24h
- Advanced settings -> Managed OAuth: enable, enable dynamic client registration,
  allow loopback, and add the allowed redirect URI `https://chatgpt.com/connector/oauth/*`
- Access token lifetime 15m, grant session 168h (same as the other API apps)

Verify before going public: an unauthenticated request to the hostname must 302 to
`stardust-ai.cloudflareaccess.com`, never reach the origin.

## 2. Tunnel ingress and DNS

In the tunnel ingress configuration, add before the catch-all 404 rule:

```json
{ "hostname": "ai-services.preseen.ai", "service": "http://127.0.0.1:8920" }
```

then push the configuration (keep any other fields of the live tunnel config, such as
`warp-routing`), and add a proxied CNAME `ai-services` pointing to
`<tunnel-id>.cfargotunnel.com`. `AI_SERVICES_MCP_ALLOWED_HOSTS` in `.env` already includes the hostname.

## 3. ChatGPT

Create a developer-mode app like the existing `video-transcribe` one:

- URL: `https://ai-services.preseen.ai/mcp` (no trailing slash, no key)
- Authorization: OAuth

Then in a chat, ask it to OCR an image (default engine) and check `health`.

## Operational caveats

- TTS cold start is ~2.5 min (the gateway unloads Qwen3-TTS after idle). Cloudflare cuts
  non-streaming responses at ~100 s, so the first TTS call after an idle period can fail with
  524 through ChatGPT; retry once it is warm.
- Revoke a ChatGPT grant at `https://ai-services.preseen.ai/cdn-cgi/access/oauth/consent`
  (the link on the consent page).

## Known backend issues seen earlier (gpu4 gateway, not this service)

- `engine=qwen` queues behind other traffic on the two qwen3.8-27b slots and can hit the
  600 s timeout when the gateway is saturated.
- TTS returns HTTP 500 when the gateway cannot load `qwen3-tts-1.7b-customvoice`
  (both GPUs held by qwen3.8-27b).
