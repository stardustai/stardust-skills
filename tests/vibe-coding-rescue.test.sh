#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/skills/vibe-coding-rescue/scripts/collect_rescue_context.py"

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

project="${tmpdir}/broken-ai-app"
mkdir -p "${project}/src"

cat >"${project}/package.json" <<'JSON'
{
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "test": "vitest run",
    "build": "tsc -b && vite build"
  },
  "dependencies": {
    "react": "latest",
    "vite": "latest"
  },
  "devDependencies": {
    "typescript": "latest",
    "vitest": "latest"
  }
}
JSON

cat >"${project}/README.md" <<'MD'
# Broken AI App

```bash
pnpm install
pnpm dev
pnpm test
```
MD

cat >"${project}/.env.example" <<'ENV'
DATABASE_URL=example-db-url
OPENAI_API_KEY=example-api-key
ENV

cat >"${project}/src/config.ts" <<'TS'
export const databaseUrl = process.env.DATABASE_URL;
export const apiKey = process.env.OPENAI_API_KEY;
export const runtimeToken = process.env.SERVICE_TOKEN;
TS

touch "${project}/pnpm-lock.yaml"

output="${tmpdir}/rescue-context.json"
python3 "${SCRIPT}" "${project}" --output "${output}"

python3 - "${output}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert data["root"].endswith("broken-ai-app"), data["root"]
assert "pnpm" in data["package_managers"], data["package_managers"]
assert "pnpm-lock.yaml" in data["lockfiles"], data["lockfiles"]
assert data["frameworks"]["frontend"] == ["React", "Vite"], data["frameworks"]
assert data["frameworks"]["test"] == ["Vitest"], data["frameworks"]

root_pkg = next(item for item in data["package_scripts"] if item["path"] == "package.json")
assert root_pkg["scripts"]["dev"] == "vite --host 0.0.0.0"
assert root_pkg["scripts"]["test"] == "vitest run"
assert root_pkg["scripts"]["build"] == "tsc -b && vite build"

readme_commands = [item["command"] for item in data["readme_commands"]]
assert "pnpm install" in readme_commands, readme_commands
assert "pnpm dev" in readme_commands, readme_commands

env_names = {item["name"] for item in data["env"]["referenced_variables"]}
assert {"DATABASE_URL", "OPENAI_API_KEY", "SERVICE_TOKEN"} <= env_names, env_names
example_names = set(data["env"]["example_variables"])
assert {"DATABASE_URL", "OPENAI_API_KEY"} <= example_names, example_names

risk_codes = {item["code"] for item in data["risk_signals"]}
assert "env-referenced-without-example" in risk_codes, risk_codes
assert "sensitive-env-name-referenced" in risk_codes, risk_codes

serialized = json.dumps(data, ensure_ascii=False)
assert "example-api-key" not in serialized
assert "example-db-url" not in serialized
PY

echo "vibe-coding-rescue tests passed"
