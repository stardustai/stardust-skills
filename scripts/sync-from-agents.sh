#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${HOME}/.agents/skills"
REPO="${ROOT}"

usage() {
  cat <<'EOF'
Usage: scripts/sync-from-agents.sh [--source DIR] [--repo DIR]

Sync matching skill directories from ~/.agents/skills back into this repository.
Only skill directories that already exist under the repository's skills/ folder
are updated.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source)
      SOURCE="${2:?missing value for --source}"
      shift 2
      ;;
    --repo)
      REPO="${2:?missing value for --repo}"
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

if [ ! -d "${SOURCE}" ]; then
  echo "source skills directory does not exist: ${SOURCE}" >&2
  exit 1
fi

if [ ! -d "${REPO}/skills" ]; then
  echo "repository skills directory does not exist: ${REPO}/skills" >&2
  exit 1
fi

updated=0

for repo_skill in "${REPO}"/skills/*; do
  [ -d "${repo_skill}" ] || continue

  name="$(basename "${repo_skill}")"
  source_skill="${SOURCE}/${name}"

  if [ ! -d "${source_skill}" ]; then
    echo "missing source skill: ${source_skill}" >&2
    exit 1
  fi

  rsync -a --checksum --delete --delete-excluded \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'config.json' \
    --exclude '.storage_state.json' \
    --exclude '.chrome-profile' \
    --exclude 'outputs' \
    --exclude 'runs' \
    --exclude '*.xlsx' \
    --exclude '*.xlsm' \
    --exclude '*.jsonl' \
    --exclude '*.log' \
    "${source_skill}/" "${repo_skill}/"

  echo "updated ${name}"
  updated=$((updated + 1))
done

if [ "${updated}" -eq 0 ]; then
  echo "no skill directories found under ${REPO}/skills" >&2
  exit 1
fi
