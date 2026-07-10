#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${ROOT}"
DEST="${HOME}/.agents/skills"
REMOTE="origin"
BRANCH="main"
STATE_FILE=""

usage() {
  cat <<'EOF'
Usage: scripts/sync-to-agents.sh [--repo DIR] [--dest DIR] [--remote NAME] [--branch NAME] [--state-file FILE]

Fetch the configured Git remote, fast-forward the local repository when GitHub
has new skill updates, then sync repository skills into ~/.agents/skills.

The script stops instead of syncing when the repository has uncommitted changes,
is on a different branch, cannot fast-forward safely, or local installed skill
changes conflict with GitHub changes.
EOF
}

RSYNC_EXCLUDES=(
  --exclude 'node_modules'
  --exclude '__pycache__'
  --exclude '*.pyc'
  --exclude '.env'
  --exclude 'config.json'
  --exclude '.storage_state.json'
  --exclude '.chrome-profile'
  --exclude 'outputs'
  --exclude 'runs'
  --exclude '*.xlsx'
  --exclude '*.xlsm'
  --exclude '*.jsonl'
  --exclude '*.log'
)

sync_filtered() {
  local source_dir="$1"
  local dest_dir="$2"

  mkdir -p "${dest_dir}"
  rsync -a --checksum --delete --delete-excluded "${RSYNC_EXCLUDES[@]}" "${source_dir}/" "${dest_dir}/"
}

copy_repo_skills_at_commit() {
  local commit="$1"
  local dest_dir="$2"
  local archive_dir

  archive_dir="$(mktemp -d)"
  git -C "${REPO}" archive "${commit}" skills | tar -x -C "${archive_dir}"
  sync_filtered "${archive_dir}/skills" "${dest_dir}"
  rm -rf "${archive_dir}"
}

has_changes() {
  local repo_dir="$1"

  [ -n "$(git -C "${repo_dir}" status --porcelain)" ]
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
    --state-file)
      STATE_FILE="${2:?missing value for --state-file}"
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

if [ -z "${STATE_FILE}" ]; then
  STATE_FILE="${DEST}/.stardust-skills-sync-state"
fi

local_ref_before_fetch="$(git -C "${REPO}" rev-parse "${BRANCH}")"
base_ref="${local_ref_before_fetch}"

if [ -f "${STATE_FILE}" ]; then
  saved_ref="$(sed -n 's/^commit=//p' "${STATE_FILE}" | tail -1)"
  if [ -n "${saved_ref}" ] && git -C "${REPO}" cat-file -e "${saved_ref}^{commit}" 2>/dev/null; then
    base_ref="${saved_ref}"
  fi
fi

git -C "${REPO}" fetch "${REMOTE}" "${BRANCH}"

local_ref="$(git -C "${REPO}" rev-parse "${BRANCH}")"
remote_ref="$(git -C "${REPO}" rev-parse "${REMOTE}/${BRANCH}")"
merge_base_ref="$(git -C "${REPO}" merge-base "${BRANCH}" "${REMOTE}/${BRANCH}")"

if [ "${local_ref}" = "${remote_ref}" ]; then
  echo "repository already up to date"
elif [ "${merge_base_ref}" = "${local_ref}" ]; then
  git -C "${REPO}" merge --ff-only "${REMOTE}/${BRANCH}"
  echo "repository fast-forwarded to ${remote_ref}"
elif [ "${merge_base_ref}" = "${remote_ref}" ]; then
  echo "local ${BRANCH} is ahead of ${REMOTE}/${BRANCH}; refusing to sync" >&2
  exit 1
else
  echo "local ${BRANCH} and ${REMOTE}/${BRANCH} have diverged; refusing to sync" >&2
  exit 1
fi

mkdir -p "${DEST}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

merge_dir="${tmpdir}/merge"
mkdir -p "${merge_dir}"
git -C "${merge_dir}" init -b main >/dev/null
git -C "${merge_dir}" config user.email "sync-to-agents@example.invalid"
git -C "${merge_dir}" config user.name "sync-to-agents"

copy_repo_skills_at_commit "${base_ref}" "${merge_dir}/skills"
git -C "${merge_dir}" add skills
git -C "${merge_dir}" commit -m "base skills" >/dev/null

git -C "${merge_dir}" switch -c local >/dev/null

for repo_skill in "${merge_dir}"/skills/* "${REPO}"/skills/*; do
  [ -d "${repo_skill}" ] || continue

  name="$(basename "${repo_skill}")"
  dest_skill="${DEST}/${name}"
  [ -d "${dest_skill}" ] || continue

  sync_filtered "${dest_skill}" "${merge_dir}/skills/${name}"
done

git -C "${merge_dir}" add -A skills
if has_changes "${merge_dir}"; then
  git -C "${merge_dir}" commit -m "local installed skills" >/dev/null
fi

git -C "${merge_dir}" switch -c remote main >/dev/null
sync_filtered "${REPO}/skills" "${merge_dir}/skills"
git -C "${merge_dir}" add -A skills
if has_changes "${merge_dir}"; then
  git -C "${merge_dir}" commit -m "remote repository skills" >/dev/null
fi

git -C "${merge_dir}" switch local >/dev/null
if ! git -C "${merge_dir}" merge --no-edit remote >/dev/null; then
  echo "local installed skill changes conflict with GitHub skill updates; refusing to sync" >&2
  git -C "${merge_dir}" status --short >&2
  exit 1
fi

updated=0

for repo_skill in "${REPO}"/skills/*; do
  [ -d "${repo_skill}" ] || continue

  name="$(basename "${repo_skill}")"
  dest_skill="${DEST}/${name}"
  merged_skill="${merge_dir}/skills/${name}"
  [ -d "${merged_skill}" ] || continue

  sync_filtered "${merged_skill}" "${dest_skill}"

  echo "synced ${name}"
  updated=$((updated + 1))
done

if [ "${updated}" -eq 0 ]; then
  echo "no skill directories found under ${REPO}/skills" >&2
  exit 1
fi

printf 'repo=%s\ncommit=%s\n' "${REPO}" "$(git -C "${REPO}" rev-parse "${BRANCH}")" > "${STATE_FILE}"
