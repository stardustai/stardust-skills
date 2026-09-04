#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

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

function defaultTokenFile() {
  return path.join(process.env.CODEX_HOME || path.join(process.env.HOME || ".", ".codex"), "sso-oidc-onboarding", "api-token");
}

const token = String(args.get("api-token") || process.env.SSO_PROJECTS_CREATE_TOKEN || "").trim();
if (!token) {
  console.error("Missing required --api-token");
  process.exit(2);
}
if (!token.startsWith("sat_")) {
  console.error("Expected a Stardust SSO user API token starting with sat_");
  process.exit(2);
}

const filePath = path.resolve(String(args.get("token-file") || defaultTokenFile()));
fs.mkdirSync(path.dirname(filePath), { recursive: true, mode: 0o700 });
fs.writeFileSync(filePath, `${token}\n`, { mode: 0o600 });
fs.chmodSync(filePath, 0o600);

console.log(JSON.stringify({
  tokenFile: filePath,
  tokenPreview: `${token.slice(0, 12)}...${token.slice(-8)}`
}, null, 2));
