---
name: sso-oidc-onboarding
description: Generate application-side Stardust SSO OIDC integration code and, with explicit authorization, register the OIDC client in SSO and persist the returned secret.
---

# SSO OIDC Onboarding

Use this skill when a user wants to connect an application to Stardust SSO, especially when they say the project has no login code yet or they want Codex to create the callback/login endpoints automatically.

## Outcome

Bring the target application to a working OIDC integration:

- Detect the app framework and existing routing/session/env patterns before editing.
- Add a server-side login start route, callback route, logout route when applicable, and user/session handling.
- Register an OIDC client in Stardust SSO only after the user logs in to SSO, creates a `projects:create` access token, and gives that token to Codex.
- Save the returned one-time `clientSecret` immediately into the target app's local secret mechanism, never into source-controlled files.
- Leave the project with clear env names, verification steps, and rollback notes.

Prefer OIDC authorization code flow. Use PKCE for browser/public clients; use a confidential client with server-side `clientSecret` for server-rendered or backend-owned apps.

## Required Inputs

Infer these from the codebase when possible, otherwise ask only for the missing high-risk values:

- SSO issuer, default `https://sso.corpintra.rosettalab.top`.
- Public service URL, for example `https://app.example.com`.
- Callback URL, usually `${serviceUrl}/sso/callback`, but match existing route conventions.
- App display name and optional description.
- Whether the app can safely store a server-side secret.
- Authorization to mutate SSO through a user API token with `projects:create` scope. Ask the user to open SSO in a browser, log in, create an access token with `projects:create`, and give the token to Codex. Codex should save it locally before registering OIDC clients.

Do not invent production domains, callback URLs, session secrets, or SSO credentials.

## Registration

Read [references/stardust-sso-api.md](references/stardust-sso-api.md) before calling SSO APIs.

Use `scripts/register-oidc-client.mjs` when registering a client. It handles the correct endpoint shape and writes the one-time secret to an env file. By default it reads the saved user API token from `~/.codex/sso-oidc-onboarding/api-token`. Do not log the full `clientSecret`.

Before registration, guide the user through token setup:

1. Give the user this clickable link: `https://sso.corpintra.rosettalab.top/?tab=tokens&scope=projects:create&tokenName=Codex%20OIDC%20Onboarding`.
2. Tell the user to open the link, log in if prompted, and click the generate access token button. The page should already be on the access-token screen with `projects:create` selected.
3. Ask the user to paste the generated `sat_...` token back into Codex.
4. Save it locally with:

```bash
node ~/.codex/skills/sso-oidc-onboarding/scripts/save-api-token.mjs \
  --api-token "<sat_token>"
```

The saved token file is local-only and should not be committed.

Typical admin registration:

```bash
node ~/.codex/skills/sso-oidc-onboarding/scripts/register-oidc-client.mjs \
  --sso-url https://sso.corpintra.rosettalab.top \
  --name "业务系统" \
  --service-url https://app.example.com \
  --callback-url https://app.example.com/sso/callback \
  --client-id app-example \
  --env-file .env.local
```

Use `--self-service` only when the current user should create a personal/custom integration through `/api/integrations` instead of an admin-managed company project.

## Code Generation Guidance

Inspect the target project first:

- Package manager and framework: `package.json`, lockfiles, router files, server entrypoint.
- Existing auth/session primitives: cookies, JWT, server sessions, middleware, guards.
- Env handling: `.env.example`, config modules, deployment manifests.
- Test style: unit, integration, e2e, or route tests.

Implement the smallest framework-native integration:

- Add env variables for issuer, client id, client secret, callback URL, and post-login redirect.
- Add `/sso/login` or equivalent route that redirects to `${issuer}/oauth/authorize`.
- Generate and persist `state`; use `nonce` for OIDC ID token validation.
- Use PKCE S256 for public clients and for confidential clients when the local framework makes it straightforward.
- Add `/sso/callback` that validates `state`, exchanges code at `${issuer}/oauth/token`, verifies the ID token/JWKS, optionally calls userinfo, and creates the app's local session.
- Add logout that clears local session and redirects to `${issuer}/oauth/logout` when the app stores an ID token or has a registered post-logout URL.
- Protect routes using the app's existing middleware/guard style.

Never put `clientSecret` into frontend bundles, checked-in config, logs, screenshots, or generated docs. Update `.env.example` with placeholder names only.

## Verification

After implementation:

- Run the target project's relevant tests and type checks.
- Exercise login/callback locally when possible with a dev callback URL registered in SSO.
- Confirm callback URL exact-match behavior, including scheme, host, port, path, and trailing slash.
- Confirm `.gitignore` protects the file containing the real secret.
- Summarize the created SSO client id, callback URL, env variables changed, and tests run. Mask secrets.
