#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${HOME}/.agents/skills"
AGENTS_HOME="${STARDUST_AGENTS_HOME:-${HOME}/.agents}"
LAUNCH_AGENTS_DIR="${STARDUST_SKILLS_LAUNCH_AGENTS_DIR:-${HOME}/Library/LaunchAgents}"
DAILY_SYNC=0
DAILY_SYNC_HOUR=9
DAILY_SYNC_MINUTE=0
PLIST_LABEL="com.stardust.skills.daily-sync"
SKIP_LAUNCHCTL="${STARDUST_SKILLS_SKIP_LAUNCHCTL:-0}"

usage() {
  cat <<'EOF'
Usage: ./install.sh [--dest DIR] [--daily-sync] [--daily-sync-hour HOUR] [--daily-sync-minute MINUTE]

Install repository skills into ~/.agents/skills.

Options:
  --dest DIR                 Install skills into DIR instead of ~/.agents/skills.
  --daily-sync               Install a macOS LaunchAgent that runs scripts/sync-to-agents.sh daily.
  --daily-sync-hour HOUR     Daily sync hour in 24-hour local time. Default: 9.
  --daily-sync-minute MIN    Daily sync minute. Default: 0.
  -h, --help                 Show this help.

Daily sync only updates installed skills from the GitHub/main repository version.
It does not copy local installed-skill changes back to the repository and does
not push commits.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dest)
      DEST="${2:?missing value for --dest}"
      shift 2
      ;;
    --daily-sync)
      DAILY_SYNC=1
      shift
      ;;
    --daily-sync-hour)
      DAILY_SYNC_HOUR="${2:?missing value for --daily-sync-hour}"
      shift 2
      ;;
    --daily-sync-minute)
      DAILY_SYNC_MINUTE="${2:?missing value for --daily-sync-minute}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "${DAILY_SYNC_HOUR}" in
  ''|*[!0-9]*)
    echo "--daily-sync-hour must be an integer from 0 to 23" >&2
    exit 2
    ;;
esac

case "${DAILY_SYNC_MINUTE}" in
  ''|*[!0-9]*)
    echo "--daily-sync-minute must be an integer from 0 to 59" >&2
    exit 2
    ;;
esac

if [ "${DAILY_SYNC_HOUR}" -gt 23 ]; then
  echo "--daily-sync-hour must be an integer from 0 to 23" >&2
  exit 2
fi

if [ "${DAILY_SYNC_MINUTE}" -gt 59 ]; then
  echo "--daily-sync-minute must be an integer from 0 to 59" >&2
  exit 2
fi

xml_escape() {
  local value="$1"

  value="${value//&/&amp;}"
  value="${value//</&lt;}"
  value="${value//>/&gt;}"
  value="${value//\"/&quot;}"
  value="${value//\'/&apos;}"

  printf '%s' "${value}"
}

install_daily_sync() {
  local log_dir="${AGENTS_HOME}/logs/stardust-skills"
  local plist_path="${LAUNCH_AGENTS_DIR}/${PLIST_LABEL}.plist"
  local tmp_plist
  local uid

  mkdir -p "${LAUNCH_AGENTS_DIR}" "${log_dir}"
  tmp_plist="$(mktemp)"

  cat > "${tmp_plist}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$(xml_escape "${ROOT}/scripts/sync-to-agents.sh")</string>
    <string>--repo</string>
    <string>$(xml_escape "${ROOT}")</string>
    <string>--dest</string>
    <string>$(xml_escape "${DEST}")</string>
    <string>--remote</string>
    <string>origin</string>
    <string>--branch</string>
    <string>main</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>${DAILY_SYNC_HOUR}</integer>
    <key>Minute</key>
    <integer>${DAILY_SYNC_MINUTE}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$(xml_escape "${log_dir}/daily-sync.log")</string>
  <key>StandardErrorPath</key>
  <string>$(xml_escape "${log_dir}/daily-sync.err.log")</string>
</dict>
</plist>
EOF

  mv "${tmp_plist}" "${plist_path}"
  echo "installed daily sync LaunchAgent ${plist_path}"

  if [ "${SKIP_LAUNCHCTL}" = "1" ]; then
    echo "skipped launchctl load because STARDUST_SKILLS_SKIP_LAUNCHCTL=1"
    return
  fi

  if command -v launchctl >/dev/null 2>&1; then
    uid="$(id -u)"
    launchctl bootout "gui/${uid}" "${plist_path}" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/${uid}" "${plist_path}"
    launchctl enable "gui/${uid}/${PLIST_LABEL}"
    echo "loaded daily sync LaunchAgent ${PLIST_LABEL}"
  else
    echo "launchctl not found; plist installed but not loaded" >&2
  fi
}

mkdir -p "${DEST}"

# Code shared by several skills (currently the Cloudflare Access client) lives
# outside skills/ so that ${DEST} contains only real skills — a directory in
# there without a SKILL.md is a risk to every skill, not just its own.  Skills
# resolve it as <parents[2]>/lib, which is the repository root in a checkout
# and ${AGENTS_HOME} once installed, so both trees must mirror each other.
if [ -d "${ROOT}/lib" ]; then
  mkdir -p "${AGENTS_HOME}/lib"
  rsync -a --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    "${ROOT}/lib/" "${AGENTS_HOME}/lib/"
  echo "installed shared lib -> ${AGENTS_HOME}/lib"
fi

for skill in "${ROOT}"/skills/*; do
  [ -d "${skill}" ] || continue
  name="$(basename "${skill}")"
  mkdir -p "${DEST}/${name}"
  rsync -a --delete \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'api_key' \
    --exclude 'config.json' \
    --exclude '.storage_state.json' \
    --exclude '.chrome-profile' \
    --exclude 'outputs' \
    --exclude 'runs' \
    --exclude '*.xlsx' \
    --exclude '*.xlsm' \
    --exclude '*.jsonl' \
    --exclude '*.log' \
    "${skill}/" "${DEST}/${name}/"
  echo "installed ${name}"
done

if [ "${DAILY_SYNC}" -eq 1 ]; then
  install_daily_sync
fi
