# GPU Service Access Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Authenticate every direct Stardust GPU service client in this repository with the shared Cloudflare Access flow, adding OCR and Video Transcribe while preserving the already-authenticated TTS client.

**Architecture:** Keep `lib/stardust_access/access_oauth.py` as the sole authentication implementation. OCR and a new Video Transcribe CLI resolve the shared library from either the checkout/installed tree, ask it for request headers per service origin, and expose origin-scoped status/logout commands. Existing application API-key paths are removed instead of retained as a fallback.

**Tech Stack:** Python 3 standard library, PyYAML for existing OCR provider settings, pytest/unittest, Cloudflare Access Managed OAuth with PKCE, shell-based repository install/sync tests.

---

## File map

- Modify `lib/stardust_access/access_oauth.py`: make shared-client labels and override names service-neutral while preserving the legacy TTS token store.
- Modify `lib/stardust_access/README.md`: document the generic token-file override, backward compatibility, and per-service Access/AUD requirement.
- Modify `skills/stardust-tts/tests/test_synthesize.py`: protect existing TTS behavior and test the generic override/labels.
- Modify `skills/ocr/scripts/ocr.py`: replace API-key resolution with shared Access headers and add status/logout.
- Modify `skills/ocr/tests/test_ocr.py`: prove Access headers, status/logout, and removal of the API-key path.
- Modify `skills/ocr/SKILL.md` and `skills/ocr/README.md`: document employee and headless Access usage.
- Create `skills/video-transcribe/scripts/video_transcribe.py`: deterministic authenticated client for `POST /transcribe`.
- Create `skills/video-transcribe/tests/test_video_transcribe.py`: cover validation, payload, auth, transport, rendering, and auth lifecycle commands.
- Modify `skills/video-transcribe/SKILL.md` and `skills/video-transcribe/README.md`: replace API-key curl/MCP guidance with the bundled CLI and Access workflow.
- Modify `README.md`: update the repository-wide credential and data-boundary table.

### Task 1: Make the shared Access client service-neutral without breaking TTS sessions

**Files:**
- Modify: `lib/stardust_access/access_oauth.py`
- Modify: `lib/stardust_access/README.md`
- Test: `skills/stardust-tts/tests/test_synthesize.py`

- [ ] **Step 1: Write failing compatibility tests**

Add tests that express generic override precedence and retained legacy behavior:

```python
def test_generic_token_file_override_precedes_legacy_override(self):
    with patch.dict(
        access.os.environ,
        {
            "STARDUST_ACCESS_TOKEN_FILE": "/tmp/generic.json",
            "STARDUST_TTS_TOKEN_FILE": "/tmp/legacy.json",
        },
        clear=True,
    ):
        self.assertEqual(Path("/tmp/generic.json"), access.token_path())

def test_legacy_tts_token_file_override_remains_supported(self):
    with patch.dict(
        access.os.environ,
        {"STARDUST_TTS_TOKEN_FILE": "/tmp/legacy.json"},
        clear=True,
    ):
        self.assertEqual(Path("/tmp/legacy.json"), access.token_path())

def test_shared_client_identity_is_service_neutral(self):
    self.assertEqual("stardust-access-client/1.0", access.USER_AGENT)
    self.assertEqual("Stardust Service Access", access.CLIENT_NAME)

def test_missing_protected_resource_metadata_identifies_server_prerequisite(self):
    with patch.object(
        access,
        "request_json",
        side_effect=RuntimeError("OAuth endpoint returned HTTP 404"),
    ):
        with self.assertRaisesRegex(RuntimeError, "service-side Access"):
            access.discover("https://ocr.example/v1")
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  skills/stardust-tts/tests/test_synthesize.py
```

Expected: failures because `STARDUST_ACCESS_TOKEN_FILE` and `CLIENT_NAME` do not yet exist and the current User-Agent is TTS-specific.

- [ ] **Step 3: Implement the minimal service-neutral shared-client changes**

Use these constants and override order:

```python
CLIENT_NAME = "Stardust Service Access"
USER_AGENT = "stardust-access-client/1.0"

def token_path() -> Path:
    override = os.getenv("STARDUST_ACCESS_TOKEN_FILE") or os.getenv(
        "STARDUST_TTS_TOKEN_FILE"
    )
    if override:
        return Path(override)
    if os.name == "nt":
        base = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
    # Keep the existing default to preserve already stored TTS sessions.
    return base / "stardust-tts" / "oauth.json"
```

Replace user-visible “TTS” wording in OAuth registration, callback, credential errors, and login instructions with service-neutral Stardust Access wording. In `discover()`, translate a protected-resource metadata HTTP 404 into an explicit service-side Access application/AUD prerequisite while preserving the original exception as the cause. Keep `DEFAULT_ACCOUNT`, the default file location, record schema, origin keys, and OAuth protocol unchanged.

- [ ] **Step 4: Update shared-client documentation**

Document `STARDUST_ACCESS_TOKEN_FILE` as preferred, `STARDUST_TTS_TOKEN_FILE` as a compatibility alias, and the existing default store as deliberately retained for session continuity.

- [ ] **Step 5: Run the TTS/shared-client suite and verify GREEN**

Run the same pytest command. Expected: all tests pass, including the pre-existing TTS request and origin-isolation tests.

- [ ] **Step 6: Commit the shared-client compatibility slice**

```bash
git add lib/stardust_access/access_oauth.py lib/stardust_access/README.md \
  skills/stardust-tts/tests/test_synthesize.py
git commit -m "refactor(access): make shared OAuth client service neutral"
```

### Task 2: Migrate OCR from API keys to shared Access

**Files:**
- Modify: `skills/ocr/scripts/ocr.py`
- Modify: `skills/ocr/tests/test_ocr.py`

- [ ] **Step 1: Write failing OCR Access tests**

Change the request test to call the desired interface and add lifecycle coverage:

```python
def test_call_ocr_sends_shared_access_headers(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps({"object": "list", "data": []}).encode()

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        return Response()

    monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
    result = ocr.call_ocr(
        base_url="https://ocr.example/v1",
        auth_headers={"Authorization": "Bearer access-token"},
        payload={"inputs": []},
        timeout=12,
    )
    assert captured["headers"]["Authorization"] == "Bearer access-token"
    assert "X-API-Key" not in captured["headers"]

def test_resolve_auth_headers_delegates_to_shared_client(monkeypatch) -> None:
    monkeypatch.setattr(ocr, "auth_headers", lambda url: {"Authorization": url})
    assert ocr.resolve_auth_headers("https://ocr.example/v1") == {
        "Authorization": "https://ocr.example/v1"
    }

def test_auth_status_and_logout_are_origin_scoped(monkeypatch, capsys) -> None:
    monkeypatch.setattr(ocr, "session_status", lambda url: url.endswith("/v1"))
    assert ocr.main(["--base-url", "https://ocr.example/v1", "--auth-status"]) == 0
    monkeypatch.setattr(ocr, "logout", lambda url: url.endswith("/v1"))
    assert ocr.main(["--base-url", "https://ocr.example/v1", "--logout"]) == 0

def test_auth_status_reports_complete_service_token_without_session_lookup(monkeypatch):
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "id")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "secret")
    monkeypatch.setattr(ocr, "session_status", lambda _url: pytest.fail("must not run"))
    assert ocr.main(["--auth-status"]) == 0
```

Add a source-level regression assertion that `DOCUMENT_OCR_API_KEY` and profile `api_key` resolution are absent from the production script.

- [ ] **Step 2: Run the OCR tests and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider skills/ocr/tests
```

Expected: failures because `call_ocr` still accepts `api_key`, shared imports/status/logout are absent, and the legacy environment variable remains.

- [ ] **Step 3: Add the shared-library resolver and lifecycle flags**

Follow the installed/checkout lookup used by `stardust-tts`:

```python
SCRIPT_DIR = Path(__file__).resolve().parent
_SHARED = SCRIPT_DIR.parents[2] / "lib" / "stardust_access"
if not _SHARED.is_dir():
    _SHARED = Path(
        os.getenv("STARDUST_AGENTS_HOME", Path.home() / ".agents")
    ) / "lib" / "stardust_access"
if not _SHARED.is_dir():
    raise SystemExit(
        f"ocr: shared Access client not found at {_SHARED}. "
        "Re-run ./install.sh from the stardust-skills checkout."
    )
sys.path.insert(0, str(_SHARED))
from access_oauth import auth_headers, logout, session_status
```

Add `--auth-status` and `--logout`; make positional files optional only for those lifecycle commands, and validate that normal OCR still requires at least one file.

- [ ] **Step 4: Replace the request authentication boundary**

Change `call_ocr` to accept `auth_headers: dict[str, str]`, merge them into the request headers, and call it with `resolve_auth_headers(base_url)`. Delete application API-key resolution while retaining model/language profile behavior.

- [ ] **Step 5: Run OCR tests and verify GREEN**

Run the focused OCR command. Expected: all OCR tests pass.

- [ ] **Step 6: Commit the OCR client slice**

```bash
git add skills/ocr/scripts/ocr.py skills/ocr/tests/test_ocr.py
git commit -m "feat(ocr): authenticate through shared Access"
```

### Task 3: Add an authenticated Video Transcribe CLI

**Files:**
- Create: `skills/video-transcribe/scripts/video_transcribe.py`
- Create: `skills/video-transcribe/tests/test_video_transcribe.py`

- [ ] **Step 1: Create tests first and verify the missing client fails**

Create a test module that loads `scripts/video_transcribe.py` and covers:

```python
def test_build_payload_preserves_service_contract():
    assert video.build_payload(
        "https://www.youtube.com/watch?v=abc",
        prefer_subtitles=True,
        langs=["zh.*", "en.*"],
        combine_subtitles=False,
        keep_workdir=False,
    ) == {
        "url": "https://www.youtube.com/watch?v=abc",
        "prefer_subtitles": True,
        "langs": ["zh.*", "en.*"],
        "combine_subtitles": False,
        "keep_workdir": False,
    }

def test_call_transcribe_sends_access_headers(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps({"text": "hello", "source": "subtitles"}).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        return Response()

    monkeypatch.setattr(video.urllib.request, "urlopen", fake_urlopen)
    response = video.call_transcribe(
        base_url="https://video.example",
        auth_headers={"Authorization": "Bearer token"},
        payload={"url": "https://example/video"},
        timeout=30,
    )
    assert captured["url"] == "https://video.example/transcribe"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert "X-API-Key" not in captured["headers"]
    assert response["text"] == "hello"

def test_render_text_requires_text_field():
    with pytest.raises(ValueError, match="text"):
        video.render({"source": "subtitles"}, "text")

def test_invalid_non_http_video_url_is_rejected():
    with pytest.raises(ValueError, match="HTTP"):
        video.validate_video_url("file:///tmp/video.mp4")

def test_auth_status_and_logout_are_origin_scoped(monkeypatch, capsys):
    monkeypatch.setattr(video, "session_status", lambda url: url == "https://video.example")
    assert video.main(["--base-url", "https://video.example", "--auth-status"]) == 0
    monkeypatch.setattr(video, "logout", lambda url: url == "https://video.example")
    assert video.main(["--base-url", "https://video.example", "--logout"]) == 0

def test_auth_status_reports_complete_service_token_without_session_lookup(monkeypatch):
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "id")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "secret")
    monkeypatch.setattr(video, "session_status", lambda _url: pytest.fail("must not run"))
    assert video.main(["--auth-status"]) == 0

def test_http_errors_do_not_echo_authorization_header(monkeypatch):
    error = urllib.error.HTTPError(
        "https://video.example/transcribe", 403, "Forbidden", {}, io.BytesIO(b"denied")
    )
    monkeypatch.setattr(video.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(RuntimeError) as caught:
        video.call_transcribe(
            base_url="https://video.example",
            auth_headers={"Authorization": "Bearer secret-value"},
            payload={"url": "https://example/video"},
            timeout=30,
        )
    assert "secret-value" not in str(caught.value)
```

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  skills/video-transcribe/tests
```

Expected: collection error because the production client does not exist. This is the RED state for the new entry point.

- [ ] **Step 2: Implement argument parsing and validation**

Implement `build_parser()`, `validate_video_url()`, `build_payload()`, and lifecycle flags. Defaults must match the existing service contract:

```python
DEFAULT_BASE_URL = "https://video-transcribe.preseen.ai"
DEFAULT_LANGS = ("zh.*", "en.*")
```

Normal mode requires exactly one HTTP(S) video URL. Status/logout modes require no URL and must not start a network request to `/transcribe`.

- [ ] **Step 3: Implement Access resolution, service request, and rendering**

Load `lib/stardust_access` with the same resolver as OCR/TTS. Implement `call_transcribe()` with JSON POST, Access headers, a distinct User-Agent, timeout validation, HTTP/URL error translation, and the Cloudflare 1010 distinction. Implement text and JSON rendering and UTF-8 output-file writes.

- [ ] **Step 4: Run Video Transcribe tests and verify GREEN**

Run the focused command. Expected: all Video Transcribe tests pass with no live network use.

- [ ] **Step 5: Commit the Video Transcribe client slice**

```bash
git add skills/video-transcribe/scripts/video_transcribe.py \
  skills/video-transcribe/tests/test_video_transcribe.py
git commit -m "feat(video-transcribe): add shared Access client"
```

### Task 4: Update skill and repository guidance

**Files:**
- Modify: `skills/ocr/SKILL.md`
- Modify: `skills/ocr/README.md`
- Modify: `skills/video-transcribe/SKILL.md`
- Modify: `skills/video-transcribe/README.md`
- Modify: `README.md`

- [ ] **Step 1: Add a documentation regression scan before editing**

Run:

```bash
rg -n 'DOCUMENT_OCR_API_KEY|VIDEO_TRANSCRIBE_API_KEY|X-API-Key|mcp/<api-key>|local installed `api_key`' \
  README.md skills/ocr skills/video-transcribe
```

Expected: matches in current documentation, demonstrating the legacy guidance still exists.

- [ ] **Step 2: Rewrite OCR guidance**

Document first-request company login, `--auth-status`, `--logout`, headless service-token variables, provider profiles as model/language-only configuration, shared library installation, per-origin sessions, and the server-side Access/AUD prerequisite.

- [ ] **Step 3: Rewrite Video Transcribe guidance**

Replace raw credential-bearing curl/MCP examples with commands using `video_transcribe.py`. Include text/JSON output, language and subtitle options, first login, status/logout, headless mode, and server-side cookie boundaries for private videos.

- [ ] **Step 4: Update the repository credential table and GPU-service inventory**

State that OCR, Video Transcribe, and TTS use shared Access; TTS was already migrated; OpenAI `transcribe` remains third-party and out of scope.

- [ ] **Step 5: Prove legacy credential guidance is gone**

Repeat the `rg` command. Expected: no matches in OCR, Video Transcribe, or the root credential table.

- [ ] **Step 6: Validate skill structure and commit documentation**

```bash
python3 /Users/derek/.agents/skills/skill-creator/scripts/quick_validate.py skills/ocr
python3 /Users/derek/.agents/skills/skill-creator/scripts/quick_validate.py skills/video-transcribe
git diff --check
git add README.md skills/ocr/SKILL.md skills/ocr/README.md \
  skills/video-transcribe/SKILL.md skills/video-transcribe/README.md
git commit -m "docs(skills): explain shared Access authentication"
```

Expected: both skills valid and diff check clean.

### Task 5: Verify checkout and installed layouts

**Files:**
- No production file changes expected unless a test exposes an integration defect.

- [ ] **Step 1: Run all focused Python suites**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  skills/stardust-tts/tests skills/ocr/tests skills/video-transcribe/tests
```

Expected: all focused tests pass.

- [ ] **Step 2: Run repository install and sync tests**

```bash
bash tests/install.test.sh
bash tests/sync-from-agents.test.sh
bash tests/sync-to-agents.test.sh
```

Expected: all three scripts pass and the installed test layout contains `lib/stardust_access` alongside the three skills.

- [ ] **Step 3: Install into a scratch agents home and import installed clients**

```bash
scratch="$(mktemp -d)"
STARDUST_AGENTS_HOME="$scratch/.agents" ./install.sh --dest "$scratch/.agents/skills"
PYTHONDONTWRITEBYTECODE=1 python3 "$scratch/.agents/skills/ocr/scripts/ocr.py" --auth-status
PYTHONDONTWRITEBYTECODE=1 python3 "$scratch/.agents/skills/video-transcribe/scripts/video_transcribe.py" --auth-status
```

Expected: imports succeed; both status commands report login required with exit code 1, without “shared client not found”. Remove only the explicit scratch directory afterward.

- [ ] **Step 4: Run secret and legacy-path scans**

```bash
rg -n 'DOCUMENT_OCR_API_KEY|VIDEO_TRANSCRIBE_API_KEY|X-API-Key|mcp/<api-key>' \
  README.md skills/ocr skills/video-transcribe
find skills/ocr skills/video-transcribe lib/stardust_access \
  \( -name '*.pyc' -o -path '*/__pycache__/*' -o -name api_key \) -print
git diff --check
```

Expected: no legacy credential references, no cache/secret artifacts, and no whitespace errors.

- [ ] **Step 5: Probe live Access prerequisites without claiming success**

Use a non-secret User-Agent against each protected-resource metadata endpoint. Expected until server work lands: TTS returns 200; OCR and Video Transcribe may return 404. Record exact results as deployment prerequisites; do not initiate browser login merely to validate client code.

- [ ] **Step 6: Commit any integration-only corrections**

If verification required a narrow fix, test it and commit only the affected files. Otherwise leave the branch clean.

### Task 6: Prepare and deliver the verified learning-group guide

**Files:**
- No repository file required; the source of truth is the updated skill READMEs.

- [ ] **Step 1: Draft the Chinese guide from verified commands**

The message must include:

```text
【Stardust GPU 服务统一鉴权使用指南】

覆盖：OCR、Video Transcribe、TTS。
安装/更新：进入 stardust-skills 后执行 git pull 和 ./install.sh。
员工首次调用：自动打开浏览器，使用 @stardust.ai 邮箱完成登录。
状态检查：分别运行三个 skill 的 --auth-status。
退出登录：分别运行三个 skill 的 --logout；只清除对应服务会话。
Headless：同时设置 CF_ACCESS_CLIENT_ID 和 CF_ACCESS_CLIENT_SECRET。
示例：一条 OCR、一条视频转写、一条 TTS 命令。
注意：每个域名需要独立 Access application/AUD；OCR 和 Video Transcribe 若尚未部署服务端 Access，会在 discovery 阶段报错，不要反复登录。
仓库链接：https://github.com/stardustai/stardust-skills
```

Do not include tokens, local credential paths containing values, or unverified live-success claims.

- [ ] **Step 2: Read the `dingtalk-chat` skill and resolve the learning group**

Use `dws chat +chat-search` or the unique group resolver. Stop on zero or multiple matches; do not select the first result.

- [ ] **Step 3: Send only after repository completion is verified**

Use the current authenticated DWS profile and the confirmed learning-group ID. Honor the runtime confirmation gate with the user's authorization from this request.

- [ ] **Step 4: Read back the exact guide**

Search for the unique title `Stardust GPU 服务统一鉴权使用指南`, or read recent messages from the resolved group. Require a complete result with no failures and preserve the actual message ID and visible text.

- [ ] **Step 5: Report completion accurately**

State code/test/branch status, the three-service inventory, live Access metadata status, and DingTalk delivery readback. Do not call OCR or Video Transcribe production authentication operational if their server-side metadata still returns 404.
