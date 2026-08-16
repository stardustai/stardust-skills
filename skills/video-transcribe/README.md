# Video Transcribe skill

This skill transcribes YouTube and Bilibili video URLs through Stardust Video
Transcribe. It prefers platform subtitles when available and otherwise returns
server-side ASR text.

Core boundaries:

- The video URL and resulting transcript are sent to the Stardust Video
  Transcribe service for the current task.
- Resolve credentials only at runtime from `VIDEO_TRANSCRIBE_API_KEY` or a
  local installed `api_key` file; neither is part of this repository.
- Private or member-only video access is configured server-side. Never copy
  browser cookies into the request or conversation.
- MCP-capable clients may use the service's local-keyed MCP endpoint, but the
  complete endpoint must stay in local client configuration because it embeds
  the API key.

See [SKILL.md](SKILL.md) for the request contract and usage example.
