# Stardust TTS Skill

Generate compressed MP3 speech through Stardust's public Qwen3-TTS
CustomVoice endpoint.

## Setup

On first use, the client opens Cloudflare Access login. Sign in with an
`@stardust.ai` mailbox and enter the emailed one-time code in the browser. The
refresh token is stored only in macOS Keychain.

Approved headless workloads use a distinct Cloudflare service token supplied
by their secret manager:

```bash
export CF_ACCESS_CLIENT_ID="..."
export CF_ACCESS_CLIENT_SECRET="..."
```

Do not share or commit credentials or store them in this skill directory. The
public Skill contains no credential; Cloudflare Access restricts the service to
company identities and individually provisioned workloads.

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

Inspect or revoke the employee session:

```bash
python3 scripts/synthesize.py --auth-status
python3 scripts/synthesize.py --logout
```

## Validation

```bash
python3 -m unittest discover -s skills/stardust-tts/tests -v
python3 skills/stardust-tts/scripts/synthesize.py --list-voices
```

The client prevalidates invalid voices and oversized input before any network
request. Production acceptance should verify company login, unauthorized
rejection, `audio/mpeg`, and a decodable MP3 through `tts-api.preseen.ai`.
