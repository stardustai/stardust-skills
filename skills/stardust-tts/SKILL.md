---
name: stardust-tts
description: Generate spoken MP3 audio from Chinese, English, Japanese, Korean, and other supported text with Stardust Qwen3-TTS CustomVoice. Use this skill whenever the user asks to synthesize speech, create narration or voice-over, read text aloud, generate an MP3 voice clip, choose a preset speaker, or control delivery with natural-language instructions.
metadata:
  requires:
    bins:
      - python3
---

# Stardust TTS

Use the authenticated Stardust speech endpoint at
`https://llm-api.preseen.ai/v1/audio/speech`. It serves
`qwen3-tts-1.7b-customvoice` and always returns compressed MP3 audio.

## Workflow

1. Confirm the text to synthesize, destination MP3 path, preset voice, and any
   delivery instructions. If the user does not choose a voice, use `Vivian`.
2. Resolve the destination to an absolute path ending in `.mp3`.
3. For short text, run:

```bash
python3 "$HOME/.agents/skills/stardust-tts/scripts/synthesize.py" \
  "你好，欢迎使用星尘语音服务。" \
  --voice Vivian \
  --instructions "温暖、自然、语速稍慢" \
  --output "/absolute/path/to/speech.mp3"
```

4. For long or multiline text, write or use an existing UTF-8 text file and
   pass `--input-file`. Do not place sensitive text in shell history:

```bash
python3 "$HOME/.agents/skills/stardust-tts/scripts/synthesize.py" \
  --input-file "/absolute/path/to/narration.txt" \
  --voice Serena \
  --instructions "专业、清晰、节奏自然" \
  --output "/absolute/path/to/narration.mp3"
```

5. Verify the command reports a nonzero file. If `ffprobe` is available, check
   the codec and duration. Return the absolute MP3 path to the user; in clients
   that render local audio, provide it as a playable file link.

## Voices and delivery control

The live service has been verified with all nine preset voices:

- `Vivian`
- `Serena`
- `Uncle_Fu`
- `Dylan`
- `Eric`
- `Ryan`
- `Aiden`
- `Ono_Anna`
- `Sohee`

Use `--instructions` for natural-language control of emotion, tone, pace, and
delivery, for example `平静、温柔、语速稍慢` or
`兴奋、充满活力、语速稍快`. Instructions customize how a preset voice speaks;
they do not create a new timbre. VoiceDesign, reference-audio cloning, uploaded
voices, and user-created speakers are not available.

List the accepted voices without making a network request:

```bash
python3 "$HOME/.agents/skills/stardust-tts/scripts/synthesize.py" --list-voices
```

## Output contract

- Output is always real MP3 (`audio/mpeg`), normally 24 kHz mono at about
  64 kbps. The service does not expose WAV output.
- The client always sends `response_format=mp3`. A requested `.wav` destination
  is an input error; use a `.mp3` path instead.
- Text must be nonblank and no longer than 3000 Unicode characters.
- The model may cold-start after being idle. Allow up to 900 seconds; warm
  requests normally return much faster.

## Authentication and data boundary

The client reads only `STARDUST_TTS_API_KEY`. Provision a distinct, scoped
LiteLLM virtual key for each employee or workload; authorize only
`qwen3-tts-1.7b-customvoice`, attach an employee/workload identity label, and set
an expiry plus appropriate rate/budget limits. Do not reuse the Open WebUI key,
the LiteLLM master key, or a generic LLM key.

The repository and generated command examples never contain a key. Do not print
environment values or pass a key as a command-line argument. The requested text
and instructions are sent to the Stardust public TTS service for synthesis. Do
not synthesize passwords, API keys, private keys, authentication codes, or other
secrets. If the source contains confidential business or personal data and the
user has not already authorized this external processing, explain the boundary
and confirm before sending it.

Publishing this Skill does not grant service access, but a bearer key proves
only possession, not current employment. To enforce company-only access, place
the endpoint behind the company's identity-aware edge (for example Cloudflare
Access with company SSO) or a company-only Tailscale network, and retain the
per-person LiteLLM key as a second authorization and quota layer. Override
`STARDUST_TTS_BASE_URL` only when the user explicitly asks to use a different
compatible deployment.

## Failure handling

- Missing credentials: ask the user to configure `STARDUST_TTS_API_KEY`; never
  ask them to paste the key into chat.
- Invalid voice, empty text, over-3000-character text, or non-MP3 output path:
  report the local validation error and do not call the service.
- HTTP 401: the virtual key is missing, invalid, expired, or lacks access.
- HTTP 403: the key is authenticated but lacks access to the TTS model.
- HTTP 5xx: report the service failure. Do not silently switch to another TTS
  provider or upload the text elsewhere.
- Never treat a zero-byte or non-MP3 response as success.
