# Stardust TTS Skill

Generate compressed MP3 speech through Stardust's public Qwen3-TTS
CustomVoice endpoint.

## Setup

Nothing to install beyond Python 3. On first use the skill opens a browser
itself, you sign in with an `@stardust.ai` mailbox and the emailed one-time
code, and that is it.

The flow is standard OAuth for native apps (RFC 8252): dynamic client
registration, authorization code with PKCE, and a loopback redirect on a random
port. The refresh token is stored in a `0600` file under your config directory
— `~/.config/stardust-tts/oauth.json`, or `%APPDATA%\stardust-tts\oauth.json`
on Windows. Set `STARDUST_TTS_TOKEN_FILE` to move it. Sign out with
`--logout`.

Because the redirect lands on `127.0.0.1`, the browser has to be on the same
machine as the skill. Over SSH the sign-in URL is printed instead of opened.

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

The first call after the model has been idle for five minutes pays a cold start
of about a minute. That is expected; do not treat it as a failure.

Inspect or revoke the employee session:

```bash
python3 scripts/synthesize.py --auth-status
python3 scripts/synthesize.py --logout
```

## Validation

```bash
cd skills/stardust-tts && python3 -m unittest tests.test_synthesize -v
python3 skills/stardust-tts/scripts/synthesize.py --list-voices
```

The client prevalidates invalid voices and oversized input before any network
request. Production acceptance should verify company login, unauthorized
rejection, `audio/mpeg`, and a decodable MP3 through `tts-api.preseen.ai`.
