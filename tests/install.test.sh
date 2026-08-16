#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/install.sh"

assert_file_contains() {
  local file="$1"
  local expected="$2"

  if ! grep -Fq "${expected}" "${file}"; then
    echo "expected ${file} to contain: ${expected}" >&2
    return 1
  fi
}

assert_exists() {
  local path="$1"

  if [ ! -e "${path}" ]; then
    echo "expected ${path} to exist" >&2
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

dest_dir="${tmpdir}/agents-skills"
agents_home="${tmpdir}/agents-home"
launch_agents_dir="${tmpdir}/LaunchAgents"
plist_path="${launch_agents_dir}/com.stardust.skills.daily-sync.plist"

bash "${SCRIPT}" --dest "${dest_dir}"

assert_exists "${dest_dir}/stardust-interview/SKILL.md"
assert_missing "${dest_dir}/dingtalk-minutes-access-request/config.json"
assert_missing "${dest_dir}/video-transcribe/api_key"

STARDUST_AGENTS_HOME="${agents_home}" \
STARDUST_SKILLS_LAUNCH_AGENTS_DIR="${launch_agents_dir}" \
STARDUST_SKILLS_SKIP_LAUNCHCTL=1 \
  bash "${SCRIPT}" --dest "${dest_dir}" --daily-sync --daily-sync-hour 3 --daily-sync-minute 17

assert_exists "${plist_path}"
assert_file_contains "${plist_path}" "<string>com.stardust.skills.daily-sync</string>"
assert_file_contains "${plist_path}" "<string>${ROOT}/scripts/sync-to-agents.sh</string>"
assert_file_contains "${plist_path}" "<string>--repo</string>"
assert_file_contains "${plist_path}" "<string>${ROOT}</string>"
assert_file_contains "${plist_path}" "<string>--dest</string>"
assert_file_contains "${plist_path}" "<string>${dest_dir}</string>"
assert_file_contains "${plist_path}" "<integer>3</integer>"
assert_file_contains "${plist_path}" "<integer>17</integer>"
assert_file_contains "${plist_path}" "<string>${agents_home}/logs/stardust-skills/daily-sync.log</string>"
assert_file_contains "${plist_path}" "<string>${agents_home}/logs/stardust-skills/daily-sync.err.log</string>"

if bash "${SCRIPT}" --dest "${dest_dir}" --daily-sync --daily-sync-hour 24 >/dev/null 2>&1; then
  echo "expected invalid daily sync hour to fail" >&2
  exit 1
fi

if bash "${SCRIPT}" --dest "${dest_dir}" --daily-sync --daily-sync-minute 60 >/dev/null 2>&1; then
  echo "expected invalid daily sync minute to fail" >&2
  exit 1
fi

echo "install tests passed"
