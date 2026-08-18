# Stardust TTS Skill

Generate compressed MP3 speech through Stardust's public Qwen3-TTS
CustomVoice endpoint.

## Setup

Configure the employee's dedicated, TTS-only LiteLLM virtual key in the
environment:

```bash
export STARDUST_TTS_API_KEY="..."
```

Do not share or commit the key, store it in this skill directory, reuse the
Open WebUI key, or use the LiteLLM master key. The public Skill contains no
credential and a request without a key returns HTTP 401. A bearer key alone is
not proof of employment; the service should additionally be protected by
company SSO at the edge or a company-only Tailscale network.

## Usage

```bash
python3 scripts/synthesize.py \
  "这是一段语音合成测试。" \
  --voice Vivian \
  --instructions "自然、清晰" \
  --output /tmp/stardust-tts.mp3
```

For multiline input:

```bash
python3 scripts/synthesize.py \
  --input-file /absolute/path/to/text.txt \
  --voice Serena \
  --output /absolute/path/to/result.mp3
```

The client has no third-party Python dependencies. It validates the nine preset
voices, the 3000-character input limit, MP3 output, authentication, response
content type, and MP3 file signature.

## Validation

```bash
python3 -m unittest discover -s skills/stardust-tts/tests -v
python3 skills/stardust-tts/scripts/synthesize.py --list-voices
```

Live service verification on 2026-08-18 confirmed all nine voices, delivery
instructions, model discovery, `audio/mpeg`, and decodable 24 kHz mono MP3
output. Missing authentication returns HTTP 401. The client prevalidates invalid
voices and oversized input because the current LiteLLM speech path surfaces
those backend validation failures as HTTP 500.
