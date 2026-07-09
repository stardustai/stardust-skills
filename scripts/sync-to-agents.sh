#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${ROOT}"
DEST="${HOME}/.agents/skills"
REMOTE="origin"
BRANCH="main"

usage() {
  cat <<'EOF'
Usage: scripts/sync-to-agents.sh [--repo DIR] [--dest DIR] [--remote NAME] [--branch NAME]

Fetch the configured Git remote, fast-forward the local repository when GitHub
has new skill updates, then sync repository skills into ~/.agents/skills.

The script stops instead of syncing when the repository has uncommitted changes,
is on a different branch, cannot fast-forward safely, or local installed skills
already differ from the current repository copy.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo)
      REPO="${2:?missing value for --repo}"
      shift 2
      ;;
    --dest)
      DEST="${2:?missing value for --dest}"
      shift 2
      ;;
    --remote)
      REMOTE="${2:?missing value for --remote}"
      shift 2
      ;;
    --branch)
      BRANCH="${2:?missing value for --branch}"
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

if [ ! -d "${REPO}/.git" ]; then
  echo "repository git directory does not exist: ${REPO}/.git" >&2
  exit 1
fi

if [ ! -d "${REPO}/skills" ]; then
  echo "repository skills directory does not exist: ${REPO}/skills" >&2
  exit 1
fi

if [ -n "$(git -C "${REPO}" status --porcelain)" ]; then
  echo "repository has uncommitted changes; refusing to sync local skills" >&2
  exit 1
fi

current_branch="$(git -C "${REPO}" rev-parse --abbrev-ref HEAD)"
if [ "${current_branch}" != "${BRANCH}" ]; then
  echo "repository is on ${current_branch}, expected ${BRANCH}" >&2
  exit 1
fi

for repo_skill in "${REPO}"/skills/*; do
  [ -d "${repo_skill}" ] || continue

  name="$(basename "${repo_skill}")"
  dest_skill="${DEST}/${name}"
  [ -d "${dest_skill}" ] || continue

  if rsync -a --delete --delete-excluded --dry-run --itemize-changes \
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
    "${repo_skill}/" "${dest_skill}/" | grep -q .; then
    echo "local installed skill differs from repository: ${dest_skill}" >&2
    echo "run scripts/sync-from-agents.sh first if this local change should update the repository" >&2
    exit 1
  fi
done

git -C "${REPO}" fetch "${REMOTE}" "${BRANCH}"

local_ref="$(git -C "${REPO}" rev-parse "${BRANCH}")"
remote_ref="$(git -C "${REPO}" rev-parse "${REMOTE}/${BRANCH}")"
base_ref="$(git -C "${REPO}" merge-base "${BRANCH}" "${REMOTE}/${BRANCH}")"

if [ "${local_ref}" = "${remote_ref}" ]; then
  echo "repository already up to date"
elif [ "${base_ref}" = "${local_ref}" ]; then
  git -C "${REPO}" merge --ff-only "${REMOTE}/${BRANCH}"
  echo "repository fast-forwarded to ${remote_ref}"
elif [ "${base_ref}" = "${remote_ref}" ]; then
  echo "local ${BRANCH} is ahead of ${REMOTE}/${BRANCH}; refusing to sync" >&2
  exit 1
else
  echo "local ${BRANCH} and ${REMOTE}/${BRANCH} have diverged; refusing to sync" >&2
  exit 1
fi

mkdir -p "${DEST}"

updated=0

for repo_skill in "${REPO}"/skills/*; do
  [ -d "${repo_skill}" ] || continue

  name="$(basename "${repo_skill}")"
  dest_skill="${DEST}/${name}"
  mkdir -p "${dest_skill}"

  rsync -a --delete --delete-excluded \
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
    "${repo_skill}/" "${dest_skill}/"

  echo "synced ${name}"
  updated=$((updated + 1))
done

if [ "${updated}" -eq 0 ]; then
  echo "no skill directories found under ${REPO}/skills" >&2
  exit 1
fi
