#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/scripts/sync-to-agents.sh"

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

remote_dir="${tmpdir}/remote.git"
seed_dir="${tmpdir}/seed"
work_dir="${tmpdir}/work"
repo_dir="${tmpdir}/repo"
dest_dir="${tmpdir}/agents-skills"

git init -b main "${seed_dir}" >/dev/null
git -C "${seed_dir}" config user.email "test@example.com"
git -C "${seed_dir}" config user.name "Test User"

mkdir -p "${seed_dir}/skills/existing-skill/scripts"
printf 'initial skill body\n' > "${seed_dir}/skills/existing-skill/SKILL.md"
printf 'initial helper\n' > "${seed_dir}/skills/existing-skill/scripts/helper.sh"
printf 'file removed by remote update\n' > "${seed_dir}/skills/existing-skill/removed.txt"
git -C "${seed_dir}" add skills
git -C "${seed_dir}" commit -m "Initial skill" >/dev/null

git clone --bare "${seed_dir}" "${remote_dir}" >/dev/null
git clone "${remote_dir}" "${repo_dir}" >/dev/null

mkdir -p "${dest_dir}/existing-skill/scripts"
printf 'initial skill body\n' > "${dest_dir}/existing-skill/SKILL.md"
printf 'initial helper\n' > "${dest_dir}/existing-skill/scripts/helper.sh"
printf 'file removed by remote update\n' > "${dest_dir}/existing-skill/removed.txt"

git clone "${remote_dir}" "${work_dir}" >/dev/null
git -C "${work_dir}" config user.email "test@example.com"
git -C "${work_dir}" config user.name "Test User"

printf 'updated skill body\n' > "${work_dir}/skills/existing-skill/SKILL.md"
printf 'updated helper\n' > "${work_dir}/skills/existing-skill/scripts/helper.sh"
rm "${work_dir}/skills/existing-skill/removed.txt"
printf 'local config must not sync\n' > "${work_dir}/skills/existing-skill/config.json"
printf 'runtime log must not sync\n' > "${work_dir}/skills/existing-skill/run.log"
mkdir -p "${work_dir}/skills/new-skill"
printf 'new skill body\n' > "${work_dir}/skills/new-skill/SKILL.md"
git -C "${work_dir}" add skills
git -C "${work_dir}" commit -m "Update remote skills" >/dev/null
git -C "${work_dir}" push origin main >/dev/null

bash "${SCRIPT}" --repo "${repo_dir}" --dest "${dest_dir}" --remote origin --branch main

assert_file_contains "${dest_dir}/existing-skill/SKILL.md" "updated skill body"
assert_file_contains "${dest_dir}/existing-skill/scripts/helper.sh" "updated helper"
assert_file_contains "${dest_dir}/new-skill/SKILL.md" "new skill body"
assert_missing "${dest_dir}/existing-skill/removed.txt"
assert_missing "${dest_dir}/existing-skill/config.json"
assert_missing "${dest_dir}/existing-skill/run.log"

if [ -n "$(git -C "${repo_dir}" status --porcelain)" ]; then
  echo "expected test repository to remain clean" >&2
  exit 1
fi

printf 'local helper edit\n' > "${dest_dir}/existing-skill/scripts/local-only.sh"
printf 'remote readme\n' > "${work_dir}/skills/existing-skill/README.md"
git -C "${work_dir}" add skills/existing-skill/README.md
git -C "${work_dir}" commit -m "Add remote readme" >/dev/null
git -C "${work_dir}" push origin main >/dev/null

bash "${SCRIPT}" --repo "${repo_dir}" --dest "${dest_dir}" --remote origin --branch main

assert_file_contains "${dest_dir}/existing-skill/scripts/local-only.sh" "local helper edit"
assert_file_contains "${dest_dir}/existing-skill/README.md" "remote readme"

printf 'local conflicting edit\n' > "${dest_dir}/existing-skill/SKILL.md"
printf 'remote conflicting edit\n' > "${work_dir}/skills/existing-skill/SKILL.md"
git -C "${work_dir}" add skills/existing-skill/SKILL.md
git -C "${work_dir}" commit -m "Add remote conflict" >/dev/null
git -C "${work_dir}" push origin main >/dev/null

if bash "${SCRIPT}" --repo "${repo_dir}" --dest "${dest_dir}" --remote origin --branch main >/dev/null 2>&1; then
  echo "expected sync to fail when local and remote edit the same skill file" >&2
  exit 1
fi

echo "sync-to-agents tests passed"
