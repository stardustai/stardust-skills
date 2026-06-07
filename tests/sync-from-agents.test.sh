#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/scripts/sync-from-agents.sh"

assert_file_contains() {
  local file="$1"
  local expected="$2"

  if ! grep -Fq "${expected}" "${file}"; then
    echo "expected ${file} to contain: ${expected}" >&2
    return 1
  fi
}

assert_missing() {
  local path="$1"

  if [ -e "${path}" ]; then
    echo "expected ${path} to be absent" >&2
    return 1
  fi
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

source_dir="${tmpdir}/agents-skills"
repo_dir="${tmpdir}/repo"

mkdir -p "${source_dir}/existing-skill/scripts"
mkdir -p "${source_dir}/extra-skill"
mkdir -p "${repo_dir}/skills/existing-skill"

printf 'new skill body\n' > "${source_dir}/existing-skill/SKILL.md"
printf 'script body\n' > "${source_dir}/existing-skill/scripts/helper.sh"
printf 'local config\n' > "${source_dir}/existing-skill/config.json"
printf 'old stale file\n' > "${repo_dir}/skills/existing-skill/old.txt"
printf 'extra body\n' > "${source_dir}/extra-skill/SKILL.md"

bash "${SCRIPT}" --source "${source_dir}" --repo "${repo_dir}"

assert_file_contains "${repo_dir}/skills/existing-skill/SKILL.md" "new skill body"
assert_file_contains "${repo_dir}/skills/existing-skill/scripts/helper.sh" "script body"
assert_missing "${repo_dir}/skills/existing-skill/old.txt"
assert_missing "${repo_dir}/skills/existing-skill/config.json"
assert_missing "${repo_dir}/skills/extra-skill"

echo "sync-from-agents tests passed"
