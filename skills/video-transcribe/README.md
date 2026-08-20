# Video Transcribe skill

This skill transcribes YouTube and Bilibili video URLs through Stardust Video
Transcribe. It prefers platform subtitles when available and otherwise returns
server-side ASR text.

Core boundaries:

- The video URL and resulting transcript are sent to the Stardust Video
  Transcribe service for the current task.
- Employees authenticate with an authorized `@stardust.ai` identity through
  Cloudflare Access on first use. Headless workloads set both
  `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET`.
- Use the bundled `scripts/video_transcribe.py` client. `--auth-status` checks
  the Video Transcribe origin and `--logout` removes only that origin's session.
- Private or member-only video access is configured server-side. Never copy
  browser cookies into the request or conversation.
- The service requires its own Cloudflare Access application and AUD; client
  installation alone does not provision the server-side policy.

See [SKILL.md](SKILL.md) for the request contract and usage example.
