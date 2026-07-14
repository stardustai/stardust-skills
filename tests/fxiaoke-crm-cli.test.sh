#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

assert_file() {
  local path="$1"

  if [ ! -f "${path}" ]; then
    printf 'FAIL [file]: expected regular file: %s\n' "${path}" >&2
    return 1
  fi
}

assert_absent() {
  local path="$1"

  if [ -e "${path}" ] || [ -L "${path}" ]; then
    printf 'FAIL [migration]: expected path and symlink to be absent: %s\n' "${path}" >&2
    return 1
  fi
}

assert_contains() {
  local group="$1"
  local file="$2"
  local expected="$3"

  if ! grep -Fq -- "${expected}" "${file}"; then
    printf 'FAIL [%s]: expected %s to contain: %s\n' "${group}" "${file}" "${expected}" >&2
    return 1
  fi
}

assert_frontmatter_name() {
  local file="$1"
  local expected="$2"

  if ! awk '
    NR == 1 && $0 == "---" { in_frontmatter = 1; next }
    in_frontmatter && $0 == "---" { exit }
    in_frontmatter { print }
  ' "${file}" | grep -Eq "^[[:space:]]*name:[[:space:]]*${expected}[[:space:]]*$"; then
    printf 'FAIL [frontmatter]: expected YAML name %s in: %s\n' "${expected}" "${file}" >&2
    return 1
  fi
}

assert_shell_command() {
  local file="$1"
  local expected="$2"

  if ! awk -v expected="${expected}" '
    function trim(value) {
      sub(/^[[:space:]]+/, "", value)
      sub(/[[:space:]]+$/, "", value)
      return value
    }

    /^[[:space:]]*```(bash|sh|shell|zsh)[[:space:]]*$/ { in_shell_fence = 1; next }
    in_shell_fence && /^[[:space:]]*```[[:space:]]*$/ { in_shell_fence = 0; next }
    {
      line = trim($0)
      sub(/^\$[[:space:]]+/, "", line)
      if (line == expected && (in_shell_fence || $0 !~ /[[:alnum:]].*[[:alnum:]].*[[:alnum:]]/ || trim($0) == expected || trim($0) == "$ " expected)) {
        found = 1
      }
    }
    END { exit(found ? 0 : 1) }
  ' "${file}"; then
    printf 'FAIL [command]: expected shell example or full command line in %s: %s\n' "${file}" "${expected}" >&2
    return 1
  fi
}

assert_markdown_heading() {
  local file="$1"
  local expected="$2"

  if ! awk -v expected="${expected}" '
    /^#{1,6}[[:space:]]+/ {
      heading = $0
      sub(/^#{1,6}[[:space:]]+/, "", heading)
      sub(/[[:space:]]+#+[[:space:]]*$/, "", heading)
      if (heading == expected) found = 1
    }
    END { exit(found ? 0 : 1) }
  ' "${file}"; then
    printf 'FAIL [metric]: expected Markdown heading in %s: %s\n' "${file}" "${expected}" >&2
    return 1
  fi
}

readme_section() {
  local heading="$1"

  awk -v heading="${heading}" '
    $0 == "## " heading { in_section = 1; next }
    in_section && /^##[[:space:]]/ { exit }
    in_section { print }
  ' README.md
}

assert_readme_skill_row() {
  local skill="$1"
  local skills_section

  skills_section="$(readme_section "包含的 Skills")"

  if ! grep -Eq "^[[:space:]]*\\|[[:space:]]*\`${skill}\`[[:space:]]*\\|" <<< "${skills_section}"; then
    printf 'FAIL [README skills table]: expected Skill row for: %s\n' "${skill}" >&2
    return 1
  fi
}

assert_readme_dependency() {
  local expected="$1"
  local install_section
  local permissions_section

  install_section="$(readme_section "安装")"
  permissions_section="$(readme_section "权限和凭证")"

  if ! grep -Fq -- "${expected}" <<< "${install_section}"$'\n'"${permissions_section}"; then
    printf 'FAIL [README install/permissions]: expected dependency declaration: %s\n' "${expected}" >&2
    return 1
  fi
}

skill_file="skills/fxiaoke-crm-cli/SKILL.md"
reference_file="skills/fxiaoke-crm-cli/references/cli-reference.md"

assert_file "${skill_file}"
assert_file "${reference_file}"
assert_absent "skills/fxiaoke-crm-mcp"

assert_frontmatter_name "${skill_file}" "fxiaoke-crm-cli"
assert_shell_command "${skill_file}" "sharecrm auth status"
assert_shell_command "${skill_file}" "sharecrm data describe get"
assert_contains "safety" "${skill_file}" "explicit confirmation"

assert_markdown_heading "${reference_file}" "Signed contract amount"
assert_markdown_heading "${reference_file}" "Deal cycle"
assert_markdown_heading "${reference_file}" "Opportunity conversion"
assert_markdown_heading "${reference_file}" "Delivery volume"
assert_markdown_heading "${reference_file}" "Payment amount"

assert_readme_skill_row "fxiaoke-crm-cli"
assert_readme_dependency '`sharecrm` CLI'

echo "fxiaoke-crm-cli tests passed"
