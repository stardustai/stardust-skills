# stardust_access

Cloudflare Access client shared by every skill that talks to an
Access-protected internal service.

It is not a skill. It lives outside `skills/` on purpose: `~/.agents/skills/` is
scanned for skills, and a directory in there without a `SKILL.md` puts every
skill at risk, not just its own. `install.sh` mirrors this tree to
`${STARDUST_AGENTS_HOME:-~/.agents}/lib`, so a skill resolves it the same way in
a checkout and once installed.

## Using it from a skill

```python
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
shared = SCRIPT_DIR.parents[2] / "lib" / "stardust_access"   # repo or ~/.agents
sys.path.insert(0, str(shared))

from access_oauth import auth_headers

headers = auth_headers("https://your-service.preseen.ai/v1")
```

That is the whole integration. Every entry point takes `base_url`, and refresh
tokens are stored per origin in one `0600` file, so signing in to one service
does not sign you in to another and signing out of one leaves the rest alone.

Set `STARDUST_ACCESS_TOKEN_FILE` to override the credential-store location.
`STARDUST_TTS_TOKEN_FILE` remains a compatibility alias. The default stays at
`~/.config/stardust-tts/oauth.json` so existing TTS sessions continue to work;
despite the legacy directory name, records inside the file are isolated by
service origin.

Headless workloads set `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET` and the
browser is never opened.

## Before pointing a skill at a new hostname

The service needs its own Access application and its own AUD — never reuse
another service's. Two client-side traps are worth knowing in advance, because
both look like authentication failures and are not:

- **`403 error code: 1010`** is Cloudflare's browser-integrity check, which runs
  *before* Access. A real User-Agent is necessary but not sufficient; it also
  weighs client IP reputation, so the same request can pass from one machine and
  fail from another. For an Access-protected API, disable it for that hostname
  with a Configuration Rule matched on `http.host`.
- **`dig` returning `198.18.x.x`** means a local fake-IP proxy, not DNS. Such a
  client gets 404 on `/cdn-cgi/access/*` and the "Unable to find your Access
  organization" page, which reads like a broken deployment.

The server side, the AUD rule, and the rest of the operational notes are in
`llm-gateway/docs/cloudflare-access-reuse.md`.
