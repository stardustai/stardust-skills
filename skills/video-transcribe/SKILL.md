---
name: video-transcribe
description: Use when the user asks to transcribe, extract subtitles, summarize a raw transcript, translate, or get text from a YouTube or Bilibili video URL through Stardust Video Transcribe.
---

# Video Transcribe

Use Stardust Video Transcribe to extract transcript text from YouTube and
Bilibili video URLs.

## Endpoint

```text
https://video-transcribe.preseen.ai/transcribe
```

OpenAPI:

```text
https://video-transcribe.preseen.ai/openapi.json
```

## Authentication

Resolve the API key at runtime from `VIDEO_TRANSCRIBE_API_KEY`. A local
installation may instead keep it in `api_key` beside this `SKILL.md`; that file
is excluded from installation and repository synchronization.

Do not print the key. Send it as `X-API-Key` or `Authorization: Bearer`.

## Request

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "prefer_subtitles": true,
  "langs": ["zh.*", "en.*"],
  "combine_subtitles": false,
  "keep_workdir": false
}
```

## Usage

```bash
curl -sS -X POST "https://video-transcribe.preseen.ai/transcribe" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${VIDEO_TRANSCRIBE_API_KEY}" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID","prefer_subtitles":true}'
```

Return the `text` field to the user or use it as source material for
summarization, translation, or analysis. Preserve `source`, `title`, and
`video_id` in citations when useful.

## Notes

- `source=subtitles` means the service used platform captions.
- `source=funasr` means the service downloaded audio and ran server-side ASR.
- For private Bilibili or member videos, configure server-side cookies. Do not
  send browser cookies in chat.
