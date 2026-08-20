# OCR and Video Transcribe Access Authentication Design

## Goal

Move the `ocr` and `video-transcribe` skills from local API-key authentication to the repository's shared Cloudflare Access client. Employees authenticate interactively with their `@stardust.ai` identity; approved headless workloads authenticate with a Cloudflare Access service-token pair.

The OpenAI-backed `transcribe` skill is explicitly outside this change.

## Current state

- `lib/stardust_access/access_oauth.py` provides Managed OAuth login with PKCE, per-origin refresh-token storage, session status, logout, and service-token headers.
- `install.sh` mirrors `lib/` to `${STARDUST_AGENTS_HOME:-~/.agents}/lib`, so installed skills and checkout-local skills can load the same client.
- `ocr` has a Python client but currently resolves `DOCUMENT_OCR_API_KEY` or a provider-level `api_key` and sends it as a bearer token.
- `video-transcribe` currently documents raw `curl`, `VIDEO_TRANSCRIBE_API_KEY`, a local `api_key` file, and an API-key-bearing MCP URL; it has no bundled deterministic client or tests.
- As of 2026-08-21, the Access protected-resource metadata endpoint succeeds for `tts-api.preseen.ai`, but returns HTTP 404 for `ocr.preseen.ai` and `video-transcribe.preseen.ai`. Each service still needs its own Access application and AUD before interactive end-to-end authentication can work.

## Chosen approach

Use the shared Access client as the only client-side authentication mechanism for both skills. Do not fall back to legacy API keys.

This avoids ambiguous authentication order, conflicting `Authorization` headers, hidden downgrade behavior, and continued distribution of long-lived application keys. It also keeps employee and headless authentication consistent with `stardust-tts`.

## Shared client loading

Each Python entry point resolves the shared library relative to its script:

1. `<repository-or-agents-home>/lib/stardust_access`
2. `${STARDUST_AGENTS_HOME:-~/.agents}/lib/stardust_access` as an installed fallback

If neither location exists, the command exits with a direct instruction to rerun `./install.sh`. It must not silently skip authentication.

The entry points import:

- `auth_headers(base_url)` for a request
- `session_status(base_url)` for `--auth-status`
- `logout(base_url)` for `--logout`

## OCR changes

### Request path

`ocr.py` keeps the current payload, model, language, page selection, rendering, and output behavior. Authentication changes only at the request boundary:

- Resolve Access headers using the selected `base_url`.
- Merge those headers with `Content-Type` and the OCR User-Agent.
- Remove `DOCUMENT_OCR_API_KEY` and provider-level `api_key` resolution.
- Continue to use provider profiles only for non-secret model and language defaults.

### Authentication commands

- `--auth-status` checks only the selected OCR origin and returns exit code 0 when a refresh-token session exists, otherwise 1.
- When both service-token variables are set, `--auth-status` reports service-token mode without opening a browser.
- `--logout` removes only the selected OCR origin's stored refresh token and is idempotent.

## Video Transcribe changes

### Bundled client

Add `skills/video-transcribe/scripts/video_transcribe.py` with a deterministic CLI:

- positional video URL
- `--base-url`, defaulting to `https://video-transcribe.preseen.ai`
- `--prefer-subtitles` / `--no-prefer-subtitles`
- repeatable `--lang`
- `--combine-subtitles`
- `--keep-workdir`
- `--format text|json`
- `--output PATH`
- `--timeout`
- `--auth-status`
- `--logout`

The request remains `POST /transcribe` with the existing JSON contract. The client validates that the input uses HTTP or HTTPS, sends shared Access headers, and never logs credentials.

### Response and output

- Text mode prints or writes the response `text` field.
- JSON mode preserves the full service response.
- File writes create parent directories and use UTF-8.
- HTTP and transport failures identify the service and status without printing authentication secrets.

### Removed legacy guidance

Remove documentation for:

- `VIDEO_TRANSCRIBE_API_KEY`
- the installed `api_key` file
- `X-API-Key`
- application bearer keys
- the API-key-bearing MCP URL

Remote MCP is not included in the replacement because the shared Python Access client authenticates HTTP requests made by the bundled CLI, not arbitrary MCP client transports.

## Error handling

- A partial Cloudflare service-token pair raises a configuration error before any network request.
- Missing shared client fails closed with reinstall instructions.
- Interactive OAuth failures are reported as authentication failures; no legacy fallback is attempted.
- HTTP 403 containing Cloudflare error 1010 is distinguished from an Access login failure, matching the shared-client operational guidance.
- Access protected-resource metadata 404 is reported as a server-side Access provisioning prerequisite, not a bad user login.

## Documentation

Update both skills' `SKILL.md` and `README.md`, plus the repository credential table, to cover:

- first request opens company-email login
- headless service-token variables
- `--auth-status`
- `--logout`
- per-origin session isolation
- server-side Access application and AUD prerequisite
- removal of legacy API keys

The learning-group guide will contain installation, first login, OCR invocation, Video Transcribe invocation, status/logout, headless setup, and troubleshooting. It will be sent only after code and repository verification, then read back from DingTalk.

## Test strategy

Follow red-green-refactor:

1. Add failing OCR tests for shared Access headers, service-token validation through the shared client boundary, status/logout, and absence of legacy API-key resolution.
2. Add failing Video Transcribe tests for payload construction, Access headers, response rendering, status/logout, URL validation, HTTP errors, and no legacy key dependency.
3. Implement the smallest production changes that make each test pass.
4. Run both focused suites, the existing shared Access/TTS suite, install tests, sync tests, skill validation, sensitive-string scans, and `git diff --check`.

Live endpoint validation is separate from client correctness. If the two service domains still return 404 for Cloudflare protected-resource metadata, completion will explicitly state that server-side Access provisioning remains outstanding.

## Acceptance criteria

- OCR and Video Transcribe use `lib/stardust_access` for every authenticated request.
- Employee mode, complete service-token mode, session status, and origin-scoped logout are documented and tested.
- Neither skill reads, documents, or sends its legacy API key.
- The installed layout resolves the shared library correctly.
- Existing OCR request/output behavior remains intact.
- Video Transcribe has a tested bundled CLI instead of a credential-bearing curl recipe.
- Relevant repository tests pass, and unrelated pre-existing failures are reported without being folded into this change.
- A verified usage guide is delivered to the DingTalk learning group only after implementation is complete.
