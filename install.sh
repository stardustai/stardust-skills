#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${HOME}/.agents/skills"

mkdir -p "${DEST}"

for skill in "${ROOT}"/skills/*; do
  [ -d "${skill}" ] || continue
  name="$(basename "${skill}")"
  mkdir -p "${DEST}/${name}"
  rsync -a --delete \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'config.json' \
    --exclude '.storage_state.json' \
    --exclude '.chrome-profile' \
    --exclude 'outputs' \
    --exclude '*.xlsx' \
    --exclude '*.xlsm' \
    --exclude '*.jsonl' \
    "${skill}/" "${DEST}/${name}/"
  echo "installed ${name}"
done
