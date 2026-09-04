#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 1) {
  const key = process.argv[index];
  if (!key.startsWith("--")) continue;
  const next = process.argv[index + 1];
  if (!next || next.startsWith("--")) {
    args.set(key.slice(2), "true");
  } else {
    args.set(key.slice(2), next);
    index += 1;
  }
}

function required(name) {
  const value = String(args.get(name) || process.env[name.toUpperCase().replaceAll("-", "_")] || "").trim();
  if (!value) {
    console.error(`Missing required --${name}`);
    process.exit(2);
  }
  return value;
}

function optional(name, fallback = "") {
  return String(args.get(name) || process.env[name.toUpperCase().replaceAll("-", "_")] || fallback).trim();
}

function defaultTokenFile() {
  return path.join(process.env.CODEX_HOME || path.join(process.env.HOME || ".", ".codex"), "sso-oidc-onboarding", "api-token");
}

function readSavedApiToken() {
  const filePath = optional("token-file", defaultTokenFile());
  if (!fs.existsSync(filePath)) return "";
  return fs.readFileSync(filePath, "utf8").trim();
}

function cookieHeader(raw) {
  if (raw.includes("=")) return raw;
  return `stardust_sso_sid=${raw}`;
}

function hostOf(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return "";
  }
}

function appendEnv(filePath, values, force) {
  const absolute = path.resolve(filePath);
  const existing = fs.existsSync(absolute) ? fs.readFileSync(absolute, "utf8") : "";
  const protectedKeys = Object.keys(values).filter((key) => new RegExp(`^${key}=`, "m").test(existing));
  if (protectedKeys.length && !force) {
    throw new Error(`Refusing to overwrite existing env keys without --force: ${protectedKeys.join(", ")}`);
  }
  let next = existing;
  for (const [key, value] of Object.entries(values)) {
    const line = `${key}=${JSON.stringify(value)}\n`;
    if (new RegExp(`^${key}=.*$`, "m").test(next)) {
      next = next.replace(new RegExp(`^${key}=.*$`, "m"), line.trimEnd());
    } else {
      if (next && !next.endsWith("\n")) next += "\n";
      next += line;
    }
  }
  fs.writeFileSync(absolute, next, { mode: 0o600 });
  return absolute;
}

const ssoUrl = required("sso-url").replace(/\/$/, "");
const name = required("name");
const callbackUrl = required("callback-url");
const serviceUrl = optional("service-url", new URL(callbackUrl).origin);
const sessionCookie = optional("session-cookie");
const provisioningToken = optional("provisioning-token") || optional("api-token") || readSavedApiToken();
if (!sessionCookie && !provisioningToken) {
  console.error("Missing required --api-token, saved token file, --provisioning-token, or --session-cookie");
  process.exit(2);
}
const publicClient = args.has("public-client");
const selfService = args.has("self-service");
const envFile = optional("env-file", ".env.local");
const force = args.has("force");
const scopes = optional("scopes", "openid,profile,email,groups").split(",").map((item) => item.trim()).filter(Boolean);
const redirectUris = optional("redirect-uris", callbackUrl).split(",").map((item) => item.trim()).filter(Boolean);

const body = selfService ? {
  name,
  description: optional("description", "Stardust SSO OIDC integration"),
  type: "oidc",
  category: optional("category", "business"),
  serviceUrl,
  callbackUrl,
  redirectUris,
  allowedDomains: optional("allowed-domains", hostOf(serviceUrl) || hostOf(callbackUrl)).split(",").map((item) => item.trim()).filter(Boolean),
  publicClient,
  scopes
} : {
  name,
  description: optional("description", "公司统一接入项目"),
  protocol: "oidc",
  category: optional("category", "business"),
  serviceUrl,
  callbackUrl,
  redirectUris,
  clientId: optional("client-id", name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")),
  publicClient,
  scopes,
  groups: optional("groups").split(",").map((item) => item.trim()).filter(Boolean)
};

const endpoint = `${ssoUrl}${selfService ? "/api/integrations" : "/api/company-projects"}`;
const response = await fetch(endpoint, {
  method: "POST",
  headers: {
    "content-type": "application/json",
    ...(provisioningToken ? { "authorization": `Bearer ${provisioningToken}` } : {}),
    ...(sessionCookie ? { "cookie": cookieHeader(sessionCookie) } : {})
  },
  body: JSON.stringify(body)
});

const payload = await response.json().catch(() => ({}));
if (!response.ok) {
  console.error(`SSO registration failed: HTTP ${response.status}`);
  console.error(payload.message || JSON.stringify(payload));
  process.exit(1);
}

const record = payload.project || payload.integration || {};
const clientId = record.clientId;
const clientSecret = record.clientSecret || "";
if (!clientId) {
  console.error("SSO registration response did not include clientId");
  process.exit(1);
}

const savedPath = appendEnv(envFile, {
  SSO_ISSUER: ssoUrl,
  OIDC_CLIENT_ID: clientId,
  ...(clientSecret ? { OIDC_CLIENT_SECRET: clientSecret } : {}),
  OIDC_CALLBACK_URL: callbackUrl
}, force);

console.log(JSON.stringify({
  id: record.id || "",
  clientId,
  clientSecretPreview: record.clientSecretPreview || (clientSecret ? `${clientSecret.slice(0, 10)}...${clientSecret.slice(-6)}` : "PKCE public client"),
  callbackUrl,
  envFile: savedPath
}, null, 2));
